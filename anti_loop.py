#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Anti-loop protection mechanism for the Telegram bot.
This module provides global locking to completely prevent message loops.
"""

import time
import hashlib
import threading
import logging
from typing import Dict, Set, Tuple, Optional, Any
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("anti_loop")

# Global lock to ensure thread safety
_lock = threading.RLock()

# Global protection mechanism
_processed_messages: Set[str] = set()
_recent_messages: Dict[str, float] = {}
_user_locks: Dict[int, bool] = defaultdict(bool)
_chat_locks: Dict[int, Dict[str, float]] = defaultdict(dict)
_callback_locks: Dict[str, float] = {}

# Memory management
MAX_TRACKING_SIZE = 1000
MAX_LOCK_DURATION = 2.0  # seconds - reduced from 5.0 to be less aggressive for buttons
BUTTON_COOLDOWN = 0.5  # seconds - very short cooldown for buttons specifically

def is_message_looping(chat_id: int, message_text: Optional[str] = None, 
                       callback_id: Optional[str] = None) -> bool:
    """
    Check if a message or callback is potentially looping.
    
    Args:
        chat_id: The chat ID
        message_text: Optional text of the message
        callback_id: Optional callback query ID
        
    Returns:
        True if the message appears to be looping, False otherwise
    """
    with _lock:
        now = time.time()
        
        # 1. Check if this chat is globally locked
        if _user_locks.get(chat_id, False):
            logger.warning(f"Chat {chat_id} is globally locked against loops")
            return True
            
        # 2. Check message content if provided
        if message_text:
            # Create a hash of the message content
            msg_hash = hashlib.md5(message_text.encode()).hexdigest()[:12]
            content_key = f"{chat_id}_{msg_hash}"
            
            # Check if this is a button-related message (callbacks or menu items)
            is_button = False
            if message_text and isinstance(message_text, str):
                # Check if this is a button callback
                button_patterns = ['menu_', 'account_', 'explore_', 'profile_', 'wallet_', 'amount_', 'simulate_']
                is_button = any(message_text.startswith(pattern) for pattern in button_patterns)
            
            # Check if we've seen this message content recently
            if content_key in _recent_messages:
                last_time = _recent_messages[content_key]
                
                # Use a shorter cooldown window for buttons
                if is_button:
                    cooldown_window = BUTTON_COOLDOWN
                else:
                    cooldown_window = 5.0  # Reduced from 10.0 seconds for regular messages
                
                if now - last_time < cooldown_window:
                    if is_button:
                        logger.info(f"Button pressed again within {cooldown_window}s: {message_text[:30]}...")
                    else:
                        logger.warning(f"Similar message detected within {cooldown_window}s window: {message_text[:30]}...")
                    
                    # For buttons, don't lock the whole chat, just reject this specific callback
                    if not is_button:
                        # Only lock chat for non-button messages
                        _user_locks[chat_id] = True
                        # Schedule unlock after MAX_LOCK_DURATION
                        threading.Timer(MAX_LOCK_DURATION, _release_lock, args=[chat_id]).start()
                    
                    return not is_button  # Return False for buttons to allow them through, True for regular messages
            
            # Update the recent messages
            _recent_messages[content_key] = now
            
            # Clean up old entries
            _cleanup_tracking()
        
        # 3. Check callback if provided
        if callback_id:
            # Whitelist for navigation buttons that should bypass anti-loop protection
            # These buttons are exempt from loop detection because they're used for core navigation
            # Comprehensive list of all main navigation buttons
            navigation_buttons = [
                # Main menu navigation
                'menu_explore', 'menu_invest', 'menu_account', 'menu_main', 'menu_faq',
                
                # Explore section buttons
                'back_to_explore', 'explore_simulate', 'explore_pools', 'explore_info', 'explore_faq',
                
                # Account section buttons - specific buttons
                'walletconnect', 'subscribe', 'unsubscribe', 'status', 'help',
                
                # Profile settings
                'profile_high-risk', 'profile_stable', 'profile_moderate',
                
                # Investment buttons
                'confirm_invest', 'invest_now', 'invest_back_to_profile', 'start_invest',
                
                # Simulation buttons
                'simulate_100', 'simulate_500', 'simulate_1000', 'simulate_5000', 'simulate_custom'
            ]
            
            # Extended comprehensive prefixes for all button patterns
            button_prefixes = [
                # Main sections
                'menu_', 'account_', 'explore_', 'profile_', 
                
                # Investment related
                'wallet_', 'invest_', 'amount_', 'simulate_', 'confirm_invest_',
                
                # Pagination and selection
                'page_', 'select_', 'pool_', 'token_'
            ]
            
            # Get callback data if available (for additional checks)
            callback_data = None
            if message_text and isinstance(message_text, str):
                callback_data = message_text
            
            # Skip looping check for navigation buttons
            if callback_data and (
                any(callback_data == nav_btn for nav_btn in navigation_buttons) or
                any(callback_data.startswith(prefix) for prefix in button_prefixes)
            ):
                logger.info(f"Navigation button pressed: {callback_data} - bypassing anti-loop protection")
                return False
            
            callback_key = f"{chat_id}_{callback_id}"
            
            # Check if we've seen this callback recently
            if callback_key in _processed_messages:
                logger.warning(f"Duplicate callback detected: {callback_id}")
                return True
                
            # Add to processed messages
            _processed_messages.add(callback_key)
            
            # Clean up old entries
            _cleanup_tracking()
        
        return False

def lock_message_processing(chat_id: int, duration: float = MAX_LOCK_DURATION) -> None:
    """
    Lock message processing for a specific chat for a duration.
    
    Args:
        chat_id: The chat ID to lock
        duration: Lock duration in seconds
    """
    with _lock:
        logger.info(f"Locking chat {chat_id} for {duration} seconds")
        _user_locks[chat_id] = True
        
        # Schedule unlock
        threading.Timer(duration, _release_lock, args=[chat_id]).start()

def _release_lock(chat_id: int) -> None:
    """
    Release the lock for a chat ID.
    
    Args:
        chat_id: The chat ID to unlock
    """
    with _lock:
        logger.info(f"Releasing lock for chat {chat_id}")
        _user_locks[chat_id] = False

def _cleanup_tracking() -> None:
    """Clean up tracking data to prevent memory leaks."""
    global _processed_messages, _recent_messages
    
    with _lock:
        # Limit the size of processed_messages
        if len(_processed_messages) > MAX_TRACKING_SIZE:
            _processed_messages = set(list(_processed_messages)[-MAX_TRACKING_SIZE:])
            
        # Remove old recent messages
        now = time.time()
        old_keys = [k for k, v in _recent_messages.items() if now - v > 30.0]
        for k in old_keys:
            _recent_messages.pop(k, None)

def reset_all_locks() -> None:
    """Reset all locks and tracking data."""
    with _lock:
        _user_locks.clear()
        _chat_locks.clear()
        _callback_locks.clear()
        _processed_messages.clear()
        _recent_messages.clear()
        logger.info("All anti-loop locks and tracking data have been reset")

# ------------------ MONKEY PATCHING FUNCTIONS ------------------
# These functions will be used to monkey-patch the bot.py and main.py functions

def safe_send_message(original_send_func):
    """
    Decorator to make any message sending function safe against loops.
    
    Args:
        original_send_func: The original function to wrap
        
    Returns:
        Wrapped function that checks for loops before sending
    """
    def wrapped_send(chat_id, text, *args, **kwargs):
        # Check if this chat is locked or the message is looping
        if is_message_looping(chat_id, text):
            logger.warning(f"Prevented potential message loop to chat {chat_id}: {text[:30]}...")
            return None
            
        # If not looping, proceed with original function
        return original_send_func(chat_id, text, *args, **kwargs)
        
    return wrapped_send

def safe_handle_callback(original_callback_func):
    """
    Decorator to make callback handling safe against loops.
    
    Args:
        original_callback_func: The original function to wrap
        
    Returns:
        Wrapped function that checks for loops before handling
    """
    def wrapped_callback(update, context, *args, **kwargs):
        chat_id = update.callback_query.message.chat_id
        callback_id = update.callback_query.id
        callback_data = update.callback_query.data
        
        # Check if this callback is locked or looping
        if is_message_looping(chat_id, callback_data, callback_id):
            logger.warning(f"Prevented potential callback loop: {callback_data}")
            return None
            
        # If not looping, proceed with original function
        return original_callback_func(update, context, *args, **kwargs)
        
    return wrapped_callback

def safe_handle_message(original_message_func):
    """
    Decorator to make message handling safe against loops.
    
    Args:
        original_message_func: The original function to wrap
        
    Returns:
        Wrapped function that checks for loops before handling
    """
    def wrapped_message(update, context, *args, **kwargs):
        chat_id = update.message.chat_id
        message_text = update.message.text
        
        # Check if this message is locked or looping
        if is_message_looping(chat_id, message_text):
            logger.warning(f"Prevented potential message loop: {message_text[:30]}...")
            return None
            
        # If not looping, proceed with original function
        return original_message_func(update, context, *args, **kwargs)
        
    return wrapped_message

# Function to apply all monkey patches
def apply_anti_loop_patches():
    """Apply anti-loop protection to the bot by monkey patching key functions."""
    try:
        # Patch bot.py functions
        import bot
        
        # Original functions to save
        original_handle_message = bot.handle_message
        original_handle_callback = bot.handle_callback_query
        
        # Apply patches
        bot.handle_message = safe_handle_message(original_handle_message)
        bot.handle_callback_query = safe_handle_callback(original_handle_callback)
        
        logger.info("Successfully applied anti-loop patches to bot.py")
        
        # For main.py, we can't directly patch send_response because it's defined inside another function
        # Instead, we'll provide a tool for main.py to check messages using our protection system
        logger.info("Ready for main.py to use anti-loop protection via direct function calls")
            
        return True
    except Exception as e:
        logger.error(f"Error applying anti-loop patches: {e}")
        return False

# Apply patches automatically when imported
success = apply_anti_loop_patches()
if success:
    logger.info("Anti-loop protection system active")
else:
    logger.error("Failed to activate anti-loop protection system")

# Make key functions available at module level
is_looping = is_message_looping
lock_chat = lock_message_processing
unlock_chat = _release_lock
reset = reset_all_locks