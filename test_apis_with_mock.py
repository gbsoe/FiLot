#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script to verify API client functionality with mock data support.
"""

import asyncio
import logging
import sys
import os
from typing import Dict, List, Any, Optional

# Set environment variable to use mock data
os.environ["USE_MOCK_DATA"] = "true"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('api_test')

# Import our clients
from solpool_client import get_client as get_solpool_client
from filotsense_client import get_client as get_filotsense_client

async def test_solpool_api():
    """Test basic functionality of the SolPool API client."""
    client = get_solpool_client()
    
    try:
        # Test health check
        health = await client.check_health()
        logger.info(f"SolPool API health check: {'Healthy' if health else 'Unhealthy'}")
        
        # Get some pools
        pools = await client.fetch_pools(min_tvl=10000, min_apr=10.0)
        logger.info(f"Found {len(pools)} pools with TVL > $10,000 and APR > 10%")
        
        if pools:
            # Display some details about the first few pools
            for idx, pool in enumerate(pools[:3]):
                logger.info(f"Pool {idx+1}: {pool.get('token_a_symbol', 'Unknown')}-{pool.get('token_b_symbol', 'Unknown')}, TVL: ${pool.get('tvl', 0):,.2f}, APR: {pool.get('apr', 0):.2f}%")
            
            # Test pool detail
            if pools[0].get('id'):
                pool_id = pools[0]['id']
                logger.info(f"Fetching details for pool ID: {pool_id}")
                pool_detail = await client.fetch_pool_detail(pool_id)
                logger.info(f"Pool detail: Name={pool_detail.get('name', 'Unknown')}, TVL=${pool_detail.get('tvl', 0):,.2f}")
                
                # Test pool history
                logger.info(f"Fetching history for pool ID: {pool_id}")
                history = await client.fetch_pool_history(pool_id, days=7, interval="day")
                logger.info(f"Received {len(history)} historical data points")
                
                # Test pool forecast
                logger.info(f"Fetching forecast for pool ID: {pool_id}")
                forecast = await client.fetch_forecast(pool_id, days=7)
                if forecast and "apr_forecast" in forecast:
                    logger.info(f"Forecast summary: Expected APR change: {forecast.get('summary', {}).get('expected_apr_change', 'N/A')}%")
        
        # Test predictions
        logger.info("Fetching pool predictions with min_score=70")
        predictions = await client.fetch_predictions(min_score=70)
        logger.info(f"Found {len(predictions)} high-scoring predictions")
        if predictions:
            prediction = predictions[0]
            logger.info(f"Top prediction: {prediction.get('name', 'Unknown')}, Score: {prediction.get('prediction_score', 0)}")
        
        return True
    except Exception as e:
        logger.error(f"Error testing SolPool API: {e}")
        return False
    finally:
        await client.close()

async def test_filotsense_api():
    """Test basic functionality of the FiLotSense API client."""
    client = get_filotsense_client()
    
    try:
        # Test health check
        health = await client.check_health()
        logger.info(f"FiLotSense API health check: {'Healthy' if health else 'Unhealthy'}")
        
        # Get sentiment for popular tokens
        tokens = ["SOL", "BTC", "ETH", "BONK", "USDC"]
        logger.info(f"Fetching sentiment for tokens: {tokens}")
        sentiment = await client.fetch_sentiment_simple(tokens)
        logger.info(f"Sentiment data: {sentiment}")
        
        # Get price data
        logger.info(f"Fetching price data for tokens: {tokens}")
        prices = await client.fetch_prices_latest(tokens)
        for token, price_data in prices.items():
            logger.info(f"{token}: ${price_data.get('price_usd', 0):,.2f}, 24h change: {price_data.get('percent_change_24h', 0):.2f}%")
        
        # Get sentiment topics
        topics = await client.fetch_sentiment_topics()
        logger.info(f"Found {len(topics)} trending sentiment topics")
        for idx, topic in enumerate(topics[:3]):
            logger.info(f"Topic {idx+1}: {topic.get('title', 'Unknown')}, Sentiment: {topic.get('sentiment_score', 0):.2f}")
        
        # Get comprehensive data
        logger.info("Fetching comprehensive data for SOL")
        realdata = await client.fetch_realdata(["SOL"])
        if "SOL" in realdata:
            sol_data = realdata["SOL"]
            logger.info(f"SOL comprehensive data: Price=${sol_data.get('price', {}).get('price_usd', 0):,.2f}, Sentiment={sol_data.get('sentiment', {}).get('score', 0):.2f}")
        
        # Get token sentiment history
        logger.info("Fetching SOL sentiment history for last 7 days")
        history = await client.fetch_token_sentiment_history("SOL", days=7)
        logger.info(f"Received {len(history)} historical sentiment points")
        
        return True
    except Exception as e:
        logger.error(f"Error testing FiLotSense API: {e}")
        return False
    finally:
        await client.close()

async def main():
    """Run all API tests with mock data."""
    logger.info("===== RUNNING API TESTS WITH MOCK DATA =====")
    
    solpool_success = await test_solpool_api()
    filotsense_success = await test_filotsense_api()
    
    if solpool_success and filotsense_success:
        logger.info("✅ All API tests passed successfully!")
        return 0
    else:
        logger.error("❌ Some API tests failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)