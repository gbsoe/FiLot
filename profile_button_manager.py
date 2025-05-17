"""
Completely isolated profile button handler to fix the Account section buttons.
This module directly modifies the database with no dependencies on other modules.
"""

import sqlite3
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Messages for each profile type
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

def handle_profile_button(user_id, callback_data):
    """
    Direct handler for profile buttons with no external dependencies.
    
    Args:
        user_id: User's Telegram ID
        callback_data: The callback data string
    
    Returns:
        Tuple of (success, message)
    """
    logger.info(f"Processing profile button: {callback_data} for user {user_id}")
    
    # Map callback data to profile types
    if callback_data in ["profile_high-risk", "account_profile_high-risk"]:
        profile_type = "high-risk"
        message = HIGH_RISK_MESSAGE
    elif callback_data in ["profile_stable", "account_profile_stable"]:
        profile_type = "stable"
        message = STABLE_PROFILE_MESSAGE
    else:
        logger.error(f"Unrecognized profile button: {callback_data}")
        return False, f"Unrecognized profile button: {callback_data}"
    
    try:
        # Connect to database directly
        conn = sqlite3.connect('filot_bot.db')
        cursor = conn.cursor()
        
        # Create table if needed
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
            logger.info(f"Updated existing user {user_id} profile to {profile_type}")
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
        
        return True, message
        
    except Exception as e:
        logger.error(f"Error in handle_profile_button: {e}")
        return False, f"Database error: {str(e)}"

def get_wallet_connection_markup():
    """
    Get the keyboard markup for wallet connection options.
    
    Returns:
        Dict containing inline keyboard markup
    """
    return {
        "inline_keyboard": [
            [{"text": "Enter Wallet Address", "callback_data": "wallet_connect_address"}],
            [{"text": "Connect via QR Code", "callback_data": "wallet_connect_qr"}],
            [{"text": "⬅️ Back to Account", "callback_data": "menu_account"}]
        ]
    }

def get_wallet_message():
    """
    Get the message for wallet connection options.
    
    Returns:
        String with wallet connection message
    """
    return """
🔐 *Connect Your Wallet* 🔐

Choose how you want to connect your wallet:

1. *Address Entry* - Enter your wallet address manually
2. *QR Code* - Scan a QR code with your wallet app

_Your private keys always remain secure in your wallet._
"""