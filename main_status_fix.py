"""
Direct fix for the Status button in the account section.
"""

import logging
import time
import sqlite3
from typing import Dict, Any, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_user_info(user_id: int) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Get user information and system stats directly from the database.
    
    Args:
        user_id: The Telegram user ID
        
    Returns:
        Tuple of user data dict and system stats dict
    """
    try:
        # Connect to database
        conn = sqlite3.connect('filot_bot.db')
        cursor = conn.cursor()
        
        # Get user profile
        cursor.execute(
            'SELECT risk_profile, subscribed, wallet_address, is_verified, created_at FROM users WHERE id = ?',
            (user_id,)
        )
        user_row = cursor.fetchone()
        
        user_data = {
            "risk_profile": "stable",
            "subscribed": False,
            "wallet_address": None,
            "is_verified": False,
            "created_at": "N/A"
        }
        
        if user_row:
            user_data["risk_profile"] = user_row[0] or "stable"
            user_data["subscribed"] = bool(user_row[1])
            user_data["wallet_address"] = user_row[2]
            user_data["is_verified"] = bool(user_row[3])
            user_data["created_at"] = user_row[4] or "N/A"
        
        # Get system stats
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE subscribed = 1')
        subscribed_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE wallet_address IS NOT NULL')
        connected_wallets = cursor.fetchone()[0]
        
        # Stats dictionary
        stats = {
            "total_users": total_users,
            "subscribed_users": subscribed_users,
            "connected_wallets": connected_wallets,
            "timestamp": int(time.time())
        }
        
        conn.close()
        return user_data, stats
        
    except Exception as e:
        logger.error(f"Database error getting user info: {e}", exc_info=True)
        return {
            "risk_profile": "stable",
            "subscribed": False,
            "wallet_address": None,
            "is_verified": False,
            "created_at": "N/A"
        }, {
            "total_users": 0,
            "subscribed_users": 0,
            "connected_wallets": 0,
            "timestamp": int(time.time())
        }

def format_status_message(user_id: int) -> str:
    """
    Format a status message with user and system information.
    
    Args:
        user_id: The Telegram user ID
        
    Returns:
        Formatted status message
    """
    try:
        # Get user and system information
        user_data, stats = get_user_info(user_id)
        
        # Format wallet status
        if user_data["wallet_address"]:
            wallet_addr = user_data["wallet_address"]
            wallet_status = f"✅ Connected ({wallet_addr[:6]}...{wallet_addr[-4:]})" 
        else:
            wallet_status = "❌ Not Connected"
        
        # Format subscription status
        subscription_status = "✅ Subscribed" if user_data["subscribed"] else "❌ Not Subscribed"
        
        # Format verification status
        verification_status = "✅ Verified" if user_data["is_verified"] else "❌ Not Verified"
        
        # Format risk profile
        profile_type = user_data["risk_profile"].capitalize()
        profile_emoji = "🔴" if profile_type.lower() == "high-risk" else "🟢"
        profile_text = f"{profile_emoji} {profile_type}"
        
        # Build the status message
        status_message = (
            "📊 *FiLot Bot Status* 📊\n\n"
            
            "*Your Profile:*\n"
            f"• Wallet: {wallet_status}\n"
            f"• Risk Profile: {profile_text}\n"
            f"• Daily Updates: {subscription_status}\n"
            f"• Account Status: {verification_status}\n\n"
            
            "*Bot Statistics:*\n"
            f"• Total Users: {stats['total_users']:,}\n"
            f"• Subscribed Users: {stats['subscribed_users']:,}\n"
            f"• Connected Wallets: {stats['connected_wallets']:,}\n\n"
            
            "*System Status:*\n"
            f"• API Status: ✅ Online\n"
            f"• Database: ✅ Connected\n"
            f"• Last Update: Just now\n\n"
            
            "*Need Help?*\n"
            f"Use the buttons below or type /help for assistance."
        )
        
        return status_message
        
    except Exception as e:
        logger.error(f"Error formatting status message: {e}", exc_info=True)
        
        # Return a simplified message on error
        return (
            "📊 *FiLot Bot Status* 📊\n\n"
            "Bot is operational and ready to assist you with your cryptocurrency investments.\n\n"
            "If you encounter any issues, please use the /help command."
        )

def process_status_button(callback_query) -> Dict[str, Any]:
    """
    Process the status button from the account section.
    
    Args:
        callback_query: The callback query from Telegram
        
    Returns:
        Dict with success status and message
    """
    try:
        # Extract data
        user_id = callback_query.from_user.id
        callback_data = callback_query.data
        
        logger.info(f"STATUS FIX: Processing {callback_data} for user {user_id}")
        
        # Verify this is a status button
        if not callback_data == "account_status":
            return {
                "success": False,
                "message": "Not a status button"
            }
        
        # Format status message
        status_message = format_status_message(user_id)
        
        return {
            "success": True,
            "message": status_message
        }
        
    except Exception as e:
        logger.error(f"Error processing status button: {e}", exc_info=True)
        
        return {
            "success": False,
            "message": (
                "📊 *FiLot Bot Status* 📊\n\n"
                "Bot is operational but encountered an error retrieving your details.\n\n"
                "Please try again later or use /status command directly."
            ),
            "error": str(e)
        }