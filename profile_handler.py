"""
Special handler for profile buttons in the account section.
"""

import logging
import sqlite3
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_high_risk_profile(user_id):
    """Handle high-risk profile selection"""
    try:
        logger.info(f"Setting high-risk profile for user {user_id}")
        
        # Connect to database
        conn = sqlite3.connect('filot_bot.db')
        cursor = conn.cursor()
        
        # Create tables if needed
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
            cursor.execute("UPDATE users SET risk_profile = ? WHERE id = ?", ("high-risk", user_id))
            logger.info(f"Updated existing user {user_id} profile to high-risk")
        else:
            # Create new user
            cursor.execute(
                "INSERT INTO users (id, risk_profile) VALUES (?, ?)",
                (user_id, "high-risk")
            )
            logger.info(f"Created new user {user_id} with high-risk profile")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        # Return success message
        profile_message = (
            "🔴 *High-Risk Profile Selected*\n\n"
            "Your investment recommendations will now focus on:\n"
            "• Higher APR opportunities\n"
            "• Newer pools with growth potential\n"
            "• More volatile but potentially rewarding options\n\n"
            "_Note: Higher returns come with increased risk_"
        )
        
        return {
            "success": True,
            "message": profile_message
        }
    
    except Exception as e:
        logger.error(f"Error handling high-risk profile: {e}")
        logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": "Sorry, there was an error updating your profile."
        }

def handle_stable_profile(user_id):
    """Handle stable profile selection"""
    try:
        logger.info(f"Setting stable profile for user {user_id}")
        
        # Connect to database
        conn = sqlite3.connect('filot_bot.db')
        cursor = conn.cursor()
        
        # Create tables if needed
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
            cursor.execute("UPDATE users SET risk_profile = ? WHERE id = ?", ("stable", user_id))
            logger.info(f"Updated existing user {user_id} profile to stable")
        else:
            # Create new user
            cursor.execute(
                "INSERT INTO users (id, risk_profile) VALUES (?, ?)",
                (user_id, "stable")
            )
            logger.info(f"Created new user {user_id} with stable profile")
        
        # Commit changes
        conn.commit()
        conn.close()
        
        # Return success message
        profile_message = (
            "🟢 *Stable Profile Selected*\n\n"
            "Your investment recommendations will now focus on:\n"
            "• Established, reliable pools\n"
            "• Lower volatility options\n"
            "• More consistent but potentially lower APR\n\n"
            "_Note: Stability typically means more moderate returns_"
        )
        
        return {
            "success": True,
            "message": profile_message
        }
    
    except Exception as e:
        logger.error(f"Error handling stable profile: {e}")
        logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": "Sorry, there was an error updating your profile."
        }