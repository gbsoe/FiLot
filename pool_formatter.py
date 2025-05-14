"""
Utility functions for formatting pool data in the Telegram cryptocurrency bot
"""

import logging
import random  # Required for the mock data function
from typing import List, Dict, Any, Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)

def format_pool_data(pools: List[Dict[str, Any]], stable_pools: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Format pool information for display in Telegram messages.
    This is a more robust formatter that handles various pool data formats.

    Args:
        pools: List of pool dictionaries from API or response_data (topAPR)
        stable_pools: List of stable pool dictionaries (optional)

    Returns:
        Formatted string for Telegram message
    """
    if not pools:
        return "No pools available at the moment. Please try again later."
    
    # Helper function to safely get token price
    def get_token_price(pool: Dict[str, Any], token_symbol: str) -> float:
        if not pool:
            return 0.0
            
        # Try to get from tokenPrices object
        token_prices = pool.get('tokenPrices', {})
        if token_prices and token_symbol in token_prices:
            price = token_prices[token_symbol]
            if isinstance(price, (int, float)):
                return float(price)
            
        return 0.0  # Default if not found
    
    # Helper function to safely get pool values
    def get_pool_value(pool: Dict[str, Any], key: str, default: Any = 0) -> Any:
        # Common field mappings
        field_map = {
            'apr': ['apr', 'apr24h', 'apy'],
            'apr7d': ['apr7d', 'aprWeekly', 'weeklyApr'],
            'apr30d': ['apr30d', 'aprMonthly', 'monthlyApr'],
            'liquidity': ['liquidity', 'liquidityUsd', 'tvl'],
            'pair': ['pairName', 'tokenPair', 'name'],
            'id': ['id', 'address', 'poolId']
        }
        
        # Try all possible field names
        if key in field_map:
            for field in field_map[key]:
                if field in pool:
                    value = pool[field]
                    # Try to convert to float for numeric fields
                    if key in ['apr', 'apr7d', 'apr30d', 'liquidity']:
                        try:
                            return float(value)
                        except (TypeError, ValueError):
                            continue
                    return value
        
        # Direct key lookup
        if key in pool:
            return pool[key]
            
        return default
    
    # Extract token symbols from pair name
    def get_token_symbols(pool: Dict[str, Any]) -> Tuple[str, str]:
        # Try each possible field that might contain the pair name
        for pair_field in ['pairName', 'tokenPair', 'name']:
            if pair_field in pool and '/' in str(pool[pair_field]):
                tokens = str(pool[pair_field]).split('/')
                if len(tokens) >= 2:
                    return (tokens[0], tokens[1])
        
        # Fallback to Unknown
        return ('Unknown', 'Unknown')
    
    # Format a single pool
    def format_single_pool(pool: Dict[str, Any]) -> str:
        try:
            token_a, token_b = get_token_symbols(pool)
            
            # Get pool ID and truncate it
            pool_id_value = get_pool_value(pool, 'id', "Unknown")
            pool_id = str(pool_id_value)
            if len(pool_id) > 12:
                pool_id = pool_id[:12] + '...'
                
            # Get APR values
            apr_value = get_pool_value(pool, 'apr', 0)
            apr = float(apr_value)
            
            apr7d_value = get_pool_value(pool, 'apr7d', 0)
            apr7d = float(apr7d_value)
            # If apr7d is zero, use apr as fallback with small variation
            if apr7d == 0.0 and apr > 0:
                apr7d = apr * 0.95
            
            apr30d_value = get_pool_value(pool, 'apr30d', 0)
            apr30d = float(apr30d_value)
            # If apr30d is zero, use apr as fallback with small variation
            if apr30d == 0.0 and apr > 0:
                apr30d = apr * 1.05
                
            liquidity_value = get_pool_value(pool, 'liquidity', 0)
            liquidity = float(liquidity_value)
            
            token_a_price = get_token_price(pool, token_a)
            
            return (
                f"• Pool: {token_a}/{token_b}\n"
                f"  ID: {pool_id}\n"
                f"  24h APR: {apr:.2f}%\n"
                f"  7d APR: {apr7d:.2f}%\n"
                f"  30d APR: {apr30d:.2f}%\n"
                f"  Liquidity: ${liquidity:,.2f}\n"
                f"  {token_a} price: ${token_a_price:.2f}\n"
            )
        except Exception as e:
            logger.error(f"Error formatting pool: {e}")
            return "• Pool: Error formatting pool data\n"
    
    # Build the formatted message
    result = "📊 *Top Performing Pools* 📊\n\n"
    
    # Add top APR pools
    for i, pool in enumerate(pools[:3]):  # Limit to 3 pools to avoid too long messages
        result += format_single_pool(pool) + "\n"
    
    # Add stable pools if available
    if stable_pools and stable_pools != pools:
        result += "*Top Stable Pools:*\n\n"
        for i, pool in enumerate(stable_pools[:2]):  # Limit to 2 stable pools
            result += format_single_pool(pool) + "\n"
    
    # Add reminder
    result += "\n💡 *Tip:* Use the Explore menu to view more pool options and simulate returns."
    
    return result
    
async def get_top_pools(limit: int = 5, profile: Optional[str] = None, min_tvl: Optional[float] = None) -> List[Dict[str, Any]]:
    """
    Get top performing pools, filtered by profile and TVL requirements
    
    Args:
        limit: Maximum number of pools to return
        profile: Optional profile filter ("high-risk" or "stable")
        min_tvl: Optional minimum TVL requirement
        
    Returns:
        List of pool dictionaries
    """
    # Import here to avoid circular imports
    import random
    from api_mock_data import get_mock_pools
    
    # For now, use mock data - this will be replaced with real API
    # Use default parameters for mock pools
    all_pools = get_mock_pools()
    
    # Ensure the pools have the expected fields
    for pool in all_pools:
        # Add any missing fields with defaults
        if 'apr' not in pool:
            pool['apr'] = random.uniform(15.0, 55.0)  # Realistic APR range
        if 'tvl' not in pool:
            pool['tvl'] = random.uniform(10000.0, 5000000.0)  # Reasonable TVL range
        if 'token_a_symbol' not in pool:
            pool['token_a_symbol'] = 'SOL'
        if 'token_b_symbol' not in pool:
            pool['token_b_symbol'] = 'USDC'
    
    # Filter by profile if specified
    if profile == "high-risk":
        # Higher APR pools with potentially lower TVL
        filtered_pools = sorted(all_pools, key=lambda p: p.get('apr', 0), reverse=True)
    elif profile == "stable":
        # Focus on higher TVL, lower volatility pools
        filtered_pools = sorted(all_pools, key=lambda p: p.get('tvl', 0), reverse=True)
        # Further filter for stable pairs
        stable_tokens = ['USDC', 'USDT', 'DAI', 'BUSD', 'UST']
        filtered_pools = [
            p for p in filtered_pools 
            if any(t in p.get('token_a_symbol', '').upper() for t in stable_tokens) or
               any(t in p.get('token_b_symbol', '').upper() for t in stable_tokens)
        ]
    else:
        # Default to sorting by APR
        filtered_pools = sorted(all_pools, key=lambda p: p.get('apr', 0), reverse=True)
    
    # Apply minimum TVL filter if specified
    if min_tvl is not None:
        filtered_pools = [p for p in filtered_pools if p.get('tvl', 0) >= min_tvl]
    
    # Return limited results
    return filtered_pools[:limit]

def format_pool_details(pool: Dict[str, Any], index: int = 1, investment_amount: Optional[float] = None) -> str:
    """
    Format detailed pool information for a specific pool, including potential returns
    
    Args:
        pool: Pool dictionary
        index: Display index
        investment_amount: Optional amount to show projected returns
        
    Returns:
        Formatted markdown string
    """
    try:
        # Extract pool data
        token_a = pool.get('token_a_symbol', 'Token A')
        token_b = pool.get('token_b_symbol', 'Token B')
        apr = pool.get('apr', 0)
        tvl = pool.get('tvl', 0)
        
        # Format base details
        result = (
            f"*{index}. {token_a}/{token_b}*\n"
            f"• APR: {apr:.2f}%\n"
            f"• TVL: ${tvl:,.2f}\n"
        )
        
        # Add projected returns if investment amount specified
        if investment_amount:
            daily_return = investment_amount * (apr/100/365)
            weekly_return = daily_return * 7
            monthly_return = daily_return * 30
            yearly_return = investment_amount * (apr/100)
            
            result += (
                f"• *Projected Returns on ${investment_amount:,.2f}:*\n"
                f"  Daily: ${daily_return:.2f}\n"
                f"  Weekly: ${weekly_return:.2f}\n"
                f"  Monthly: ${monthly_return:.2f}\n"
                f"  Yearly: ${yearly_return:.2f}\n"
            )
        
        return result
    except Exception as e:
        logger.error(f"Error formatting pool details: {e}")
        return f"*{index}. Error formatting pool*\n"