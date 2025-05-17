"""
Extremely direct simple fix for profile buttons.
This script directly handles the two profile button formats.
"""

import logging
import sqlite3

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database file
DB_FILE = "filot_bot.db"

def set_user_profile(user_id, profile_type):
    """
    Set a user's profile directly in the database.
    
    Args:
        user_id: The user's ID
        profile_type: Either 'high-risk' or 'stable'
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            # Update existing user
            cursor.execute(
                "UPDATE users SET risk_profile = ? WHERE id = ?",
                (profile_type, user_id)
            )
        else:
            # Create new user with this profile
            cursor.execute(
                "INSERT INTO users (id, username, first_name, last_name, risk_profile) VALUES (?, ?, ?, ?, ?)",
                (user_id, f"user_{user_id}", "User", "", profile_type)
            )
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error setting user profile: {e}")
        return False

def handle_profile_button(callback_data, user_id):
    """
    Handle profile button callback by directly updating the database.
    
    Args:
        callback_data: The callback data from the button
        user_id: The user's ID
        
    Returns:
        Dict with success status and message
    """
    # Map callback data to profile type
    profile_mapping = {
        "profile_high-risk": "high-risk",
        "account_profile_high-risk": "high-risk",
        "profile_stable": "stable",
        "account_profile_stable": "stable"
    }
    
    profile_type = profile_mapping.get(callback_data)
    
    if not profile_type:
        return {
            "success": False,
            "message": f"Unknown profile type: {callback_data}"
        }
    
    # Update the profile
    success = set_user_profile(user_id, profile_type)
    
    if not success:
        return {
            "success": False,
            "message": "Failed to update your profile. Please try again."
        }
    
    # Create appropriate message
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
        "message": message
    }