#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Temporary API mock data provider to use while the actual API endpoints
are being set up. This ensures the system can continue to function with
realistic data patterns.

Note: This is a stopgap solution only, and we will transition to using
the real APIs once they're properly deployed.
"""

import time
import logging
import random
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger('api_mock_data')

# ======= SolPool API Mock Data =======

def get_mock_pools(dex: Optional[str] = "Raydium", min_tvl: Optional[float] = None, 
                   min_apr: Optional[float] = None, min_prediction: Optional[float] = None) -> List[Dict[str, Any]]:
    """Generate mock pool data for testing."""
    logger.info(f"Using mock pool data. Filters: dex={dex}, min_tvl={min_tvl}, min_apr={min_apr}, min_prediction={min_prediction}")
    
    # Major token pairs commonly found in pools
    major_pairs = [("SOL", "USDC"), ("BTC", "USDC"), ("ETH", "USDC"), 
                   ("SOL", "USDT"), ("BTC", "USDT"), ("ETH", "USDT"),
                   ("RAY", "USDC"), ("BONK", "USDC"), ("JTO", "USDC"),
                   ("JUP", "USDC"), ("PYTH", "USDC"), ("MSOL", "USDC")]
    
    # Generate between 5 and 15 pools
    num_pools = random.randint(5, 15)
    pools = []
    
    for i in range(num_pools):
        # Randomly select a token pair
        token_a, token_b = random.choice(major_pairs)
        
        # Generate TVL between $10k and $50M with exponential distribution
        tvl = random.expovariate(1/1000000) * 1000000
        tvl = max(10000, min(tvl, 50000000))
        
        # Generate APR between 1% and 100% with concentration around 5-20%
        apr = random.expovariate(1/10) + 1
        apr = max(1, min(apr, 100))
        
        # Generate prediction score (0-100)
        prediction = random.randint(1, 100)
        
        # Apply filters
        if min_tvl is not None and tvl < min_tvl:
            continue
        if min_apr is not None and apr < min_apr:
            continue
        if min_prediction is not None and prediction < min_prediction:
            continue
        if dex is not None and random.random() < 0.2:  # 20% chance to be from a different DEX
            continue
            
        # Create pool with ID based on tokens
        pool_id = f"{hash(f'{token_a}{token_b}{tvl}{apr}') % 10**12:012x}"
        
        pool = {
            "id": pool_id,
            "name": f"{token_a}/{token_b}",
            "dex": dex or "Raydium",
            "category": random.choice(["Major", "DeFi", "Meme", "Gaming", "Stablecoin"]),
            "token_a_symbol": token_a,
            "token_b_symbol": token_b,
            "tvl": round(tvl, 2),
            "volume_24h": round(tvl * random.uniform(0.05, 0.5), 2),
            "apr": round(apr, 2),
            "volatility": round(random.uniform(0.01, 0.2), 2),
            "fee": 0.0025,
            "prediction_score": prediction,
            "apr_change_24h": round(random.uniform(-5, 5), 2),
            "apr_change_7d": round(random.uniform(-10, 10), 2),
            "created_at": (datetime.now() - timedelta(days=random.randint(10, 300))).isoformat(),
            "last_updated": datetime.now().isoformat()
        }
        pools.append(pool)
    
    return pools

def get_mock_pool_detail(pool_id: str) -> Dict[str, Any]:
    """Generate mock detailed data for a specific pool."""
    logger.info(f"Using mock pool detail data for pool_id: {pool_id}")
    
    # Extract token info from pool_id if possible, or use defaults
    token_a = "SOL"
    token_b = "USDC"
    
    # Generate more detailed data than the basic pool list
    tvl = random.expovariate(1/1000000) * 1000000
    tvl = max(10000, min(tvl, 50000000))
    
    apr = random.expovariate(1/10) + 1
    apr = max(1, min(apr, 100))
    
    return {
        "id": pool_id,
        "name": f"{token_a}/{token_b}",
        "dex": "Raydium",
        "category": random.choice(["Major", "DeFi", "Meme", "Gaming", "Stablecoin"]),
        "token_a_symbol": token_a,
        "token_b_symbol": token_b,
        "token_a_address": "So11111111111111111111111111111111111111112",
        "token_b_address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "tvl": round(tvl, 2),
        "volume_24h": round(tvl * random.uniform(0.05, 0.5), 2),
        "apr": round(apr, 2),
        "volatility": round(random.uniform(0.01, 0.2), 2),
        "fee": 0.0025,
        "version": "v4",
        "prediction_score": random.randint(1, 100),
        "apr_change_24h": round(random.uniform(-5, 5), 2),
        "apr_change_7d": round(random.uniform(-10, 10), 2),
        "apr_change_30d": round(random.uniform(-15, 15), 2),
        "tvl_change_24h": round(random.uniform(-3, 3), 2),
        "tvl_change_7d": round(random.uniform(-10, 10), 2),
        "tvl_change_30d": round(random.uniform(-20, 20), 2),
        "token_a_price_usd": 175.46 if token_a == "SOL" else random.uniform(0.0001, 1000),
        "token_b_price_usd": 1.0 if token_b == "USDC" else random.uniform(0.0001, 1000),
        "created_at": (datetime.now() - timedelta(days=random.randint(10, 300))).isoformat(),
        "last_updated": datetime.now().isoformat(),
        "description": f"Liquidity pool for {token_a}/{token_b} trading on Raydium",
        "risk_score": random.randint(1, 100),
        "liquidity_depth": round(tvl * 0.1, 2),
        "price_impact_1k": round(random.uniform(0.01, 0.5), 3),
        "price_impact_10k": round(random.uniform(0.1, 1.5), 3),
        "price_impact_100k": round(random.uniform(0.5, 5.0), 3),
    }

def get_mock_pool_history(pool_id: str, days: int = 30, interval: str = "day") -> List[Dict[str, Any]]:
    """Generate mock historical data for a specific pool."""
    logger.info(f"Using mock pool history data for pool_id: {pool_id}, days: {days}, interval: {interval}")
    
    history = []
    now = datetime.now()
    
    # Determine the appropriate time delta based on the interval
    if interval == "hour":
        delta = timedelta(hours=1)
        iterations = min(days * 24, 168)  # Cap at 1 week of hourly data
    elif interval == "week":
        delta = timedelta(weeks=1)
        iterations = min(days // 7, 52)  # Cap at 1 year of weekly data
    else:  # "day" (default)
        delta = timedelta(days=1)
        iterations = min(days, 365)  # Cap at 1 year of daily data
    
    # Initial values
    tvl = random.expovariate(1/1000000) * 1000000
    tvl = max(10000, min(tvl, 50000000))
    
    apr = random.expovariate(1/10) + 1
    apr = max(1, min(apr, 100))
    
    volume = tvl * random.uniform(0.05, 0.5)
    token1_price = 175.46  # SOL price
    token2_price = 1.0     # USDC price
    
    # Walk backwards from now to generate historical data with realistic trends
    for i in range(iterations):
        timestamp = now - (delta * i)
        
        # Add some random variation to each metric to create a realistic time series
        tvl_change = random.uniform(-0.05, 0.05)  # -5% to +5% daily change
        apr_change = random.uniform(-0.1, 0.1)    # -10% to +10% daily change
        volume_change = random.uniform(-0.2, 0.2)  # -20% to +20% daily change
        price1_change = random.uniform(-0.03, 0.03)  # -3% to +3% daily change
        
        # Update values with temporal consistency
        tvl = tvl * (1 + tvl_change)
        apr = apr * (1 + apr_change)
        volume = volume * (1 + volume_change)
        token1_price = token1_price * (1 + price1_change)
        
        # Ensure values stay within realistic ranges
        tvl = max(10000, min(tvl, 50000000))
        apr = max(1, min(apr, 100))
        volume = max(100, min(volume, tvl))
        token1_price = max(1, min(token1_price, 500))
        
        history.append({
            "timestamp": timestamp.isoformat(),
            "liquidity": round(tvl, 2),
            "volume": round(volume, 2),
            "apr": round(apr, 2),
            "token1_price_usd": round(token1_price, 2),
            "token2_price_usd": token2_price,
            "fees_earned": round(volume * 0.0025, 2),
            "transactions": int(volume / 1000),
            "unique_users": int(volume / 5000)
        })
    
    # Reverse so it's in chronological order
    return list(reversed(history))

def get_mock_predictions(min_score: Optional[float] = None) -> List[Dict[str, Any]]:
    """Generate mock ML-based predictions for pool performance."""
    logger.info(f"Using mock predictions data with min_score: {min_score}")
    
    # Major token pairs commonly found in pools
    major_pairs = [("SOL", "USDC"), ("BTC", "USDC"), ("ETH", "USDC"), 
                   ("SOL", "USDT"), ("BTC", "USDT"), ("ETH", "USDT"),
                   ("RAY", "USDC"), ("BONK", "USDC"), ("JTO", "USDC"),
                   ("JUP", "USDC"), ("PYTH", "USDC"), ("MSOL", "USDC")]
    
    # Generate between 3 and 10 predictions
    num_predictions = random.randint(3, 10)
    predictions = []
    
    for i in range(num_predictions):
        # Randomly select a token pair
        token_a, token_b = random.choice(major_pairs)
        
        # Generate prediction score (0-100)
        prediction_score = random.randint(1, 100)
        
        # Apply filter
        if min_score is not None and prediction_score < min_score:
            continue
            
        # Create pool with ID based on tokens
        pool_id = f"{hash(f'{token_a}{token_b}{prediction_score}') % 10**12:012x}"
        
        # Generate current metrics
        tvl = random.expovariate(1/1000000) * 1000000
        tvl = max(10000, min(tvl, 50000000))
        
        apr = random.expovariate(1/10) + 1
        apr = max(1, min(apr, 100))
        
        prediction = {
            "pool_id": pool_id,
            "name": f"{token_a}/{token_b}",
            "dex": "Raydium",
            "category": random.choice(["Major", "DeFi", "Meme", "Gaming", "Stablecoin"]),
            "current_tvl": round(tvl, 2),
            "current_apr": round(apr, 2),
            "prediction_score": prediction_score,
            "predicted_apr_range": {
                "low": round(apr * 0.9, 2),
                "mid": round(apr * (1 + (prediction_score - 50) / 100), 2),
                "high": round(apr * 1.3, 2)
            },
            "predicted_tvl_change": round((prediction_score - 50) / 10, 2),
            "confidence_interval": round(random.uniform(3, 15), 2),
            "key_factors": random.sample([
                "Strong positive APR trend",
                "Increasing liquidity",
                "High trading volume relative to TVL",
                "Popular Meme category with current market momentum",
                "Decreasing slippage",
                "Growing user base",
                "Positive token sentiment",
                "Recent protocol upgrade",
                "Decreasing impermanent loss risk",
                "High reward token valuation growth"
            ], k=random.randint(2, 4)),
            "last_updated": datetime.now().isoformat()
        }
        predictions.append(prediction)
    
    return predictions

def get_mock_forecast(pool_id: str, days: int = 7) -> Dict[str, Any]:
    """Generate mock forecast data for a specific pool."""
    logger.info(f"Using mock forecast data for pool_id: {pool_id}, days: {days}")
    
    # Initial values
    current_apr = random.uniform(5, 30)
    current_tvl = random.uniform(100000, 5000000)
    
    # Generate daily forecast data
    apr_forecast = []
    tvl_forecast = []
    
    # Create time series with realistic patterns
    for i in range(days):
        date = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
        
        # Add some randomness but maintain a trend
        trend_factor = (i / days) * 2 - 1  # -1 to 1
        
        # APR forecast with trend and noise
        apr_value = current_apr * (1 + trend_factor * 0.1 + random.uniform(-0.05, 0.05))
        apr_forecast.append({
            "date": date,
            "value": round(apr_value, 2),
            "lower_bound": round(apr_value * 0.9, 2),
            "upper_bound": round(apr_value * 1.1, 2)
        })
        
        # TVL forecast with trend and noise
        tvl_value = current_tvl * (1 + trend_factor * 0.05 + random.uniform(-0.03, 0.03))
        tvl_forecast.append({
            "date": date,
            "value": round(tvl_value, 2),
            "lower_bound": round(tvl_value * 0.95, 2),
            "upper_bound": round(tvl_value * 1.05, 2)
        })
    
    # Generate forecast summary
    forecast = {
        "pool_id": pool_id,
        "forecast_created_at": datetime.now().isoformat(),
        "forecast_days": days,
        "apr_forecast": apr_forecast,
        "tvl_forecast": tvl_forecast,
        "summary": {
            "apr_trend": random.choice(["increasing", "stable", "decreasing"]),
            "tvl_trend": random.choice(["increasing", "stable", "decreasing"]),
            "expected_apr_change": round(random.uniform(-5, 5), 2),
            "expected_tvl_change": round(random.uniform(-3, 8), 2),
            "confidence_level": random.choice(["high", "medium", "low"])
        },
        "factors": random.sample([
            "Market sentiment",
            "Token price trends",
            "Protocol events",
            "Trading volume",
            "Historical volatility",
            "Seasonal patterns",
            "Token emissions schedule",
            "Competitor analysis"
        ], k=random.randint(3, 5))
    }
    
    return forecast


# ======= FiLotSense API Mock Data =======

def get_mock_sentiment_simple(symbols: Optional[List[str]] = None) -> Dict[str, float]:
    """Generate mock sentiment data for tokens."""
    logger.info(f"Using mock sentiment data for symbols: {symbols}")
    
    # Common tokens with their base sentiment tendencies
    common_tokens = {
        "SOL": 0.7,    # Solana tends positive
        "BTC": 0.6,    # Bitcoin tends positive
        "ETH": 0.5,    # Ethereum neutral to positive
        "USDC": 0.3,   # Stablecoins more neutral
        "USDT": 0.2,
        "BONK": 0.8,   # Meme coins more volatile/positive
        "PYTH": 0.6,
        "JUP": 0.7,
        "RAY": 0.5,
        "JTO": 0.6,
        "MSOL": 0.5
    }
    
    # If no symbols provided, use all common tokens
    if not symbols:
        symbols = list(common_tokens.keys())
    
    sentiment_data = {}
    
    for symbol in symbols:
        # Get base sentiment or generate random one if not in common tokens
        base_sentiment = common_tokens.get(symbol, random.uniform(-0.3, 0.7))
        
        # Add some randomness to create variety
        sentiment = base_sentiment + random.uniform(-0.2, 0.2)
        
        # Ensure sentiment is within -1 to 1 range
        sentiment = max(-1.0, min(sentiment, 1.0))
        
        sentiment_data[symbol] = round(sentiment, 2)
    
    return sentiment_data

def get_mock_prices_latest(symbols: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """Generate mock price data for tokens."""
    logger.info(f"Using mock price data for symbols: {symbols}")
    
    # Common tokens with their base prices and volatility
    common_tokens = {
        "SOL": {"price": 175.46, "volatility": 0.05},
        "BTC": {"price": 62500.0, "volatility": 0.03},
        "ETH": {"price": 3100.0, "volatility": 0.04},
        "USDC": {"price": 1.0, "volatility": 0.001},
        "USDT": {"price": 1.0, "volatility": 0.001},
        "BONK": {"price": 0.00002234, "volatility": 0.1},
        "PYTH": {"price": 0.45, "volatility": 0.07},
        "JUP": {"price": 0.85, "volatility": 0.06},
        "RAY": {"price": 1.25, "volatility": 0.05},
        "JTO": {"price": 2.75, "volatility": 0.06},
        "MSOL": {"price": 186.0, "volatility": 0.04}
    }
    
    # If no symbols provided, use all common tokens
    if not symbols:
        symbols = list(common_tokens.keys())
    
    price_data = {}
    now = datetime.now().isoformat()
    
    for symbol in symbols:
        # Get base price info or generate random one if not in common tokens
        token_info = common_tokens.get(symbol, {"price": random.uniform(0.01, 10.0), "volatility": random.uniform(0.03, 0.1)})
        
        # Add some randomness to create variety
        price = token_info["price"] * (1 + random.uniform(-0.05, 0.05))
        percent_change = random.uniform(-token_info["volatility"] * 100 * 3, token_info["volatility"] * 100 * 3)
        volume = token_info["price"] * 10000000 * random.uniform(0.5, 2.0)
        
        price_data[symbol] = {
            "price_usd": round(price, 6) if price < 0.01 else round(price, 2),
            "percent_change_24h": round(percent_change, 2),
            "volume_24h_usd": round(volume, 2),
            "timestamp": now,
            "source": "MockDataProvider"
        }
    
    return price_data

def get_mock_sentiment_topics() -> List[Dict[str, Any]]:
    """Generate mock sentiment topics data."""
    logger.info("Using mock sentiment topics data")
    
    # List of potential topics
    topics_list = [
        {"title": "Solana Ecosystem Growth", "keywords": ["SOL", "ecosystem", "scalability"]},
        {"title": "DeFi Yield Opportunities", "keywords": ["yield", "farming", "APR"]},
        {"title": "NFT Market Trends", "keywords": ["NFT", "collections", "trading"]},
        {"title": "Bitcoin ETF Impact", "keywords": ["BTC", "ETF", "institutional"]},
        {"title": "Layer 2 Solutions", "keywords": ["L2", "scaling", "rollups"]},
        {"title": "Meme Coin Season", "keywords": ["BONK", "meme", "viral"]},
        {"title": "Regulatory Developments", "keywords": ["regulation", "SEC", "compliance"]},
        {"title": "Cross-chain Bridges", "keywords": ["bridge", "interoperability", "cross-chain"]},
        {"title": "Smart Contract Security", "keywords": ["security", "audit", "vulnerability"]},
        {"title": "Decentralized Identity", "keywords": ["identity", "DID", "verification"]}
    ]
    
    # Select 3-7 random topics
    selected_topics = random.sample(topics_list, k=random.randint(3, 7))
    
    topics = []
    
    for topic in selected_topics:
        # Generate a sentiment score between -1 and 1, with most topics being positive
        sentiment_score = random.uniform(-0.5, 1.0)
        
        # Create a topic object
        topic_obj = {
            "title": topic["title"],
            "sentiment_score": round(sentiment_score, 2),
            "keywords": topic["keywords"],
            "volume": random.randint(100, 10000),
            "sentiment_change_24h": round(random.uniform(-0.2, 0.2), 2),
            "related_tokens": random.sample(["SOL", "BTC", "ETH", "BONK", "RAY", "JUP"], k=random.randint(1, 3)),
            "sources": random.randint(5, 100)
        }
        topics.append(topic_obj)
    
    # Sort by volume (descending)
    topics.sort(key=lambda x: x["volume"], reverse=True)
    
    return topics

def get_mock_realdata(symbols: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """Generate mock comprehensive data including price, sentiment, and metrics."""
    logger.info(f"Using mock realdata for symbols: {symbols}")
    
    # Get sentiment and price data from other mock functions
    sentiment_data = get_mock_sentiment_simple(symbols)
    price_data = get_mock_prices_latest(symbols)
    
    # If no symbols provided, use the symbols from sentiment data
    if not symbols:
        symbols = list(sentiment_data.keys())
    
    real_data = {}
    now = datetime.now().isoformat()
    
    for symbol in symbols:
        if symbol not in sentiment_data or symbol not in price_data:
            continue
            
        # Generate additional metrics
        social_volume = random.randint(100, 10000)
        market_cap = price_data[symbol]["price_usd"] * random.uniform(10000000, 10000000000)
        
        real_data[symbol] = {
            "price": price_data[symbol],
            "sentiment": {
                "score": sentiment_data[symbol],
                "social_volume": social_volume,
                "bullish_signals": random.randint(1, 10),
                "bearish_signals": random.randint(1, 10),
                "major_influencers": random.randint(0, 5)
            },
            "market_data": {
                "market_cap": round(market_cap, 2),
                "rank": random.randint(1, 300),
                "circulating_supply": round(market_cap / price_data[symbol]["price_usd"], 2),
                "max_supply": round((market_cap / price_data[symbol]["price_usd"]) * random.uniform(1, 3), 2)
            },
            "technical_indicators": {
                "rsi": round(random.uniform(30, 70), 2),
                "macd": round(random.uniform(-10, 10), 2),
                "sma_50": price_data[symbol]["price_usd"] * random.uniform(0.9, 1.1),
                "sma_200": price_data[symbol]["price_usd"] * random.uniform(0.8, 1.2)
            },
            "last_updated": now
        }
    
    return real_data

def get_mock_token_sentiment_history(symbol: str, days: int = 7) -> List[Dict[str, Any]]:
    """Generate mock historical sentiment data for a specific token."""
    logger.info(f"Using mock token sentiment history for symbol: {symbol}, days: {days}")
    
    # Common tokens with their base sentiment tendencies
    common_tokens = {
        "SOL": 0.7,    # Solana tends positive
        "BTC": 0.6,    # Bitcoin tends positive
        "ETH": 0.5,    # Ethereum neutral to positive
        "USDC": 0.3,   # Stablecoins more neutral
        "USDT": 0.2,
        "BONK": 0.8,   # Meme coins more volatile/positive
        "PYTH": 0.6,
        "JUP": 0.7,
        "RAY": 0.5,
        "JTO": 0.6,
        "MSOL": 0.5
    }
    
    # Get base sentiment or use a default
    base_sentiment = common_tokens.get(symbol, 0.5)
    
    # Generate historical data with realistic patterns
    history = []
    now = datetime.now()
    
    # Random trend direction for more realistic data
    trend = random.uniform(-0.01, 0.01)
    
    for i in range(days):
        timestamp = (now - timedelta(days=i)).isoformat()
        
        # Create a realistic sentiment time series with some trend and volatility
        day_sentiment = base_sentiment + (trend * i) + random.uniform(-0.2, 0.2)
        # Ensure it stays within -1 to 1
        day_sentiment = max(-1.0, min(day_sentiment, 1.0))
        
        # Generate social volume with realistic pattern (higher on some days)
        weekday = (now - timedelta(days=i)).weekday()
        # More activity on weekdays
        volume_factor = 1.0 if weekday < 5 else 0.7
        social_volume = int(random.uniform(500, 5000) * volume_factor)
        
        history.append({
            "timestamp": timestamp,
            "sentiment_score": round(day_sentiment, 2),
            "social_volume": social_volume,
            "bullish_signals": round(day_sentiment * 10) if day_sentiment > 0 else 0,
            "bearish_signals": round(-day_sentiment * 10) if day_sentiment < 0 else 0,
            "news_sentiment": round(day_sentiment + random.uniform(-0.3, 0.3), 2),
            "social_sentiment": round(day_sentiment + random.uniform(-0.4, 0.4), 2)
        })
    
    # Reverse the list so it's in chronological order
    return list(reversed(history))