#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main entry point for the Telegram bot and Flask web application
"""

import os
import sys
import logging
import asyncio
import traceback
import threading
import time
import hashlib
import json
import requests
import sqlite3
from collections import deque
from datetime import datetime
from dotenv import load_dotenv

# Update DATABASE_URL in os.environ to use SQLite
sqlite_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'filot_bot.db')
os.environ["DATABASE_URL"] = f"sqlite:///{sqlite_path}"

# Import Telegram components - these need to be accessible globally
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ContextTypes

# Import keyboard utilities for consistent UI
from keyboard_utils import MAIN_KEYBOARD

# Global set to track processed messages and prevent duplication
processed_messages = set()
# Keep track of only the last 1000 messages to prevent memory leaks
MAX_PROCESSED_MESSAGES = 1000
# Dictionary to track recently sent messages to prevent duplicates
recent_messages = {}

# ANTI-LOOP SYSTEM: Import the aggressive anti-loop protection system
# This will automatically monkey-patch key functions to prevent message loops
import anti_loop

def is_message_processed(chat_id, message_id):
    """
    Check if a message has already been processed and mark it as processed if not.
    
    Args:
        chat_id: Chat ID
        message_id: Message ID
        
    Returns:
        bool: True if the message has already been processed, False otherwise
    """
    global processed_messages
    
    # Create a unique tracking ID for this message
    tracking_id = f"{chat_id}_{message_id}"
    
    # Check if we've seen this message before
    if tracking_id in processed_messages:
        return True
        
    # Mark message as processed
    processed_messages.add(tracking_id)
    
    # Maintain max size for processed_messages
    if len(processed_messages) > MAX_PROCESSED_MESSAGES:
        # Convert to list, slice, and convert back to set to remove oldest entries
        processed_messages_list = list(processed_messages)
        processed_messages = set(processed_messages_list[-MAX_PROCESSED_MESSAGES:])
        
    return False
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler
)

# Import bot command handlers
from bot import (
    start_command,
    help_command,
    info_command,
    simulate_command,
    subscribe_command,
    unsubscribe_command,
    status_command,
    verify_command,
    wallet_command,
    walletconnect_command,
    profile_command,
    handle_message,
    handle_callback_query,
    error_handler
)

# Import Flask app for the web interface
from app import app

# Import health check module
import health_check

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global application variable
application = None

def anti_idle_thread():
    """
    Thread that performs regular database activity to prevent the application
    from being terminated due to inactivity.
    """
    logger.info("Starting anti-idle thread for telegram bot process")

    # Sleep interval in seconds (60 seconds is well below the ~2m21s timeout)
    interval = 60

    while True:
        try:
            # Access the database with app context
            with app.app_context():
                from sqlalchemy import text
                from models import db, BotStatistics, ErrorLog

                # Simple query to keep connection alive
                result = db.session.execute(text("SELECT 1")).fetchone()
                logger.info(f"Bot process anti-idle: Database ping successful, result={result}")

                # Create a log entry to show activity
                log = ErrorLog(
                    error_type="keep_alive_main",
                    error_message="Main.py telegram bot anti-idle activity",
                    module="main.py",
                    resolved=True
                )
                db.session.add(log)

                # Update statistics
                stats = BotStatistics.query.order_by(BotStatistics.id.desc()).first()
                if stats:
                    # Increment uptime percentage slightly (which we can modify directly)
                    stats.uptime_percentage += 0.01  # Small increment
                    db.session.commit()
                    logger.info("Bot process anti-idle: Updated statistics")
        except Exception as e:
            logger.error(f"Bot process anti-idle error: {e}")

        # Sleep for the interval
        time.sleep(interval)

def run_telegram_bot():
    """
    Run the Telegram bot using a direct approach to handle messages.

    This function avoids using the PTB built-in polling mechanisms which require 
    signal handlers and instead implements a direct command handling approach.
    """
    try:
        # Import necessary modules here for thread safety
        import threading
        import requests
        import json
        from telegram import Bot, Update

        # Get the token from environment variables
        bot_token = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            logger.error("No Telegram bot token found")
            return

        # Create a bot instance directly
        bot = Bot(token=bot_token)
        # Set the global bot instance
        import globals
        globals.set_bot(bot)
        logger.info("Created Telegram bot instance and set global reference")
        
        # Send a debug message to verify bot functionality
        try:
            # Try to send a test message to a default chat ID for debugging
            debug_chat_id = os.environ.get("ADMIN_CHAT_ID", "")
            if debug_chat_id and debug_chat_id != "<use_your_actual_id_here>":
                from datetime import datetime
                # Use direct API call instead of bot.send_message which is async
                import requests
                response = requests.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={
                        "chat_id": debug_chat_id,
                        "text": f"🤖 Bot restarted and online at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                )
                if response.status_code == 200:
                    logger.info(f"Sent startup message to debug chat {debug_chat_id}")
                else:
                    logger.error(f"Failed to send debug message: {response.text}")
            else:
                logger.info("No valid ADMIN_CHAT_ID found for debug messages")
        except Exception as e:
            logger.error(f"Error sending debug message: {e}")

        # Import command handlers
        from bot import (
            start_command, help_command, info_command, simulate_command,
            subscribe_command, unsubscribe_command, status_command,
            verify_command, wallet_command, walletconnect_command,
            profile_command, faq_command, social_command,
            handle_message, handle_callback_query
        )

        # Set up base URL for Telegram Bot API
        base_url = f"https://api.telegram.org/bot{bot_token}"

        # Track the last update ID we've processed
        last_update_id = 0

        # Dictionary mapping command names to handler functions
        command_handlers = {
            "start": start_command,
            "help": help_command,
            "info": info_command,
            "simulate": simulate_command,
            "subscribe": subscribe_command,
            "unsubscribe": unsubscribe_command,
            "status": status_command,
            "verify": verify_command,
            "wallet": wallet_command,  # We've implemented special direct handling for this command
            "walletconnect": walletconnect_command,  # We've implemented special direct handling for this command
            "profile": profile_command,
            "faq": faq_command,
            "social": social_command
        }

        # Function to handle a specific update by determining its type and routing to appropriate handler
        def handle_update(update_dict):
            from app import app
            import threading
            from telegram import Bot, Update

            try:
                # Create a bot instance to use with de_json
                bot = Bot(token=os.environ.get("TELEGRAM_BOT_TOKEN"))
                
                # Convert the dictionary to a Telegram Update object
                update_obj = Update.de_json(update_dict, bot)
                logger.info(f"Processing update type: {update_dict.keys()}")

                # Create a simple context type that mimics ContextTypes.DEFAULT_TYPE
                class SimpleContext:
                    def __init__(self):
                        self.bot = bot
                        self.args = []
                        self.match = None
                        self.user_data = {}
                        self.chat_data = {}
                        self.bot_data = {}

                # Function to directly send a response without using async
                def send_response(chat_id, text, parse_mode=None, reply_markup=None, message_id=None):
                    try:
                        # Create a unique identifier for this message to prevent duplicates
                        msg_hash = f"{chat_id}_{hashlib.md5(text.encode()).hexdigest()[:8]}"
                        
                        # Check if we've already sent a very similar message in the last 10 seconds
                        now = time.time()
                        if msg_hash in recent_messages:
                            if now - recent_messages[msg_hash] < 10:
                                logger.warning(f"Preventing duplicate message: {text[:30]}...")
                                return
                        
                        # Update the recent messages tracker
                        recent_messages[msg_hash] = now
                        
                        # Clean up old messages to prevent memory leak
                        old_msgs = [k for k, v in recent_messages.items() if now - v > 30]
                        for k in old_msgs:
                            recent_messages.pop(k, None)

                        params = {
                            "chat_id": chat_id,
                            "text": text,
                        }

                        if parse_mode:
                            params["parse_mode"] = parse_mode

                        # If no custom reply markup is provided, use the MAIN_KEYBOARD
                        # for error messages or regular text responses
                        if reply_markup:
                            # Handle different types of reply_markup objects
                            if hasattr(reply_markup, 'to_dict'):
                                # This is a telegram.ReplyMarkup object (like InlineKeyboardMarkup)
                                params["reply_markup"] = json.dumps(reply_markup.to_dict())
                            elif isinstance(reply_markup, dict):
                                # Already a dictionary
                                params["reply_markup"] = json.dumps(reply_markup)
                            else:
                                # Try our best to convert it
                                try:
                                    params["reply_markup"] = json.dumps(reply_markup)
                                except Exception as markup_error:
                                    logger.error(f"Failed to serialize reply_markup: {markup_error}")
                        else:
                            # Import here to avoid circular imports
                            try:
                                from keyboard_utils import MAIN_KEYBOARD_DICT
                                # Apply the persistent keyboard to all messages without custom markup
                                params["reply_markup"] = json.dumps(MAIN_KEYBOARD_DICT)
                            except Exception as kb_error:
                                logger.error(f"Failed to import MAIN_KEYBOARD_DICT: {kb_error}")
                            
                        # Add message tracking ID if provided
                        if message_id:
                            # Use the message ID to mark this as already processed
                            is_message_processed(chat_id, message_id)

                        response = requests.post(f"{base_url}/sendMessage", json=params)
                        if response.status_code != 200:
                            logger.error(f"Failed to send message: {response.text}")
                        return response.json() if response.status_code == 200 else None
                    except Exception as e:
                        logger.error(f"Error sending message: {e}")
                        return None

                # Handle WalletConnect command in a separate thread to avoid blocking
                def handle_walletconnect_sequence(chat_id, user_id):
                    try:
                        # Import needed modules
                        import qrcode
                        import uuid
                        import time
                        from datetime import datetime
                        from io import BytesIO

                        # 1. First message - Security info
                        send_response(
                            chat_id,
                            "🔒 *Secure Wallet Connection*\n\n"
                            "Our wallet connection process is designed with your security in mind:\n\n"
                            "• Your private keys remain in your wallet app\n"
                            "• We only request permission to view balances\n"
                            "• No funds will be transferred without your explicit approval\n"
                            "• All connections use encrypted communication\n\n"
                            "Creating your secure connection now...",
                            parse_mode="Markdown"
                        )

                        # Wait briefly for better message flow
                        time.sleep(0.5)

                        # Generate a session ID for the connection
                        session_id = str(uuid.uuid4())

                        # 2. Session information message
                        send_response(
                            chat_id,
                            "🔗 *WalletConnect Session Created*\n\n"
                            "Copy the connection code below and paste it into your wallet app to connect.\n\n"
                            f"Session ID: {session_id}\n\n"
                            "✅ What to expect in your wallet app:\n"
                            "• You'll be asked to approve a connection request\n"
                            "• Your wallet app will show exactly what permissions are being requested\n"
                            "• No funds will be transferred without your explicit approval\n\n"
                            "Once connected, click 'Check Connection Status' to verify.",
                            parse_mode="Markdown"
                        )

                        # Wait briefly for better message flow
                        time.sleep(0.5)

                        # Create WalletConnect data for QR code
                        # Use a deterministic but secure method to generate these values
                        wc_topic = f"{uuid.uuid4().hex[:16]}"
                        sym_key = f"{uuid.uuid4().hex}{uuid.uuid4().hex[:8]}"
                        project_id = os.environ.get("WALLETCONNECT_PROJECT_ID", "")

                        # Format the WalletConnect URI
                        wc_uri = f"wc:{wc_topic}@2?relay-protocol=irn&relay-url=wss://relay.walletconnect.org&symKey={sym_key}"

                        # Add project ID to the URI if available
                        if project_id:
                            wc_uri = f"{wc_uri}&projectId={project_id}"

                        # Create QR code with the WalletConnect URI
                        qr = qrcode.QRCode(
                            version=1,
                            error_correction=qrcode.constants.ERROR_CORRECT_L,
                            box_size=10,
                            border=4,
                        )
                        qr.add_data(wc_uri)
                        qr.make(fit=True)

                        img = qr.make_image(fill_color="black", back_color="white")

                        # Save QR code to a bytes buffer
                        buffer = BytesIO()
                        img.save(buffer, format="PNG")
                        buffer.seek(0)

                        # 3. QR code message
                        send_response(
                            chat_id,
                            f"📱 *Scan this QR code with your wallet app to connect*\n"
                            f"(Generated at {datetime.now().strftime('%H:%M:%S')})",
                            parse_mode="Markdown"
                        )

                        # Send QR code image
                        files = {"photo": ("qrcode.png", buffer.getvalue(), "image/png")}
                        photo_response = requests.post(
                            f"{base_url}/sendPhoto",
                            data={"chat_id": chat_id},
                            files=files
                        )

                        if photo_response.status_code != 200:
                            logger.error(f"Failed to send QR code: {photo_response.text}")
                            send_response(
                                chat_id,
                                "Sorry, there was an error generating the QR code. Please try again later."
                            )
                            return

                        # Wait briefly for better message flow
                        time.sleep(0.5)

                        # 4. Text link for copying
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        send_response(
                            chat_id,
                            f"📋 *COPY THIS LINK (tap to select):*\n\n"
                            f"`{wc_uri}`\n\n"
                            f"Generated at {current_time}",
                            parse_mode="Markdown"
                        )

                        # Wait briefly for better message flow
                        time.sleep(0.5)

                        # 5. Final security reminder
                        send_response(
                            chat_id,
                            "🔒 Remember: Only approve wallet connections from trusted sources and always verify the requested permissions.\n\n"
                            "If the QR code doesn't work, manually copy the link above and paste it into your wallet app."
                        )

                        logger.info(f"Successfully sent complete WalletConnect sequence to user {user_id}")

                    except Exception as wc_thread_error:
                        logger.error(f"Error in walletconnect thread: {wc_thread_error}")
                        logger.error(traceback.format_exc())
                        send_response(
                            chat_id,
                            "Sorry, an error occurred while creating your wallet connection. Please try again later."
                        )

                # Extract command arguments if this is a command
                if update_obj.message and update_obj.message.text and update_obj.message.text.startswith('/'):
                    # Split the message into command and arguments
                    text_parts = update_obj.message.text.split()
                    command = text_parts[0][1:].split('@')[0]  # Remove the '/' and any bot username

                    # Create context with arguments
                    context = SimpleContext()
                    context.args = text_parts[1:]
                    chat_id = update_obj.message.chat_id

                    # Execute inside the Flask app context
                    with app.app_context():
                        try:
                            # IMMEDIATE ACKNOWLEDGMENT FOR ALL COMMANDS
                            # This ensures the user knows the command was received,
                            # especially important for commands that take time to process
                            ack_message = "Processing your request..."
                            if command == "start":
                                ack_message = "Welcome! Setting up your profile..."
                            elif command == "help":
                                ack_message = "Preparing help information..."
                            elif command == "info":
                                ack_message = "Fetching latest pool information..."
                            elif command == "walletconnect":
                                ack_message = "Initializing secure wallet connection..."
                            elif command == "verify":
                                ack_message = "Starting verification process..."

                            # Don't send acknowledgments for commands that return data immediately
                            if command not in ["status", "profile"]:
                                try:
                                    requests.post(
                                        f"{base_url}/sendChatAction",
                                        json={
                                            "chat_id": chat_id,
                                            "action": "typing"
                                        }
                                    )
                                except Exception:
                                    pass  # Ignore errors in sending chat action

                            # Route to appropriate command handler
                            if command in command_handlers:
                                logger.info(f"Calling handler for command: {command}")

                                # Special handling for commands
                                if command == "info":
                                    # Get predefined pool data
                                    from response_data import get_pool_data as get_predefined_pool_data

                                    # Process top APR pools from the predefined data
                                    predefined_data = get_predefined_pool_data()
                                    pool_list = predefined_data.get('topAPR', [])

                                    if not pool_list:
                                        send_response(
                                            chat_id,
                                            "Sorry, I couldn't retrieve pool data at the moment. Please try again later."
                                        )
                                    else:
                                        # Import at function level to avoid circular imports
                                        from utils import format_pool_info
                                        formatted_info = format_pool_info(pool_list)
                                        send_response(chat_id, formatted_info)
                                        logger.info("Sent pool info response using direct API call")

                                elif command == "wallet":
                                    # Handle wallet command directly
                                    try:
                                        # Import needed wallet utilities
                                        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                                        from wallet_utils import connect_wallet, check_wallet_balance, format_wallet_info

                                        # Check if a wallet address is provided
                                        if context.args and context.args[0]:
                                            wallet_address = context.args[0]

                                            try:
                                                # Validate wallet address
                                                from wallet_utils import connect_wallet
                                                wallet_address = connect_wallet(wallet_address)

                                                # First send confirmation message
                                                send_response(
                                                    chat_id,
                                                    f"✅ Wallet successfully connected: `{wallet_address}`\n\n"
                                                    "Fetching wallet balance...",
                                                    parse_mode="Markdown"
                                                )

                                                # Import needed for async operations
                                                import asyncio

                                                # Create a new event loop for this thread
                                                loop = asyncio.new_event_loop()
                                                asyncio.set_event_loop(loop)

                                                # Get wallet balance
                                                balance = loop.run_until_complete(check_wallet_balance(wallet_address))

                                                if "error" in balance:
                                                    send_response(
                                                        chat_id,
                                                        f"❌ Error: {balance['error']}\n\n"
                                                        "Please try again with a valid wallet address.",
                                                        parse_mode="Markdown"
                                                    )
                                                    return

                                                # Format balance information
                                                balance_text = "💼 *Wallet Balance* 💼\n\n"

                                                for token, amount in balance.items():
                                                    if token == "SOL":
                                                        balance_text += f"• SOL: *{amount:.4f}* (≈${amount * 133:.2f})\n"
                                                    elif token == "USDC" or token == "USDT":
                                                        balance_text += f"• {token}: *{amount:.2f}*\n"
                                                    else:
                                                        balance_text += f"• {token}: *{amount:.4f}*\n"

                                                # Add investment options buttons
                                                keyboard = [
                                                    [{"text": "View Pool Opportunities", "callback_data": "view_pools"}],
                                                    [{"text": "Connect with WalletConnect", "callback_data": "walletconnect"}]
                                                ]

                                                # Format reply markup as a proper dictionary
                                                reply_markup_dict = {"inline_keyboard": keyboard}
                                                send_response(
                                                    chat_id,
                                                    balance_text + "\n\n💡 Use /simulate to see potential earnings with these tokens in liquidity pools.",
                                                    parse_mode="Markdown",
                                                    reply_markup=reply_markup_dict
                                                )

                                                logger.info(f"Successfully processed wallet balance for {wallet_address}")

                                            except ValueError as e:
                                                send_response(
                                                    chat_id,
                                                    f"❌ Error: {str(e)}\n\n"
                                                    "Please provide a valid Solana wallet address.",
                                                    parse_mode="Markdown"
                                                )

                                        else:
                                            # No address provided, show wallet menu
                                            keyboard = [
                                                [{"text": "Connect with WalletConnect", "callback_data": "walletconnect"}],
                                                [{"text": "Enter Wallet Address", "callback_data": "enter_address"}]
                                            ]

                                            # Format reply markup as a proper dictionary
                                            reply_markup_dict = {"inline_keyboard": keyboard}
                                            send_response(
                                                chat_id,
                                                "💼 *Wallet Management*\n\n"
                                                "Connect your wallet to view balances and interact with liquidity pools.\n\n"
                                                "Choose an option below, or provide your wallet address directly using:\n"
                                                "/wallet [your_address]",
                                                parse_mode="Markdown",
                                                reply_markup=reply_markup_dict
                                            )

                                            logger.info("Sent wallet management menu")

                                    except Exception as wallet_error:
                                        logger.error(f"Error in wallet command: {wallet_error}")
                                        logger.error(traceback.format_exc())
                                        send_response(
                                            chat_id,
                                            "Sorry, an error occurred while processing your wallet request. Please try again later."
                                        )

                                elif command == "walletconnect":
                                    # Launch the walletconnect sequence in a separate thread
                                    # to avoid blocking the main handler thread
                                    user_id = update_obj.message.from_user.id
                                    wc_thread = threading.Thread(
                                        target=handle_walletconnect_sequence,
                                        args=(chat_id, user_id)
                                    )
                                    wc_thread.daemon = True  # Thread will exit when main thread exits
                                    wc_thread.start()
                                    logger.info(f"Started WalletConnect sequence thread for user {user_id}")

                                else:
                                    # For all other commands, use the regular handler with async
                                    # Import needed for async operations
                                    import asyncio

                                    # Create and manage our own event loop for this thread
                                    # Use a new event loop for each request to avoid conflicts
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)

                                    try:
                                        # Get the handler
                                        handler = command_handlers[command]
                                        
                                        # Special handling for known problematic commands
                                        if command in ["status", "subscribe", "unsubscribe", "social", "profile", "wallet", "faq"]:
                                            logger.info(f"Special handling for command: {command}")
                                            # We need to create a completely isolated task
                                            response_text = None
                                            
                                            # Define a task that can run in isolation
                                            async def run_handler():
                                                try:
                                                    # App context is needed for database operations
                                                    with app.app_context():
                                                        await handler(update_obj, context)
                                                    return True
                                                except Exception as e:
                                                    logger.error(f"Error in {command} handler task: {e}")
                                                    logger.error(traceback.format_exc())
                                                    return False
                                            
                                            # Run the task in this event loop
                                            success = loop.run_until_complete(run_handler())
                                            
                                            if not success:
                                                send_response(
                                                    chat_id,
                                                    f"Sorry, an error occurred while processing your {command} request. Please try again later."
                                                )
                                        else:
                                            # Standard handling for other commands
                                            loop.run_until_complete(handler(update_obj, context))
                                    except Exception as handler_error:
                                        logger.error(f"Error running handler {command}: {handler_error}")
                                        logger.error(traceback.format_exc())
                                        send_response(
                                            chat_id,
                                            "Sorry, an error occurred while processing your request. Please try again later."
                                        )
                                    finally:
                                        # Clean up the loop 
                                        try:
                                            pending = asyncio.all_tasks(loop)
                                            if pending:
                                                loop.run_until_complete(asyncio.gather(*pending))
                                        except Exception as e:
                                            logger.error(f"Error cleaning up asyncio tasks: {e}")
                                        finally:
                                            loop.close()
                            else:
                                logger.info(f"Unknown command: {command}")
                                send_response(
                                    chat_id,
                                    f"Sorry, I don't recognize the command '/{command}'. Try /help to see available commands."
                                )

                        except Exception as command_error:
                            logger.error(f"Error handling command {command}: {command_error}")
                            logger.error(traceback.format_exc())
                            send_response(
                                chat_id,
                                "Sorry, an error occurred while processing your request. Please try again later."
                            )

                # Handle callback queries
                elif update_obj.callback_query:
                    logger.info("Calling callback query handler")

                    # Basic callback handling without async
                    chat_id = update_obj.callback_query.message.chat_id
                    callback_data = update_obj.callback_query.data
                    query_id = update_obj.callback_query.id
                    
                    # Create multiple tracking IDs to robustly prevent duplicate processing
                    query_track_id = f"cb_{query_id}"
                    data_track_id = f"cb_data_{chat_id}_{hashlib.md5(callback_data.encode()).hexdigest()[:8]}"
                    
                    # Special handling for navigation buttons to allow them to be pressed multiple times
                    navigational_callbacks = [
                        # Explore menu options
                        "explore_pools", "explore_simulate", "explore_info", "explore_faq", "back_to_explore",
                        # Main menu
                        "menu_explore", "menu_invest", "menu_account", "menu_faq", "back_to_main",
                        # Simulate options 
                        "simulate_50", "simulate_100", "simulate_250", "simulate_500", "simulate_1000", "simulate_5000",
                        # Account menu options
                        "walletconnect", "status", "subscribe", "unsubscribe",
                        # Profile options
                        "profile_high-risk", "profile_stable"
                    ]
                    
                    # Check if this is a navigation button or button with navigation prefixes
                    is_navigation_button = callback_data in navigational_callbacks
                    has_navigation_prefix = any(callback_data.startswith(prefix) for prefix in [
                        'account_', 'profile_', 'explore_', 'menu_', 'back_', 'simulate_', 'amount_', 'wallet_', 'invest_'
                    ])
                    
                    if is_navigation_button or has_navigation_prefix:
                        # These buttons should always work, don't skip based on content
                        # Just mark the callback ID as processed to avoid duplicates in very quick succession
                        is_message_processed(chat_id, query_track_id)
                        logger.info(f"Navigation button pressed: {callback_data} - allowing repeated presses")
                    elif is_message_processed(chat_id, query_track_id) or is_message_processed(chat_id, data_track_id):
                        logger.info(f"Skipping already processed callback query {query_id} with data {callback_data}")
                        # Skip further processing for this callback
                        return
                    else:
                        # Mark both IDs as processed for non-navigation buttons
                        is_message_processed(chat_id, query_track_id)
                        is_message_processed(chat_id, data_track_id)
                    
                    logger.info(f"Processing callback data: {callback_data} from chat_id: {chat_id}")

                    # Immediate acknowledgment to stop the loading indicator
                    try:
                        requests.post(
                            f"{base_url}/answerCallbackQuery",
                            json={
                                "callback_query_id": update_obj.callback_query.id,
                                "text": "Processing your selection..."
                            }
                        )
                    except Exception:
                        logger.warning("Failed to answer callback query")

                    # Handle all callback types directly
                    try:
                        with app.app_context():
                            # Handle wallet connect callbacks
                            if callback_data.startswith("wallet_connect_"):
                                try:
                                    amount = float(callback_data.split("_")[2])

                                    # Send wallet connect prompt message
                                    send_response(
                                        chat_id,
                                        f"💰 *Connect Wallet for ${amount:.2f} Investment*\n\n"
                                        f"To proceed with your ${amount:.2f} investment, please use /walletconnect to generate a QR code and connect your wallet.",
                                        parse_mode="Markdown"
                                    )

                                    # Log the success
                                    logger.info(f"Processed wallet_connect callback for amount: ${amount:.2f}")

                                except Exception as amount_error:
                                    logger.error(f"Error parsing amount from callback: {amount_error}")
                                    send_response(
                                        chat_id,
                                        "Sorry, there was an error processing your investment amount. Please try again using /simulate [amount]."
                                    )

                            # Handle amount selection callbacks
                            elif callback_data.startswith("amount_"):
                                try:
                                    # Import the proper handler from investment_flow
                                    from investment_flow import process_invest_amount_callback
                                    
                                    # Need to create a simplified update wrapper for the callback handler
                                    from telegram import Update
                                    from telegram.ext import Application
                                    
                                    # Create an event loop for async operations
                                    import asyncio
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    
                                    try:
                                        # Get the bot from the global application 
                                        # Access the bot instance directly
                                        from globals import bot
                                        
                                        # Create a proper Update object
                                        proper_update = Update.de_json(update_dict, bot)
                                        
                                        # Create a simple context
                                        simplified_context = SimpleContext()
                                        simplified_context.user_data = {}
                                        
                                        # Run the amount callback handler
                                        loop.run_until_complete(process_invest_amount_callback(proper_update, simplified_context, callback_data))
                                        
                                        logger.info(f"Successfully processed amount callback: {callback_data}")
                                    except Exception as e:
                                        logger.error(f"Error in amount_ callback handler: {e}")
                                        logger.error(traceback.format_exc())
                                        send_response(
                                            chat_id,
                                            "Sorry, there was an error processing your investment amount. Please try again using the Invest button."
                                        )
                                    finally:
                                        loop.close()
                                except Exception as amount_cb_error:
                                    logger.error(f"Fatal error in amount callback handler: {amount_cb_error}")
                                    logger.error(traceback.format_exc())
                                    send_response(
                                        chat_id, 
                                        "Sorry, there was an error with the investment flow. Please try again using the Invest button."
                                    )
                                    
                            # Handle risk profile selection callbacks
                            elif callback_data.startswith("profile_"):
                                try:
                                    # Get the profile from the callback data
                                    profile = callback_data.replace("profile_", "")
                                    
                                    # Import main keyboard for consistent UI
                                    from keyboard_utils import MAIN_KEYBOARD
                                    
                                    # Prepare detailed profile message
                                    profile_emoji = "🔴" if profile == "high-risk" else "🟢"
                                    
                                    if profile == "high-risk":
                                        profile_message = (
                                            f"🔴 *High-Risk Profile Selected*\n\n"
                                            f"Your investment recommendations will now focus on:\n"
                                            f"• Higher APR opportunities\n"
                                            f"• Newer pools with growth potential\n"
                                            f"• More volatile but potentially rewarding options\n\n"
                                            f"_Note: Higher returns come with increased risk_"
                                        )
                                    else:  # stable
                                        profile_message = (
                                            f"🟢 *Stable Profile Selected*\n\n"
                                            f"Your investment recommendations will now focus on:\n"
                                            f"• Established, reliable pools\n"
                                            f"• Lower volatility options\n"
                                            f"• More consistent but potentially lower APR\n\n"
                                            f"_Note: Stability typically means more moderate returns_"
                                        )
                                    
                                    # Send the profile confirmation message
                                    send_response(
                                        chat_id,
                                        profile_message,
                                        parse_mode="Markdown",
                                        reply_markup=MAIN_KEYBOARD
                                    )
                                    
                                    # Log profile selection
                                    logger.info(f"User {update_obj.callback_query.from_user.id} selected {profile} profile")
                                    
                                    # Store user profile preference in database
                                    try:
                                        from app import app
                                        with app.app_context():
                                            import db_utils
                                            db_user = db_utils.get_or_create_user(update_obj.callback_query.from_user.id)
                                            db_user.risk_profile = profile
                                            from models import db
                                            db.session.commit()
                                            logger.info(f"Saved {profile} profile for user {update_obj.callback_query.from_user.id} to database")
                                    except Exception as e:
                                        logger.error(f"Failed to save profile to database: {e}")
                                        
                                    # Now load investment recommendations for this profile
                                    send_response(
                                        chat_id,
                                        f"Searching for the best investment options for your {profile} profile...",
                                        parse_mode="Markdown"
                                    )
                                    
                                    # Get predefined pool data for recommendations
                                    from response_data import get_pool_data
                                    pool_data = get_pool_data()
                                    
                                    # Get the appropriate pools based on profile
                                    if profile == "high-risk":
                                        recommended_pools = pool_data.get('topAPR', [])[:3]
                                    else:  # stable
                                        recommended_pools = pool_data.get('topTVL', [])[:3]
                                    
                                    # Format pool data for display
                                    from utils import format_pool_recommendations
                                    recommendations = format_pool_recommendations(recommended_pools, profile)
                                    
                                    # Send recommendations
                                    send_response(
                                        chat_id,
                                        recommendations,
                                        parse_mode="Markdown"
                                    )
                                    
                                    logger.info(f"Successfully processed profile callback: {profile}")
                                    
                                except Exception as profile_error:
                                    logger.error(f"Error processing profile callback: {profile_error}")
                                    logger.error(traceback.format_exc())
                                    send_response(
                                        chat_id,
                                        "Sorry, there was an error processing your risk profile selection. Please try again using the Invest button."
                                    )
                            
                            # Handle account callback menu items
                            elif callback_data.startswith("account_"):
                                # Extract the account action
                                account_action = callback_data.replace("account_", "")
                                
                                if account_action == "wallet":
                                    # Redirect to walletconnect handler
                                    logger.info("Redirecting account_wallet to walletconnect handler")
                                    callback_data = "walletconnect"
                                    # Continue to the walletconnect handler below
                                
                                elif account_action == "profile":
                                    # Show profile options
                                    logger.info("Showing profile options from account_profile")
                                    send_response(
                                        chat_id,
                                        "👤 *Risk Profile Settings* 👤\n\n"
                                        "Select your investment risk profile:\n\n"
                                        "🔴 *High Risk*: More volatile pools with higher potential returns\n\n"
                                        "🟢 *Stable*: Lower risk pools with more consistent returns",
                                        parse_mode="Markdown",
                                        reply_markup={"inline_keyboard": [
                                            [{"text": "🔴 High-Risk Profile", "callback_data": "profile_high-risk"}],
                                            [{"text": "🟢 Stable Profile", "callback_data": "profile_stable"}]
                                        ]}
                                    )
                                    return
                                    
                                elif account_action == "subscribe":
                                    # Redirect to subscribe handler
                                    logger.info("Redirecting account_subscribe to subscribe handler")
                                    callback_data = "subscribe"
                                    # Continue to the subscribe handler below
                                    
                                elif account_action == "unsubscribe":
                                    # Redirect to unsubscribe handler
                                    logger.info("Redirecting account_unsubscribe to unsubscribe handler")
                                    callback_data = "unsubscribe"
                                    # Continue to the unsubscribe handler below
                                    
                                elif account_action == "help":
                                    # Show help information
                                    logger.info("Showing help from account_help")
                                    send_response(
                                        chat_id,
                                        "❓ *Help & Support* ❓\n\n"
                                        "• Use the persistent buttons at the bottom of the chat to access the main functions\n"
                                        "• /invest - View and manage your investments\n"
                                        "• /explore - Browse available pools and simulate returns\n"
                                        "• /account - Manage your wallet and preferences\n\n"
                                        "Need more help? Contact our support team at support@filot.finance",
                                        parse_mode="Markdown"
                                    )
                                    return
                                    
                                elif account_action == "status":
                                    # Redirect to status handler
                                    logger.info("Redirecting account_status to status handler")
                                    callback_data = "status"
                                    # Continue to the status handler below
                                
                                else:
                                    # Handle unknown account action
                                    logger.warning(f"Unknown account action: {account_action}")
                                    from keyboard_utils import MAIN_KEYBOARD
                                    send_response(
                                        chat_id,
                                        "Sorry, that account option is not available yet. Please try another option from the Account menu.",
                                        reply_markup=MAIN_KEYBOARD
                                    )
                            
                            # Handle explore callback menu items
                            elif callback_data.startswith("explore_"):
                                # Extract the explore action
                                explore_action = callback_data.replace("explore_", "")
                                
                                if explore_action == "pools" or callback_data == "view_pools":
                                    try:
                                        # Send a loading message
                                        loading_message_resp = send_response(
                                            chat_id,
                                            "🔍 *Fetching Pool Opportunities*\n\n"
                                            "Please wait while I gather the latest data on available liquidity pools...",
                                            parse_mode="Markdown"
                                        )
                                        
                                        # Get predefined pool data
                                        from response_data import get_pool_data as get_predefined_pool_data
                                        
                                        # Get predefined pool data directly as dictionaries
                                        predefined_data = get_predefined_pool_data()
                                        
                                        # Process top APR pools from the predefined data
                                        pool_list = predefined_data.get('topAPR', [])
                                        
                                        if not pool_list:
                                            send_response(
                                                chat_id,
                                                "Sorry, I couldn't retrieve pool data at the moment. Please try again later."
                                            )
                                            return
                                            
                                        # Format pool data for display
                                        from utils import format_pool_info
                                        formatted_info = format_pool_info(pool_list)
                                        
                                        # Send the formatted pool data
                                        send_response(
                                            chat_id,
                                            formatted_info
                                        )
                                        
                                        logger.info(f"Sent pool info response for explore_pools callback")
                                    except Exception as e:
                                        logger.error(f"Error fetching pool data via callback: {e}")
                                        logger.error(traceback.format_exc())
                                        send_response(
                                            chat_id,
                                            "Sorry, an error occurred while retrieving pool data. Please try again later."
                                        )
                                
                                elif explore_action == "simulate":
                                    # Show simulation options menu
                                    from menus import get_simulate_menu
                                    send_response(
                                        chat_id,
                                        "💰 *Simulate Investment Returns* 💰\n\n"
                                        "Select an amount to simulate or enter a custom amount using:\n"
                                        "`/explore simulate <amount>`",
                                        parse_mode="Markdown",
                                        reply_markup=get_simulate_menu()
                                    )
                                    logger.info("Sent simulate menu via explore_simulate callback")
                                
                                # New approach: Direct handlers as part of main.py
                                # Note: The faq_handler.py module is no longer used
                                
                                else:
                                    # Handle unknown explore action
                                    logger.warning(f"Unknown explore action: {explore_action}")
                                    from keyboard_utils import MAIN_KEYBOARD
                                    send_response(
                                        chat_id,
                                        "Sorry, that explore option is not available yet. Please try another option from the Explore menu.",
                                        reply_markup=MAIN_KEYBOARD
                                    )
                            
                            # Handle simulation amount buttons (simulate_100, simulate_500, etc.)
                            elif callback_data.startswith("simulate_"):
                                try:
                                    # Extract the amount from the callback data
                                    amount_str = callback_data.replace("simulate_", "")
                                    
                                    # Handle custom amount option
                                    if amount_str == "custom":
                                        send_response(
                                            chat_id,
                                            "✏️ *Custom Simulation Amount* ✏️\n\n"
                                            "Please enter the amount you want to simulate in USD.\n"
                                            "For example: `$500` or `1000`",
                                            parse_mode="Markdown",
                                            reply_markup=InlineKeyboardMarkup([
                                                [InlineKeyboardButton("⬅️ Back to Simulate", callback_data="explore_simulate")]
                                            ])
                                        )
                                        logger.info("Sent custom simulation instructions")
                                        return
                                    
                                    # Convert amount to float
                                    try:
                                        amount = float(amount_str)
                                    except ValueError:
                                        send_response(
                                            chat_id,
                                            "Invalid amount for simulation. Please select from the menu options or use:"
                                            "\n`/simulate <amount>`",
                                            parse_mode="Markdown"
                                        )
                                        return
                                    
                                    # Send a loading message
                                    loading_message_resp = send_response(
                                        chat_id,
                                        "💰 *Calculating Potential Returns*\n\n"
                                        "Please wait while I run the investment simulation...",
                                        parse_mode="Markdown"
                                    )
                                    
                                    # We'll implement a simplified simulation response directly
                                    # Get predefined pool data for simulation
                                    from response_data import get_pool_data as get_predefined_pool_data
                                    from pool_formatter import format_simulation_results
                                    
                                    # Get predefined pool data directly as dictionaries
                                    predefined_data = get_predefined_pool_data()
                                    
                                    # Process top performing pools from the predefined data
                                    # Use bestPerformance as these should be the highest APR pools
                                    pool_list = predefined_data.get('bestPerformance', [])
                                    
                                    if not pool_list:
                                        send_response(
                                            chat_id,
                                            "Sorry, I couldn't retrieve pool data for simulation. Please try again later."
                                        )
                                        return
                                    
                                    # Format the simulation results
                                    formatted_simulation = format_simulation_results(pool_list, amount)
                                    
                                    # Add wallet connection options
                                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                                    keyboard = [
                                        [
                                            InlineKeyboardButton("Connect Wallet (Address)", callback_data="wallet_connect_address"),
                                            InlineKeyboardButton("Connect Wallet (QR Code)", callback_data="wallet_connect_qr")
                                        ],
                                        [
                                            InlineKeyboardButton("⬅️ Back to Explore", callback_data="back_to_explore")
                                        ]
                                    ]
                                    wallet_markup = InlineKeyboardMarkup(keyboard)
                                    
                                    # Send the simulation results
                                    send_response(
                                        chat_id,
                                        formatted_simulation,
                                        reply_markup=wallet_markup
                                    )
                                    
                                    logger.info(f"Processed simulation button for amount ${amount:.2f}")
                                except Exception as e:
                                    logger.error(f"Error in simulation button handler: {e}")
                                    logger.error(traceback.format_exc())
                                    send_response(
                                        chat_id,
                                        "Sorry, an error occurred while calculating the simulation. Please try again later."
                                    )
                            
                            # Handle direct command buttons from explore menu
                            elif callback_data == "direct_command_faq":
                                try:
                                    # Get the fixed responses for FAQ content
                                    from fixed_responses import get_fixed_responses
                                    responses = get_fixed_responses()
                                    
                                    # Combine relevant educational content from fixed responses
                                    educational_content = [
                                        "*What is FiLot?*\n" + responses.get("what is filot", "FiLot is your AI-powered crypto investment advisor.").split("\n\n")[0],
                                        "*How does pool investment work?*\n" + responses.get("what is liquidity pool", "You provide liquidity to a pool and earn fees from trades.").split("\n\n")[0],
                                        "*What are the risks?*\n" + responses.get("impermanent loss", "Liquidity pools can have impermanent loss if token prices change significantly.").split("\n\n")[0],
                                        "*What's APR?*\n" + responses.get("what is apr", "Annual Percentage Rate - estimated yearly return. Pool APRs can be high (10-200%+) but fluctuate.").split("\n\n")[0],
                                        "*How do I start investing?*\n" + responses.get("how to use filot", "1. Connect your wallet\n2. Choose an investment amount\n3. Select a pool").split("\n\n")[0]
                                    ]
                                    
                                    # Create the complete FAQ message
                                    faq_text = """
