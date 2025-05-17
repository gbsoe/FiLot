"""
Direct fix for ALL button issues in the account section.
This module provides both 'account_profile_*' and 'profile_*' handlers.
"""

import logging
import sqlite3
import traceback
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_button(callback_data: str, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Universal handler for both callback formats:
    - account_profile_high-risk
    - account_profile_stable 
    - profile_high-risk
    - profile_stable
    
    Args:
        callback_data: The callback data from the button
        user_id: The user's ID
        
    Returns:
        Dict with result or None if button isn't handled
    """
    # Map button callbacks to profile types
    profile_mapping = {
        # Account section buttons
        "account_profile_high-risk": "high-risk",
        "account_profile_stable": "stable",
        # Alternative formats that seem to be needed
        "profile_high-risk": "high-risk",
        "profile_stable": "stable"
    }
    
    # Extract the profile type if this is a profile button
    profile_type = profile_mapping.get(callback_data)
    
    if profile_type:
        # This is a profile button, handle it
        return set_profile(user_id, profile_type)
    elif callback_data in ["account_wallet", "wallet"]:
        # This is a wallet button
        return get_wallet_options()
    else:
        # Not a button we handle
        return None

def set_profile(user_id: int, profile_type: str) -> Dict[str, Any]:
    """
    Set user profile using direct database access.
    
    Args:
        user_id: The user's ID
        profile_type: Either 'high-risk' or 'stable'
        
    Returns:
        Dict with success status and message
    """
    try:
        logger.info(f"Setting {profile_type} profile for user {user_id}")
        
        # Validate profile type
        if profile_type not in ['high-risk', 'stable']:
            return {
                "success": False,
                "message": f"Invalid profile type: {profile_type}"
            }
        
        # Connect to database directly
        conn = sqlite3.connect('filot_bot.db')
        cursor = conn.cursor()
        
        # Create table if doesn't exist
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
            logger.info(f"Updated profile for existing user {user_id}")
        else:
            # Create new user
            cursor.execute(
                'INSERT INTO users (id, risk_profile) VALUES (?, ?)',
                (user_id, profile_type)
            )
            logger.info(f"Created new user {user_id} with profile {profile_type}")
        
        # Commit and close
        conn.commit()
        conn.close()
        
        # Format message based on profile type
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
            
        return {
            "success": True,
            "message": profile_message
        }
        
    except Exception as e:
        logger.error(f"Error in profile button handler: {e}")
        logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": "Sorry, there was an error setting your profile. Please try again later."
        }

def get_wallet_options() -> Dict[str, Any]:
    """
    Get wallet connection options.
    
    Returns:
        Dict with success status, message, and keyboard markup
    """
    try:
        wallet_message = (
            "🔐 *Connect Your Wallet* 🔐\n\n"
            "Choose how you want to connect your wallet:\n\n"
            "1. *Address Entry* - Enter your wallet address manually\n"
            "2. *QR Code* - Scan a QR code with your wallet app\n\n"
            "_Your private keys always remain secure in your wallet._"
        )
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "Enter Wallet Address", "callback_data": "wallet_connect_address"}],
                [{"text": "Connect via QR Code", "callback_data": "wallet_connect_qr"}],
                [{"text": "⬅️ Back to Account", "callback_data": "menu_account"}]
            ]
        }
        
        return {
            "success": True,
            "message": wallet_message,
            "keyboard": keyboard
        }
        
    except Exception as e:
        logger.error(f"Error getting wallet options: {e}")
        logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": "Sorry, there was an error with the wallet connection. Please try again later."
        }