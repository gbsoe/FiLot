"""
Extremely simple and direct profile button handler.
No dependencies, no complex logic, just works.
"""

import logging
import sqlite3
from typing import Dict, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_profile_button(callback_data: str, user_id: int) -> Dict[str, Any]:
    """
    Ultra-simple profile button handler that works with any callback format.
    
    Args:
        callback_data: The callback data from button
        user_id: The user ID
        
    Returns:
        Dict with response message and success status
    """
    logger.info(f"Simple profile button handler processing: {callback_data}")
    
    # Determine profile type from callback data
    if "high-risk" in callback_data:
        profile_type = "high-risk"
    elif "stable" in callback_data:
        profile_type = "stable"
    else:
        return {
            "success": False,
            "message": "Unknown profile type."
        }
    
    # Update the profile in the database
    success = update_profile_direct(user_id, profile_type)
    
    if not success:
        return {
            "success": False,
            "message": "Sorry, there was a problem updating your profile. Please try again."
        }
    
    # Create response message based on profile type
    if profile_type == "high-risk":
        message = (
            "🔴 *High-Risk Profile Selected* 🔴\n\n"
            "Your investment recommendations will now focus on:\n"
            "• Higher APR opportunities\n"
            "• Newer pools with growth potential\n"
            "• More volatile but potentially rewarding options\n\n"
            "_Note: Higher returns come with increased risk_"
        )
    else:  # stable
        message = (
            "🟢 *Stable Profile Selected* 🟢\n\n"
            "Your investment recommendations will now focus on:\n"
            "• Consistent returns\n"
            "• Established pools with proven track records\n"
            "• Lower volatility options\n\n"
            "_Note: Stability typically means more moderate but reliable returns_"
        )
    
    return {
        "success": True,
        "message": message
    }

def update_profile_direct(user_id: int, profile_type: str) -> bool:
    """
    Update user profile directly in SQLite database.
    
    Args:
        user_id: User ID
        profile_type: Either 'high-risk' or 'stable'
        
    Returns:
        True if update succeeded, False otherwise
    """
    try:
        # Connect to the database
        conn = sqlite3.connect("filot_bot.db")
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT 1 FROM users WHERE id = ?", (user_id,))
        if cursor.fetchone() is None:
            # Create user if they don't exist
            logger.info(f"Creating new user record for {user_id}")
            cursor.execute(
                "INSERT INTO users (id, username, risk_profile) VALUES (?, ?, ?)",
                (user_id, f"user_{user_id}", profile_type)
            )
        else:
            # Update existing user
            logger.info(f"Updating risk profile to {profile_type} for user {user_id}")
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
        logger.error(f"Error updating profile: {e}")
        return False