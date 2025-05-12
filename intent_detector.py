"""
Intent detection functions for the Telegram cryptocurrency pool bot
These functions are used to determine user intent from natural language messages
"""

import re
from typing import Optional, List, Dict, Any


def is_investment_intent(text: str) -> bool:
    """
    Check if text contains investment intent.
    
    Args:
        text: The text to analyze
        
    Returns:
        True if investment intent is detected, False otherwise
    """
    investment_keywords = [
        r'invest\b', r'\binvest', r'buy', r'purchase', r'acquire', r'put money in',
        r'allocate', r'deploy capital', r'add liquidity', r'deposit', r'stake',
        r'want to invest', r'looking to invest', r'interested in investing'
    ]
    
    for keyword in investment_keywords:
        if re.search(keyword, text.lower()):
            return True
    
    # Check for amount mentions with investment context
    amount_pattern = r'(\$\d+|\d+\s*(?:dollars|usd|usdc|usdt|sol)|\d+k)'
    if re.search(amount_pattern, text.lower()):
        context_keywords = [
            'in', 'with', 'using', 'spend', 'use', 'investing', 'investment'
        ]
        for keyword in context_keywords:
            if keyword in text.lower():
                return True
    
    return False


def is_position_inquiry(text: str) -> bool:
    """
    Check if text is asking about current positions.
    
    Args:
        text: The text to analyze
        
    Returns:
        True if position inquiry is detected, False otherwise
    """
    position_keywords = [
        r'my position', r'my investment', r'my portfolio', r'my holding',
        r'how am i doing', r'current investment', r'how\'s my investment',
        r'portfolio status', r'investment status', r'position status',
        r'check position', r'view position', r'my balance', r'position details'
    ]
    
    for keyword in position_keywords:
        if re.search(keyword, text.lower()):
            return True
    
    return False


def is_pool_inquiry(text: str) -> bool:
    """
    Check if text is asking about pools.
    
    Args:
        text: The text to analyze
        
    Returns:
        True if pool inquiry is detected, False otherwise
    """
    pool_keywords = [
        r'pool\b', r'\bpool', r'liquidity pool', r'best pool', r'top pool',
        r'recommend pool', r'which pool', r'pool stats', r'pool performance',
        r'pool data', r'pool info', r'pool details', r'pool apr', r'pool return',
        r'show me pool', r'list pool', r'available pool'
    ]
    
    for keyword in pool_keywords:
        if re.search(keyword, text.lower()):
            return True
    
    return False


def is_wallet_inquiry(text: str) -> bool:
    """
    Check if text is asking about wallet connection.
    
    Args:
        text: The text to analyze
        
    Returns:
        True if wallet inquiry is detected, False otherwise
    """
    wallet_keywords = [
        r'wallet\b', r'\bwallet', r'connect wallet', r'wallet connect',
        r'link wallet', r'wallet integration', r'add wallet', r'setup wallet',
        r'my wallet', r'wallet setup', r'how to connect', r'wallet connection'
    ]
    
    for keyword in wallet_keywords:
        if re.search(keyword, text.lower()):
            return True
    
    return False


def extract_amount(text: str) -> float:
    """
    Extract a monetary amount from text.
    
    Args:
        text: The text to analyze
        
    Returns:
        The extracted amount as a float, or 0 if no amount is found
    """
    # Look for dollar signs
    dollar_pattern = r'\$\s*(\d+(?:,\d+)*(?:\.\d+)?)'
    dollar_match = re.search(dollar_pattern, text)
    if dollar_match:
        amount_str = dollar_match.group(1).replace(',', '')
        return float(amount_str)
    
    # Look for amounts followed by currency indicators
    currency_pattern = r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:dollars|usd|usdc|usdt|sol)'
    currency_match = re.search(currency_pattern, text.lower())
    if currency_match:
        amount_str = currency_match.group(1).replace(',', '')
        return float(amount_str)
    
    # Look for k/thousand notation
    k_pattern = r'(\d+(?:\.\d+)?)\s*k\b'
    k_match = re.search(k_pattern, text.lower())
    if k_match:
        k_amount = float(k_match.group(1))
        return k_amount * 1000
    
    # Look for standalone numbers if they seem like they could be amounts
    # but only in investment contexts
    if is_investment_intent(text):
        num_pattern = r'\b(\d+(?:,\d+)*(?:\.\d+)?)\b'
        numbers = re.findall(num_pattern, text)
        if numbers:
            # Use the largest number as the amount
            cleaned_numbers = [float(num.replace(',', '')) for num in numbers]
            # Filter out very small numbers (likely not amounts) and very large numbers (likely not amounts)
            valid_amounts = [num for num in cleaned_numbers if 5 <= num <= 1000000]
            if valid_amounts:
                return max(valid_amounts)
    
    return 0