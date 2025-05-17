"""
Direct implementation of profile commands.
This module provides standalone functionality for setting user profiles.
"""

import logging
import sqlite3
from typing import Dict, Any, Optional

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database file path
DB_FILE = 'filot_bot.db'

# Main menu keyboard (simplified version for direct commands)
MAIN_KEYBOARD = ReplyKeyboardMarkup([
    ["💰 Invest", "🔍 Explore", "👤 Account"]
], resize_keyboard=True)

async def set_risk_profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE, profile_type: Optional[str] = None) -> None:
    """
    Direct command to set user risk profile.
    
    Args:
        update: The update object
        context: The context object
        profile_type: The profile type to set ('high-risk', 'stable', or None to parse from command args)
    """
    if update.effective_chat is None or update.effective_user is None or update.message is None:
        logger.error("Missing chat, user or message in set_risk_profile_command")
        return
    
    user_id = update.effective_user.id
    
    # If profile_type not provided, try to get it from command args
    if profile_type is None and context.args:
        profile_arg = context.args[0].lower()
        if profile_arg in ["high-risk", "high_risk", "highrisk", "high"]:
            profile_type = "high-risk"
        elif profile_arg in ["stable", "conservative", "safe"]:
            profile_type = "stable"
        else:
            await update.message.reply_text(
                "Please specify a valid profile type: 'high-risk' or 'stable'.\n"
                "Example: /set_profile stable",
                reply_markup=MAIN_KEYBOARD
            )
            return
    
    # If still no profile type, show options
    if profile_type is None:
        await update.message.reply_markdown(
            "📊 *Set Your Risk Profile*\n\n"
            "Please choose your investment risk tolerance:\n\n"
            "• `/high_risk` - For higher returns with increased volatility\n"
            "• `/stable` - For more conservative, steady returns\n\n"
            "Or use: `/set_profile [type]` - e.g., `/set_profile stable`",
            reply_markup=MAIN_KEYBOARD
        )
        return
    
    try:
        # Connect directly to the database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # First check if the user exists
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            # Create user if it doesn't exist
            cursor.execute(
                "INSERT INTO users (id, username, first_name, last_name, risk_profile, investment_horizon, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
                (user_id, f"user_{user_id}", "User", "", profile_type, "medium")
            )
        else:
            # Update existing user
            cursor.execute(
                "UPDATE users SET risk_profile = ? WHERE id = ?",
                (profile_type, user_id)
            )
        
        conn.commit()
        conn.close()
        
        profile_display = "High-Risk" if profile_type == "high-risk" else "Stable"
        
        await update.message.reply_markdown(
            f"✅ Your profile has been set to *{profile_display}*.\n\n"
            f"{'You\'ll now receive investment recommendations suited for a higher risk tolerance.' if profile_type == 'high-risk' else 'You\'ll now receive conservative investment recommendations with lower risk.'}",
            reply_markup=MAIN_KEYBOARD
        )
        
        logger.info(f"Successfully updated user {user_id} profile to {profile_type}")
        
    except Exception as e:
        logger.error(f"Error setting profile for user {user_id}: {e}")
        await update.message.reply_text(
            f"❌ Sorry, I couldn't update your profile. Please try again later.",
            reply_markup=MAIN_KEYBOARD
        )