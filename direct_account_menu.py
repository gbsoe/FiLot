"""
Direct no-frills implementation of account menu handler.
Completely self-contained with no dependencies on complex database access.
"""

import logging
import sqlite3
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def simple_account_menu() -> Dict[str, Any]:
    """
    Get a simple account menu with buttons.
    No database access at all, just the menu.
    
    Returns:
        Dict with message and reply_markup
    """
    # Very simple message
    message = "👤 *Account Management*\n\nManage your account settings:"
    
    # Simple inline keyboard
    reply_markup = {
        "inline_keyboard": [
            [{"text": "💼 Connect Wallet", "callback_data": "account_wallet"}],
            [
                {"text": "🔴 High-Risk Profile", "callback_data": "account_profile_high-risk"},
                {"text": "🟢 Stable Profile", "callback_data": "account_profile_stable"}
            ],
            [
                {"text": "🔔 Subscribe", "callback_data": "account_subscribe"},
                {"text": "🔕 Unsubscribe", "callback_data": "account_unsubscribe"}
            ],
            [{"text": "❓ Help", "callback_data": "account_help"}],
            [{"text": "🏠 Back to Main Menu", "callback_data": "back_to_main"}]
        ]
    }
    
    return {
        "message": message,
        "reply_markup": reply_markup
    }

def fixed_account_menu(user_id: int) -> Dict[str, Any]:
    """
    Super simple account menu with minimal error-prone operations.
    
    Args:
        user_id: User ID
        
    Returns:
        Dict with message and reply_markup
    """
    try:
        # Connect to database - very simple operation
        conn = sqlite3.connect("filot_bot.db")
        cursor = conn.cursor()
        
        # Check if user exists - super simple query
        cursor.execute("SELECT 1 FROM users WHERE id = ?", (user_id,))
        if cursor.fetchone() is None:
            # If user doesn't exist, create default record
            cursor.execute("INSERT INTO users (id) VALUES (?)", (user_id,))
            conn.commit()
        
        # Close connection
        conn.close()
        
        # Return simple menu
        return simple_account_menu()
    except Exception as e:
        logger.error(f"Error in fixed_account_menu: {e}")
        # If anything fails, return the simple menu
        return simple_account_menu()