"""
Direct fix for account section profile buttons.
This module bypasses the regular callback flow to provide reliable profile updates.
"""

import logging
import sqlite3
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_account_profile_buttons(callback_query) -> Dict[str, Any]:
    """
    Direct handler for account profile buttons that bypasses regular callback flow.
    
    Args:
        callback_query: The callback query from Telegram
        
    Returns:
        Dict with success status, message, and details
    """
    try:
        # Extract basic information
        user_id = callback_query.from_user.id
        callback_data = callback_query.data
        
        logger.info(f"🔧 ACCOUNT BUTTON FIX: Handling {callback_data} for user {user_id}")
        
        # Only process account profile buttons
        if not callback_data.startswith("account_profile_"):
            return {"success": False, "message": "Not an account profile button"}
        
        # Extract the profile type
        profile_type = callback_data.replace("account_profile_", "")
        
        # Update the database directly
        db_path = 'filot_bot.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Ensure the users table exists
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            risk_profile TEXT DEFAULT 'stable',
            subscribed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            wallet_address TEXT,
            verification_code TEXT,
            is_verified BOOLEAN DEFAULT 0
        )
        ''')
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        user_exists = cursor.fetchone()
        
        if user_exists:
            # Update existing user
            cursor.execute(
                "UPDATE users SET risk_profile = ? WHERE id = ?",
                (profile_type, user_id)
            )
            logger.info(f"✅ Updated existing user {user_id} profile to {profile_type}")
        else:
            # Create new user
            cursor.execute(
                "INSERT INTO users (id, risk_profile) VALUES (?, ?)",
                (user_id, profile_type)
            )
            logger.info(f"✅ Created new user {user_id} with {profile_type} profile")
        
        # Commit the changes
        conn.commit()
        conn.close()
        
        # Prepare appropriate emoji and profile-specific message
        profile_emoji = "🔴" if profile_type == "high-risk" else "🟢"
        
        if profile_type == "high-risk":
            profile_message = (
                f"{profile_emoji} *High-Risk Profile Selected*\n\n"
                f"Your investment recommendations will now focus on:\n"
                f"• Higher APR opportunities\n"
                f"• Newer pools with growth potential\n"
                f"• More volatile but potentially rewarding options\n\n"
                f"_Note: Higher returns come with increased risk_"
            )
        else:  # stable
            profile_message = (
                f"{profile_emoji} *Stable Profile Selected*\n\n"
                f"Your investment recommendations will now focus on:\n"
                f"• Established, reliable pools\n"
                f"• Lower volatility options\n"
                f"• More consistent but potentially lower APR\n\n"
                f"_Note: Stability typically means more moderate returns_"
            )
            
        return {
            "success": True,
            "message": profile_message,
            "profile_type": profile_type,
            "emoji": profile_emoji
        }
        
    except Exception as e:
        logger.error(f"❌ Error in account profile button fix: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Error updating profile: {str(e)}",
            "error": str(e)
        }