"""
Simple direct account handler to fix the account access error.
This bypasses the complex database queries that might be failing.
"""

import logging
import sqlite3
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database file
DB_FILE = "filot_bot.db"

def get_account_info(user_id: int) -> Dict[str, Any]:
    """
    Get basic account info directly from SQLite database.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dict with account information
    """
    try:
        # Connect to database with direct SQLite3 connection
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            logger.info(f"Creating users table for user {user_id}")
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                risk_profile TEXT DEFAULT 'stable',
                investment_horizon TEXT DEFAULT 'medium',
                subscribed BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                wallet_address TEXT,
                verification_code TEXT,
                verified BOOLEAN DEFAULT 0
            )
            ''')
            conn.commit()
        
        # Check if user exists
        cursor.execute("SELECT id, risk_profile, subscribed, wallet_address FROM users WHERE id = ?", (user_id,))
        user_record = cursor.fetchone()
        
        conn.close()
        
        if user_record:
            # User exists - extract info
            user_id, risk_profile, subscribed, wallet_address = user_record
            
            # Format wallet status
            wallet_status = "❌ Not Connected"
            if wallet_address:
                wallet_status = f"✅ Connected ({wallet_address[:6]}...{wallet_address[-4:]})"
            
            # Format profile type
            profile_type = "Not Set"
            if risk_profile:
                profile_type = risk_profile.capitalize()
            
            # Format subscription status
            subscription_status = "❌ Not Subscribed"
            if subscribed:
                subscription_status = "✅ Subscribed"
            
            return {
                "success": True,
                "user_id": user_id,
                "wallet_status": wallet_status,
                "profile_type": profile_type,
                "subscription_status": subscription_status
            }
        else:
            # User doesn't exist - return default info
            logger.info(f"User {user_id} not found, creating new record")
            
            # Create the user
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (id, username) VALUES (?, ?)",
                (user_id, f"user_{user_id}")
            )
            conn.commit()
            conn.close()
            
            # Return default info
            return {
                "success": True,
                "user_id": user_id,
                "wallet_status": "❌ Not Connected",
                "profile_type": "Not Set",
                "subscription_status": "❌ Not Subscribed"
            }
    except Exception as e:
        logger.error(f"Database error: {e}")
        # Return default info on error
        return {
            "success": False,
            "error": str(e),
            "fallback_message": "👤 *Your Account* 👤\n\n"
                               "*Wallet:* ❌ Not Connected\n"
                               "*Risk Profile:* Not Set\n"
                               "*Daily Updates:* ❌ Not Subscribed\n\n"
                               "Select an option below to manage your account:"
        }