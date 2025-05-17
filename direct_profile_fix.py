"""
Direct and isolated fix for profile buttons with no external dependencies.
This module handles both account_profile_* and profile_* button formats.
"""

import logging
import sqlite3
import json
from typing import Dict, Any, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database file
DB_FILE = "filot_bot.db"

def update_profile_in_db(user_id: int, profile_type: str) -> bool:
    """
    Update user profile directly in the database.
    
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
        
        # Create users table if it doesn't exist
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
            logger.info(f"Updating existing user {user_id} with profile {profile_type}")
            cursor.execute("UPDATE users SET risk_profile = ? WHERE id = ?", (profile_type, user_id))
        else:
            # Create new user
            logger.info(f"Creating new user {user_id} with profile {profile_type}")
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

def create_profile_response(profile_type: str) -> Dict[str, Any]:
    """
    Create a standardized response for profile selection.
    
    Args:
        profile_type: Either 'high-risk' or 'stable'
        
    Returns:
        Dict with success status and message
    """
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

def handle_profile_button(callback_data: str, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Handle profile button callbacks with any format.
    
    Args:
        callback_data: The callback data from the button
        user_id: The user's ID
        
    Returns:
        Dict with response or None if not a profile button
    """
    # Define all possible profile button formats
    profile_mapping = {
        # Main menu versions
        "profile_high-risk": "high-risk",
        "profile_stable": "stable",
        # Account menu versions
        "account_profile_high-risk": "high-risk",
        "account_profile_stable": "stable"
    }
    
    # Check if this is a profile button
    profile_type = profile_mapping.get(callback_data)
    if not profile_type:
        # Not a profile button we handle
        return None
    
    # Log this action
    logger.info(f"Processing {callback_data} button for user {user_id}")
    
    # Update the database
    success = update_profile_in_db(user_id, profile_type)
    
    if success:
        # Return successful response
        return create_profile_response(profile_type)
    else:
        # Return error response
        return {
            "success": False,
            "message": "Sorry, there was an error updating your profile. Please try again later."
        }

# Function for direct Telegram integration
def process_callback_query(update: Any, context: Any) -> bool:
    """
    Process callback query for profile buttons directly in Telegram.
    
    Args:
        update: The Telegram update object
        context: The Telegram context object
        
    Returns:
        True if handled, False otherwise
    """
    try:
        # Extract essential data
        query = update.callback_query
        callback_data = query.data
        user_id = query.from_user.id
        
        # Process the button
        result = handle_profile_button(callback_data, user_id)
        
        if result is None:
            # Not our button
            return False
            
        # Answer the callback
        query.answer()
        
        # Update the message
        if result["success"]:
            query.edit_message_text(
                text=result["message"],
                parse_mode="Markdown"
            )
        else:
            query.edit_message_text(text=result["message"])
            
        return True
        
    except Exception as e:
        logger.error(f"Error in process_callback_query: {e}")
        try:
            # Try to send an error message
            update.callback_query.answer()
            update.callback_query.edit_message_text(
                "Sorry, there was an error processing your request."
            )
        except:
            pass
        return True  # We tried to handle it