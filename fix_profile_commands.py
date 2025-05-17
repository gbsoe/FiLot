"""
Simple, standalone command handlers for profile selection.
This creates direct commands that work without relying on buttons.
"""

import logging
import sqlite3
from typing import Dict, Any, Optional, Tuple
from telegram import Update
from telegram.ext import ContextTypes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Profile messages
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

async def high_risk_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Direct command to set profile to high-risk."""
    if not update.message:
        return
    
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    
    success, message = set_profile(user_id, "high-risk")
    
    await update.message.reply_text(
        message,
        parse_mode="Markdown"
    )
    
    logger.info(f"Processed /high_risk command for user {user_id}")

async def stable_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Direct command to set profile to stable."""
    if not update.message:
        return
    
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    
    success, message = set_profile(user_id, "stable")
    
    await update.message.reply_text(
        message,
        parse_mode="Markdown"
    )
    
    logger.info(f"Processed /stable command for user {user_id}")

def set_profile(user_id: int, profile_type: str) -> Tuple[bool, str]:
    """
    Set user profile directly in the database.
    
    Args:
        user_id: The user's Telegram ID
        profile_type: Either 'high-risk' or 'stable'
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Connect to the database
        conn = sqlite3.connect('filot_bot.db')
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
            logger.info(f"Updated user {user_id} profile to {profile_type}")
        else:
            # Create new user with profile
            cursor.execute(
                "INSERT INTO users (id, risk_profile) VALUES (?, ?)",
                (user_id, profile_type)
            )
            logger.info(f"Created new user {user_id} with {profile_type} profile")
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        # Return success message
        if profile_type == "high-risk":
            return True, HIGH_RISK_MESSAGE
        else:
            return True, STABLE_PROFILE_MESSAGE
        
    except Exception as e:
        logger.error(f"Error setting profile: {e}")
        return False, f"Sorry, there was an error setting your profile: {str(e)}"

def register_commands(application):
    """Register the commands with the application."""
    from telegram.ext import CommandHandler
    
    application.add_handler(CommandHandler("high_risk", high_risk_command))
    application.add_handler(CommandHandler("stable", stable_command))
    
    logger.info("Registered profile commands: /high_risk and /stable")