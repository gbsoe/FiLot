"""
Improved button handler for the FiLot Telegram bot.

This module provides enhanced handling for main navigation buttons (Invest, Explore, Account),
ensuring reliable navigation and preventing common button-related issues.
"""

import logging
from typing import Dict, Any, Optional, Callable, Awaitable, Union

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import fix_navigation
from menus import get_main_menu, get_invest_menu, get_explore_menu, get_account_menu

# Configure logging
logger = logging.getLogger(__name__)

# Store reference to handlers for dynamic dispatch
MENU_HANDLERS = {}

async def register_menu_handler(menu_name: str, handler_func: Callable):
    """
    Register a handler function for a specific menu.
    
    Args:
        menu_name: Name of the menu
        handler_func: Handler function to call
    """
    MENU_HANDLERS[menu_name] = handler_func
    logger.info(f"Registered menu handler for {menu_name}")

async def handle_main_button(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE,
    button_name: str
) -> bool:
    """
    Handle main navigation button presses with enhanced error recovery.
    
    Args:
        update: Telegram update
        context: Callback context
        button_name: Name of the button pressed (invest, explore, account)
        
    Returns:
        True if handled successfully, False otherwise
    """
    # Extract chat ID for tracking
    chat_id = update.effective_chat.id if update.effective_chat else 0
    user_id = update.effective_user.id if update.effective_user else 0
    
    if not chat_id or not user_id:
        logger.error("Missing chat_id or user_id in handle_main_button")
        return False
    
    # Check if this is a duplicate (with shorter window for main navigation)
    callback_data = f"menu_{button_name}"
    if fix_navigation.is_duplicate(chat_id, callback_data, window=0.3):
        logger.info(f"Ignoring duplicate main button press: {button_name}")
        if update.callback_query:
            await update.callback_query.answer("Already on this menu")
        return True
    
    # Record this navigation action
    fix_navigation.record_navigation(chat_id, callback_data)
    
    # Check if we should force a refresh based on navigation patterns
    force_refresh = fix_navigation.should_force_refresh(chat_id, callback_data)
    
    # Get the appropriate menu keyboard
    menu_keyboard = None
    menu_text = "Welcome to FiLot! How can I help you today?"
    
    try:
        if button_name == "invest":
            menu_keyboard = get_invest_menu()
            menu_text = "💰 *Investment Menu*\n\nChoose an investment option:"
        elif button_name == "explore":
            menu_keyboard = get_explore_menu()
            menu_text = "🔍 *Explore Menu*\n\nDiscover new investment opportunities:"
        elif button_name == "account":
            menu_keyboard = get_account_menu()
            menu_text = "👤 *Account Menu*\n\nManage your account and settings:"
        elif button_name == "main":
            menu_keyboard = get_main_menu()
            menu_text = "Welcome back to the main menu! How can I help you today?"
        else:
            logger.warning(f"Unknown button name: {button_name}")
            menu_keyboard = get_main_menu()
    except Exception as e:
        logger.error(f"Error creating menu keyboard for {button_name}: {e}")
        # Fallback to main menu
        try:
            menu_keyboard = get_main_menu()
        except Exception as e2:
            logger.error(f"Critical error creating main menu fallback: {e2}")
            return False
    
    # Handle the button press based on the update type
    if update.callback_query:
        # This is a callback query from an inline button
        query = update.callback_query
        
        # Check if we need to edit or send a new message
        try:
            # Always acknowledge the callback
            await query.answer()
            
            if force_refresh:
                # Send a new message instead of editing
                await query.message.reply_markdown(
                    menu_text,
                    reply_markup=menu_keyboard
                )
            else:
                # Edit the existing message
                await query.edit_message_text(
                    menu_text,
                    reply_markup=menu_keyboard,
                    parse_mode="Markdown"
                )
        except Exception as e:
            logger.error(f"Error handling button via callback: {e}")
            # Try recovery by sending a new message
            try:
                await query.message.reply_markdown(
                    f"{menu_text}\n\n(Refreshed due to an error)",
                    reply_markup=menu_keyboard
                )
            except Exception as e2:
                logger.error(f"Failed recovery attempt: {e2}")
                return False
    else:
        # This is a direct command
        try:
            await update.message.reply_markdown(
                menu_text,
                reply_markup=menu_keyboard
            )
        except Exception as e:
            logger.error(f"Error handling button via command: {e}")
            return False
    
    # Call specific menu handler if registered
    if button_name in MENU_HANDLERS:
        try:
            await MENU_HANDLERS[button_name](update, context)
        except Exception as e:
            logger.error(f"Error in menu handler for {button_name}: {e}")
    
    return True

async def handle_menu_invest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handler for /invest command and menu_invest button."""
    return await handle_main_button(update, context, "invest")

async def handle_menu_explore(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handler for /explore command and menu_explore button."""
    return await handle_main_button(update, context, "explore")

async def handle_menu_account(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handler for /account command and menu_account button."""
    return await handle_main_button(update, context, "account")

async def handle_back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Handler for back_to_main button."""
    return await handle_main_button(update, context, "main")