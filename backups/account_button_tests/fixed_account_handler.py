"""
Fixed account handler to properly handle profile buttons
with both callback data formats.
"""

import logging
import sqlite3
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database file
DB_FILE = "filot_bot.db"

def handle_account_button(callback_data: str, user_id: int) -> Dict[str, Any]:
    """
    Handle account button clicks with improved error handling
    for both callback data formats.
    
    Args:
        callback_data: The callback data from the button
        user_id: The user's ID
        
    Returns:
        Dict with success status and message
    """
    logger.info(f"Fixed account handler processing: {callback_data} for user {user_id}")
    
    # Check if this is a profile button
    if callback_data in ["profile_high-risk", "account_profile_high-risk"]:
        return update_profile(user_id, "high-risk")
    elif callback_data in ["profile_stable", "account_profile_stable"]:
        return update_profile(user_id, "stable")
    else:
        logger.info(f"Callback data {callback_data} not handled by fixed_account_handler")
        return {
            "success": False,
            "message": "This button is not a profile button."
        }

def update_profile(user_id: int, profile_type: str) -> Dict[str, Any]:
    """
    Update user profile in database with improved error handling.
    
    Args:
        user_id: The user's ID
        profile_type: Either 'high-risk' or 'stable'
        
    Returns:
        Dict with success status and message
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
        
        # Create success message based on profile type
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
    except Exception as e:
        logger.error(f"Database error: {e}")
        return {
            "success": False,
            "message": "There was an error updating your profile. Please try again later."
        }