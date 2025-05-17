"""
Complete account menu handler with all buttons from screenshot.
This provides a clean, reliable implementation for the Account section.
"""

import logging
import sqlite3
from typing import Dict, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

def handle_account_button(user_id: int) -> Dict[str, Any]:
    """
    Provide a complete account menu matching the screenshot.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dict with message and reply_markup for the account menu
    """
    try:
        # Get user info directly using SQLite
        user_info = get_user_info(user_id)
        
        # Create status indicators based on user info
        wallet_status = "✅ Connected" if user_info.get("wallet_connected", False) else "❌ Not Connected"
        risk_profile = user_info.get("risk_profile", "Moderate")
        subscription_status = "✅ Subscribed" if user_info.get("subscribed", False) else "❌ Not Subscribed"
        
        # Create message that matches the screenshot
        message = (
            f"👤 *Your Account* 👤\n\n"
            f"Wallet: {wallet_status}\n"
            f"Risk Profile: {risk_profile}\n"
            f"Daily Updates: {subscription_status}\n\n"
            "Select an option below to manage your account:"
        )
        
        # Create reply markup that exactly matches the screenshot
        reply_markup = {
            "inline_keyboard": [
                [{"text": "💼 Connect Wallet", "callback_data": "account_wallet"}],
                [
                    {"text": "🔴 High-Risk Profile", "callback_data": "account_profile_high-risk"},
                    {"text": "🟢 Stable Profile", "callback_data": "account_profile_stable"}
                ],
                [
                    {"text": "🔔 Subscribe", "callback_data": "account_subscribe"},
                    {"text": "🔕 Unsubscribe", "callback_data": "account_unsubscribe"}
                ],
                [
                    {"text": "❓ Help", "callback_data": "show_help"},
                    {"text": "📊 Status", "callback_data": "account_status"}
                ],
                [{"text": "🏠 Back to Main Menu", "callback_data": "back_to_main"}]
            ]
        }
        
        return {
            "success": True,
            "message": message,
            "reply_markup": reply_markup
        }
    except Exception as e:
        logger.error(f"Error in handle_account_button: {e}")
        # Create a fallback that still provides all required buttons
        return {
            "success": False,
            "message": "👤 *Account Management* 👤\n\nManage your account settings:",
            "reply_markup": create_basic_account_menu()
        }

def get_user_info(user_id: int) -> Dict[str, Any]:
    """
    Get user info directly from SQLite database.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dict with user information
    """
    conn = None
    try:
        # Connect directly to SQLite database
        conn = sqlite3.connect("filot_bot.db")
        cursor = conn.cursor()
        
        # Check if users table exists, create if not
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                risk_profile TEXT DEFAULT 'Moderate',
                subscribed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Check if wallets table exists, create if not
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                wallet_address TEXT,
                wallet_type TEXT DEFAULT 'solana',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        conn.commit()
        
        # Try to get user info
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user_row = cursor.fetchone()
        
        # Create user if doesn't exist
        if not user_row:
            cursor.execute(
                "INSERT INTO users (user_id, risk_profile, subscribed) VALUES (?, ?, ?)",
                (user_id, "Moderate", 0)
            )
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user_row = cursor.fetchone()
        
        # Get column names
        columns = [desc[0] for desc in cursor.description]
        
        # Create user info dictionary
        user_info = {}
        for i, col in enumerate(columns):
            user_info[col] = user_row[i]
        
        # Check if wallet is connected
        cursor.execute("SELECT * FROM wallets WHERE user_id = ?", (user_id,))
        wallet_row = cursor.fetchone()
        user_info["wallet_connected"] = wallet_row is not None
        
        # Convert boolean values
        user_info["subscribed"] = bool(user_info.get("subscribed", 0))
        
        return user_info
    
    except Exception as e:
        logger.error(f"Error in get_user_info: {e}")
        # Return default user info
        return {
            "user_id": user_id,
            "risk_profile": "Moderate",
            "wallet_connected": False,
            "subscribed": False
        }
    finally:
        # Close connection if it exists
        if conn:
            conn.close()

def create_basic_account_menu() -> Dict[str, Any]:
    """
    Create a basic account menu that matches the screenshot.
    
    Returns:
        Dict with inline keyboard markup
    """
    return {
        "inline_keyboard": [
            [{"text": "💼 Connect Wallet", "callback_data": "account_wallet"}],
            [
                {"text": "🔴 High-Risk Profile", "callback_data": "account_profile_high-risk"},
                {"text": "🟢 Stable Profile", "callback_data": "account_profile_stable"}
            ],
            [
                {"text": "🔔 Subscribe", "callback_data": "account_subscribe"},
                {"text": "🔕 Unsubscribe", "callback_data": "account_unsubscribe"}
            ],
            [
                {"text": "❓ Help", "callback_data": "show_help"},
                {"text": "📊 Status", "callback_data": "account_status"}
            ],
            [{"text": "🏠 Back to Main Menu", "callback_data": "back_to_main"}]
        ]
    }

