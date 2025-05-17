"""
Simple, reliable profile handler with no dependencies.
This module provides a direct way to handle profile buttons
without relying on complex database operations.
"""

import logging
import sqlite3
from typing import Dict, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_profile_button(callback_data: str, user_id: int) -> Dict[str, Any]:
    """
    Handle profile button clicks (High-Risk or Stable) in the simplest possible way.
    
    Args:
        callback_data: Callback data from the button
        user_id: User ID
        
    Returns:
        Dict with response message and success status
    """
    try:
        # Extract profile type from callback data
        if "high-risk" in callback_data:
            profile_type = "high-risk"
        elif "stable" in callback_data:
            profile_type = "stable"
        else:
            return {
                "success": False,
                "message": "❌ Invalid profile type. Please try again."
            }
        
        # Update user profile directly in the database
        success = update_profile_direct(user_id, profile_type)
        
        if success:
            # Create success message based on profile type
            if profile_type == "high-risk":
                message = (
                    "🔴 *High-Risk Profile Selected* 🔴\n\n"
                    "You've chosen a high-risk investment strategy which focuses on:\n"
                    "• Higher potential returns\n"
                    "• Newer and more volatile pools\n"
                    "• Less established protocols\n\n"
                    "We'll now show you higher-risk, higher-reward opportunities."
                )
            else:  # stable
                message = (
                    "🟢 *Stable Profile Selected* 🟢\n\n"
                    "You've chosen a stable investment strategy which focuses on:\n"
                    "• Consistent returns\n"
                    "• Lower volatility\n"
                    "• Established protocols with longer track records\n\n"
                    "We'll now show you safer, more reliable opportunities."
                )
            
            return {
                "success": True,
                "message": message
            }
        else:
            return {
                "success": False,
                "message": "❌ There was a problem updating your profile. Please try again."
            }
    except Exception as e:
        logger.error(f"Error in handle_profile_button: {e}")
        return {
            "success": False,
            "message": "❌ An error occurred while updating your profile. Please try again."
        }

def update_profile_direct(user_id: int, profile_type: str) -> bool:
    """
    Update user profile directly in the SQLite database.
    
    Args:
        user_id: User ID
        profile_type: Either 'high-risk' or 'stable'
        
    Returns:
        True if update was successful, False otherwise
    """
    try:
        # Connect directly to the database
        conn = sqlite3.connect("filot_bot.db")
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT 1 FROM users WHERE id = ?", (user_id,))
        if cursor.fetchone() is None:
            # Create user if they don't exist
            cursor.execute(
                "INSERT INTO users (id, risk_profile) VALUES (?, ?)",
                (user_id, profile_type)
            )
        else:
            # Update existing user
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
        logger.error(f"Error in update_profile_direct: {e}")
        return False

def process_profile_callback(callback_data: str, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Process profile button callbacks from multiple formats.
    
    Args:
        callback_data: Callback data from button
        user_id: User ID
        
    Returns:
        Response dict if it's a profile button, None otherwise
    """
    # Support multiple callback data formats for backward compatibility
    if any(x in callback_data for x in ["profile_high-risk", "profile_stable", 
                                        "account_profile_high-risk", "account_profile_stable"]):
        return handle_profile_button(callback_data, user_id)
    
    return None