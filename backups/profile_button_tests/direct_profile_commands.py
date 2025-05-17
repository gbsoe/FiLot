"""
Direct command handlers for profile selection.
This module provides a reliable way to set profiles through commands.
"""

import logging
import sqlite3
from typing import Dict, Any, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database file
DB_FILE = "filot_bot.db"

def set_user_profile(user_id: int, profile_type: str) -> bool:
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
        
        # Create table if it doesn't exist
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

def get_profile_message(profile_type: str) -> str:
    """
    Get formatted message for the selected profile.
    
    Args:
        profile_type: Either 'high-risk' or 'stable'
        
    Returns:
        Formatted message
    """
    if profile_type == "high-risk":
        return """
🔴 *High-Risk Profile Selected*

Your investment recommendations will now focus on:
• Higher APR opportunities
• Newer pools with growth potential
• More volatile but potentially rewarding options

_Note: Higher returns come with increased risk_
"""
    else:  # stable
        return """
🟢 *Stable Profile Selected*

Your investment recommendations will now focus on:
• Established, reliable pools
• Lower volatility options
• More consistent but potentially lower APR

_Note: Stability typically means more moderate returns_
"""

def set_risk_profile_command(update: Any, context: Any, profile_type: Optional[str] = None) -> None:
    """
    Direct command handler to set risk profile.
    
    Args:
        update: The Telegram update
        context: The Telegram context
        profile_type: Optional profile type override (high-risk or stable)
    """
    try:
        user = update.message.from_user
        user_id = user.id
        
        # If profile type is not specified, check if it's in the command arguments
        if not profile_type and context.args:
            arg = context.args[0].lower()
            if arg in ["high-risk", "highrisk", "high_risk", "high"]:
                profile_type = "high-risk"
            elif arg in ["stable", "conservative", "safe"]:
                profile_type = "stable"
                
        # If still no profile type, show help message
        if not profile_type:
            update.message.reply_markdown(
                "Please specify a risk profile:\n\n"
                "• `/high_risk` - For higher APR but more volatile investments\n"
                "• `/stable` - For more conservative, stable investments"
            )
            return
            
        # Set the profile
        success = set_user_profile(user_id, profile_type)
        
        if success:
            # Send success message
            update.message.reply_markdown(get_profile_message(profile_type))
            logger.info(f"Successfully set {profile_type} profile for user {user_id}")
        else:
            # Send error message
            update.message.reply_text(
                "Sorry, there was an error setting your profile. Please try again later."
            )
            logger.error(f"Failed to set {profile_type} profile for user {user_id}")
            
    except Exception as e:
        logger.error(f"Error in set_risk_profile_command: {e}")
        try:
            update.message.reply_text(
                "Sorry, an error occurred. Please try again later."
            )
        except:
            pass