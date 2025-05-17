"""
Final fix for the Account button that directly provides a working
menu without relying on database access.
"""

import logging
import sqlite3
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_account_menu_keyboard():
    """
    Get the account menu inline keyboard with proper callback data.
    """
    return {
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

def handle_account_button(user_id: int) -> Dict[str, Any]:
    """
    Handle the Account button click in a way that doesn't rely on complex database access.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dict with message and reply_markup
    """
    try:
        # Try to get basic user info from database
        user_info = get_basic_user_info(user_id)
        
        # Create account details based on retrieved info
        wallet_status = "❌ Not Connected"
        profile_type = "Not Set"
        subscription_status = "❌ Not Subscribed"
        
        if user_info.get("success"):
            wallet_address = user_info.get("wallet_address")
            if wallet_address:
                wallet_status = f"✅ Connected ({wallet_address[:6]}...{wallet_address[-4:]})"
            
            risk_profile = user_info.get("risk_profile")
            if risk_profile:
                profile_type = risk_profile.capitalize()
            
            if user_info.get("subscribed"):
                subscription_status = "✅ Subscribed"
        
        # Create message
        message = (
            f"👤 *Your Account* 👤\n\n"
            f"*Wallet:* {wallet_status}\n"
            f"*Risk Profile:* {profile_type}\n"
            f"*Daily Updates:* {subscription_status}\n\n"
            f"Select an option below to manage your account:"
        )
        
        # Get account menu keyboard
        reply_markup = get_account_menu_keyboard()
        
        return {
            "success": True,
            "message": message,
            "reply_markup": reply_markup
        }
    except Exception as e:
        logger.error(f"Error in handle_account_button: {e}")
        
        # Return a simple fallback message with the menu
        return {
            "success": False,
            "message": "👤 *Account Management* 👤\n\nManage your FiLot account settings and preferences:",
            "reply_markup": get_account_menu_keyboard()
        }

def get_basic_user_info(user_id: int) -> Dict[str, Any]:
    """
    Get basic user info directly from SQLite database with simplified error handling.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dict with basic user info
    """
    try:
        # Use a direct connection to the database
        conn = sqlite3.connect("filot_bot.db")
        cursor = conn.cursor()
        
        # Make sure the table exists
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
        
        # Check if user exists
        cursor.execute("SELECT id, risk_profile, subscribed, wallet_address FROM users WHERE id = ?", (user_id,))
        user_record = cursor.fetchone()
        
        # Close connection
        conn.close()
        
        if user_record:
            # User exists, return the info
            user_id, risk_profile, subscribed, wallet_address = user_record
            return {
                "success": True,
                "user_id": user_id,
                "risk_profile": risk_profile,
                "subscribed": subscribed == 1,
                "wallet_address": wallet_address
            }
        else:
            # User doesn't exist, create one
            conn = sqlite3.connect("filot_bot.db")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (id, username) VALUES (?, ?)",
                (user_id, f"user_{user_id}")
            )
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "user_id": user_id,
                "risk_profile": "stable",
                "subscribed": False,
                "wallet_address": None
            }
    except Exception as e:
        logger.error(f"Database error in get_basic_user_info: {e}")
        return {
            "success": False,
            "error": str(e)
        }