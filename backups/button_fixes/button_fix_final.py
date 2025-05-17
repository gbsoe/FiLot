"""
Final attempt to fix the problematic buttons in the account section.
This module provides handlers that completely bypass regular callback flow.
"""

import logging
import sqlite3
import traceback
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_main_keyboard():
    """Get the main keyboard for consistent UI."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [
            InlineKeyboardButton("💰 Invest", callback_data="menu_invest")
        ],
        [
            InlineKeyboardButton("🔍 Explore Pools", callback_data="menu_explore"),
            InlineKeyboardButton("👤 Account", callback_data="menu_account")
        ],
        [
            InlineKeyboardButton("❓ FAQ", callback_data="menu_faq"),
            InlineKeyboardButton("💬 Community", callback_data="menu_community")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def fix_profile_button(user_id: int, profile_type: str) -> Dict[str, Any]:
    """
    Fix for the profile buttons.
    
    Args:
        user_id: User ID
        profile_type: Either 'high-risk' or 'stable'
        
    Returns:
        Dict with success status and message
    """
    try:
        logger.info(f"FINAL FIX: Setting profile to {profile_type} for user {user_id}")
        
        # Validate profile type
        if profile_type not in ['high-risk', 'stable']:
            return {
                "success": False,
                "message": f"Invalid profile type: {profile_type}"
            }
        
        # Update database directly
        db_path = 'filot_bot.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create table if not exists
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
        cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
        user_exists = cursor.fetchone()
        
        if user_exists:
            # Update existing user
            cursor.execute(
                'UPDATE users SET risk_profile = ? WHERE id = ?',
                (profile_type, user_id)
            )
            logger.info(f"Updated profile for existing user {user_id}")
        else:
            # Create new user
            cursor.execute(
                'INSERT INTO users (id, risk_profile) VALUES (?, ?)',
                (user_id, profile_type)
            )
            logger.info(f"Created new user {user_id} with profile {profile_type}")
        
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
            "success": True,
            "message": profile_message
        }
        
    except Exception as e:
        logger.error(f"Error in profile button fix: {e}")
        logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": "Sorry, there was an error setting your profile. Please try again later."
        }

def fix_wallet_button(user_id: int) -> Dict[str, Any]:
    """
    Fix for the wallet button.
    
    Args:
        user_id: User ID
        
    Returns:
        Dict with success status and message
    """
    try:
        logger.info(f"FINAL FIX: Handling wallet button for user {user_id}")
        
        # Create wallet connection message with options
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        wallet_message = (
            "🔐 *Connect Your Wallet* 🔐\n\n"
            "Choose how you want to connect your wallet:\n\n"
            "1. *Address Entry* - Enter your wallet address manually\n"
            "2. *QR Code* - Scan a QR code with your wallet app\n\n"
            "_Your private keys always remain secure in your wallet._"
        )
        
        # Create keyboard with wallet connection options
        keyboard = [
            [
                InlineKeyboardButton("Enter Wallet Address", callback_data="wallet_connect_address")
            ],
            [
                InlineKeyboardButton("Connect via QR Code", callback_data="wallet_connect_qr")
            ],
            [
                InlineKeyboardButton("⬅️ Back to Account", callback_data="menu_account")
            ]
        ]
        
        keyboard_markup = InlineKeyboardMarkup(keyboard)
        
        return {
            "success": True,
            "message": wallet_message,
            "reply_markup": keyboard_markup
        }
        
    except Exception as e:
        logger.error(f"Error in wallet button fix: {e}")
        logger.error(traceback.format_exc())
        
        return {
            "success": False,
            "message": "Sorry, there was an error with the wallet connection. Please try again later."
        }

def apply_button_fixes(callback_data: str, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Apply fixes for problematic buttons.
    
    Args:
        callback_data: The callback data
        user_id: User ID
        
    Returns:
        Optional dict with fix result, or None if button doesn't need a fix
    """
    try:
        # Handle account profile buttons
        if callback_data == "account_profile_high-risk":
            return fix_profile_button(user_id, "high-risk")
        elif callback_data == "account_profile_stable":
            return fix_profile_button(user_id, "stable")
        # Handle wallet button
        elif callback_data == "account_wallet":
            return fix_wallet_button(user_id)
        # Other buttons don't need special handling
        else:
            return None
            
    except Exception as e:
        logger.error(f"Error applying button fixes: {e}")
        logger.error(traceback.format_exc())
        return None