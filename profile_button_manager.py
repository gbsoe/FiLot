"""
Completely isolated button handler to fix the Account section buttons.
This module directly handles profile and wallet buttons with no dependencies on other modules.
"""

import sqlite3
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Messages for each profile type
HIGH_RISK_MESSAGE = """
🔴 *High-Risk Profile Selected*

Your investment recommendations will now focus on:
• Higher APR opportunities
• Newer pools with growth potential
• More volatile but potentially rewarding options

_Note: Higher returns come with increased risk_
"""

STABLE_PROFILE_MESSAGE = """
🟢 *Stable Profile Selected*

Your investment recommendations will now focus on:
• Established, reliable pools
• Lower volatility options
• More consistent but potentially lower APR

_Note: Stability typically means more moderate returns_
"""

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
        # Connect to database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Create table if not exists
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
            cursor.execute(
                "UPDATE users SET risk_profile = ? WHERE id = ?",
                (profile_type, user_id)
            )
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
        logger.error(f"Error setting user profile: {e}")
        return False

def handle_profile_button(callback_data, user_id):
    """
    Handle profile button press with any format.
    
    Args:
        callback_data: The callback data from the button
        user_id: The user's ID
        
    Returns:
        Dict with success status and message
    """
    # Map all known callback formats to profile types
    profile_mapping = {
        # Account section buttons
        "account_profile_high-risk": "high-risk",
        "account_profile_stable": "stable",
        # Alternative formats
        "profile_high-risk": "high-risk",
        "profile_stable": "stable"
    }
    
    # Check if this is a profile button
    profile_type = profile_mapping.get(callback_data)
    
    if not profile_type:
        # Not a profile button
        return None
        
    # Update the profile
    success = set_user_profile(user_id, profile_type)
    
    if not success:
        return {
            "success": False,
            "message": "Sorry, there was an error updating your profile. Please try again later."
        }
        
    # Format response based on profile type
    message = HIGH_RISK_MESSAGE if profile_type == "high-risk" else STABLE_PROFILE_MESSAGE
    
    return {
        "success": True,
        "message": message
    }
    
def process_button_callback(update, context):
    """
    Process a button callback from Telegram.
    
    Args:
        update: The Telegram update
        context: The Telegram context
        
    Returns:
        True if handled, False if not
    """
    try:
        query = update.callback_query
        callback_data = query.data
        user_id = query.from_user.id
        
        # Process the button
        result = handle_profile_button(callback_data, user_id)
        
        if not result:
            # Not our button
            return False
            
        # Answer the callback query
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
        logger.error(f"Error processing button callback: {e}")
        try:
            # Try to send error message
            update.callback_query.answer()
            update.callback_query.edit_message_text(
                "Sorry, there was an error processing your request."
            )
        except:
            pass
        return True  # We tried to handle it