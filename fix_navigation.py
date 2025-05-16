"""
Improved navigation system for FiLot Telegram bot.

This module provides enhanced navigation tracking and duplicate detection
to ensure smooth button navigation, especially for main menu buttons.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Set

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Global navigation tracking
user_navigation = {}
MAX_NAVIGATION_HISTORY = 50
DUPLICATE_WINDOW = 0.5  # 500ms window for duplicate detection by default

def record_navigation(chat_id: int, action: str) -> None:
    """
    Record a navigation action for a chat.
    
    Args:
        chat_id: The chat ID
        action: The action/button that was pressed
    """
    global user_navigation
    
    # Initialize if needed
    if chat_id not in user_navigation:
        user_navigation[chat_id] = []
        
    # Record this action
    user_navigation[chat_id].append({
        "action": action,
        "timestamp": time.time()
    })
    
    # Limit history size
    if len(user_navigation[chat_id]) > MAX_NAVIGATION_HISTORY:
        user_navigation[chat_id] = user_navigation[chat_id][-MAX_NAVIGATION_HISTORY:]
        
    logger.debug(f"Recorded navigation for {chat_id}: {action}")

def is_duplicate(chat_id: int, action: str, window: float = DUPLICATE_WINDOW) -> bool:
    """
    Check if a navigation action is a duplicate (same action within time window).
    
    Args:
        chat_id: The chat ID
        action: The action/button to check
        window: Time window in seconds to consider for duplicates
        
    Returns:
        True if the action is a duplicate, False otherwise
    """
    global user_navigation
    
    # No history for this chat
    if chat_id not in user_navigation:
        return False
        
    # Check recent actions
    current_time = time.time()
    history = user_navigation[chat_id]
    
    # Check for duplicate actions within the time window
    for entry in reversed(history):
        # Skip if this is not the same action
        if entry["action"] != action:
            continue
            
        # Check if this action happened within the time window
        time_diff = current_time - entry["timestamp"]
        if time_diff < window:
            logger.info(f"Duplicate action detected: {action} (within {time_diff:.2f}s)")
            return True
            
    return False

def detect_pattern(chat_id: int) -> Optional[str]:
    """
    Detect special navigation patterns that might need special handling.
    
    Args:
        chat_id: The chat ID
        
    Returns:
        Pattern name if detected, None otherwise
    """
    global user_navigation
    
    # No history for this chat
    if chat_id not in user_navigation or len(user_navigation[chat_id]) < 3:
        return None
        
    # Get the most recent actions
    history = user_navigation[chat_id][-3:]
    actions = [entry["action"] for entry in history]
    
    # Check for ping-pong pattern (A -> B -> A)
    if actions[0] == actions[2] and actions[0] != actions[1]:
        return "ping_pong"
        
    # Check for rapid switching between main menu items
    main_menu_actions = ["menu_invest", "menu_explore", "menu_account"]
    if all(action in main_menu_actions for action in actions):
        # If all recent actions are main menu items
        return "menu_switching"
        
    return None

def reset_navigation(chat_id: int) -> None:
    """
    Reset navigation history for a specific chat.
    
    Args:
        chat_id: The chat ID to reset
    """
    global user_navigation
    
    if chat_id in user_navigation:
        user_navigation[chat_id] = []
        logger.info(f"Reset navigation history for chat {chat_id}")

def get_user_path(chat_id: int, limit: int = 10) -> List[str]:
    """
    Get the recent navigation path for a user.
    
    Args:
        chat_id: The chat ID
        limit: Maximum number of steps to return
        
    Returns:
        List of recent actions
    """
    global user_navigation
    
    if chat_id not in user_navigation:
        return []
        
    # Get the most recent actions (up to limit)
    history = user_navigation[chat_id][-limit:]
    return [entry["action"] for entry in history]

def cleanup_old_data(max_age: int = 3600) -> None:
    """
    Clean up old navigation data to prevent memory leaks.
    
    Args:
        max_age: Maximum age in seconds to keep navigation data
    """
    global user_navigation
    current_time = time.time()
    
    # Check each chat
    for chat_id in list(user_navigation.keys()):
        # Filter out old entries
        user_navigation[chat_id] = [
            entry for entry in user_navigation[chat_id]
            if current_time - entry["timestamp"] < max_age
        ]
        
        # Remove empty chats
        if not user_navigation[chat_id]:
            del user_navigation[chat_id]
            
    logger.debug(f"Cleaned up navigation data, tracking {len(user_navigation)} chats")