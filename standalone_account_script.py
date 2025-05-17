#!/usr/bin/env python3
"""
Standalone script to debug and fix the Account button issue.
This creates a simple account menu directly in a Telegram bot.
"""

import os
import sys
import logging
import sqlite3
import json
import requests
from typing import Dict, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_token_from_env():
    """Get the Telegram bot token from environment variables."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables.")
        sys.exit(1)
    return token

def send_telegram_message(chat_id: int, text: str, reply_markup: Optional[Dict] = None):
    """
    Send a message to Telegram.
    
    Args:
        chat_id: The chat ID to send the message to
        text: The text of the message
        reply_markup: Optional inline keyboard markup
    """
    token = get_token_from_env()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logger.info(f"Message sent successfully to chat {chat_id}")
        return response.json()
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return None

def get_user_info(user_id: int) -> Dict[str, Any]:
    """
    Get user info from SQLite database.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dict with user information
    """
    conn = None
    try:
        # Connect to database directly
        conn = sqlite3.connect("filot_bot.db")
        cursor = conn.cursor()
        
        # Create tables if they don't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                risk_profile TEXT DEFAULT 'Moderate',
                subscribed INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                wallet_address TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        conn.commit()
        
        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user_row = cursor.fetchone()
        
        if not user_row:
            # Create user if doesn't exist
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
            "subscribed": False,
            "wallet_connected": False
        }
    
    finally:
        if conn:
            conn.close()

def create_account_menu(user_id: int) -> Dict[str, Any]:
    """
    Create an account menu for a user.
    
    Args:
        user_id: The user's ID
        
    Returns:
        Dict with message and reply_markup
    """
    # Get user info
    user_info = get_user_info(user_id)
    logger.info(f"User info: {user_info}")
    
    # Format user status
    wallet_status = "✅ Connected" if user_info.get("wallet_connected") else "❌ Not Connected"
    risk_profile = user_info.get("risk_profile", "Moderate")
    subscription_status = "✅ Subscribed" if user_info.get("subscribed") else "❌ Not Subscribed"
    
    # Create message
    message = (
        f"👤 *Your Account* 👤\n\n"
        f"Wallet: {wallet_status}\n"
        f"Risk Profile: {risk_profile}\n"
        f"Daily Updates: {subscription_status}\n\n"
        "Select an option below to manage your account:"
    )
    
    # Create reply markup
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
        "message": message,
        "reply_markup": reply_markup
    }

def main():
    """Main function to run the script."""
    if len(sys.argv) < 2:
        print("Usage: python standalone_account_script.py <chat_id>")
        sys.exit(1)
    
    try:
        chat_id = int(sys.argv[1])
    except ValueError:
        print("Error: chat_id must be an integer")
        sys.exit(1)
    
    # Get account menu
    result = create_account_menu(chat_id)
    
    # Send message
    send_telegram_message(
        chat_id=chat_id,
        text=result["message"],
        reply_markup=result["reply_markup"]
    )
    
    print(f"Account menu sent to chat {chat_id}!")

if __name__ == "__main__":
    main()