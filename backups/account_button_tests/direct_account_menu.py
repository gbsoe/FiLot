"""
Direct account menu handler that provides reliable account functionality.
This module contains a simple implementation that creates a working account menu
with all required button options.
"""

import logging
import sqlite3
from typing import Dict, Any, Optional

# Set up logging
logger = logging.getLogger(__name__)

def handle_account_button(user_id: int) -> Dict[str, Any]:
    """
    Handle the Account button click with a direct implementation.
    This function returns a working account menu with all required buttons.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dict with message and reply_markup for the account menu
    """
    try:
        # Get user info from the database
        user_info = get_user_info(user_id)
        
        # Create the message based on user info
        wallet_status = "✅ Connected" if user_info.get("wallet_connected", False) else "❌ Not Connected"
        risk_profile = user_info.get("risk_profile", "Moderate")
        subscription_status = "✅ Subscribed" if user_info.get("subscribed", False) else "❌ Not Subscribed"
        
        message = (
            f"👤 *Your Account* 👤\n\n"
            f"Wallet: {wallet_status}\n"
            f"Risk Profile: {risk_profile}\n"
            f"Daily Updates: {subscription_status}\n\n"
            "Select an option below to manage your account:"
        )
        
        # Create the account menu keyboard with all required buttons
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
        # Create a simplified response if there's an error
        return {
            "success": False,
            "message": "👤 *Account Management* 👤\n\nManage your FiLot account settings and preferences:",
            "reply_markup": create_basic_menu()
        }

def get_user_info(user_id: int) -> Dict[str, Any]:
    """
    Get user info from the database with direct SQLite access.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dict with user information
    """
    conn = None
    try:
        # Connect to SQLite database
        conn = sqlite3.connect("filot_bot.db")
        cursor = conn.cursor()
        
        # Try to get user info
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user_row = cursor.fetchone()
        
        # Check if user exists
        if not user_row:
            # Create a new user if they don't exist
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
        
        # Convert boolean values for consistency
        user_info["subscribed"] = bool(user_info.get("subscribed", 0))
        
        return user_info
    
    except Exception as e:
        logger.error(f"Error in get_user_info: {e}")
        # Return default user info if there's an error
        return {
            "user_id": user_id,
            "risk_profile": "Moderate",
            "wallet_connected": False,
            "subscribed": False
        }
    finally:
        # Make sure to close the connection if it was opened
        if conn:
            conn.close()

def create_basic_menu() -> Dict[str, Any]:
    """
    Create a basic account menu without any database access.
    
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
    Handle the wallet button click to show wallet connection options.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dict with success status, message, and reply_markup
    """
    try:
        # Create wallet connection options
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
        # Return a simple fallback
        return {
            "success": False,
            "message": "💼 *Connect Your Wallet* 💼\n\nChoose how you want to connect your wallet:",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "📝 Connect by Address", "callback_data": "wallet_connect_address"}],
                    [{"text": "👤 Back to Account", "callback_data": "menu_account"}]
                ]
            }
        }

def handle_profile_button(user_id: int, profile_type: str) -> Dict[str, Any]:
    """
    Handle profile button clicks (high-risk or stable).
    
    Args:
        user_id: The user's ID
        profile_type: Either 'high-risk' or 'stable'
        
    Returns:
        Dict with success status and message
    """
    try:
        # Update the user's profile
        update_user_profile(user_id, profile_type)
        
        # Create a message for the selected profile
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
        
        # Get back to account menu keyboard
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
        # Return a simple fallback
        return {
            "success": False,
            "message": f"There was an error updating your profile. Please try again later.",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "👤 Back to Account", "callback_data": "menu_account"}]
                ]
            }
        }

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
        # Connect to SQLite database
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
        
        # Commit the changes
        conn.commit()
        
        # Close the connection
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Error in update_user_profile: {e}")
        return False

def handle_subscription_button(user_id: int, subscribe: bool) -> Dict[str, Any]:
    """
    Handle subscription button clicks (subscribe or unsubscribe).
    
    Args:
        user_id: The user's ID
        subscribe: True to subscribe, False to unsubscribe
        
    Returns:
        Dict with success status and message
    """
    try:
        # Update the user's subscription status
        update_subscription_status(user_id, subscribe)
        
        # Create a message for the subscription status
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
        
        # Get back to account menu keyboard
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
        # Return a simple fallback
        return {
            "success": False,
            "message": f"There was an error updating your subscription status. Please try again later.",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "👤 Back to Account", "callback_data": "menu_account"}]
                ]
            }
        }

def update_subscription_status(user_id: int, subscribed: bool) -> bool:
    """
    Update a user's subscription status directly in the database.
    
    Args:
        user_id: The user's ID
        subscribed: True to subscribe, False to unsubscribe
        
    Returns:
        True if update was successful, False otherwise
    """
    try:
        # Connect to SQLite database
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
        
        # Commit the changes
        conn.commit()
        
        # Close the connection
        conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Error in update_subscription_status: {e}")
        return False

def handle_status_button(user_id: int) -> Dict[str, Any]:
    """
    Handle the status button click to show user's account status.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dict with success status and message
    """
    try:
        # Get user info
        user_info = get_user_info(user_id)
        
        # Create a detailed status message
        wallet_status = "✅ Connected" if user_info.get("wallet_connected", False) else "❌ Not Connected"
        risk_profile = user_info.get("risk_profile", "Moderate")
        subscription_status = "✅ Subscribed" if user_info.get("subscribed", False) else "❌ Not Subscribed"
        
        message = (
            "📊 *Your Account Status* 📊\n\n"
            f"User ID: `{user_id}`\n"
            f"Wallet: {wallet_status}\n"
            f"Risk Profile: {risk_profile}\n"
            f"Daily Updates: {subscription_status}\n\n"
        )
        
        # Add investment status if available
        message += (
            "💰 *Investment Status* 💰\n\n"
            "Total Invested: $0.00\n"
            "Active Pools: 0\n"
            "Current Returns: $0.00\n\n"
            "Use the Explore or Invest buttons to start investing!"
        )
        
        # Get back to account menu keyboard
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
        # Return a simple fallback
        return {
            "success": False,
            "message": "There was an error retrieving your account status. Please try again later.",
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "👤 Back to Account", "callback_data": "menu_account"}]
                ]
            }
        }

def process_account_button(callback_data: str, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Process any account-related button callback.
    
    Args:
        callback_data: The callback data from the button
        user_id: The user's ID
        
    Returns:
        Dict with result or None if the button isn't related to account
    """
    # Handle account wallet button
    if callback_data == "account_wallet":
        return handle_wallet_button(user_id)
    
    # Handle profile buttons with both callback patterns
    elif callback_data == "account_profile_high-risk" or callback_data == "profile_high-risk":
        return handle_profile_button(user_id, "high-risk")
    elif callback_data == "account_profile_stable" or callback_data == "profile_stable":
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