"""
Button fixing system for FiLot Telegram Bot.

This module provides special handling for button clicks that have been
identified as problematic, especially wallet and profile buttons.
"""

import time
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Track button clicks per user
BUTTON_CLICK_TRACKING = {}  # {user_id: {button_type: last_click_time}}
RATE_LIMIT_WINDOWS = {
    "back_to_main": 1.0,  # 1 second
    "profile_high-risk": 1.5,  # 1.5 seconds
    "profile_stable": 1.5,  # 1.5 seconds
    "profile_": 1.0,  # All other profile types
    "wallet_": 1.5,  # All wallet operations
    "connect_": 1.5,  # Connection operations
    "default": 0.5,  # Default for other buttons
}

def is_wallet_button_click_allowed(user_id: int, button_type: str) -> bool:
    """
    Check if a wallet button click should be allowed based on rate limiting.
    
    Args:
        user_id: The user ID
        button_type: The type of button being clicked
        
    Returns:
        True if the click should be allowed, False if it should be rate limited
    """
    current_time = time.time()
    
    # Initialize user tracking if needed
    if user_id not in BUTTON_CLICK_TRACKING:
        BUTTON_CLICK_TRACKING[user_id] = {}
        
    # Get the appropriate rate limit window
    rate_limit_window = RATE_LIMIT_WINDOWS.get("default")
    
    # Check all rate limit windows to find the most specific one
    for key, window in RATE_LIMIT_WINDOWS.items():
        if button_type == key or (key.endswith('_') and button_type.startswith(key)):
            rate_limit_window = window
            break
            
    # Check if this button was clicked recently
    if button_type in BUTTON_CLICK_TRACKING[user_id]:
        last_click_time = BUTTON_CLICK_TRACKING[user_id][button_type]
        time_since_last_click = current_time - last_click_time
        
        if time_since_last_click < rate_limit_window:
            logger.info(f"Rate limiting button click for user {user_id}: {button_type} (too soon: {time_since_last_click:.2f}s < {rate_limit_window}s)")
            return False
            
    # Record this click
    BUTTON_CLICK_TRACKING[user_id][button_type] = current_time
    return True
    
def fix_wallet_button_action(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply fixes to wallet button action results.
    
    Args:
        result: The original result dictionary
        
    Returns:
        Modified result dictionary with fixes applied
    """
    # Ensure we have a non-None context and chat_id
    if not result:
        result = {}
        
    if "chat_id" not in result or result["chat_id"] is None:
        logger.warning("Missing chat_id in wallet button result, adding placeholder")
        result["chat_id"] = 0
        
    # Add additional needed context for certain actions
    action = result.get("action")
    
    if action == "profile":
        # For profile actions, make sure profile_type exists
        if "profile_type" not in result or result["profile_type"] is None:
            result["profile_type"] = "moderate"  # Default to moderate risk
            logger.warning("Added missing profile_type in profile action")
            
    elif action == "back_to_main":
        # Make sure we have a message for main menu returns
        if "message" not in result:
            result["message"] = "Returning to main menu..."
            
    # Add general safety fields
    if "error_handled" not in result:
        result["error_handled"] = True
        
    return result

def cleanup_tracking(max_age: int = 3600) -> None:
    """
    Clean up old button tracking data.
    
    Args:
        max_age: Maximum age in seconds to keep tracking data
    """
    current_time = time.time()
    
    for user_id in list(BUTTON_CLICK_TRACKING.keys()):
        user_data = BUTTON_CLICK_TRACKING[user_id]
        
        # Remove old entries
        for button_type in list(user_data.keys()):
            if current_time - user_data[button_type] > max_age:
                del user_data[button_type]
                
        # Remove empty user entries
        if not user_data:
            del BUTTON_CLICK_TRACKING[user_id]
            
    logger.debug(f"Cleaned up button tracking data, now tracking {len(BUTTON_CLICK_TRACKING)} users")