#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Monitoring Agent for the Telegram cryptocurrency pool bot
Periodically monitors active positions for exit conditions
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Union
import json

# Import local modules
from models import User, Pool, Position, CompositeSignal, PositionStatus, db
from solpool_client import get_client as get_solpool_client
from filotsense_client import get_client as get_filotsense_client
from raydium_client import get_client as get_raydium_client
from execution_agent import ExecutionAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class MonitoringAgent:
    """Agent responsible for monitoring positions and detecting exit conditions"""
    
    def __init__(self):
        """Initialize the monitoring agent"""
        # Default thresholds
        self.default_thresholds = {
            "apr_drop_percentage": 0.3,  # Exit if APR drops by 30%
            "sentiment_threshold": -0.2,  # Exit if sentiment drops below -0.2
            "impermanent_loss_threshold": 0.05  # Exit if impermanent loss exceeds 5%
        }
        
        # In-memory cache of alerts sent to avoid duplicates
        self.sent_alerts = {}
        
        # Initialize execution agent for building exit transactions
        self.execution_agent = ExecutionAgent()
        
    async def evaluate_positions(self) -> List[Dict[str, Any]]:
        """
        Evaluate all active positions for exit conditions
        
        Returns:
            List of positions that need exit transactions
        """
        try:
            # Get all active positions
            active_positions = db.session.query(Position).filter(
                Position.status.in_([PositionStatus.ACTIVE.value, PositionStatus.MONITORED.value])
            ).all()
            
            if not active_positions:
                logger.info("No active positions to monitor")
                return []
                
            logger.info(f"Evaluating {len(active_positions)} active positions")
            
            # Get all unique pool IDs from positions
            pool_ids = list(set(p.pool_id for p in active_positions))
            
            # Fetch current data for all these pools
            pools_data = await self._fetch_pools_data(pool_ids)
            
            # Calculate latest signals for these pools
            signals_data = await self._calculate_signals(pool_ids)
            
            # Evaluate each position
            positions_to_exit = []
            
            for position in active_positions:
                exit_recommended, exit_reason = await self._evaluate_position(
                    position, pools_data.get(position.pool_id, {}), signals_data.get(position.pool_id, {})
                )
                
                if exit_recommended:
                    # Update position status to monitored if not already
                    if position.status != PositionStatus.MONITORED.value:
                        position.status = PositionStatus.MONITORED.value
                        position.updated_at = datetime.now()
                        db.session.commit()
                    
                    positions_to_exit.append({
                        "position_id": position.id,
                        "user_id": position.user_id,
                        "pool_id": position.pool_id,
                        "exit_reason": exit_reason
                    })
                    
            return positions_to_exit
            
        except Exception as e:
            logger.error(f"Error evaluating positions: {e}")
            return []
            
    async def _fetch_pools_data(self, pool_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch current data for multiple pools
        
        Args:
            pool_ids: List of pool IDs to fetch data for
            
        Returns:
            Dictionary mapping pool IDs to their data
        """
        try:
            raydium_client = get_raydium_client()
            
            pools_data = {}
            for pool_id in pool_ids:
                try:
                    # First try to get from database
                    pool = db.session.query(Pool).filter(Pool.id == pool_id).first()
                    
                    # If pool is found and was updated within the last hour, use it
                    if pool and pool.last_updated > datetime.now() - timedelta(hours=1):
                        pools_data[pool_id] = {
                            "id": pool.id,
                            "token_a": pool.token_a_symbol,
                            "token_b": pool.token_b_symbol,
                            "token_a_price": pool.token_a_price,
                            "token_b_price": pool.token_b_price,
                            "apr": pool.apr_24h,
                            "tvl": pool.tvl,
                            "fee": pool.fee,
                            "volume_24h": pool.volume_24h,
                            "last_updated": pool.last_updated
                        }
                    else:
                        # Otherwise fetch from API
                        pool_data = await raydium_client.get_pool_by_id(pool_id)
                        
                        if pool_data and pool_data.get("success", False) != False:
                            # Format API data
                            token_a_symbol = pool_data.get("tokenA", {}).get("symbol", "Unknown")
                            token_b_symbol = pool_data.get("tokenB", {}).get("symbol", "Unknown")
                            
                            pools_data[pool_id] = {
                                "id": pool_id,
                                "token_a": token_a_symbol,
                                "token_b": token_b_symbol,
                                "token_a_price": pool_data.get("tokenPrices", {}).get(token_a_symbol, 0.0),
                                "token_b_price": pool_data.get("tokenPrices", {}).get(token_b_symbol, 0.0),
                                "apr": pool_data.get("apr", 0.0),
                                "tvl": pool_data.get("tvl", 0.0),
                                "fee": pool_data.get("fee", 0.0),
                                "volume_24h": pool_data.get("volumeUsd24h", 0.0),
                                "last_updated": datetime.now()
                            }
                            
                            # Update database with latest data
                            if pool:
                                pool.token_a_price = pools_data[pool_id]["token_a_price"]
                                pool.token_b_price = pools_data[pool_id]["token_b_price"]
                                pool.apr_24h = pools_data[pool_id]["apr"]
                                pool.tvl = pools_data[pool_id]["tvl"]
                                pool.volume_24h = pools_data[pool_id]["volume_24h"]
                                pool.last_updated = datetime.now()
                                db.session.commit()
                            
                except Exception as e:
                    logger.error(f"Error fetching data for pool {pool_id}: {e}")
                    # If we already have a pool object, use whatever data we have
                    if "pool" in locals() and pool:
                        pools_data[pool_id] = {
                            "id": pool.id,
                            "token_a": pool.token_a_symbol,
                            "token_b": pool.token_b_symbol,
                            "token_a_price": pool.token_a_price,
                            "token_b_price": pool.token_b_price,
                            "apr": pool.apr_24h,
                            "tvl": pool.tvl,
                            "fee": pool.fee,
                            "volume_24h": pool.volume_24h,
                            "last_updated": pool.last_updated
                        }
            
            return pools_data
            
        except Exception as e:
            logger.error(f"Error fetching pools data: {e}")
            return {}
            
    async def _calculate_signals(self, pool_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Calculate latest signals for pools
        
        Args:
            pool_ids: List of pool IDs to calculate signals for
            
        Returns:
            Dictionary mapping pool IDs to their signal data
        """
        try:
            # Get pools from database
            pools = db.session.query(Pool).filter(Pool.id.in_(pool_ids)).all()
            
            if not pools:
                logger.warning(f"No pools found for IDs: {pool_ids}")
                return {}
                
            # Extract token symbols
            token_symbols = []
            for pool in pools:
                if pool.token_a_symbol not in token_symbols:
                    token_symbols.append(pool.token_a_symbol)
                if pool.token_b_symbol not in token_symbols:
                    token_symbols.append(pool.token_b_symbol)
            
            # Fetch sentiment
            filotsense_client = get_filotsense_client()
            sentiment = await filotsense_client.fetch_sentiment_simple(token_symbols)
            
            # Fetch SolPool predictions
            solpool_client = get_solpool_client()
            predictions = await solpool_client.fetch_predictions()
            
            # Format predictions by pool ID
            predictions_by_pool = {}
            for prediction in predictions:
                pool_id = prediction.get("pool_id")
                score = prediction.get("score", 0.5)
                
                if pool_id:
                    predictions_by_pool[pool_id] = score
            
            # Calculate signals
            signals_data = {}
            for pool in pools:
                # Get prediction score
                sol_score = predictions_by_pool.get(pool.id, 0.5)
                
                # Get sentiment scores
                token_a_sentiment = sentiment.get(pool.token_a_symbol, 0.0)
                token_b_sentiment = sentiment.get(pool.token_b_symbol, 0.0)
                
                # Average the sentiment scores
                sentiment_score = (token_a_sentiment + token_b_sentiment) / 2
                
                # Store signal
                signals_data[pool.id] = {
                    "sol_score": sol_score,
                    "sentiment_score": sentiment_score,
                    "timestamp": datetime.now()
                }
                
                # Create and store in database
                signal = CompositeSignal(
                    pool_id=pool.id,
                    sol_score=sol_score,
                    sentiment_score=sentiment_score,
                    profile_high=0.0,  # Calculate if needed
                    profile_stable=0.0  # Calculate if needed
                )
                
                db.session.add(signal)
                
            db.session.commit()
            
            return signals_data
            
        except Exception as e:
            logger.error(f"Error calculating signals: {e}")
            return {}
            
    async def _evaluate_position(
        self,
        position: Position,
        pool_data: Dict[str, Any],
        signal_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluate a position for exit conditions
        
        Args:
            position: Position to evaluate
            pool_data: Current data for the pool
            signal_data: Current signals for the pool
            
        Returns:
            Tuple of (exit_recommended, exit_reason)
        """
        try:
            # Skip if we don't have pool data
            if not pool_data:
                logger.warning(f"No pool data for position {position.id}")
                return False, None
                
            # Skip if we don't have signal data
            if not signal_data:
                logger.warning(f"No signal data for position {position.id}")
                return False, None
                
            # Get initial signal if available
            initial_signal = None
            if position.initial_composite_signal_id:
                initial_signal = db.session.query(CompositeSignal).filter(
                    CompositeSignal.id == position.initial_composite_signal_id
                ).first()
                
            # Check APR drop
            current_apr = pool_data.get("apr", 0.0)
            initial_apr = position.current_apr
            
            apr_drop_threshold = position.exit_threshold_apr or self.default_thresholds["apr_drop_percentage"]
            
            if initial_apr > 0 and current_apr < initial_apr * (1 - apr_drop_threshold):
                return True, f"APR dropped from {initial_apr:.2f}% to {current_apr:.2f}%"
                
            # Check sentiment drop
            current_sentiment = signal_data.get("sentiment_score", 0.0)
            sentiment_threshold = position.exit_threshold_sentiment or self.default_thresholds["sentiment_threshold"]
            
            if current_sentiment < sentiment_threshold:
                return True, f"Sentiment dropped to {current_sentiment:.2f}"
                
            # Check impermanent loss
            if pool_data.get("token_a_price", 0) > 0 and pool_data.get("token_b_price", 0) > 0:
                # Update position metrics
                token_a_initial_value = position.token_a_amount * position.position_metadata.get("initial_token_a_price", pool_data.get("token_a_price", 0))
                token_b_initial_value = position.token_b_amount * position.position_metadata.get("initial_token_b_price", pool_data.get("token_b_price", 0))
                
                token_a_current_value = position.token_a_amount * pool_data.get("token_a_price", 0)
                token_b_current_value = position.token_b_amount * pool_data.get("token_b_price", 0)
                
                # Calculate current position value
                current_value = token_a_current_value + token_b_current_value
                
                # Calculate value if held separately
                initial_total = token_a_initial_value + token_b_initial_value
                held_separately_value = (initial_total / 2) * (
                    pool_data.get("token_a_price", 0) / position.position_metadata.get("initial_token_a_price", pool_data.get("token_a_price", 0)) +
                    pool_data.get("token_b_price", 0) / position.position_metadata.get("initial_token_b_price", pool_data.get("token_b_price", 0))
                )
                
                # Calculate impermanent loss
                impermanent_loss = (current_value - held_separately_value) / held_separately_value
                
                # Update position
                position.current_value_usd = current_value
                position.impermanent_loss = impermanent_loss
                position.current_apr = current_apr
                position.updated_at = datetime.now()
                db.session.commit()
                
                # Check if impermanent loss exceeds threshold
                impermanent_loss_threshold = self.default_thresholds["impermanent_loss_threshold"]
                
                if impermanent_loss < -impermanent_loss_threshold:
                    return True, f"Impermanent loss of {impermanent_loss:.2%} exceeds threshold"
            
            # No exit conditions met
            return False, None
            
        except Exception as e:
            logger.error(f"Error evaluating position {position.id}: {e}")
            return False, None
            
    async def build_exit_transactions(self, positions_to_exit: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Build exit transactions for positions meeting exit conditions
        
        Args:
            positions_to_exit: List of positions to build exit transactions for
            
        Returns:
            List of built transactions
        """
        exit_transactions = []
        
        for position_data in positions_to_exit:
            try:
                # Build exit transaction
                exit_tx = await self.execution_agent.build_exit_tx(
                    position_data["user_id"],
                    position_data["position_id"]
                )
                
                if exit_tx.get("success", False):
                    exit_transactions.append({
                        **position_data,
                        "transaction": exit_tx
                    })
                    
                    # Add this position to sent alerts to avoid duplicates
                    alert_key = f"{position_data['user_id']}_{position_data['position_id']}"
                    self.sent_alerts[alert_key] = datetime.now()
                    
            except Exception as e:
                logger.error(f"Error building exit transaction for position {position_data['position_id']}: {e}")
        
        return exit_transactions
        
    def should_send_alert(self, user_id: int, position_id: int) -> bool:
        """
        Check if an alert should be sent for this position
        
        Args:
            user_id: Telegram user ID
            position_id: Position ID
            
        Returns:
            True if an alert should be sent, False otherwise
        """
        alert_key = f"{user_id}_{position_id}"
        
        # If no alert was sent yet for this position, send one
        if alert_key not in self.sent_alerts:
            return True
            
        # If an alert was sent recently, don't send another one
        last_alert = self.sent_alerts[alert_key]
        if datetime.now() - last_alert < timedelta(hours=12):
            return False
            
        # Otherwise, send a reminder
        return True