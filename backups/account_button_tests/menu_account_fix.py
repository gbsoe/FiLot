"""
Direct fix for the account menu button.
This module provides a completely self-contained handler
for the account menu that doesn't rely on complex database access.
"""

import logging
import sqlite3
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_account_button(user_id: int) -> Dict[str, Any]:
    """
    Handle the account button click with a direct, simplified implementation.
    
    This function bypasses the regular account handler flow and gets
    account information directly from SQLite to avoid any ORM-related issues.
    
    Args:
        user_id: The ID of the user clicking the button
        
    Returns:
        Dict with message and reply markup
    """
    try:
        # Get user information directly from SQLite
        wallet_status, profile_type, subscription_status = get_user_info(user_id)
        
        # Prepare message
        message = (
            f"👤 *Your Account* 👤\n\n"
            f"*Wallet:* {wallet_status}\n"
            f"*Risk Profile:* {profile_type}\n"
            f"*Daily Updates:* {subscription_status}\n\n"
            f"Select an option below to manage your account:"
        )
        
        # Prepare reply markup with inline keyboard
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
            "success": True,
            "message": message,
            "reply_markup": reply_markup
        }
    except Exception as e:
        logger.error(f"Error in handle_account_button: {e}")
        
        # Fallback to a simple message if anything fails
        fallback_message = (
            "👤 *Account Management* 👤\n\n"
            "Manage your FiLot account settings and preferences:"
        )
        
        # Simple reply markup as fallback
        fallback_markup = {
            "inline_keyboard": [
                [{"text": "💼 Connect Wallet", "callback_data": "account_wallet"}],
                [
                    {"text": "🔴 High-Risk Profile", "callback_data": "account_profile_high-risk"},
                    {"text": "🟢 Stable Profile", "callback_data": "account_profile_stable"}
                ],
                [{"text": "❓ Help", "callback_data": "account_help"}],
                [{"text": "🏠 Back to Main Menu", "callback_data": "back_to_main"}]
            ]
        }
        
        return {
            "success": False,
            "message": fallback_message,
            "reply_markup": fallback_markup
        }

def get_user_info(user_id: int) -> tuple:
    """
    Get user information directly from SQLite.
    
    This approach avoids ORM layer issues by using direct SQL.
    
    Args:
        user_id: The ID of the user
        
    Returns:
        Tuple with (wallet_status, profile_type, subscription_status)
    """
    try:
        # Connect directly to the SQLite database
        conn = sqlite3.connect("filot_bot.db")
        cursor = conn.cursor()
        
        # Ensure the users table exists
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            risk_profile TEXT DEFAULT 'stable',
            investment_horizon TEXT DEFAULT 'medium',
            subscribed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            wallet_address TEXT,
            verification_code TEXT,
            verified BOOLEAN DEFAULT 0
        )
        ''')
        
        # Check if the user exists
        cursor.execute("SELECT risk_profile, subscribed, wallet_address FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        
        if not result:
            # User doesn't exist, create them
            logger.info(f"User {user_id} not found, creating record")
            cursor.execute(
                "INSERT INTO users (id, username) VALUES (?, ?)",
                (user_id, f"user_{user_id}")
            )
            conn.commit()
            
            # Return default values
            conn.close()
            return "❌ Not Connected", "Not Set", "❌ Not Subscribed"
        
        # User exists, extract their info
        risk_profile, subscribed, wallet_address = result
        
        # Format wallet status
        wallet_status = "❌ Not Connected"
        if wallet_address:
            wallet_status = f"✅ Connected ({wallet_address[:6]}...{wallet_address[-4:]})"
        
        # Format profile type
        profile_type = "Not Set"
        if risk_profile:
            profile_type = risk_profile.capitalize()
        
        # Format subscription status
        subscription_status = "❌ Not Subscribed"
        if subscribed:
            subscription_status = "✅ Subscribed"
        
        # Close connection
        conn.close()
        
        return wallet_status, profile_type, subscription_status
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        # Return default values in case of error
        return "❌ Not Connected", "Not Set", "❌ Not Subscribed"