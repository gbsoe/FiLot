"""
Direct fix for account section buttons.
This is a simple, focused solution for the problematic buttons in the account section.
"""

import logging
import sqlite3
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_profile_high_risk(user_id):
    """
    Set user profile to high-risk using direct database access.
    
    Args:
        user_id: The user's Telegram ID
        
    Returns:
        Success message
    """
    try:
        logger.info(f"Setting high-risk profile for user {user_id}")
        
        # Connect to SQLite database directly
        conn = sqlite3.connect('filot_bot.db')
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
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
            # Update user's profile
            cursor.execute("UPDATE users SET risk_profile = 'high-risk' WHERE id = ?", (user_id,))
            logger.info(f"Updated existing user {user_id} profile to high-risk")
        else:
            # Insert new user with high-risk profile
            cursor.execute("INSERT INTO users (id, risk_profile) VALUES (?, 'high-risk')", (user_id,))
            logger.info(f"Created new user {user_id} with high-risk profile")
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        # Return success message
        return (
            "🔴 *High-Risk Profile Selected*\n\n"
            "Your investment recommendations will now focus on:\n"
            "• Higher APR opportunities\n"
            "• Newer pools with growth potential\n"
            "• More volatile but potentially rewarding options\n\n"
            "_Note: Higher returns come with increased risk_"
        )
        
    except Exception as e:
        logger.error(f"Error setting high-risk profile: {e}")
        logger.error(traceback.format_exc())
        return None

def fix_profile_stable(user_id):
    """
    Set user profile to stable using direct database access.
    
    Args:
        user_id: The user's Telegram ID
        
    Returns:
        Success message
    """
    try:
        logger.info(f"Setting stable profile for user {user_id}")
        
        # Connect to SQLite database directly
        conn = sqlite3.connect('filot_bot.db')
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
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
            # Update user's profile
            cursor.execute("UPDATE users SET risk_profile = 'stable' WHERE id = ?", (user_id,))
            logger.info(f"Updated existing user {user_id} profile to stable")
        else:
            # Insert new user with stable profile
            cursor.execute("INSERT INTO users (id, risk_profile) VALUES (?, 'stable')", (user_id,))
            logger.info(f"Created new user {user_id} with stable profile")
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        # Return success message
        return (
            "🟢 *Stable Profile Selected*\n\n"
            "Your investment recommendations will now focus on:\n"
            "• Established, reliable pools\n"
            "• Lower volatility options\n"
            "• More consistent but potentially lower APR\n\n"
            "_Note: Stability typically means more moderate returns_"
        )
        
    except Exception as e:
        logger.error(f"Error setting stable profile: {e}")
        logger.error(traceback.format_exc())
        return None

def get_wallet_connect_options():
    """
    Get wallet connection options markup.
    
    Returns:
        Dict with message and keyboard markup
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
            "message": wallet_message,
            "keyboard": keyboard
        }
        
    except Exception as e:
        logger.error(f"Error creating wallet options: {e}")
        logger.error(traceback.format_exc())
        return None