"""
Direct fix for profile buttons in the account menu.
This module directly handles high-risk and stable profile buttons.
"""

import logging
import sqlite3
import traceback
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Main database file
DB_FILE = 'filot_bot.db'

def fix_profile_button(user_id: int, profile_type: str) -> Dict[str, Any]:
    """
    Directly handle profile button clicks without using the ORM.
    
    Args:
        user_id: The user's ID
        profile_type: Either 'high-risk' or 'stable'
        
    Returns:
        Dict with success status and message
    """
    try:
        logger.info(f"Setting {profile_type} profile for user {user_id} using direct fix")
        
        # Validate profile type
        if profile_type not in ['high-risk', 'stable']:
            return {
                'success': False,
                'message': f"Invalid profile type: {profile_type}"
            }
        
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
        
        # Format message based on profile type
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
            'success': True,
            'message': profile_message
        }
        
    except Exception as e:
        logger.error(f"Error in profile button handler: {e}")
        logger.error(traceback.format_exc())
        
        return {
            'success': False,
            'message': "Sorry, there was an error setting your profile. Please try again later."
        }

def handle_button(callback_data: str, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Process profile button callbacks with any possible prefix/format.
    
    Args:
        callback_data: The callback data string from the button
        user_id: The user ID
        
    Returns:
        Dict with results or None if not a profile button
    """
    # Handle all known variations of profile button callbacks
    if callback_data in ["profile_high-risk", "account_profile_high-risk"]:
        return fix_profile_button(user_id, "high-risk")
    elif callback_data in ["profile_stable", "account_profile_stable"]:
        return fix_profile_button(user_id, "stable")
    else:
        # Not a profile button we handle
        return None