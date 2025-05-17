"""
Direct command handlers for the FiLot Telegram bot.
These commands provide a direct way to set user profiles and other settings.
"""

import sqlite3
import logging
import re
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Success messages
HIGH_RISK_MESSAGE = """
🔴 *High-Risk Profile Selected*

Your investment recommendations will now focus on:
• Higher APR opportunities
• Newer pools with growth potential
• More volatile but potentially rewarding options

_Note: Higher returns come with increased risk_
"""

STABLE_PROFILE_MESSAGE = """
🟢 *Stable Profile Selected*

Your investment recommendations will now focus on:
• Established, reliable pools
• Lower volatility options
• More consistent but potentially lower APR

_Note: Stability typically means more moderate returns_
"""

def process_set_profile_command(user_id: int, message_text: str) -> Tuple[bool, str]:
    """
    Process the /set_profile command to directly set a user's risk profile.
    
    Args:
        user_id: The user's Telegram ID
        message_text: The full command text including arguments
        
    Returns:
        Tuple of (success, message)
    """
    # Extract the profile type from the message
    match = re.search(r'/set_profile\s+(\S+)', message_text)
    
    if not match:
        return False, "Please specify a profile type: /set_profile high-risk or /set_profile stable"
    
    profile_type = match.group(1).lower()
    
    # Validate the profile type
    if profile_type not in ["high-risk", "stable"]:
        return False, "Invalid profile type. Please use either 'high-risk' or 'stable'."
    
    try:
        # Connect to the database
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
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        user_exists = cursor.fetchone()
        
        if user_exists:
            # Update existing user
            cursor.execute(
                "UPDATE users SET risk_profile = ? WHERE id = ?",
                (profile_type, user_id)
            )
            logger.info(f"Updated user {user_id} profile to {profile_type}")
        else:
            # Create new user with profile
            cursor.execute(
                "INSERT INTO users (id, risk_profile) VALUES (?, ?)",
                (user_id, profile_type)
            )
            logger.info(f"Created new user {user_id} with {profile_type} profile")
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        # Return success message based on profile type
        if profile_type == "high-risk":
            return True, HIGH_RISK_MESSAGE
        else:  # stable
            return True, STABLE_PROFILE_MESSAGE
            
    except Exception as e:
        logger.error(f"Error setting profile: {e}")
        return False, f"Sorry, there was an error setting your profile: {str(e)}"

def process_wallet_connect_command(user_id: int) -> dict:
    """
    Process the /connect_wallet command to show wallet connection options.
    
    Args:
        user_id: The user's Telegram ID
        
    Returns:
        Dict with message and keyboard markup
    """
    wallet_message = """
🔐 *Connect Your Wallet* 🔐

Choose how you want to connect your wallet:

1. *Address Entry* - Enter your wallet address manually
2. *QR Code* - Scan a QR code with your wallet app

_Your private keys always remain secure in your wallet._
"""

    wallet_keyboard = {
        "inline_keyboard": [
            [{"text": "Enter Wallet Address", "callback_data": "wallet_connect_address"}],
            [{"text": "Connect via QR Code", "callback_data": "wallet_connect_qr"}],
            [{"text": "⬅️ Back to Account", "callback_data": "menu_account"}]
        ]
    }
    
    return {
        "message": wallet_message,
        "keyboard": wallet_keyboard
    }