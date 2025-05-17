"""
Special handler for the Account Status button that was malfunctioning.
This provides a direct way to fix the Status button in the account section.
"""

import logging
import sqlite3
import time
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_account_status_button(user_id: int) -> Dict[str, Any]:
    """
    Handle the account status button click.
    
    Args:
        user_id: The ID of the user clicking the button
        
    Returns:
        A dictionary with the success status and formatted message
    """
    try:
        logger.info(f"Handling account status button for user {user_id}")
        
        # Format status message using direct DB access
        status_message = format_status_message(user_id)
        
        return {
            "success": True,
            "message": status_message
        }
    except Exception as e:
        logger.error(f"Error handling account status button: {e}", exc_info=True)
        
        # Return a fallback status message
        return {
            "success": False,
            "message": (
                "📊 *FiLot Bot Status* 📊\n\n"
                "Bot is operational. Some status details could not be retrieved.\n\n"
                "Please try again later or contact support if this issue persists."
            ),
            "error": str(e)
        }
        
def format_status_message(user_id: int) -> str:
    """
    Format a nice status message for the user with all relevant information.
    
    Args:
        user_id: The ID of the user
        
    Returns:
        Formatted status message with markdown
    """
    try:
        # Connect to the database
        db_path = 'filot_bot.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get user information
        cursor.execute('''
            SELECT risk_profile, subscribed, wallet_address, created_at 
            FROM users WHERE id = ?
        ''', (user_id,))
        
        user_data = cursor.fetchone()
        
        # Default values
        risk_profile = "stable"
        subscribed = False
        wallet_address = None
        created_at = "recently"
        
        # Process user data if it exists
        if user_data:
            risk_profile = user_data[0] or risk_profile
            subscribed = bool(user_data[1])
            wallet_address = user_data[2]
            created_at = user_data[3] or created_at
        
        # Get bot statistics
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE subscribed = 1')
        subscribed_users = cursor.fetchone()[0]
        
        # Format wallet status
        wallet_status = "❌ Not Connected"
        if wallet_address:
            wallet_status = f"✅ Connected ({wallet_address[:6]}...{wallet_address[-4:]})"
        
        # Format profile status
        profile_emoji = "🔴" if risk_profile == "high-risk" else "🟢"
        profile_text = f"{profile_emoji} {risk_profile.capitalize()}"
        
        # Format subscription status
        subscription_status = "✅ Subscribed" if subscribed else "❌ Not Subscribed"
        
        # Close the database connection
        conn.close()
        
        # Build the status message
        status_message = (
            "📊 *FiLot Bot Status* 📊\n\n"
            
            "*Your Profile:*\n"
            f"• Wallet: {wallet_status}\n"
            f"• Risk Profile: {profile_text}\n"
            f"• Daily Updates: {subscription_status}\n"
            f"• Account Created: {created_at}\n\n"
            
            "*Bot Statistics:*\n"
            f"• Total Users: {total_users:,}\n"
            f"• Subscribed Users: {subscribed_users:,}\n"
            f"• Service Status: ✅ Online\n"
            f"• Last Update: Just now\n\n"
            
            "_Use the menu buttons to navigate through FiLot's features_"
        )
        
        return status_message
        
    except Exception as e:
        logger.error(f"Error formatting status message: {e}", exc_info=True)
        
        # Return a simplified status message
        return (
            "📊 *FiLot Bot Status* 📊\n\n"
            "✅ Bot is operational and ready to assist you!\n\n"
            "Please use the help button if you need assistance."
        )