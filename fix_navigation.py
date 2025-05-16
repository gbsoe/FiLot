"""
Improved navigation system for FiLot Telegram bot.

This module enhances the navigation system to ensure smooth transitions
between main menu items (Invest, Explore, Account) and prevents duplicate
responses when buttons are pressed multiple times.
"""

import logging
import time
from typing import Dict, Any, List, Optional, Set

# Configure logging
logger = logging.getLogger(__name__)

# Navigation history
# Format: {chat_id: [{"callback_data": data, "timestamp": time, "context": context}]}
NAVIGATION_HISTORY = {}

# Maximum number of navigation actions to keep in history per chat
MAX_HISTORY_SIZE = 20

# Set of main navigation buttons
MAIN_BUTTONS = {
    "menu_invest",
    "menu_explore", 
    "menu_account",
    "back_to_main"
}

# Button sequence patterns to detect
BUTTON_SEQUENCES = {
    "menu_invest,menu_explore": "invest_to_explore",
    "menu_explore,menu_invest": "explore_to_invest",
    "menu_invest,menu_account": "invest_to_account",
    "menu_account,menu_invest": "account_to_invest",
    "menu_explore,menu_account": "explore_to_account",
    "menu_account,menu_explore": "account_to_explore"
}

def record_navigation(chat_id: int, callback_data: str, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Record a navigation action in the history.
    
    Args:
        chat_id: Chat ID
        callback_data: Callback data
        context: Optional context information
    """
    if chat_id not in NAVIGATION_HISTORY:
        NAVIGATION_HISTORY[chat_id] = []
        
    # Add to history
    NAVIGATION_HISTORY[chat_id].append({
        "callback_data": callback_data,
        "timestamp": time.time(),
        "context": context or {}
    })
    
    # Limit history size
    if len(NAVIGATION_HISTORY[chat_id]) > MAX_HISTORY_SIZE:
        NAVIGATION_HISTORY[chat_id] = NAVIGATION_HISTORY[chat_id][-MAX_HISTORY_SIZE:]
        
    logger.debug(f"Recorded navigation for chat {chat_id}: {callback_data}")

def is_duplicate(chat_id: int, callback_data: str, window: float = 0.5) -> bool:
    """
    Check if this navigation action is a duplicate within the time window.
    Using a shorter window (0.5s) to allow legitimate sequential navigation.
    
    Args:
        chat_id: Chat ID
        callback_data: Callback data
        window: Time window in seconds to consider for duplicates
        
    Returns:
        True if duplicate, False otherwise
    """
    if chat_id not in NAVIGATION_HISTORY:
        return False
        
    recent_actions = NAVIGATION_HISTORY[chat_id]
    if not recent_actions:
        return False
        
    current_time = time.time()
    
    # For main navigation buttons (Invest, Explore, Account), use special handling
    if callback_data in MAIN_BUTTONS:
        # For main navigation, check if we're already on this page
        # and the last action was less than 2 seconds ago
        last_action = recent_actions[-1]
        if last_action["callback_data"] == callback_data:
            time_diff = current_time - last_action["timestamp"]
            if time_diff < 2.0:  # Longer window for main navigation
                logger.info(f"Detected duplicate main navigation: {callback_data} within {time_diff:.2f}s")
                return True
        return False  # Always allow main navigation otherwise
        
    # Check for exact duplicates within the window
    for action in recent_actions:
        if action["callback_data"] == callback_data:
            time_diff = current_time - action["timestamp"]
            if time_diff < window:
                logger.info(f"Detected duplicate navigation: {callback_data} within {time_diff:.2f}s")
                return True
    
    return False

def detect_pattern(chat_id: int, depth: int = 3) -> Optional[str]:
    """
    Detect navigation patterns to handle special cases.
    
    Args:
        chat_id: Chat ID
        depth: How many recent actions to consider
        
    Returns:
        Detected pattern name or None
    """
    if chat_id not in NAVIGATION_HISTORY:
        return None
        
    actions = NAVIGATION_HISTORY[chat_id]
    if len(actions) < 2:
        return None
        
    # Get recent actions limited by depth
    recent = actions[-depth:]
    
    # Extract just the callback data
    recent_callbacks = [action["callback_data"] for action in recent]
    
    # Check for button sequences
    for i in range(len(recent_callbacks) - 1):
        pair = f"{recent_callbacks[i]},{recent_callbacks[i+1]}"
        if pair in BUTTON_SEQUENCES:
            pattern = BUTTON_SEQUENCES[pair]
            logger.info(f"Detected navigation pattern: {pattern}")
            return pattern
    
    # Check for back-and-forth pattern (ping-pong)
    if len(recent_callbacks) >= 3:
        if recent_callbacks[-3] == recent_callbacks[-1] and recent_callbacks[-2] != recent_callbacks[-1]:
            logger.info("Detected ping-pong navigation pattern")
            return "ping_pong"
    
    return None

def get_current_menu(chat_id: int) -> Optional[str]:
    """
    Get the current menu for a chat based on navigation history.
    
    Args:
        chat_id: Chat ID
        
    Returns:
        Current menu or None if not available
    """
    if chat_id not in NAVIGATION_HISTORY or not NAVIGATION_HISTORY[chat_id]:
        return None
        
    # Find the most recent main menu navigation
    for action in reversed(NAVIGATION_HISTORY[chat_id]):
        callback = action["callback_data"]
        if callback.startswith("menu_"):
            return callback[5:]  # Remove "menu_" prefix
            
    return None

def should_force_refresh(chat_id: int, callback_data: str) -> bool:
    """
    Determine if we should force a menu refresh based on navigation patterns.
    
    Args:
        chat_id: Chat ID
        callback_data: Current callback data
        
    Returns:
        True if we should force refresh, False otherwise
    """
    pattern = detect_pattern(chat_id)
    
    # Force refresh on ping-pong pattern
    if pattern == "ping_pong":
        return True
        
    # Force refresh when user explicitly returns to the same menu
    current_menu = get_current_menu(chat_id)
    if current_menu and callback_data == f"menu_{current_menu}":
        return True
        
    return False

def clean_navigation_history() -> None:
    """Clean up old navigation history to prevent memory leaks."""
    # Get current time
    current_time = time.time()
    
    # Remove any history older than 1 hour
    cutoff_time = current_time - 3600
    
    chats_to_remove = []
    
    for chat_id, actions in NAVIGATION_HISTORY.items():
        # Check if all actions are old
        if actions and actions[-1]["timestamp"] < cutoff_time:
            chats_to_remove.append(chat_id)
            
    # Remove old chat histories
    for chat_id in chats_to_remove:
        del NAVIGATION_HISTORY[chat_id]
        
    logger.debug(f"Cleaned up navigation history for {len(chats_to_remove)} chats")

def reset_chat_navigation(chat_id: int) -> None:
    """
    Reset navigation history for a specific chat.
    
    Args:
        chat_id: Chat ID to reset
    """
    if chat_id in NAVIGATION_HISTORY:
        del NAVIGATION_HISTORY[chat_id]
        logger.info(f"Reset navigation history for chat {chat_id}")