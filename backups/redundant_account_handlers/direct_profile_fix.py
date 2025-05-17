"""
Direct profile button handler for both callback formats.
This fixes the profile buttons regardless of the callback format used.
"""

import logging
import sqlite3
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database file
DB_FILE = "filot_bot.db"

def process_profile_callback(callback_data: str, user_id: int, chat_id: int) -> Dict[str, Any]:
    """
    Process profile button callbacks.
    
    Args:
        callback_data: The callback data from the button press
        user_id: The user's ID
        chat_id: The chat ID
        
    Returns:
        Dict with success status and message
    """
    logger.info(f"Processing profile callback: {callback_data} for user {user_id}")
    
    # Determine which profile type was selected
    if callback_data in ["profile_high-risk", "account_profile_high-risk"]:
        profile_type = "high-risk"
    elif callback_data in ["profile_stable", "account_profile_stable"]:
        profile_type = "stable"
    else:
        logger.error(f"Unknown profile type in callback: {callback_data}")
        return {
            "success": False,
            "message": "Unknown profile type. Please try again."
        }
    
    # Update the user's profile in the database
    success = update_user_profile(user_id, profile_type)
    
    if success:
        # Return appropriate message based on profile type
        if profile_type == "high-risk":
            message = """
🔴 *High-Risk Profile Selected*

Your investment recommendations will now focus on:
• Higher APR opportunities
• Newer pools with growth potential
• More volatile but potentially rewarding options

_Note: Higher returns come with increased risk_
"""
        else:  # stable
            message = """
🟢 *Stable Profile Selected*

Your investment recommendations will now focus on:
• Established, reliable pools
• Lower volatility options
• More consistent but potentially lower APR

_Note: Stability typically means more moderate returns_
"""
        
        return {
            "success": True,
            "message": message,
            "profile_type": profile_type
        }
    else:
        return {
            "success": False,
            "message": "There was an error updating your profile. Please try again later."
        }

def update_user_profile(user_id: int, profile_type: str) -> bool:
    """
    Update user profile in database.
    
    Args:
        user_id: The user's ID
        profile_type: Either 'high-risk' or 'stable'
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Connect to database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Make sure the table exists
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
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        user_exists = cursor.fetchone() is not None
        
        if user_exists:
            # Update existing user
            logger.info(f"Updating existing user {user_id} with {profile_type} profile")
            cursor.execute("UPDATE users SET risk_profile = ? WHERE id = ?", (profile_type, user_id))
        else:
            # Create new user
            logger.info(f"Creating new user {user_id} with {profile_type} profile")
            cursor.execute(
                "INSERT INTO users (id, risk_profile, username) VALUES (?, ?, ?)",
                (user_id, profile_type, f"user_{user_id}")
            )
            
        # Commit and close
        conn.commit()
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Database error: {e}")
        return False