"""
Direct handler for account profile buttons.
This module provides a simple and reliable handler for the profile buttons
without relying on complex database queries.
"""

import logging
import sqlite3
from typing import Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_profile_button(callback_data: str, user_id: int) -> Dict[str, Any]:
    """
    Direct handler for profile buttons that updates the database and returns a message.
    
    Args:
        callback_data: The button's callback data
        user_id: The user's ID
        
    Returns:
        Dict with success status and message
    """
    logger.info(f"Direct profile handler processing: {callback_data} for user {user_id}")
    
    # Determine profile type from callback data
    if "high-risk" in callback_data:
        profile_type = "high-risk"
        message = (
            "🔴 *High-Risk Profile Selected* 🔴\n\n"
            "Your investment recommendations will now focus on:\n"
            "• Higher APR opportunities\n"
            "• Newer pools with growth potential\n"
            "• More volatile but potentially rewarding options\n\n"
            "_Note: Higher returns come with increased risk_"
        )
    elif "stable" in callback_data:
        profile_type = "stable"
        message = (
            "🟢 *Stable Profile Selected* 🟢\n\n"
            "Your investment recommendations will now focus on:\n"
            "• Consistent returns\n"
            "• Established pools with proven track records\n"
            "• Lower volatility options\n\n"
            "_Note: Stability typically means more moderate but reliable returns_"
        )
    else:
        logger.error(f"Unknown profile type in callback data: {callback_data}")
        return {
            "success": False,
            "message": "Unknown profile type. Please try again."
        }
    
    # Update the user's profile in the database
    success = update_user_profile(user_id, profile_type)
    
    if not success:
        logger.error(f"Failed to update profile for user {user_id}")
        return {
            "success": False,
            "message": "Failed to update your profile. Please try again."
        }
    
    return {
        "success": True,
        "message": message
    }

def update_user_profile(user_id: int, profile_type: str) -> bool:
    """
    Update a user's profile directly in the SQLite database.
    
    Args:
        user_id: The user's ID
        profile_type: The profile type ('high-risk' or 'stable')
        
    Returns:
        True if the update was successful, False otherwise
    """
    try:
        # Connect to the database
        conn = sqlite3.connect("filot_bot.db")
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute("""
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
        """)
        
        # Check if user exists
        cursor.execute("SELECT 1 FROM users WHERE id = ?", (user_id,))
        if cursor.fetchone() is None:
            # User doesn't exist, create new user
            logger.info(f"Creating new user {user_id} with profile {profile_type}")
            cursor.execute(
                "INSERT INTO users (id, risk_profile) VALUES (?, ?)",
                (user_id, profile_type)
            )
        else:
            # User exists, update their profile
            logger.info(f"Updating profile for user {user_id} to {profile_type}")
            cursor.execute(
                "UPDATE users SET risk_profile = ? WHERE id = ?",
                (profile_type, user_id)
            )
        
        # Commit changes
        conn.commit()
        
        # Close connection
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        return False