"""
Simple utility script to fix the account buttons directly via commands.
"""

import sqlite3
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Messages
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

def fix_profile_high_risk(user_id):
    """
    Direct command to set profile to high-risk.
    
    Args:
        user_id: User's ID
        
    Returns:
        Message to send to the user
    """
    try:
        conn = sqlite3.connect('filot_bot.db')
        cursor = conn.cursor()
        
        # Ensure user exists
        cursor.execute("SELECT id FROM users WHERE id=?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            # Update existing user
            cursor.execute("UPDATE users SET risk_profile = 'high-risk' WHERE id = ?", (user_id,))
            logger.info(f"Updated user {user_id} profile to high-risk")
        else:
            # Create new user
            cursor.execute("INSERT INTO users (id, risk_profile) VALUES (?, 'high-risk')", (user_id,))
            logger.info(f"Created new user {user_id} with high-risk profile")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        return HIGH_RISK_MESSAGE
        
    except Exception as e:
        logger.error(f"Error setting high-risk profile: {e}")
        return "Sorry, there was an error setting your profile to high-risk. Please try again."

def fix_profile_stable(user_id):
    """
    Direct command to set profile to stable.
    
    Args:
        user_id: User's ID
        
    Returns:
        Message to send to the user
    """
    try:
        conn = sqlite3.connect('filot_bot.db')
        cursor = conn.cursor()
        
        # Ensure user exists
        cursor.execute("SELECT id FROM users WHERE id=?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            # Update existing user
            cursor.execute("UPDATE users SET risk_profile = 'stable' WHERE id = ?", (user_id,))
            logger.info(f"Updated user {user_id} profile to stable")
        else:
            # Create new user
            cursor.execute("INSERT INTO users (id, risk_profile) VALUES (?, 'stable')", (user_id,))
            logger.info(f"Created new user {user_id} with stable profile")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        return STABLE_PROFILE_MESSAGE
        
    except Exception as e:
        logger.error(f"Error setting stable profile: {e}")
        return "Sorry, there was an error setting your profile to stable. Please try again."

def get_wallet_connect_options():
    """
    Get wallet connection options.
    
    Returns:
        Dict with message and keyboard
    """
    return {
        "message": """
🔐 *Connect Your Wallet* 🔐

Choose how you want to connect your wallet:

1. *Address Entry* - Enter your wallet address manually
2. *QR Code* - Scan a QR code with your wallet app

_Your private keys always remain secure in your wallet._
""",
        "keyboard": {
            "inline_keyboard": [
                [{"text": "Enter Wallet Address", "callback_data": "wallet_connect_address"}],
                [{"text": "Connect via QR Code", "callback_data": "wallet_connect_qr"}],
                [{"text": "⬅️ Back to Account", "callback_data": "menu_account"}]
            ]
        }
    }

if __name__ == "__main__":
    # Test code - only runs when script is executed directly
    import sys
    if len(sys.argv) < 3:
        print("Usage: python fix_account_buttons.py <user_id> <profile_type>")
        print("Example: python fix_account_buttons.py 12345678 high-risk")
        sys.exit(1)
    
    user_id = int(sys.argv[1])
    profile_type = sys.argv[2]
    
    if profile_type == "high-risk":
        message = fix_profile_high_risk(user_id)
    elif profile_type == "stable":
        message = fix_profile_stable(user_id)
    else:
        print(f"Invalid profile type: {profile_type}")
        sys.exit(1)
    
    print(message)
    print(f"Profile set to {profile_type} for user {user_id}")