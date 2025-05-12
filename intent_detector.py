"""
Intent detection functions for the Telegram cryptocurrency pool bot
These functions are used to determine user intent from natural language messages
"""

import re
import logging
from typing import Optional, Dict, List, Tuple, Any

logger = logging.getLogger(__name__)

def is_investment_intent(text: str) -> bool:
    """
    Check if text contains investment intent.
    
    Args:
        text: The text to analyze
        
    Returns:
        True if investment intent is detected, False otherwise
    """
    intent_keywords = [
        "invest", "buy", "purchase", "put money", "spend", "allocate", 
        "deploying capital", "stake", "provide liquidity", "join pool",
        "enter pool", "add liquidity", "deposit"
    ]
    
    text_lower = text.lower()
    
    for keyword in intent_keywords:
        if keyword.lower() in text_lower:
            logger.info(f"Detected investment intent in message: {text[:30]}...")
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
    inquiry_keywords = [
        "position", "holding", "portfolio", "investment", 
        "what do i own", "my stake", "my liquidity", 
        "how much", "balance", "portfolio", "my pools",
        "my investment", "current investment", "what i have"
    ]
    
    text_lower = text.lower()
    
    for keyword in inquiry_keywords:
        if keyword.lower() in text_lower:
            logger.info(f"Detected position inquiry in message: {text[:30]}...")
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
    inquiry_keywords = [
        "pools", "liquidity pools", "show pools", "best pools", 
        "top pools", "high yield", "high apr", "high return",
        "pool list", "available pools", "pool info", "pool data"
    ]
    
    text_lower = text.lower()
    
    for keyword in inquiry_keywords:
        if keyword.lower() in text_lower:
            logger.info(f"Detected pool inquiry in message: {text[:30]}...")
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
    inquiry_keywords = [
        "wallet", "connect wallet", "my wallet", "wallet connection",
        "link wallet", "add wallet", "wallet integration", "account"
    ]
    
    text_lower = text.lower()
    
    for keyword in inquiry_keywords:
        if keyword.lower() in text_lower:
            logger.info(f"Detected wallet inquiry in message: {text[:30]}...")
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
    # Look for dollar amounts like $1000 or 1000 dollars
    dollar_pattern = r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)'
    amount_pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?:dollars|usd|sol)'
    
    # Try the dollar pattern first
    dollar_match = re.search(dollar_pattern, text, re.IGNORECASE)
    if dollar_match:
        amount_str = dollar_match.group(1)
        # Remove commas
        amount_str = amount_str.replace(',', '')
        try:
            return float(amount_str)
        except ValueError:
            pass
    
    # Try the amount pattern next
    amount_match = re.search(amount_pattern, text, re.IGNORECASE)
    if amount_match:
        amount_str = amount_match.group(1)
        # Remove commas
        amount_str = amount_str.replace(',', '')
        try:
            return float(amount_str)
        except ValueError:
            pass
    
    # Number followed by the word investment
    investment_pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?:investment)'
    investment_match = re.search(investment_pattern, text, re.IGNORECASE)
    if investment_match:
        amount_str = investment_match.group(1)
        # Remove commas
        amount_str = amount_str.replace(',', '')
        try:
            return float(amount_str)
        except ValueError:
            pass
    
    return 0.0