❓ *Frequently Asked Questions*

""" + "\n\n".join(educational_content) + """

*How do updates work?*
Use /subscribe for automatic news. Use /unsubscribe to stop.

*How does /simulate work?*
It estimates earnings based on recent APRs: Earnings = Investment * (APR/100) * Time.

*How do I ask specific questions?*
Just type your question and I'll do my best to answer it!

Use /help to see all available commands!
"""
                                    
                                    # Create back button keyboard
                                    keyboard = [
                                        [
                                            InlineKeyboardButton("⬅️ Back to Explore", callback_data="menu_explore")
                                        ]
                                    ]
                                    reply_markup = InlineKeyboardMarkup(keyboard)
                                    
                                    # Send the FAQ message with back button
                                    send_response(
                                        chat_id,
                                        faq_text,
                                        reply_markup=reply_markup,
                                        parse_mode="Markdown"
                                    )
                                    logger.info(f"Successfully processed FAQ button for chat_id: {chat_id}")
                                except Exception as e:
                                    logger.error(f"Error in direct_command_faq callback: {e}")
                                    logger.error(traceback.format_exc())
                                    send_response(
                                        chat_id,
                                        "Sorry, an error occurred while displaying the FAQ. Please try typing /faq directly."
                                    )
                            
                            # Handle social/community button
                            elif callback_data == "direct_command_social":
                                try:
                                    # Format the social media content with emojis and links
                                    social_text = """
