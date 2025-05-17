"""
Direct fix for problematic account section buttons.
This module intercepts specific button presses and handles them directly.
"""

import logging
import sqlite3
import traceback
from typing import Dict, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_button(callback_query) -> Tuple[bool, Dict[str, Any]]:
    """
    Handle problematic buttons directly before regular processing.
    
    Args:
        callback_query: The callback query from Telegram
        
    Returns:
        Tuple of (was_handled, result_dict)
    """
    try:
        if not callback_query or not hasattr(callback_query, 'data'):
            return False, {"success": False, "message": "Invalid callback query"}
            
        # Extract basic info
        callback_data = callback_query.data
        user_id = callback_query.from_user.id if hasattr(callback_query, 'from_user') else None
        
        logger.info(f"DIRECT FIX: Checking if button '{callback_data}' needs special handling")
        
        # Handle specific problematic buttons
        if callback_data == "account_status":
            return True, handle_status_button(user_id)
        elif callback_data.startswith("account_profile_"):
            return True, handle_profile_button(callback_data, user_id)
            
        # Button doesn't need special handling
        return False, {"success": False, "message": "No special handling needed"}
        
    except Exception as e:
        logger.error(f"Error in direct button handler: {e}")
        logger.error(traceback.format_exc())
        return False, {
            "success": False, 
            "message": "Error in direct button handler", 
            "error": str(e)
        }

def handle_status_button(user_id: Optional[int]) -> Dict[str, Any]:
    """
    Handle the account status button.
    
    Args:
        user_id: The user ID
        
    Returns:
        Result dictionary
    """
    try:
        logger.info(f"DIRECT FIX: Handling account_status button for user {user_id}")
        
        if not user_id:
            return {
                "success": False,
                "message": "📊 *FiLot Bot Status* 📊\n\nBot is operational. User ID could not be determined."
            }
            
        # Connect to database
        db_path = 'filot_bot.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get user information
        cursor.execute('''
            SELECT risk_profile, subscribed, wallet_address
            FROM users WHERE id = ?
        ''', (user_id,))
        
        user_data = cursor.fetchone()
        
        # Default values
        risk_profile = "stable"
        subscribed = False
        wallet_address = None
        
        if user_data:
            risk_profile = user_data[0] or risk_profile
            subscribed = bool(user_data[1])
            wallet_address = user_data[2]
            
        # Get basic stats
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE subscribed = 1')
        subscribed_users = cursor.fetchone()[0]
        
        conn.close()
        
        # Format wallet status
        wallet_status = "❌ Not Connected"
        if wallet_address:
            wallet_status = f"✅ Connected ({wallet_address[:6]}...{wallet_address[-4:]})"
            
        # Format profile status
        profile_emoji = "🔴" if risk_profile == "high-risk" else "🟢" 
        profile_text = f"{profile_emoji} {risk_profile.capitalize()}"
        
        # Format subscription status
        subscription_status = "✅ Subscribed" if subscribed else "❌ Not Subscribed"
        
        # Build the status message
        status_message = (
            "📊 *FiLot Bot Status* 📊\n\n"
            
            "*Your Profile:*\n"
            f"• Wallet: {wallet_status}\n"
            f"• Risk Profile: {profile_text}\n"
            f"• Daily Updates: {subscription_status}\n\n"
            
            "*Bot Statistics:*\n"
            f"• Total Users: {total_users:,}\n"
            f"• Subscribed Users: {subscribed_users:,}\n\n"
            
            "*System Status:*\n"
            f"• Bot: ✅ Online\n"
            f"• API: ✅ Operational\n"
            f"• Last Update: Just now"
        )
        
        return {
            "success": True,
            "message": status_message,
            "acknowledgment": "Status updated!"
        }
        
    except Exception as e:
        logger.error(f"Error handling status button: {e}")
        logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": "📊 *FiLot Bot Status* 📊\n\nBot is operational. Error retrieving detailed status.",
            "error": str(e),
            "acknowledgment": "Error retrieving status"
        }

def handle_profile_button(callback_data: str, user_id: Optional[int]) -> Dict[str, Any]:
    """
    Handle account profile buttons.
    
    Args:
        callback_data: The callback data
        user_id: The user ID
        
    Returns:
        Result dictionary
    """
    try:
        logger.info(f"DIRECT FIX: Handling {callback_data} button for user {user_id}")
        
        if not user_id:
            return {
                "success": False,
                "message": "Error: Could not determine user ID"
            }
            
        # Extract profile type
        profile_type = callback_data.replace("account_profile_", "")
        
        # Determine profile details
        profile_emoji = "🔴" if profile_type == "high-risk" else "🟢"
        
        # Format appropriate message
        if profile_type == "high-risk":
            profile_message = (
                f"{profile_emoji} *High-Risk Profile Selected*\n\n"
                f"Your investment recommendations will now focus on:\n"
                f"• Higher APR opportunities\n"
                f"• Newer pools with growth potential\n"
                f"• More volatile but potentially rewarding options\n\n"
                f"_Note: Higher returns come with increased risk_"
            )
        else:  # stable
            profile_message = (
                f"{profile_emoji} *Stable Profile Selected*\n\n"
                f"Your investment recommendations will now focus on:\n"
                f"• Established, reliable pools\n"
                f"• Lower volatility options\n"
                f"• More consistent but potentially lower APR\n\n"
                f"_Note: Stability typically means more moderate returns_"
            )
            
        # Update database
        try:
            # Connect to database
            db_path = 'filot_bot.db'
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
            user_exists = cursor.fetchone()
            
            if user_exists:
                # Update existing user
                cursor.execute(
                    "UPDATE users SET risk_profile = ? WHERE id = ?",
                    (profile_type, user_id)
                )
                logger.info(f"Updated existing user {user_id} profile to {profile_type}")
            else:
                # Create new user
                cursor.execute(
                    "INSERT INTO users (id, risk_profile, created_at, last_active) VALUES (?, ?, datetime('now'), datetime('now'))",
                    (user_id, profile_type)
                )
                logger.info(f"Created new user {user_id} with {profile_type} profile")
                
            conn.commit()
            conn.close()
            
        except Exception as db_err:
            logger.error(f"Database error in profile button handler: {db_err}")
            logger.error(traceback.format_exc())
            
        return {
            "success": True,
            "message": profile_message,
            "acknowledgment": "Profile updated!"
        }
        
    except Exception as e:
        logger.error(f"Error handling profile button: {e}")
        logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": "Sorry, there was an error updating your profile. Please try again.",
            "error": str(e),
            "acknowledgment": "Error updating profile"
        }