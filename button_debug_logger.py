"""
Button interaction debug logger for the FiLot Telegram bot.

This module tracks button interactions to help diagnose issues
with the button handling system. It provides a simple way to
log button presses and their results.
"""

import time
import json
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Maximum number of button interactions to store
MAX_BUTTON_LOGS = 100

# Global tracking for button interactions
button_interactions = []

def log_button_interaction(user_id: int, 
                          chat_id: int, 
                          callback_data: str, 
                          context: Optional[Dict[str, Any]] = None, 
                          result: Optional[Dict[str, Any]] = None, 
                          error: Optional[str] = None) -> None:
    """
    Log a button interaction for debugging purposes.
    
    Args:
        user_id: The user ID
        chat_id: The chat ID
        callback_data: The callback data from the button
        context: Optional additional context
        result: Optional result of the callback handling
        error: Optional error message if handling failed
    """
    global button_interactions
    
    # Create log entry
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "unix_time": time.time(),
        "user_id": user_id,
        "chat_id": chat_id,
        "callback_data": callback_data,
        "context": context or {},
        "result": result or {},
        "error": error,
        "success": error is None
    }
    
    # Add to log
    button_interactions.append(log_entry)
    
    # Limit log size
    if len(button_interactions) > MAX_BUTTON_LOGS:
        button_interactions = button_interactions[-MAX_BUTTON_LOGS:]
        
    # Log to logger as well
    if error:
        logger.error(f"Button interaction error: {callback_data} - {error}")
    else:
        logger.info(f"Button interaction success: {callback_data}")
        
def save_logs(filename: str = "button_debug_logs.json") -> None:
    """
    Save button interaction logs to a file.
    
    Args:
        filename: The filename to save logs to
    """
    global button_interactions
    
    try:
        with open(filename, 'w') as f:
            json.dump(button_interactions, f, indent=2)
        logger.info(f"Saved {len(button_interactions)} button interaction logs to {filename}")
    except Exception as e:
        logger.error(f"Failed to save button logs: {str(e)}")
        
def get_recent_interactions(user_id: Optional[int] = None, 
                           limit: int = 10,
                           filter_callback: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get recent button interactions, optionally filtered by user ID.
    
    Args:
        user_id: Optional user ID to filter by
        limit: Maximum number of interactions to return
        filter_callback: Optional callback data prefix to filter by
        
    Returns:
        List of recent button interactions
    """
    global button_interactions
    
    # Filter interactions
    filtered = button_interactions
    
    if user_id is not None:
        filtered = [i for i in filtered if i["user_id"] == user_id]
        
    if filter_callback:
        filtered = [i for i in filtered if i["callback_data"].startswith(filter_callback)]
        
    # Return most recent
    return filtered[-limit:]
    
def analyze_failures() -> Dict[str, Any]:
    """
    Analyze button interaction failures to identify patterns.
    
    Returns:
        Analysis results containing failure patterns and statistics
    """
    global button_interactions
    
    # Count failures by callback type
    failure_counts = {}
    total_failures = 0
    total_interactions = len(button_interactions)
    
    for interaction in button_interactions:
        if not interaction["success"]:
            # Extract button type (first part of callback data)
            callback_parts = interaction["callback_data"].split("_")
            button_type = callback_parts[0] if callback_parts else "unknown"
            
            # Count this failure
            failure_counts[button_type] = failure_counts.get(button_type, 0) + 1
            total_failures += 1
            
    # Prepare analysis results
    results = {
        "total_interactions": total_interactions,
        "total_failures": total_failures,
        "failure_rate": total_failures / total_interactions if total_interactions > 0 else 0,
        "failure_by_type": failure_counts,
    }
    
    return results