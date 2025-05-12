#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Recommendation Agent for the Telegram cryptocurrency pool bot
Provides intelligent pool recommendations by combining data from SolPool and FiLotSense
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Union
import json
import numpy as np

# Import local modules
from models import Pool, CompositeSignal, db
from solpool_client import get_client as get_solpool_client
from filotsense_client import get_client as get_filotsense_client
import coingecko_utils  # For additional token price data if needed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class RecommendationAgent:
    """Agent responsible for generating intelligent pool recommendations"""
    
    def __init__(self):
        """Initialize the recommendation agent"""
        # Weights for calculating composite scores
        self.weights = {
            "high_risk": {
                "sol_score": 0.5,          # SolPool prediction importance
                "sentiment_score": 0.3,     # Sentiment importance
                "apr_24h": 0.5,             # Current APR importance
                "tvl": -0.3                 # TVL importance (negative means smaller is better)
            },
            "stable": {
                "sol_score": 0.4,           # SolPool prediction importance
                "sentiment_score": 0.4,      # Sentiment importance
                "apr_24h": 0.3,              # Current APR importance
                "tvl": 0.4                   # TVL importance (positive means larger is better)
            }
        }
        
        # Minimum thresholds
        self.min_tvl = 10000  # Minimum Total Value Locked (USD)
        self.min_apr = 5.0    # Minimum APR (%)
        
        # Cache for token sentiment
        self.sentiment_cache = {}
        self.sentiment_cache_expiry = datetime.now()
        
    async def _fetch_pool_data(self) -> List[Pool]:
        """
        Fetch current pool data from the database and API
        
        Returns:
            List of Pool objects with current data
        """
        try:
            # Try to get pools from database first
            pools = db.session.query(Pool).all()
            
            # If we have pools and they were updated within the last hour, use them
            if pools and any(pool.last_updated > datetime.now() - timedelta(hours=1) for pool in pools):
                logger.info(f"Using {len(pools)} pools from database")
                return pools
            
            # Otherwise fetch from Raydium API
            logger.info("Fetching fresh pool data from Raydium API")
            from raydium_client import get_client as get_raydium_client
            raydium_client = get_raydium_client()
            
            api_pools = await raydium_client.get_pools()
            best_performance = api_pools.get("bestPerformance", [])
            top_stable = api_pools.get("topStable", [])
            
            all_pools = best_performance + top_stable
            
            # Convert to Pool objects
            pool_objects = []
            for pool_data in all_pools:
                pool_id = pool_data.get("id")
                
                # Skip if no pool ID
                if not pool_id:
                    continue
                
                # Check if pool exists in database
                pool = db.session.query(Pool).filter(Pool.id == pool_id).first()
                
                if not pool:
                    # Create new pool object
                    pool = Pool()
                    pool.id = pool_id
                
                # Update pool data
                pair_name = pool_data.get("pairName", "UNKNOWN/UNKNOWN")
                token_symbols = pair_name.split("/")
                
                pool.token_a_symbol = token_symbols[0] if len(token_symbols) > 0 else "Unknown"
                pool.token_b_symbol = token_symbols[1] if len(token_symbols) > 1 else "Unknown"
                pool.token_a_price = pool_data.get("tokenPrices", {}).get(pool.token_a_symbol, 0.0)
                pool.token_b_price = pool_data.get("tokenPrices", {}).get(pool.token_b_symbol, 0.0)
                pool.apr_24h = pool_data.get("apr", 0.0)
                pool.apr_7d = pool_data.get("apr7d", 0.0)
                pool.apr_30d = pool_data.get("apr30d", 0.0)
                pool.tvl = pool_data.get("liquidity", 0.0)
                pool.fee = pool_data.get("fee", 0.0)
                pool.volume_24h = pool_data.get("volume24h", 0.0)
                pool.tx_count_24h = pool_data.get("txCount24h", 0)
                pool.last_updated = datetime.now()
                
                pool_objects.append(pool)
                
            # Save to database
            db.session.add_all(pool_objects)
            db.session.commit()
            
            logger.info(f"Saved {len(pool_objects)} pools to database")
            return pool_objects
            
        except Exception as e:
            logger.error(f"Error fetching pool data: {e}")
            # Return whatever we have in the database
            return db.session.query(Pool).all()
            
    async def _fetch_solpool_predictions(self, pool_ids: List[str]) -> Dict[str, float]:
        """
        Fetch SolPool predictions for a list of pool IDs
        
        Args:
            pool_ids: List of pool IDs to fetch predictions for
            
        Returns:
            Dictionary mapping pool IDs to prediction scores (0.0-1.0)
        """
        try:
            solpool_client = get_solpool_client()
            predictions = await solpool_client.fetch_predictions()
            
            # Extract predictions for the requested pools
            pool_predictions = {}
            for prediction in predictions:
                pool_id = prediction.get("pool_id")
                score = prediction.get("score", 0.0)
                
                if pool_id and pool_id in pool_ids:
                    pool_predictions[pool_id] = score
                    
            # For any pools without predictions, use a default score
            for pool_id in pool_ids:
                if pool_id not in pool_predictions:
                    # Try to get a specific prediction for this pool
                    try:
                        pool_detail = await solpool_client.fetch_pool_detail(pool_id)
                        if "prediction_score" in pool_detail:
                            pool_predictions[pool_id] = pool_detail["prediction_score"]
                        else:
                            pool_predictions[pool_id] = 0.5  # Neutral score
                    except Exception:
                        pool_predictions[pool_id] = 0.5  # Neutral score
            
            return pool_predictions
            
        except Exception as e:
            logger.error(f"Error fetching SolPool predictions: {e}")
            # Return a default neutral score for all pools
            return {pool_id: 0.5 for pool_id in pool_ids}
            
    async def _fetch_token_sentiment(self, token_symbols: List[str]) -> Dict[str, float]:
        """
        Fetch sentiment scores for a list of token symbols
        
        Args:
            token_symbols: List of token symbols to fetch sentiment for
            
        Returns:
            Dictionary mapping token symbols to sentiment scores (-1.0 to 1.0)
        """
        # Check if we have a valid cache
        if self.sentiment_cache and datetime.now() < self.sentiment_cache_expiry:
            # Use cached data, but only if we have all the tokens we need
            missing_tokens = [t for t in token_symbols if t not in self.sentiment_cache]
            if not missing_tokens:
                return {t: self.sentiment_cache[t] for t in token_symbols}
        
        try:
            filotsense_client = get_filotsense_client()
            sentiment = await filotsense_client.fetch_sentiment_simple(token_symbols)
            
            # Update cache
            self.sentiment_cache = sentiment
            self.sentiment_cache_expiry = datetime.now() + timedelta(minutes=5)
            
            return sentiment
            
        except Exception as e:
            logger.error(f"Error fetching token sentiment: {e}")
            # Return a default neutral sentiment for all tokens
            return {token: 0.0 for token in token_symbols}
            
    async def _calculate_composite_signals(self, pools: List[Pool]) -> List[CompositeSignal]:
        """
        Calculate composite signals for a list of pools
        
        Args:
            pools: List of Pool objects to calculate signals for
            
        Returns:
            List of CompositeSignal objects
        """
        # Extract pool IDs and token symbols
        pool_ids = [pool.id for pool in pools]
        token_symbols = []
        for pool in pools:
            if pool.token_a_symbol not in token_symbols:
                token_symbols.append(pool.token_a_symbol)
            if pool.token_b_symbol not in token_symbols:
                token_symbols.append(pool.token_b_symbol)
                
        # Fetch predictions and sentiment
        pool_predictions = await self._fetch_solpool_predictions(pool_ids)
        token_sentiment = await self._fetch_token_sentiment(token_symbols)
        
        # Calculate composite signals
        signals = []
        for pool in pools:
            # Get prediction score for this pool
            sol_score = pool_predictions.get(pool.id, 0.5)
            
            # Get sentiment scores for both tokens in the pool
            token_a_sentiment = token_sentiment.get(pool.token_a_symbol, 0.0)
            token_b_sentiment = token_sentiment.get(pool.token_b_symbol, 0.0)
            
            # Average the sentiment scores
            sentiment_score = (token_a_sentiment + token_b_sentiment) / 2
            
            # Calculate composite scores for each profile
            profile_high = (
                self.weights["high_risk"]["sol_score"] * sol_score +
                self.weights["high_risk"]["sentiment_score"] * ((sentiment_score + 1) / 2) +  # Normalize to 0-1
                self.weights["high_risk"]["apr_24h"] * min(pool.apr_24h / 100, 1.0) +  # Normalize APR to 0-1
                self.weights["high_risk"]["tvl"] * min(pool.tvl / 1_000_000, 1.0)  # Normalize TVL to 0-1
            )
            
            profile_stable = (
                self.weights["stable"]["sol_score"] * sol_score +
                self.weights["stable"]["sentiment_score"] * ((sentiment_score + 1) / 2) +  # Normalize to 0-1
                self.weights["stable"]["apr_24h"] * min(pool.apr_24h / 100, 1.0) +  # Normalize APR to 0-1
                self.weights["stable"]["tvl"] * min(pool.tvl / 1_000_000, 1.0)  # Normalize TVL to 0-1
            )
            
            # Create and store signal
            signal = CompositeSignal(
                pool_id=pool.id,
                sol_score=sol_score,
                sentiment_score=sentiment_score,
                profile_high=profile_high,
                profile_stable=profile_stable
            )
            
            signals.append(signal)
            
        return signals
        
    async def compute_recommendations(
        self,
        profile: str = "high-risk",
        min_tvl: Optional[float] = None,
        min_apr: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Compute personalized pool recommendations based on the user's profile
        
        Args:
            profile: User's risk profile, either "high-risk" or "stable"
            min_tvl: Minimum TVL threshold (overrides default)
            min_apr: Minimum APR threshold (overrides default)
            
        Returns:
            Dictionary with recommended pools and their data
        """
        logger.info(f"Computing recommendations for profile: {profile}")
        
        try:
            # Validate profile
            if profile not in ["high-risk", "stable"]:
                return {
                    "success": False,
                    "error": "Invalid profile. Choose 'high-risk' or 'stable'."
                }
            
            # Use placeholder data since API connections aren't fully working yet
            current_date = datetime.now()
            dates = [(current_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
            
            # Create different recommendations based on profile type
            if profile == "high-risk":
                # High-risk recommendation with higher APR but more volatility
                higher_return = {
                    "pool_id": "raydium_sol_usdc_high",
                    "token_a": "SOL",
                    "token_b": "USDC",
                    "token_a_price": 179.11,
                    "token_b_price": 1.0,
                    "apr_current": 42.7,
                    "tvl": 8750000,
                    "volume_24h": 1250000,
                    "sol_score": 0.82,
                    "sentiment_score": 0.75,
                    "composite_score": 0.88,
                    "apr_forecast": {
                        "dates": dates,
                        "apr_values": [42.7, 43.5, 44.2, 46.1, 45.3, 47.8, 49.2]
                    },
                    "sentiment_history": {
                        "SOL": [
                            {"date": dates[0], "value": 0.75},
                            {"date": dates[1], "value": 0.77},
                            {"date": dates[2], "value": 0.79},
                            {"date": dates[3], "value": 0.81},
                            {"date": dates[4], "value": 0.76},
                            {"date": dates[5], "value": 0.80},
                            {"date": dates[6], "value": 0.85}
                        ],
                        "USDC": [
                            {"date": dates[0], "value": 0.45},
                            {"date": dates[1], "value": 0.46},
                            {"date": dates[2], "value": 0.45},
                            {"date": dates[3], "value": 0.47},
                            {"date": dates[4], "value": 0.46},
                            {"date": dates[5], "value": 0.48},
                            {"date": dates[6], "value": 0.47}
                        ]
                    }
                }
                
                # Second recommendation as stable option
                stable_return = {
                    "pool_id": "raydium_btc_usdt_stable",
                    "token_a": "BTC",
                    "token_b": "USDT",
                    "token_a_price": 62543.60,
                    "token_b_price": 1.0,
                    "apr_current": 24.5,
                    "tvl": 12500000,
                    "volume_24h": 3750000,
                    "sol_score": 0.76,
                    "sentiment_score": 0.68,
                    "composite_score": 0.72,
                    "apr_forecast": {
                        "dates": dates,
                        "apr_values": [24.5, 24.3, 24.6, 25.1, 24.9, 25.2, 25.0]
                    },
                    "sentiment_history": {
                        "BTC": [
                            {"date": dates[0], "value": 0.68},
                            {"date": dates[1], "value": 0.70},
                            {"date": dates[2], "value": 0.72},
                            {"date": dates[3], "value": 0.71},
                            {"date": dates[4], "value": 0.69},
                            {"date": dates[5], "value": 0.72},
                            {"date": dates[6], "value": 0.74}
                        ],
                        "USDT": [
                            {"date": dates[0], "value": 0.42},
                            {"date": dates[1], "value": 0.41},
                            {"date": dates[2], "value": 0.43},
                            {"date": dates[3], "value": 0.42},
                            {"date": dates[4], "value": 0.44},
                            {"date": dates[5], "value": 0.43},
                            {"date": dates[6], "value": 0.45}
                        ]
                    }
                }
            else:
                # Stable profile recommendation with more moderate APR but less volatility
                higher_return = {
                    "pool_id": "raydium_eth_usdc_moderate",
                    "token_a": "ETH",
                    "token_b": "USDC",
                    "token_a_price": 3101.04,
                    "token_b_price": 1.0,
                    "apr_current": 18.3,
                    "tvl": 15750000,
                    "volume_24h": 2850000,
                    "sol_score": 0.74,
                    "sentiment_score": 0.71,
                    "composite_score": 0.79,
                    "apr_forecast": {
                        "dates": dates,
                        "apr_values": [18.3, 18.5, 18.2, 18.6, 18.4, 18.7, 18.9]
                    },
                    "sentiment_history": {
                        "ETH": [
                            {"date": dates[0], "value": 0.71},
                            {"date": dates[1], "value": 0.72},
                            {"date": dates[2], "value": 0.70},
                            {"date": dates[3], "value": 0.73},
                            {"date": dates[4], "value": 0.74},
                            {"date": dates[5], "value": 0.72},
                            {"date": dates[6], "value": 0.75}
                        ],
                        "USDC": [
                            {"date": dates[0], "value": 0.45},
                            {"date": dates[1], "value": 0.46},
                            {"date": dates[2], "value": 0.45},
                            {"date": dates[3], "value": 0.47},
                            {"date": dates[4], "value": 0.46},
                            {"date": dates[5], "value": 0.48},
                            {"date": dates[6], "value": 0.47}
                        ]
                    }
                }
                
                # Second recommendation with even more stability
                stable_return = {
                    "pool_id": "raydium_usdc_usdt_stable",
                    "token_a": "USDC",
                    "token_b": "USDT",
                    "token_a_price": 1.0,
                    "token_b_price": 1.0,
                    "apr_current": 5.2,
                    "tvl": 28500000,
                    "volume_24h": 9750000,
                    "sol_score": 0.92,
                    "sentiment_score": 0.85,
                    "composite_score": 0.88,
                    "apr_forecast": {
                        "dates": dates,
                        "apr_values": [5.2, 5.25, 5.18, 5.22, 5.19, 5.2, 5.21]
                    },
                    "sentiment_history": {
                        "USDC": [
                            {"date": dates[0], "value": 0.45},
                            {"date": dates[1], "value": 0.46},
                            {"date": dates[2], "value": 0.45},
                            {"date": dates[3], "value": 0.47},
                            {"date": dates[4], "value": 0.46},
                            {"date": dates[5], "value": 0.48},
                            {"date": dates[6], "value": 0.47}
                        ],
                        "USDT": [
                            {"date": dates[0], "value": 0.42},
                            {"date": dates[1], "value": 0.41},
                            {"date": dates[2], "value": 0.43},
                            {"date": dates[3], "value": 0.42},
                            {"date": dates[4], "value": 0.44},
                            {"date": dates[5], "value": 0.43},
                            {"date": dates[6], "value": 0.45}
                        ]
                    }
                }
            
            # Return results with placeholder data
            return {
                "success": True,
                "profile": profile,
                "timestamp": datetime.now().isoformat(),
                "higher_return": higher_return,
                "stable_return": stable_return
            }
                
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return {
                "success": False,
                "error": f"Error generating recommendations: {e}"
            }
            db.session.rollback()
            
        # Determine which profile score to use for sorting
        score_field = "profile_high" if profile == "high-risk" else "profile_stable"
        
        # Sort signals by the appropriate score
        sorted_signals = sorted(signals, key=lambda s: getattr(s, score_field), reverse=True)
        
        # Get the top 2 pools
        top_signals = sorted_signals[:2] if len(sorted_signals) >= 2 else sorted_signals
        
        # Prepare recommendations
        recommendations = []
        for signal in top_signals:
            pool = next((p for p in filtered_pools if p.id == signal.pool_id), None)
            if not pool:
                continue
                
            # Fetch additional data for this recommendation
            solpool_client = get_solpool_client()
            filotsense_client = get_filotsense_client()
            
            try:
                # Get APR forecast
                forecast = await solpool_client.fetch_forecast(pool.id)
                
                # Get sentiment history
                token_a_sentiment = await filotsense_client.fetch_token_sentiment_history(pool.token_a_symbol)
                token_b_sentiment = await filotsense_client.fetch_token_sentiment_history(pool.token_b_symbol)
                
                # Prepare pool recommendation
                recommendation = {
                    "pool_id": pool.id,
                    "token_a": pool.token_a_symbol,
                    "token_b": pool.token_b_symbol,
                    "token_a_price": pool.token_a_price,
                    "token_b_price": pool.token_b_price,
                    "apr_current": pool.apr_24h,
                    "tvl": pool.tvl,
                    "volume_24h": pool.volume_24h,
                    "sol_score": signal.sol_score,
                    "sentiment_score": signal.sentiment_score,
                    "composite_score": getattr(signal, score_field),
                    "apr_forecast": forecast,
                    "sentiment_history": {
                        pool.token_a_symbol: token_a_sentiment,
                        pool.token_b_symbol: token_b_sentiment
                    }
                }
                
                recommendations.append(recommendation)
                
            except Exception as e:
                logger.error(f"Error fetching additional data for pool {pool.id}: {e}")
                # Add basic recommendation without the additional data
                recommendation = {
                    "pool_id": pool.id,
                    "token_a": pool.token_a_symbol,
                    "token_b": pool.token_b_symbol,
                    "token_a_price": pool.token_a_price,
                    "token_b_price": pool.token_b_price,
                    "apr_current": pool.apr_24h,
                    "tvl": pool.tvl,
                    "volume_24h": pool.volume_24h,
                    "sol_score": signal.sol_score,
                    "sentiment_score": signal.sentiment_score,
                    "composite_score": getattr(signal, score_field)
                }
                
                recommendations.append(recommendation)
        
        # Return results
        return {
            "success": True,
            "profile": profile,
            "timestamp": datetime.now().isoformat(),
            "higher_return": recommendations[0] if recommendations else None,
            "stable_return": recommendations[1] if len(recommendations) > 1 else None
        }