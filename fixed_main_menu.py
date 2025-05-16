"""
Fixed main menu button handler for FiLot Telegram bot.

This module provides enhanced main menu button handling with robust error handling
to prevent JavaScript errors like "Cannot read properties of null (reading 'value')".
"""

import logging
import traceback
import time
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Keep track of main menu button clicks to prevent rapid clicking
menu_clicks = {}  # {user_id: last_click_time}
MENU_CLICK_COOLDOWN = 2.0  # seconds

def handle_back_to_main_menu(user_id: int, chat_id: int) -> Dict[str, Any]:
    """
    Handle the back to main menu button click with improved error handling.
    
    Args:
        user_id: The Telegram user ID
        chat_id: The Telegram chat ID
        
    Returns:
        Dict with response data
    """
    try:
        logger.info(f"User {user_id} clicked Back to Main Menu")
        
        # Check for rate limiting (prevent rapid clicks)
        current_time = time.time()
        if user_id in menu_clicks:
            time_diff = current_time - menu_clicks[user_id]
            
            # If clicking too rapidly, throttle
            if time_diff < MENU_CLICK_COOLDOWN:
                logger.warning(f"User {user_id} clicking main menu button too rapidly ({time_diff:.2f}s)")
                return {
                    "success": False,
                    "action": "back_to_main_throttled",
                    "message": "Please wait a moment before navigating to the main menu again.",
                    "throttled": True,
                    "chat_id": chat_id
                }
        
        # Record this click
        menu_clicks[user_id] = current_time
        
        # Reset user navigation state if possible
        try:
            from fix_navigation import reset_navigation
            reset_navigation(chat_id)
            logger.info(f"Reset navigation state for user {user_id}")
        except ImportError:
            logger.warning("Navigation reset not available")
        
        # Prepare success response
        message = "🏠 Returning to main menu..."
        
        # Return success response
        return {
            "success": True,
            "action": "back_to_main",
            "message": message,
            "chat_id": chat_id
        }
        
    except Exception as e:
        logger.error(f"Error handling back to main menu: {e}")
        logger.error(traceback.format_exc())
        
        # Fallback message if something goes wrong
        message = (
            "Sorry, I couldn't process your request to return to the main menu. "
            "Please try again in a moment."
        )
        
        return {
            "success": False,
            "action": "back_to_main_error",
            "error": str(e),
            "message": message,
            "chat_id": chat_id
        }

def cleanup_menu_data(max_age: int = 3600) -> None:
    """
    Clean up old menu click data.
    
    Args:
        max_age: Maximum age in seconds to keep menu data
    """
    current_time = time.time()
    
    for user_id in list(menu_clicks.keys()):
        last_click = menu_clicks[user_id]
        if current_time - last_click > max_age:
            del menu_clicks[user_id]
            
    logger.debug(f"Cleaned up menu clicks data, now tracking {len(menu_clicks)} users")