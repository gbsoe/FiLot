"""
Simple demonstration of RL-based investment recommendations
"""

import asyncio
import logging
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

# Sample pool data for testing
SAMPLE_POOLS = [
    {
        'id': 'pool1',
        'token0': 'SOL',
        'token1': 'USDC',
        'apr': 35.2,
        'tvl': 1250000,
        'volume': 320000,
    },
    {
        'id': 'pool2',
        'token0': 'BTC',
        'token1': 'ETH',
        'apr': 28.7, 
        'tvl': 4500000,
        'volume': 980000,
    },
    {
        'id': 'pool3',
        'token0': 'USDC',
        'token1': 'USDT',
        'apr': 12.1,
        'tvl': 8900000,
        'volume': 1200000,
    },
    {
        'id': 'pool4',
        'token0': 'SOL',
        'token1': 'BONK',
        'apr': 85.2,
        'tvl': 350000,
        'volume': 270000,
    },
    {
        'id': 'pool5',
        'token0': 'ETH',
        'token1': 'USDC',
        'apr': 25.3,
        'tvl': 2800000,
        'volume': 620000,
    }
]

async def test_reinforcement_learning():
    """Test the RL-based investment recommendations"""
    try:
        # Import RL integration
        from rl_integration import RLInvestmentAdvisor
        
        # Create advisors for different risk profiles
        profiles = ['conservative', 'moderate', 'aggressive']
        
        for profile in profiles:
            logger.info(f"\n===== Testing {profile.upper()} risk profile =====")
            
            # Create an RL advisor for this profile
            advisor = RLInvestmentAdvisor(risk_profile=profile)
            
            # Get RL-powered recommendations
            recommendations = await advisor.get_investment_recommendations(
                pools=SAMPLE_POOLS,
                amount=1000.0
            )
            
            # Print the top 3 recommendations
            logger.info(f"Top recommendations for {profile} investor:")
            for i, rec in enumerate(recommendations[:3], 1):
                token_pair = f"{rec.get('token0', '')}-{rec.get('token1', '')}"
                apr = rec.get('apr', 0)
                confidence = rec.get('confidence', 0) * 100
                explanation = rec.get('explanation', '')
                
                logger.info(f"{i}. {token_pair}: {apr:.1f}% APR ({confidence:.0f}% confidence)")
                logger.info(f"   {explanation}")
            
            # Get market timing recommendation
            timing = await advisor.get_market_timing()
            should_enter = timing.get('should_enter', False)
            confidence = timing.get('confidence', 0) * 100
            
            logger.info("\nMarket timing recommendation:")
            logger.info(f"Should enter: {'YES' if should_enter else 'NO'} ({confidence:.0f}% confidence)")
            
            if 'market_conditions' in timing:
                conditions = timing['market_conditions']
                condition_str = ", ".join([f"{k}: {v}" for k, v in conditions.items()])
                logger.info(f"Market conditions: {condition_str}")
            
            logger.info("=" * 60)
        
        logger.info("\nRL-based investment recommendation test completed successfully!")
            
    except Exception as e:
        logger.error(f"Error during RL test: {e}")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_reinforcement_learning())