def handle_wallet_button(user_id: int) -> Dict[str, Any]:
    """
    Handle wallet connection options.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dict with message and reply markup
    """
    try:
        message = (
            "💼 *Connect Your Wallet* 💼\n\n"
            "Choose how you want to connect your wallet:"
        )
        
        reply_markup = {
            "inline_keyboard": [
                [{"text": "📝 Connect by Address", "callback_data": "wallet_connect_address"}],
                [{"text": "📱 Connect with QR Code", "callback_data": "wallet_connect_qr"}],
                [{"text": "👤 Back to Account", "callback_data": "menu_account"}]
            ]
        }
        
        return {
            "success": True,
            "message": message,
            "reply_markup": reply_markup
        }
    except Exception as e:
        logger.error(f"Error in handle_wallet_button: {e}")
        # Return fallback
        return {
            "success": False,
            "message": "💼 *Connect Your Wallet* 💼\n\nChoose a connection method:",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "📝 Connect by Address", "callback_data": "wallet_connect_address"}],
                    [{"text": "👤 Back to Account", "callback_data": "menu_account"}]
                ]
            }
        }

def handle_profile_button(user_id: int, profile_type: str) -> Dict[str, Any]:
    """
    Handle profile selection (high-risk or stable).
    
    Args:
        user_id: The user's ID
        profile_type: Either 'high-risk' or 'stable'
        
    Returns:
        Dict with message and reply markup
    """
    try:
        # Update user profile
        update_user_profile(user_id, profile_type)
        
        if profile_type == "high-risk":
            message = (
                "🔴 *High-Risk Profile Selected* 🔴\n\n"
                "You've set your risk preference to *High-Risk*.\n\n"
                "You'll now receive investment opportunities with higher potential returns "
                "but also higher volatility and risk exposure.\n\n"
                "Remember that high returns come with increased risk of loss. "
                "Only invest what you can afford to lose."
            )
        else:  # stable profile
            message = (
                "🟢 *Stable Profile Selected* 🟢\n\n"
                "You've set your risk preference to *Stable*.\n\n"
                "You'll now receive investment opportunities with moderate returns "
                "and lower volatility and risk exposure.\n\n"
                "This profile focuses on more established pools with proven track records "
                "and lower impermanent loss risk."
            )
        
        # Back to account menu button
        reply_markup = {
            "inline_keyboard": [
                [{"text": "👤 Back to Account", "callback_data": "menu_account"}]
            ]
        }
        
        return {
            "success": True,
            "message": message,
            "reply_markup": reply_markup
        }
    except Exception as e:
        logger.error(f"Error in handle_profile_button: {e}")
        # Return fallback
        return {
            "success": False,
            "message": "There was an error updating your profile. Please try again.",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "👤 Back to Account", "callback_data": "menu_account"}]
                ]
            }
        }

def update_user_profile(user_id: int, profile_type: str) -> bool:
    """
    Update user profile in database.
    
    Args:
        user_id: The user's ID
        profile_type: Either 'high-risk' or 'stable'
        
    Returns:
        True if successful, False otherwise
    """
    conn = None
    try:
        # Connect to database
        conn = sqlite3.connect("filot_bot.db")
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user_row = cursor.fetchone()
        
        if user_row:
            # Update existing user
            cursor.execute(
                "UPDATE users SET risk_profile = ? WHERE user_id = ?",
                (profile_type.title(), user_id)
            )
        else:
            # Create new user
            cursor.execute(
                "INSERT INTO users (user_id, risk_profile, subscribed) VALUES (?, ?, ?)",
                (user_id, profile_type.title(), 0)
            )
        
        conn.commit()
        return True
    
    except Exception as e:
        logger.error(f"Error in update_user_profile: {e}")
        return False
    
    finally:
        if conn:
            conn.close()

