"""
Profile button fixer that integrates with the main bot.
This module will be imported in main.py to fix the profile buttons.
"""

import logging
import sqlite3
from typing import Dict, Any, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Main database file
DB_FILE = 'filot_bot.db'

def update_user_profile(user_id: int, profile_type: str) -> bool:
    """
    Update a user's risk profile directly in the database.
    
    Args:
        user_id: The user's ID
        profile_type: Either 'high-risk' or 'stable'
        
    Returns:
        True if update was successful, False otherwise
    """
    try:
        # Validate profile type
        if profile_type not in ['high-risk', 'stable']:
            logger.error(f"Invalid profile type: {profile_type}")
            return False
        
        # Connect to the database directly
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Make sure users table exists
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
        cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
        user_exists = cursor.fetchone()
        
        if user_exists:
            # Update existing user's profile
            logger.info(f"Updating profile for existing user {user_id} to {profile_type}")
            cursor.execute(
                'UPDATE users SET risk_profile = ? WHERE id = ?',
                (profile_type, user_id)
            )
        else:
            # Create new user with profile
            logger.info(f"Creating new user {user_id} with profile {profile_type}")
            cursor.execute(
                'INSERT INTO users (id, risk_profile, username, first_name, last_name) VALUES (?, ?, ?, ?, ?)',
                (user_id, profile_type, f"user_{user_id}", "User", "")
            )
        
        # Commit and close
        conn.commit()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        return False

def create_profile_message(profile_type: str) -> str:
    """
    Create a markdown message for the selected profile.
    
    Args:
        profile_type: Either 'high-risk' or 'stable'
        
    Returns:
        Formatted message string with markdown
    """
    # Format message based on profile type
    profile_emoji = "🔴" if profile_type == "high-risk" else "🟢"
    
    if profile_type == "high-risk":
        return (
            f"{profile_emoji} *High-Risk Profile Selected*\n\n"
            f"Your investment recommendations will now focus on:\n"
            f"• Higher APR opportunities\n"
            f"• Newer pools with growth potential\n"
            f"• More volatile but potentially rewarding options\n\n"
            f"_Note: Higher returns come with increased risk_"
        )
    else:  # stable
        return (
            f"{profile_emoji} *Stable Profile Selected*\n\n"
            f"Your investment recommendations will now focus on:\n"
            f"• Established, reliable pools\n"
            f"• Lower volatility options\n"
            f"• More consistent but potentially lower APR\n\n"
            f"_Note: Stability typically means more moderate returns_"
        )

def process_profile_callback(callback_data: str, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Process any of the profile-related callback patterns.
    
    Args:
        callback_data: The callback data string from the button
        user_id: The user ID
        
    Returns:
        Dict with results or None if not a profile button
    """
    profile_mapping = {
        # Handle both main formats
        "profile_high-risk": "high-risk",
        "account_profile_high-risk": "high-risk",
        "profile_stable": "stable",
        "account_profile_stable": "stable"
    }
    
    # Check if this is a profile button
    profile_type = profile_mapping.get(callback_data)
    
    if not profile_type:
        # Not a profile button
        return None
    
    # Update the user's profile
    success = update_user_profile(user_id, profile_type)
    
    if success:
        # Create the success message
        message = create_profile_message(profile_type)
        return {
            'success': True,
            'message': message
        }
    else:
        # Return error message
        return {
            'success': False,
            'message': "Sorry, there was an error updating your profile. Please try again later."
        }

# Import this function in main.py
def handle_profile_button(update: Any, context: Any, callback_data: str) -> bool:
    """
    Handle profile button clicks from the Telegram bot.
    
    Args:
        update: The update object from Telegram
        context: The context object from Telegram
        callback_data: The callback data from the button
        
    Returns:
        True if the button was handled, False otherwise
    """
    try:
        # Extract user ID
        user_id = update.callback_query.from_user.id
        
        # Process the callback
        result = process_profile_callback(callback_data, user_id)
        
        if not result:
            # Not a profile button
            return False
        
        # Handle the result
        if result['success']:
            # Send success message
            update.callback_query.message.edit_text(
                result['message'],
                parse_mode='Markdown'
            )
        else:
            # Send error message
            update.callback_query.message.edit_text(
                result['message']
            )
        
        # Answer the callback query to remove the loading indicator
        update.callback_query.answer()
        
        return True
        
    except Exception as e:
        logger.error(f"Error handling profile button: {e}")
        try:
            # Try to answer the callback query to remove the loading indicator
            update.callback_query.answer()
            # Send error message
            update.callback_query.message.edit_text(
                "Sorry, there was an error processing your request. Please try again later."
            )
        except:
            # If everything fails, at least log it
            logger.error("Failed to send error message.")
        
        return True  # We handled it, even though it failed