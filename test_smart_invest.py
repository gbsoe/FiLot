"""
Test script for the smart investment feature using reinforcement learning
"""

import asyncio
import logging
import os
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

# Import our investment agent with RL capabilities
from investment_agent import InvestmentAgent
from rl_integration import get_rl_advisor

# Mock pool data for testing
MOCK_POOLS = [
    {
        'id': 'pool1',
        'token0': 'SOL',
        'token1': 'USDC',
        'apr': 35.2,
        'tvl': 1250000,
        'volume': 320000,
        'price_correlation': 0.6,
        'token0_volatility': 0.4,
        'token1_volatility': 0.05,
    },
    {
        'id': 'pool2',
        'token0': 'BTC',
        'token1': 'ETH',
        'apr': 28.7,
        'tvl': 4500000,
        'volume': 980000,
        'price_correlation': 0.85,
        'token0_volatility': 0.32,
        'token1_volatility': 0.28,
    },
    {
        'id': 'pool3',
        'token0': 'USDC',
        'token1': 'USDT',
        'apr': 12.1,
        'tvl': 8900000,
        'volume': 1200000,
        'price_correlation': 0.98,
        'token0_volatility': 0.02,
        'token1_volatility': 0.02,
    },
    {
        'id': 'pool4',
        'token0': 'SOL',
        'token1': 'BONK',
        'apr': 85.2,
        'tvl': 350000,
        'volume': 270000,
        'price_correlation': 0.4,
        'token0_volatility': 0.4,
        'token1_volatility': 0.8,
    },
    {
        'id': 'pool5',
        'token0': 'ETH',
        'token1': 'USDC',
        'apr': 25.3,
        'tvl': 2800000,
        'volume': 620000,
        'price_correlation': 0.65,
        'token0_volatility': 0.3,
        'token1_volatility': 0.05,
    }
]

async def test_rl_recommendations(user_id: int = 12345):
    """Test the RL-based investment recommendations."""
    
    logger.info("=== Starting RL Investment Recommendation Test ===")
    
    # Test with different risk profiles
    for risk_profile in ['conservative', 'moderate', 'aggressive']:
        logger.info(f"\nTesting with {risk_profile} risk profile:")
        
        # Create the agent with RL enabled
        agent = InvestmentAgent(
            user_id=user_id,
            risk_profile=risk_profile,
            use_rl=True
        )
        
        # Override the _get_pool_data method to use our mock data
        async def mock_get_pool_data():
            return MOCK_POOLS
        
        agent._get_pool_data = mock_get_pool_data
        
        # Test recommendations with different amounts
        for amount in [100, 1000, 5000]:
            logger.info(f"Testing amount: ${amount}")
            
            # Get recommendations
            recommendations = await agent.get_recommendations(amount=amount)
            
            # Check if we got RL-powered recommendations
            if recommendations.get('method') == 'reinforcement_learning':
                logger.info("✅ Successfully used RL for recommendations")
            else:
                logger.info("⚠️ Fell back to traditional recommendation method")
            
            # Print top ranked pools
            ranked_pools = recommendations.get('ranked_pools', [])
            logger.info(f"Got {len(ranked_pools)} pool recommendations")
            
            # Print top 3 or fewer if less available
            num_to_show = min(3, len(ranked_pools))
            for i, pool in enumerate(ranked_pools[:num_to_show], 1):
                token_pair = f"{pool.get('token0', 'Unknown')}-{pool.get('token1', 'Unknown')}"
                apr = pool.get('apr', 0)
                confidence = pool.get('confidence', 0) * 100  # Convert to percentage
                explanation = pool.get('explanation', 'No explanation provided')
                
                logger.info(f"  {i}. {token_pair}: {apr:.2f}% APR, {confidence:.0f}% confidence")
                logger.info(f"     Explanation: {explanation}")
            
            # Print market timing advice if available
            timing = recommendations.get('timing', {})
            if timing:
                should_enter = timing.get('should_enter', False)
                confidence = timing.get('confidence', 0) * 100  # Convert to percentage
                status = "FAVORABLE" if should_enter else "UNFAVORABLE"
                logger.info(f"Market timing: {status} ({confidence:.0f}% confidence)")
                
                # Show market conditions if available
                conditions = timing.get('market_conditions', {})
                if conditions:
                    condition_str = ", ".join([f"{k}: {v}" for k, v in conditions.items()])
                    logger.info(f"Market conditions: {condition_str}")
            
            logger.info("-" * 50)
    
    # Test the direct RL advisor API
    logger.info("\n=== Testing Direct RL Advisor API ===")
    
    try:
        # Get the RL advisor singleton
        rl_advisor = get_rl_advisor(risk_profile='moderate')
        
        # Test investment recommendations
        recommendations = await rl_advisor.get_investment_recommendations(
            pools=MOCK_POOLS,
            amount=1000.0
        )
        
        logger.info(f"Direct RL API returned {len(recommendations)} recommendations")
        
        # Test market timing
        timing = await rl_advisor.get_market_timing()
        timing_str = "FAVORABLE" if timing.get('should_enter', False) else "UNFAVORABLE"
        confidence = timing.get('confidence', 0) * 100
        
        logger.info(f"Market timing advice: {timing_str} ({confidence:.0f}% confidence)")
        
    except Exception as e:
        logger.error(f"Error testing direct RL advisor API: {e}")
    
    logger.info("\n=== Test Completed ===")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_rl_recommendations())