def handle_subscription_button(user_id: int, subscribe: bool) -> Dict[str, Any]:
    """
    Handle subscribe/unsubscribe button.
    
    Args:
        user_id: The user's ID
        subscribe: True to subscribe, False to unsubscribe
        
    Returns:
        Dict with message and reply markup
    """
    try:
        # Update subscription status
        update_subscription_status(user_id, subscribe)
        
        if subscribe:
            message = (
                "🔔 *Subscribed to Daily Updates* 🔔\n\n"
                "You've successfully subscribed to daily updates!\n\n"
                "You'll receive daily insights about the best performing pools, "
                "market trends, and personalized investment recommendations."
            )
        else:
            message = (
                "🔕 *Unsubscribed from Daily Updates* 🔕\n\n"
                "You've successfully unsubscribed from daily updates.\n\n"
                "You won't receive daily notifications anymore, but you can "
                "always subscribe again from your account menu."
            )
        
        # Back to account menu button
        reply_markup = {
            "inline_keyboard": [
                [{"text": "👤 Back to Account", "callback_data": "menu_account"}]
            ]
        }
        
        return {
            "success": True,
            "message": message,
            "reply_markup": reply_markup
        }
    except Exception as e:
        logger.error(f"Error in handle_subscription_button: {e}")
        # Return fallback
        return {
            "success": False,
            "message": "There was an error updating your subscription. Please try again.",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "👤 Back to Account", "callback_data": "menu_account"}]
                ]
            }
        }

def update_subscription_status(user_id: int, subscribed: bool) -> bool:
    """
    Update subscription status in database.
    
    Args:
        user_id: The user's ID
        subscribed: True to subscribe, False to unsubscribe
        
    Returns:
        True if successful, False otherwise
    """
    conn = None
    try:
        # Connect to database
        conn = sqlite3.connect("filot_bot.db")
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user_row = cursor.fetchone()
        
        if user_row:
            # Update existing user
            cursor.execute(
                "UPDATE users SET subscribed = ? WHERE user_id = ?",
                (1 if subscribed else 0, user_id)
            )
        else:
            # Create new user
            cursor.execute(
                "INSERT INTO users (user_id, risk_profile, subscribed) VALUES (?, ?, ?)",
                (user_id, "Moderate", 1 if subscribed else 0)
            )
        
        conn.commit()
        return True
    
    except Exception as e:
        logger.error(f"Error in update_subscription_status: {e}")
        return False
    
    finally:
        if conn:
            conn.close()

def handle_status_button(user_id: int) -> Dict[str, Any]:
    """
    Handle status button to show account details.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dict with message and reply markup
    """
    try:
        # Get user info
        user_info = get_user_info(user_id)
        
        # Create detailed status message
        wallet_status = "✅ Connected" if user_info.get("wallet_connected", False) else "❌ Not Connected"
        risk_profile = user_info.get("risk_profile", "Moderate")
        subscription_status = "✅ Subscribed" if user_info.get("subscribed", False) else "❌ Not Subscribed"
        
        message = (
            "📊 *Your Account Status* 📊\n\n"
            f"User ID: `{user_id}`\n"
            f"Wallet: {wallet_status}\n"
            f"Risk Profile: {risk_profile}\n"
            f"Daily Updates: {subscription_status}\n\n"
            "💰 *Investment Status* 💰\n\n"
            "Total Invested: $0.00\n"
            "Active Pools: 0\n"
            "Current Returns: $0.00\n\n"
            "Use the Explore or Invest buttons to start investing!"
        )
        
        # Back to account menu button
        reply_markup = {
            "inline_keyboard": [
                [{"text": "👤 Back to Account", "callback_data": "menu_account"}]
            ]
        }
        
        return {
            "success": True,
            "message": message,
            "reply_markup": reply_markup
        }
    except Exception as e:
        logger.error(f"Error in handle_status_button: {e}")
        # Return fallback
        return {
            "success": False,
            "message": "There was an error retrieving your status. Please try again.",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "👤 Back to Account", "callback_data": "menu_account"}]
                ]
            }
        }

def process_account_callback(callback_data: str, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Process all account-related callbacks.
    
    Args:
        callback_data: The callback data from button
        user_id: The user's ID
        
    Returns:
        Dict with result or None if not account-related
    """
    # Handle wallet button
    if callback_data == "account_wallet":
        return handle_wallet_button(user_id)
    
    # Handle profile buttons - both formats for compatibility
    elif callback_data in ["account_profile_high-risk", "profile_high-risk"]:
        return handle_profile_button(user_id, "high-risk")
    elif callback_data in ["account_profile_stable", "profile_stable"]:
        return handle_profile_button(user_id, "stable")
    
    # Handle subscription buttons
    elif callback_data == "account_subscribe":
        return handle_subscription_button(user_id, True)
    elif callback_data == "account_unsubscribe":
        return handle_subscription_button(user_id, False)
    
    # Handle status button
    elif callback_data == "account_status":
        return handle_status_button(user_id)
    
    # Not an account-related button
    return None