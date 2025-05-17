"""
Direct fix for the Account button to ensure it displays properly.
This module provides a simple and reliable implementation for the Account menu.
"""

import logging
import sqlite3
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_account_button(user_id: int) -> Dict[str, Any]:
    """
    Direct handler for the Account button that simply returns a working menu.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dict with message and reply_markup
    """
    logger.info(f"Direct account button handler for user {user_id}")
    
    try:
        # Get basic user info directly from SQLite for display
        user_info = get_basic_user_info(user_id)
        
        # Create profile status text
        risk_profile = user_info.get("risk_profile", "stable")
        profile_emoji = "🔴" if risk_profile == "high-risk" else "🟢"
        profile_text = f"{profile_emoji} {risk_profile.capitalize()}"
        
        # Create wallet status text
        wallet_address = user_info.get("wallet_address")
        if wallet_address:
            # Truncate for display
            truncated = wallet_address[:6] + "..." + wallet_address[-4:]
            wallet_text = f"✅ Connected: {truncated}"
        else:
            wallet_text = "❌ Not Connected"
        
        # Create subscription status text
        subscribed = user_info.get("subscribed", False)
        subscription_text = "✅ Active" if subscribed else "❌ Inactive"
        
        # Create the account info message
        message = (
            "👤 *Your FiLot Account* 👤\n\n"
            f"*Risk Profile:* {profile_text}\n"
            f"*Wallet:* {wallet_text}\n"
            f"*Subscription:* {subscription_text}\n\n"
            "Use the buttons below to manage your account:"
        )
        
        # Create account menu
        reply_markup = {
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
            "success": True,
            "message": message,
            "reply_markup": reply_markup
        }
    except Exception as e:
        logger.error(f"Error in direct_account_menu: {e}")
        
        # Provide a simplified fallback menu if anything fails
        fallback_message = (
            "👤 *Account Management* 👤\n\n"
            "Manage your FiLot account settings and preferences:"
        )
        
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
            "success": True,  # Still return success so the menu displays
            "message": fallback_message,
            "reply_markup": fallback_markup
        }

def get_basic_user_info(user_id: int) -> Dict[str, Any]:
    """
    Get basic user info directly from SQLite database.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dict with user info (risk_profile, wallet_address, subscribed)
    """
    try:
        # Connect to the database
        conn = sqlite3.connect("filot_bot.db")
        cursor = conn.cursor()
        
        # Ensure users table exists
        cursor.execute("""
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
        """)
        
        # Check if user exists
        cursor.execute(
            "SELECT risk_profile, wallet_address, subscribed FROM users WHERE id = ?", 
            (user_id,)
        )
        result = cursor.fetchone()
        
        if result:
            # User exists, return their info
            return {
                "risk_profile": result[0] or "stable",
                "wallet_address": result[1],
                "subscribed": bool(result[2])
            }
        else:
            # User doesn't exist, create default entry
            cursor.execute(
                "INSERT INTO users (id, risk_profile, subscribed) VALUES (?, ?, ?)",
                (user_id, "stable", 0)
            )
            conn.commit()
            
            # Return default values
            return {
                "risk_profile": "stable",
                "wallet_address": None,
                "subscribed": False
            }
    except Exception as e:
        logger.error(f"Database error in get_basic_user_info: {e}")
        # Return default values as fallback
        return {
            "risk_profile": "stable",
            "wallet_address": None,
            "subscribed": False
        }
    finally:
        # Close the database connection
        if 'conn' in locals():
            conn.close()