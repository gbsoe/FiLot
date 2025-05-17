"""
Direct handler for account section buttons.
This module provides specialized processing for account-related buttons that have been problematic.
"""

import logging
import sqlite3
import traceback
from typing import Dict, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_account_button(callback_data: str, user_id: int, chat_id: int) -> Dict[str, Any]:
    """
    Special handler for account section buttons.
    
    Args:
        callback_data: The callback data from the button
        user_id: The ID of the user who pressed the button
        chat_id: The chat ID where the button was pressed
        
    Returns:
        Dictionary with status and response
    """
    logger.info(f"BUTTON HANDLER: Processing {callback_data} for user {user_id}")
    
    try:
        # Handle account status button
        if callback_data == "account_status":
            return handle_status_button(user_id)
            
        # Handle profile buttons
        elif callback_data.startswith("account_profile_"):
            profile_type = callback_data.replace("account_profile_", "")
            return handle_profile_button(profile_type, user_id)
            
        # Other account buttons don't need special handling
        else:
            return {
                "success": False,
                "message": "Not a handled button type"
            }
    
    except Exception as e:
        logger.error(f"Error in account button handler: {e}")
        logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": f"Error handling button: {str(e)}"
        }

def handle_status_button(user_id: int) -> Dict[str, Any]:
    """
    Handle account status button.
    
    Args:
        user_id: The user ID
        
    Returns:
        Dictionary with status and response
    """
    try:
        # Connect to database
        conn = sqlite3.connect('filot_bot.db')
        cursor = conn.cursor()
        
        # Ensure user exists
        cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
        if not cursor.fetchone():
            # Create user if not exists
            cursor.execute(
                'INSERT INTO users (id, risk_profile, created_at, last_active) VALUES (?, ?, datetime("now"), datetime("now"))',
                (user_id, "stable")
            )
            conn.commit()
        
        # Get user information
        cursor.execute('SELECT risk_profile, subscribed, wallet_address FROM users WHERE id = ?', (user_id,))
        user_data = cursor.fetchone()
        
        # Default values
        risk_profile = "stable"
        subscribed = False
        wallet_address = None
        
        if user_data:
            risk_profile = user_data[0] or risk_profile
            subscribed = bool(user_data[1])
            wallet_address = user_data[2]
            
        # Get basic statistics
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE subscribed = 1')
        subscribed_users = cursor.fetchone()[0]
        
        # Format wallet status
        if wallet_address:
            wallet_status = f"✅ Connected ({wallet_address[:6]}...{wallet_address[-4:]})"
        else:
            wallet_status = "❌ Not Connected"
            
        # Format risk profile
        profile_emoji = "🔴" if risk_profile == "high-risk" else "🟢"
        profile_text = f"{profile_emoji} {risk_profile.capitalize()}"
        
        # Format subscription status
        subscription_status = "✅ Subscribed" if subscribed else "❌ Not Subscribed"
        
        # Close database connection
        conn.close()
        
        # Format the message
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
            "action": "status",
            "acknowledgment": "Status updated!"
        }
        
    except Exception as e:
        logger.error(f"Error in status button handler: {e}")
        logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": "Error retrieving status information",
            "error": str(e)
        }

def handle_profile_button(profile_type: str, user_id: int) -> Dict[str, Any]:
    """
    Handle profile selection button.
    
    Args:
        profile_type: The profile type (high-risk or stable)
        user_id: The user ID
        
    Returns:
        Dictionary with status and response
    """
    try:
        # Prepare appropriate emoji and profile-specific message
        profile_emoji = "🔴" if profile_type == "high-risk" else "🟢"
        
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
        
        # Update the database directly
        conn = sqlite3.connect('filot_bot.db')
        cursor = conn.cursor()
        
        # Ensure users table exists
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            risk_profile TEXT DEFAULT 'stable',
            subscribed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            wallet_address TEXT,
            verification_code TEXT,
            is_verified BOOLEAN DEFAULT 0
        )
        ''')
        
        # Check if user exists
        cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
        user_exists = cursor.fetchone()
        
        if user_exists:
            # Update existing user
            cursor.execute(
                'UPDATE users SET risk_profile = ? WHERE id = ?',
                (profile_type, user_id)
            )
            logger.info(f"Updated existing user {user_id} profile to {profile_type}")
        else:
            # Create new user
            cursor.execute(
                'INSERT INTO users (id, risk_profile, created_at, last_active) VALUES (?, ?, datetime("now"), datetime("now"))',
                (user_id, profile_type)
            )
            logger.info(f"Created new user {user_id} with {profile_type} profile")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": profile_message,
            "action": "profile",
            "profile_type": profile_type,
            "acknowledgment": "Profile updated!"
        }
        
    except Exception as e:
        logger.error(f"Error in profile button handler: {e}")
        logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": "Error updating profile",
            "error": str(e)
        }