"""
Dedicated handler for the Status button in the Account section.
This is a simplified, direct approach to fix this button.
"""

import logging
import sqlite3
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_status(user_id: int) -> Dict[str, Any]:
    """
    Handle the account status button press.
    
    Args:
        user_id: The user ID
        
    Returns:
        Dictionary with success status and formatted message
    """
    try:
        logger.info(f"FIXED STATUS BUTTON: Processing status for user {user_id}")
        
        # Connect to database directly
        conn = sqlite3.connect('filot_bot.db')
        cursor = conn.cursor()
        
        # Get user info
        cursor.execute('''
            SELECT risk_profile, subscribed, wallet_address 
            FROM users WHERE id = ?
        ''', (user_id,))
        
        user_info = cursor.fetchone()
        
        # Default values
        risk_profile = "stable"  
        subscribed = False
        wallet_address = None
        
        if user_info:
            risk_profile = user_info[0] or risk_profile
            subscribed = bool(user_info[1])
            wallet_address = user_info[2]
        
        # Format user status
        wallet_text = "❌ Not Connected"
        if wallet_address:
            short_address = wallet_address[:6] + "..." + wallet_address[-4:]
            wallet_text = f"✅ Connected ({short_address})"
            
        profile_emoji = "🔴" if risk_profile == "high-risk" else "🟢"
        profile_text = f"{profile_emoji} {risk_profile.capitalize()}"
        
        subscription_text = "✅ Subscribed" if subscribed else "❌ Not Subscribed"
        
        # Get bot stats
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        
        conn.close()
        
        # Format message
        status_message = (
            "📊 *FiLot Bot Status* 📊\n\n"
            
            "*Your Account:*\n"
            f"• Wallet: {wallet_text}\n"
            f"• Risk Profile: {profile_text}\n"
            f"• Daily Updates: {subscription_text}\n\n"
            
            "*Bot Information:*\n"
            f"• Total Users: {user_count}\n"
            f"• Status: ✅ Online\n"
            f"• Version: 1.2.0\n\n"
            
            "*Need help?*\n"
            "Use the menu buttons below or send a message with your question."
        )
        
        return {
            "success": True,
            "message": status_message
        }
    
    except Exception as e:
        logger.error(f"Error in fixed status button handler: {e}", exc_info=True)
        
        # Fallback message
        return {
            "success": False,
            "message": (
                "📊 *FiLot Bot Status* 📊\n\n"
                "Bot is operational and ready to assist you.\n\n"
                "If you encounter any issues, please try again later."
            ),
            "error": str(e)
        }