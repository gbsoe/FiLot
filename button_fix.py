"""
Simple and effective button navigation fix for the FiLot Telegram bot.

This module provides a straightforward solution to fix button navigation issues,
especially with the main menu buttons (Invest, Explore, Account) and wallet connection.
"""

import time
import logging
from typing import Dict, Any, Set, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Simple button tracking
button_history = {}
wallet_connect_attempts = {}

def log_button_click(user_id: int, chat_id: int, button_name: str) -> None:
    """
    Log a button click with timestamp to track user navigation.
    
    Args:
        user_id: Telegram user ID
        chat_id: Telegram chat ID
        button_name: Name/ID of the button clicked
    """
    key = f"{chat_id}:{button_name}"
    button_history[key] = time.time()
    logger.info(f"Button click: {button_name} by user {user_id} in chat {chat_id}")

def is_duplicate_click(chat_id: int, button_name: str, window: float = 0.5) -> bool:
    """
    Check if this button was recently clicked (within the time window).
    
    Args:
        chat_id: Telegram chat ID
        button_name: Name/ID of the button
        window: Time window in seconds to consider as duplicate
        
    Returns:
        True if this is a duplicate click, False otherwise
    """
    key = f"{chat_id}:{button_name}"
    
    # If no history for this button, it's not a duplicate
    if key not in button_history:
        return False
        
    # Check if the click is within the time window
    now = time.time()
    last_click = button_history[key]
    
    if now - last_click < window:
        logger.info(f"Duplicate click detected: {button_name} (within {window}s)")
        return True
        
    return False

def track_wallet_connect(user_id: int) -> bool:
    """
    Track wallet connection attempts to prevent rapid repeated attempts.
    
    Args:
        user_id: User ID attempting to connect
        
    Returns:
        True if this attempt should proceed, False if it should be blocked
    """
    now = time.time()
    
    # If no previous attempts, allow this one
    if user_id not in wallet_connect_attempts:
        wallet_connect_attempts[user_id] = now
        return True
        
    # Check if the last attempt was recent (within 2 seconds)
    last_attempt = wallet_connect_attempts[user_id]
    if now - last_attempt < 2.0:
        logger.warning(f"Blocking rapid wallet connect attempt for user {user_id}")
        return False
        
    # Update the timestamp and allow this attempt
    wallet_connect_attempts[user_id] = now
    return True

def special_button_handling(button_name: str, user_id: int, chat_id: int) -> Optional[Dict[str, Any]]:
    """
    Apply special handling for problematic buttons.
    
    Args:
        button_name: Name/ID of the button
        user_id: Telegram user ID
        chat_id: Telegram chat ID
        
    Returns:
        Optional special response for this button
    """
    # Special handling for Connect Wallet button
    if button_name == "connect_wallet":
        if not track_wallet_connect(user_id):
            return {
                "success": False,
                "action": "ignore",
                "message": "Please wait before trying again."
            }
    
    # Special handling for main menu buttons to prevent navigation issues
    if button_name in ["menu_invest", "menu_explore", "menu_account"]:
        # Log this navigation for future reference
        log_button_click(user_id, chat_id, button_name)
        
    return None

def cleanup_old_data():
    """Remove old entries to prevent memory leaks."""
    now = time.time()
    
    # Clean up old button history (older than 1 hour)
    for key in list(button_history.keys()):
        if now - button_history[key] > 3600:
            button_history.pop(key)
            
    # Clean up old wallet connect attempts (older than 1 hour)
    for user_id in list(wallet_connect_attempts.keys()):
        if now - wallet_connect_attempts[user_id] > 3600:
            wallet_connect_attempts.pop(user_id)