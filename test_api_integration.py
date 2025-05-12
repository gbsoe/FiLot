#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script to verify the integration with SolPool and FiLotSense APIs.
"""

import asyncio
import logging
import sys
from typing import Dict, Any

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
        
        # Display some details about the first few pools
        for idx, pool in enumerate(pools[:3]):
            logger.info(f"Pool {idx+1}: {pool.get('token_a_symbol', 'Unknown')}-{pool.get('token_b_symbol', 'Unknown')}, TVL: ${pool.get('tvl', 0):,.2f}, APR: {pool.get('apr', 0):.2f}%")
        
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
        sentiment = await client.fetch_sentiment_simple(["SOL", "BTC", "ETH"])
        logger.info(f"Sentiment data for popular tokens: {sentiment}")
        
        # Get some trending topics
        topics = await client.fetch_sentiment_topics()
        logger.info(f"Found {len(topics)} trending sentiment topics")
        for idx, topic in enumerate(topics[:3]):
            logger.info(f"Topic {idx+1}: {topic.get('title', 'Unknown')}, Sentiment: {topic.get('sentiment_score', 0):.2f}")
        
        return True
    except Exception as e:
        logger.error(f"Error testing FiLotSense API: {e}")
        return False
    finally:
        await client.close()

async def main():
    """Run all API tests."""
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