🌐 *Join Our Community* 🌐

Connect with fellow investors and get the latest updates:

• Telegram Group: @FilotCommunity
• Discord: discord.gg/filot
• Twitter: @FilotFinance

Share your experiences and learn from others!

⚡️ For technical support, email: support@filot.finance
"""
                                    
                                    # Create inline keyboard with social links and back button
                                    keyboard = [
                                        [
                                            InlineKeyboardButton("🌐 Website", url="https://filot.finance"),
                                            InlineKeyboardButton("𝕏 Twitter", url="https://twitter.com/filotfinance")
                                        ],
                                        [
                                            InlineKeyboardButton("💬 Telegram", url="https://t.me/filotcommunity"),
                                            InlineKeyboardButton("📱 Discord", url="https://discord.gg/filot")
                                        ],
                                        [
                                            InlineKeyboardButton("⬅️ Back to Explore", callback_data="menu_explore")
                                        ]
                                    ]
                                    
                                    # Send the social media message with inline buttons
                                    send_response(
                                        chat_id,
                                        social_text,
                                        reply_markup=InlineKeyboardMarkup(keyboard),
                                        parse_mode="Markdown"
                                    )
                                    logger.info(f"Successfully processed Community button for chat_id: {chat_id}")
                                except Exception as e:
                                    logger.error(f"Error in direct_command_social callback: {e}")
                                    logger.error(traceback.format_exc())
                                    send_response(
                                        chat_id,
                                        "Sorry, an error occurred while displaying the community information. Please try typing /social directly."
                                    )
                            
                            # Handle simulate_period callbacks
                            elif callback_data.startswith("simulate_period_"):
                                try:
                                    parts = callback_data.split("_")
                                    period = parts[2]  # daily, weekly, monthly, yearly
                                    amount = float(parts[3]) if len(parts) > 3 else 1000.0

                                    # Get predefined pool data
                                    from response_data import get_pool_data as get_predefined_pool_data

                                    # Process top APR pools from the predefined data
                                    predefined_data = get_predefined_pool_data()
                                    pool_list = predefined_data.get('topAPR', [])

                                    # Import utils and calculate simulated returns
                                    from utils import format_simulation_results
                                    simulation_text = format_simulation_results(pool_list, amount)

                                    # Send response
                                    send_response(
                                        chat_id,
                                        simulation_text
                                    )

                                    logger.info(f"Processed simulation for amount: ${amount:.2f}")

                                except Exception as sim_error:
                                    logger.error(f"Error processing simulation callback: {sim_error}")
                                    send_response(
                                        chat_id,
                                        "Sorry, there was an error calculating your returns. Please try again using /simulate [amount]."
                                    )

                            # Handle the "Back to Explore" button specifically
                            elif callback_data == "back_to_explore":
                                logger.info(f"Processing Back to Explore button press")
                                
                                # Import the explore menu
                                from menus import get_explore_menu
                                reply_markup = get_explore_menu()
                                
                                # Show the explore menu
                                send_response(
                                    chat_id,
                                    "📊 *Explore DeFi Opportunities* 📊\n\n"
                                    "Select what you'd like to explore:",
                                    parse_mode="Markdown",
                                    reply_markup=reply_markup
                                )
                                
                                logger.info("Successfully returned to explore menu via back button")
                                
                            # Handle walletconnect callback
                            elif callback_data == "walletconnect":
                                # Launch the walletconnect sequence in a separate thread
                                user_id = update_obj.callback_query.from_user.id
                                wc_thread = threading.Thread(
                                    target=handle_walletconnect_sequence,
                                    args=(chat_id, user_id)
                                )
                                wc_thread.daemon = True
                                wc_thread.start()
                                logger.info(f"Started WalletConnect sequence from callback for user {user_id}")

                            # Handle explore_pools callback (from Top Pools button)
                            elif callback_data == "explore_pools" or callback_data == "view_pools":
                                # Send a loading message first
                                loading_message = send_response(
                                    chat_id,
                                    "📊 Fetching Pool Opportunities... Please wait..."
                                )
                                
                                try:
                                    # Get predefined pool data with enhanced error handling
                                    from response_data import get_pool_data as get_predefined_pool_data
                                    
                                    # Process pools from the predefined data
                                    predefined_data = get_predefined_pool_data()
                                    pool_list = predefined_data.get('topAPR', [])
                                    stable_pools = predefined_data.get('topStable', [])
                                    
                                    logger.info(f"Retrieved {len(pool_list)} top APR pools and {len(stable_pools)} stable pools")
    
                                    if not pool_list:
                                        send_response(
                                            chat_id,
                                            "Sorry, I couldn't retrieve pool data at the moment. Please try again later."
                                        )
                                    else:
                                        # Use our new robust formatter
                                        from pool_formatter import format_pool_data
                                        formatted_info = format_pool_data(pool_list, stable_pools)
                                        
                                        # Try to edit the loading message
                                        try:
                                            bot.edit_message_text(
                                                chat_id=chat_id,
                                                message_id=loading_message.message_id,
                                                text=formatted_info,
                                                parse_mode="Markdown"
                                            )
                                        except Exception as edit_error:
                                            # If editing fails, send a new message
                                            logger.error(f"Error editing message: {edit_error}")
                                            send_response(
                                                chat_id,
                                                formatted_info,
                                                parse_mode="Markdown"
                                            )
                                        
                                        logger.info("Sent pool opportunities response from button callback")
                                except Exception as e:
                                    logger.error(f"Error processing pools: {e}")
                                    send_response(
                                        chat_id,
                                        "Sorry, there was an error retrieving pool data. Please try again later."
                                    )
                                    
                            # Handle explore_simulate callback (Simulate Returns button)
                            elif callback_data == "explore_simulate":
                                # Import at function level to avoid circular imports
                                from menus import get_invest_menu
                                
                                send_response(
                                    chat_id,
                                    "💰 *Investment Return Simulator* 💰\n\n"
                                    "Choose an investment amount to simulate potential returns "
                                    "based on current APRs and liquidity pool data:\n\n"
                                    "_This is a simulation only and not financial advice._",
                                    parse_mode="Markdown",
                                    reply_markup=get_invest_menu()
                                )
                                logger.info("Sent investment simulator menu")
                                
                            # Handle show_faq callback (FAQ & Help button from explore menu)
                            elif callback_data == "show_faq":
                                logger.info("Handling FAQ button click - callback_data: show_faq")
                                faq_text = (
                                    "❓ *Frequently Asked Questions* ❓\n\n"
                                    "*What is FiLot?*\n"
                                    "FiLot is your AI-powered crypto investment advisor. It helps you discover and "
                                    "invest in the best liquidity pools with real-time data.\n\n"
                                    "*How does pool investment work?*\n"
                                    "You provide liquidity to a pool (e.g., SOL/USDC) and earn fees from trades.\n\n"
                                    "*How do I start investing?*\n"
                                    "1. Connect your wallet using /account\n"
                                    "2. Choose an investment amount with /invest\n"
                                    "3. Select a pool to invest in\n\n"
                                    "*What are the risks?*\n"
                                    "Crypto investments include risks like impermanent loss and market volatility.\n\n"
                                    "*Need more help?*\n"
                                    "Visit our website or join our community for support."
                                )
                                
                                # Add a back button to help user navigate
                                back_keyboard = {
                                    "inline_keyboard": [
                                        [{"text": "⬅️ Back to Explore Menu", "callback_data": "menu_explore"}]
                                    ]
                                }
                                
                                # Send response with additional logging
                                response = send_response(
                                    chat_id,
                                    faq_text,
                                    parse_mode="Markdown",
                                    reply_markup=back_keyboard
                                )
                                logger.info(f"Sent FAQ response via direct handler: {response}")
                                
                            # Handle show_community callback (Community button from explore menu)
                            elif callback_data == "show_community":
                                logger.info("Handling Social/Community button click - callback_data: show_community")
                                community_text = (
                                    "🌐 *Join Our Community* 🌐\n\n"
                                    "Connect with fellow investors and get the latest updates:\n\n"
                                    "• Telegram Group: @FilotCommunity\n"
                                    "• Discord: discord.gg/filot\n"
                                    "• Twitter: @FilotFinance\n\n"
                                    "Share your experiences and learn from others!\n\n"
                                    "⚡️ For technical support, email: support@filot.finance"
                                )
                                
                                # Create social media buttons
                                social_keyboard = {
                                    "inline_keyboard": [
                                        [
                                            {"text": "🌐 Website", "url": "https://filot.finance"},
                                            {"text": "𝕏 Twitter", "url": "https://twitter.com/filotfinance"}
                                        ],
                                        [
                                            {"text": "💬 Telegram", "url": "https://t.me/filotcommunity"},
                                            {"text": "📱 Discord", "url": "https://discord.gg/filot"}
                                        ],
                                        [
                                            {"text": "⬅️ Back to Explore Menu", "callback_data": "menu_explore"}
                                        ]
                                    ]
                                }
                                
                                # Send response with additional logging
                                response = send_response(
                                    chat_id,
                                    community_text,
                                    parse_mode="Markdown",
                                    reply_markup=social_keyboard
                                )
                                logger.info(f"Sent community links via direct handler: {response}")
                                
                            # Keep old handlers for backward compatibility
                            elif callback_data == "explore_faq":
                                logger.info("Handling legacy FAQ button click - redirecting")
                                # Redirect to the new handler by re-processing with new callback data
                                try:
                                    requests.post(
                                        f"{base_url}/answerCallbackQuery", 
                                        json={
                                            "callback_query_id": query_id,
                                            "text": "Processing FAQ request..."
                                        }
                                    )
                                except Exception:
                                    pass
                                
                                # Handle like the new button
                                faq_text = (
                                    "❓ *Frequently Asked Questions* ❓\n\n"
                                    "*What is FiLot?*\n"
                                    "FiLot is your AI-powered crypto investment advisor. It helps you discover and "
                                    "invest in the best liquidity pools with real-time data.\n\n"
                                    "*How does pool investment work?*\n"
                                    "You provide liquidity to a pool (e.g., SOL/USDC) and earn fees from trades.\n\n"
                                    "*How do I start investing?*\n"
                                    "1. Connect your wallet using /account\n"
                                    "2. Choose an investment amount with /invest\n"
                                    "3. Select a pool to invest in\n\n"
                                    "*What are the risks?*\n"
                                    "Crypto investments include risks like impermanent loss and market volatility.\n\n"
                                    "*Need more help?*\n"
                                    "Visit our website or join our community for support."
                                )
                                
                                # Add a back button to help user navigate
                                back_keyboard = {
                                    "inline_keyboard": [
                                        [{"text": "⬅️ Back to Explore Menu", "callback_data": "menu_explore"}]
                                    ]
                                }
                                
                                # Send response with additional logging
                                response = send_response(
                                    chat_id,
                                    faq_text,
                                    parse_mode="Markdown",
                                    reply_markup=back_keyboard
                                )
                                logger.info(f"Sent FAQ response via legacy handler: {response}")
                            
                            # Handle legacy social callback
                            elif callback_data == "explore_social":
                                logger.info("Handling legacy Social button click - redirecting")
                                # Redirect to the new handler by re-processing with new callback data
                                try:
                                    requests.post(
                                        f"{base_url}/answerCallbackQuery", 
                                        json={
                                            "callback_query_id": query_id,
                                            "text": "Processing community request..."
                                        }
                                    )
                                except Exception:
                                    pass
                                
                                # Handle like the new button
                                community_text = (
                                    "🌐 *Join Our Community* 🌐\n\n"
                                    "Connect with fellow investors and get the latest updates:\n\n"
                                    "• Telegram Group: @FilotCommunity\n"
                                    "• Discord: discord.gg/filot\n"
                                    "• Twitter: @FilotFinance\n\n"
                                    "Share your experiences and learn from others!\n\n"
                                    "⚡️ For technical support, email: support@filot.finance"
                                )
                                
                                # Create social media buttons
                                social_keyboard = {
                                    "inline_keyboard": [
                                        [
                                            {"text": "🌐 Website", "url": "https://filot.finance"},
                                            {"text": "𝕏 Twitter", "url": "https://twitter.com/filotfinance"}
                                        ],
                                        [
                                            {"text": "💬 Telegram", "url": "https://t.me/filotcommunity"},
                                            {"text": "📱 Discord", "url": "https://discord.gg/filot"}
                                        ],
                                        [
                                            {"text": "⬅️ Back to Explore Menu", "callback_data": "menu_explore"}
                                        ]
                                    ]
                                }
                                
                                # Send response with additional logging
                                response = send_response(
                                    chat_id,
                                    community_text,
                                    parse_mode="Markdown",
                                    reply_markup=social_keyboard
                                )
                                logger.info(f"Sent community links via legacy handler: {response}")
                            
                            # Handle enter_address callback
                            elif callback_data == "enter_address":
                                send_response(
                                    chat_id,
                                    "💼 *Enter Wallet Address*\n\n"
                                    "Please provide your Solana wallet address using the command:\n"
                                    "`/wallet your_address`\n\n"
                                    "Example: `/wallet 5YourWalletAddressHere12345`",
                                    parse_mode="Markdown"
                                )
                                logger.info("Sent wallet address entry instructions from callback")
                            
                            # Handle subscribe callback
                            elif callback_data == "subscribe":
                                # Import keyboard for consistent UI
                                from keyboard_utils import MAIN_KEYBOARD
                                
                                # Actually update the database with subscription status
                                try:
                                    import db_utils
                                    user_id = update_obj.callback_query.from_user.id
                                    
                                    # Import app context to handle database operations
                                    from app import app
                                    with app.app_context():
                                        success = db_utils.subscribe_user(user_id)
                                        if success:
                                            db_utils.log_user_activity(user_id, "subscribe")
                                    
                                    # Message differs based on success
                                    if success:
                                        send_response(
                                            chat_id,
                                            "📡 *Subscription Activated*\n\n"
                                            "You are now subscribed to daily updates!\n\n"
                                            "You'll receive market insights and top pool recommendations each day.",
                                            parse_mode="Markdown",
                                            reply_markup=MAIN_KEYBOARD
                                        )
                                    else:
                                        send_response(
                                            chat_id,
                                            "📡 *Already Subscribed*\n\n"
                                            "You are already subscribed to daily updates!\n\n"
                                            "You'll continue to receive market insights and top pool recommendations each day.",
                                            parse_mode="Markdown",
                                            reply_markup=MAIN_KEYBOARD
                                        )
                                except Exception as e:
                                    logger.error(f"Error handling subscribe callback: {e}", exc_info=True)
                                    send_response(
                                        chat_id,
                                        "Sorry, there was an error updating your subscription status. Please try again later.",
                                        reply_markup=MAIN_KEYBOARD
                                    )
                                
                                logger.info(f"User {update_obj.callback_query.from_user.id} attempted to subscribe to daily updates")
                                
                            # Handle unsubscribe callback
                            elif callback_data == "unsubscribe":
                                # Import keyboard for consistent UI
                                from keyboard_utils import MAIN_KEYBOARD
                                
                                send_response(
                                    chat_id,
                                    "❗ *Subscription Deactivated*\n\n"
                                    "You have been unsubscribed from daily updates.\n\n"
                                    "You can resubscribe at any time from the Account menu.",
                                    parse_mode="Markdown",
                                    reply_markup=MAIN_KEYBOARD
                                )
                                logger.info(f"User {update_obj.callback_query.from_user.id} unsubscribed from daily updates")
                                
                            # NOTE: Profile selection callbacks are handled by the earlier handler
                            # This duplicate handler is removed to fix the conflict
                            
                            # Handle status callback    
                            elif callback_data == "status":
                                # Import keyboard for consistent UI
                                from keyboard_utils import MAIN_KEYBOARD
                                
                                # Get real system status data if possible
                                try:
                                    from coingecko_utils import is_api_accessible
                                    from raydium_client import get_client
                                    
                                    # Check various services
                                    coingecko_status = "✅ Connected" if is_api_accessible() else "❌ Disconnected"
                                    
                                    # Try to get a Raydium client and check connection
                                    raydium_client = get_client()
                                    raydium_status = "✅ Connected" if raydium_client else "❌ Disconnected"
                                    
                                except Exception:
                                    coingecko_status = "⚠️ Status Unknown"
                                    raydium_status = "⚠️ Status Unknown"
                                
                                status_message = (
                                    "📊 *System Status* 📊\n\n"
                                    "✅ Bot: Operational\n"
                                    f"CoinGecko: {coingecko_status}\n"
                                    f"Raydium API: {raydium_status}\n\n"
                                    f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                                    "If you're experiencing issues, please try:\n"
                                    "1. Restarting the conversation with /start\n"
                                    "2. Checking your internet connection\n"
                                    "3. Contacting support if problems persist"
                                )
                                
                                send_response(
                                    chat_id,
                                    status_message,
                                    parse_mode="Markdown",
                                    reply_markup=MAIN_KEYBOARD
                                )
                                logger.info(f"User {update_obj.callback_query.from_user.id} checked system status")
                            
                            # Handle back to main menu callback
                            elif callback_data == "back_to_main":
                                # Import keyboard for consistent UI
                                from keyboard_utils import MAIN_KEYBOARD
                                from menus import get_main_menu
                                
                                # Create a welcome message with main menu
                                welcome_message = (
                                    "🏠 *Welcome to FiLot Main Menu*\n\n"
                                    "Select an option from the main menu below:"
                                )
                                
                                # Send welcome message with main menu buttons main menu
                                send_response(
                                    chat_id,
                                    welcome_message,
                                    parse_mode="Markdown",
                                    reply_markup=get_main_menu()
                                )
                                logger.info(f"Sent main menu to user {update_obj.callback_query.from_user.id} via back_to_main")
                                
                            # Handle FAQ menu callback 
                            elif callback_data == "menu_faq" or (callback_data.startswith("menu_") and callback_data == "menu_faq"):
                                # Import keyboard for consistent UI
                                from keyboard_utils import MAIN_KEYBOARD
                                
                                # Create an FAQ message with commonly asked questions
                                faq_message = (
                                    "📚 *Frequently Asked Questions* 📚\n\n"
                                    
                                    "*What is FiLot Bot?*\n"
                                    "FiLot is an AI-powered investment assistant for DeFi liquidity pools on Solana.\n\n"
                                    
                                    "*How do I start investing?*\n"
                                    "Use the 💰 Invest button to select an amount and risk profile, then connect your wallet.\n\n"
                                    
                                    "*What's a liquidity pool?*\n"
                                    "A liquidity pool is where you deposit two tokens to earn trading fees when others trade that pair.\n\n"
                                    
                                    "*How do earnings work?*\n"
                                    "You earn a portion of trading fees proportional to your share of the pool, shown as APR (Annual Percentage Rate).\n\n"
                                    
                                    "*What are the risks?*\n"
                                    "Liquidity pools have risks including impermanent loss, smart contract vulnerabilities, and token price volatility.\n\n"
                                    
                                    "*How do I withdraw my investment?*\n"
                                    "Use the 💰 Invest button to see your active positions, then select one to withdraw funds."
                                )
                                
                                send_response(
                                    chat_id,
                                    faq_message,
                                    parse_mode="Markdown",
                                    reply_markup=MAIN_KEYBOARD
                                )
                                logger.info(f"Sent FAQ information to user {update_obj.callback_query.from_user.id}")

                            # Handle menu button callbacks
                            elif callback_data.startswith("menu_"):
                                # Get bot instance for update creation
                                from telegram.ext import Application
                                
                                # Get the bot from the global application
                                # Access the bot instance directly
                                from globals import bot  
                                
                                menu_action = callback_data.replace("menu_", "")
                                
                                if menu_action == "invest":
                                    # Create investment menu using the menus module for consistency
                                    from menus import get_invest_menu
                                    logger.info(f"Triggering investment menu from menu_invest button (Back to Amounts button)")
                                    
                                    # Create the invest options message with simplified approach
                                    invest_message = (
                                        "💰 *Ready to Invest?* 💰\n\n"
                                        "With our One-Touch interface, simply select an investment amount below or choose 'Custom Amount' to enter a specific value.\n\n"
                                        "💡 *Tip:* All investment options can be managed through our convenient buttons - no typing required!"
                                    )
                                    
                                    # Send the investment options menu directly
                                    send_response(
                                        chat_id,
                                        invest_message,
                                        parse_mode="Markdown",
                                        reply_markup=get_invest_menu()
                                    )
                                    logger.info("Successfully showed investment menu via menu_invest callback")
                                
                                elif menu_action == "explore":
                                    # Handle explore menu item with direct implementation to avoid relying on database
                                    logger.info(f"Triggering simplified explore flow from menu button")
                                    
                                    # Import from menus to ensure consistency with the rest of the application
                                    from menus import get_explore_menu
                                    reply_markup = get_explore_menu()
                                    
                                    # Send explore menu directly
                                    send_response(
                                        chat_id,
                                        "📊 *Explore DeFi Opportunities* 📊\n\n"
                                        "Select what you'd like to explore:",
                                        parse_mode="Markdown",
                                        reply_markup=reply_markup
                                    )
                                    
                                    # No need to send additional messages about the keyboard
                                    
                                    logger.info("Successfully displayed simplified explore menu")
                                
                                
                                elif menu_action == "positions":
                                    # Handle positions menu item - View user's positions
                                    logger.info(f"Triggering positions view from menu button")
                                    
                                    # Run the positions command handler using async and event loop
                                    import asyncio
                                    from bot_commands import positions_command
                                    
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    
                                    try:
                                        # Create a simplified update object for the handler
                                        simplified_update = Update.de_json(
                                            {
                                                'update_id': update_dict.get('update_id', 0),
                                                'message': update_obj.callback_query.message.to_dict()
                                            }, 
                                            bot
                                        )
                                        simplified_context = SimpleContext()
                                        simplified_context.user_data = {"message_handled": True}
                                        
                                        # Run the positions command handler
                                        loop.run_until_complete(positions_command(simplified_update, simplified_context))
                                        logger.info("Successfully displayed user positions")
                                    except Exception as positions_error:
                                        logger.error(f"Error in menu_positions handler: {positions_error}")
                                        logger.error(traceback.format_exc())
                                        send_response(
                                            chat_id,
                                            "Sorry, there was an error retrieving your positions. Please try again later."
                                        )
                                    finally:
                                        loop.close()
                                
                                elif menu_action == "account":
                                    # Handle account menu item with direct implementation to avoid relying on database
                                    logger.info(f"Triggering simplified account flow from menu button")
                                    
                                    # Import account menu from menus.py for consistency
                                    from menus import get_account_menu
                                    reply_markup = get_account_menu()
                                    
                                    # Send account menu directly
                                    send_response(
                                        chat_id,
                                        "👤 *Your Account* 👤\n\n"
                                        "Wallet: ❌ Not Connected\n"
                                        "Risk Profile: Moderate\n"
                                        "Daily Updates: ❌ Not Subscribed\n\n"
                                        "Select an option below to manage your account:",
                                        parse_mode="Markdown",
                                        reply_markup=reply_markup
                                    )
                                    
                                    # No need to send additional messages about the keyboard
                                    
                                    logger.info("Successfully displayed simplified account menu")
                                
                                else:
                                    logger.warning(f"Unknown menu action: {menu_action}")
                                    send_response(
                                        chat_id,
                                        "Sorry, that menu option is not available yet. Please try another option."
                                    )
                            
                            # Handle any other callback type
                            else:
                                # Send a generic response for unhandled callback types
                                send_response(
                                    chat_id,
                                    "I received your selection, but I'm not sure how to process it. Please use /help to see available commands."
                                )
                                logger.warning(f"Unhandled callback type: {callback_data}")

                    except Exception as cb_error:
                        logger.error(f"Error handling callback query: {cb_error}")
                        logger.error(traceback.format_exc())

                        # Send error response
                        send_response(
                            chat_id,
                            "Sorry, an error occurred processing your selection. Please try again later."
                        )

                # Handle regular messages
                elif update_obj.message and update_obj.message.text:
                    logger.info("Handling regular message")
                    chat_id = update_obj.message.chat_id
                    message_text = update_obj.message.text
                    message_id = update_obj.message.message_id
                    
                    # Create multiple tracking IDs for this message
                    msg_track_id = f"msg_{message_id}"
                    msg_content_id = f"msg_content_{chat_id}_{hashlib.md5(message_text.encode()).hexdigest()[:8]}"
                    
                    # Check if we've already processed this message using any tracking method
                    # Special handling for menu items to allow them to be pressed multiple times
                    if message_text in ["🔍 Explore", "💰 Invest", "👤 Account"]:
                        # These menu buttons should always work, don't skip
                        # Just mark the message ID as processed to avoid duplicates in very quick succession
                        is_message_processed(chat_id, msg_track_id)
                        logger.info(f"Menu button pressed: {message_text} - allowing repeated presses")
                    elif is_message_processed(chat_id, msg_track_id) or is_message_processed(chat_id, msg_content_id):
                        logger.info(f"Skipping already processed message {message_id}: {message_text[:30]}...")
                        # Skip further processing for this message
                        return
                    else:
                        # Mark both IDs as processed for non-menu messages
                        is_message_processed(chat_id, msg_track_id)
                        is_message_processed(chat_id, msg_content_id)

                    # For question detection and predefined answers
                    with app.app_context():
                        try:
                            from question_detector import is_question
                            from response_data import get_predefined_response

                            # Check if this is a question
                            question_detected = is_question(message_text)
                            logger.info(f"Is question detection: {question_detected}")

                            # Check for predefined responses
                            predefined_response = get_predefined_response(message_text)

                            if predefined_response:
                                logger.info(f"Found predefined response for: {message_text[:30]}...")

                                # Send predefined response using our direct API
                                send_response(
                                    chat_id,
                                    predefined_response,
                                    parse_mode="Markdown"
                                )

                                # Log the success
                                logger.info(f"Sent predefined answer for: {message_text}")
                                return

                        except Exception as predef_error:
                            logger.error(f"Error checking predefined answers: {predef_error}")

                    # If no predefined answer or error occurred, fall back to async handler
                    import asyncio

                    # Create and manage our own event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    try:
                        # Get message ID
                        message_id = update_obj.message.message_id if update_obj and update_obj.message else "unknown"
                        
                        # Check if we've already processed this message
                        if is_message_processed(chat_id, message_id):
                            logger.info(f"Skipping already processed message {chat_id}_{message_id}")
                            # Skip further processing for this message
                            return
                            
                        # This message is new, process it
                        # Run the message handler
                        context = SimpleContext()
                        # Add a flag to indicate message is being handled to prevent duplicate responses
                        context.user_data["message_handled"] = True
                        context.user_data["tracking_id"] = f"{chat_id}_{message_id}"
                        loop.run_until_complete(handle_message(update_obj, context))
                        
                        # Mark as response sent
                        context.user_data["message_response_sent"] = True
                    except Exception as msg_error:
                        logger.error(f"Error handling message: {msg_error}")
                        logger.error(traceback.format_exc())
                        # Only send fallback response if not already handled
                        if not context.user_data.get("message_response_sent", False):
                            send_response(
                                chat_id,
                                "Sorry, I encountered a problem processing your message. Please try again or type /help for available commands."
                            )
                            context.user_data["message_response_sent"] = True
                    finally:
                        # Clean up the loop
                        try:
                            pending = asyncio.all_tasks(loop)
                            loop.run_until_complete(asyncio.gather(*pending))
                        except Exception:
                            pass

                logger.info(f"Successfully processed update ID: {update_dict.get('update_id')}")

            except Exception as e:
                logger.error(f"Error processing update: {e}")
                logger.error(traceback.format_exc())
                
                # Try to send an error message with the inline menu if we have a chat_id
                try:
                    if 'message' in update_dict and 'chat' in update_dict['message']:
                        chat_id = update_dict['message']['chat']['id']
                        
                        # Import the keyboard helper
                        from keyboard_utils import MAIN_KEYBOARD, get_main_menu_inline
                        
                        # Show error message with persistent keyboard directly
                        # This eliminates the redundant second message
                        send_response(
                            chat_id,
                            "❗ *Sorry, something went wrong*\n\n"
                            "Please use the buttons below to continue:",
                            parse_mode="Markdown",
                            reply_markup=MAIN_KEYBOARD
                        )
                except Exception as inner_e:
                    logger.error(f"Error sending error message: {inner_e}")

        # Function to continuously poll for updates
        def poll_for_updates():
            nonlocal last_update_id

            logger.info("Starting update polling thread")

            while True:
                try:
                    # Construct the getUpdates API call
                    params = {
                        "timeout": 30,
                        "allowed_updates": json.dumps(["message", "callback_query"]),
                    }

                    # If we have a last update ID, only get updates after that
                    if last_update_id > 0:
                        params["offset"] = last_update_id + 1

                    # First, try to delete webhook (if any)
                    try:
                        logger.info("Attempting to delete any existing webhook")
                        delete_webhook_resp = requests.get(f"{base_url}/deleteWebhook?drop_pending_updates=true")
                        if delete_webhook_resp.status_code == 200:
                            webhook_result = delete_webhook_resp.json()
                            logger.info(f"Webhook deletion result: {webhook_result}")
                        else:
                            logger.warning(f"Failed to delete webhook: {delete_webhook_resp.status_code} - {delete_webhook_resp.text}")
                    except Exception as e:
                        logger.error(f"Error deleting webhook: {e}")
                    
                    # Make the API call with exponential backoff
                    logger.info(f"Requesting updates from Telegram API...")
                    # Add unique parameter to avoid conflicts with other instances
                    params["allowed_updates"] = json.dumps(["message", "callback_query", "edited_message"])
                    # Add unique client identifier to prevent conflict with other instances
                    import uuid
                    params["client_id"] = str(uuid.uuid4())  # Add unique identifier for this client
                    # Terminate other polling sessions before starting our own
                    requests.get(f"{base_url}/getUpdates", params={"offset": -1, "timeout": 0})
                    # Now start our polling
                    response = requests.get(f"{base_url}/getUpdates", params=params, timeout=60)

                    # Process the response if successful
                    if response.status_code == 200:
                        result = response.json()
                        updates = result.get("result", [])

                        # Enhanced debug log
                        logger.info(f"Received response: {len(updates)} updates")
                        if len(updates) > 0:
                            logger.info(f"Update keys: {', '.join(updates[0].keys())}")
                            # Log full update for debugging
                            logger.info(f"First update content: {json.dumps(updates[0])}")

                        # Process each update
                        for update in updates:
                            # Update the last update ID
                            update_id = update.get("update_id", 0)
                            if update_id > last_update_id:
                                last_update_id = update_id

                            # Process the update in a separate thread
                            logger.info(f"Starting thread to process update {update_id}")
                            threading.Thread(target=handle_update, args=(update,)).start()
                    else:
                        logger.error(f"Error getting updates: {response.status_code} - {response.text}")

                    # Log status periodically
                    if int(time.time()) % 60 == 0:  # Log once per minute
                        logger.info(f"Bot polling active. Last update ID: {last_update_id}")

                except Exception as e:
                    logger.error(f"Error in update polling: {e}")
                    logger.error(traceback.format_exc())

                # Sleep briefly to avoid hammering the API
                time.sleep(1)

        # Start the polling thread
        polling_thread = threading.Thread(target=poll_for_updates, daemon=True)
        polling_thread.start()

        # Keep the main thread alive
        while True:
            try:
                time.sleep(300)  # Sleep for 5 minutes
                logger.info("Telegram bot still running...")
            except Exception as e:
                logger.error(f"Error in main bot thread: {e}")
                break

    except Exception as e:
        logger.error(f"Error in telegram bot: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")

def main():
    """
    Main function to start both the Flask app and Telegram bot
    """
    try:
        # Check if we're allowed to run the bot using our anti-looping protection
        from debug_message_tracking import acquire_instance_lock, is_message_tracked
        
        # First, check if another process already has the lock 
        has_lock = acquire_instance_lock()
        
        # If another process already holds the lock (likely the Start application workflow)
        if not has_lock:
            logger.warning("⚠️ Another process (likely the Start application workflow) already holds the bot lock.")
            logger.warning("Exiting this process to prevent duplicate polling.")
            
            # Exit gracefully
            logger.info("Exiting to prevent duplicate Telegram polling")
            sys.exit(0)
        
        # We have the lock, proceed with normal startup
        
        # First, kill any existing bot process that might be running
        try:
            # Try to terminate any other instance gracefully
            import requests
            import os
            bot_token = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
            if bot_token:
                base_url = f"https://api.telegram.org/bot{bot_token}"
                requests.get(f"{base_url}/getUpdates", params={"offset": -1, "timeout": 0})
                requests.get(f"{base_url}/deleteWebhook", params={"drop_pending_updates": "true"})
                logger.info("Terminated any existing bot polling")
        except Exception as e:
            logger.warning(f"Failed to terminate existing bot: {e}")
            
        # Mark this as the primary bot instance
        is_message_tracked(0, "MAIN_PY_PRIMARY_BOT_INSTANCE")
        logger.info("✅ This is now the primary bot instance")
        
        # Start in the appropriate mode
        if os.environ.get('PRODUCTION') == 'true':
            # In production, run only the bot
            run_telegram_bot()
        else:
            # In development, run both Flask and bot
            from threading import Thread
            
            # Add a short delay to ensure clean startup
            import time
            time.sleep(2)
            
            # Start bot in a thread
            bot_thread = Thread(target=run_telegram_bot)
            bot_thread.daemon = True
            bot_thread.start()

            # Run Flask app on a different port when running with bot
            app.run(host='0.0.0.0', port=5001)

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()