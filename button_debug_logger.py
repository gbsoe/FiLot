"""
Comprehensive button debug logger for FiLot Telegram bot.

This module provides detailed logging of button interactions to help identify
navigation issues and button-related errors.
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
DEBUG_LOG_FILE = "button_debug_log.json"
MAX_LOG_ENTRIES = 1000

# Global storage for button interactions
button_interactions = []

def log_button_interaction(
    user_id: int,
    chat_id: int,
    callback_data: str,
    context: Optional[Dict[str, Any]] = None,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
) -> None:
    """
    Log a button interaction with detailed context.
    
    Args:
        user_id: Telegram user ID
        chat_id: Telegram chat ID
        callback_data: Button callback data
        context: Optional context data
        result: Optional result data
        error: Optional error message
    """
    global button_interactions
    
    # Create log entry
    entry = {
        "timestamp": time.time(),
        "datetime": datetime.now().isoformat(),
        "user_id": user_id,
        "chat_id": chat_id,
        "callback_data": callback_data,
        "context": context or {},
        "result": result or {},
        "error": error,
        "success": error is None
    }
    
    # Add to in-memory log
    button_interactions.append(entry)
    
    # Trim log if needed
    if len(button_interactions) > MAX_LOG_ENTRIES:
        button_interactions = button_interactions[-MAX_LOG_ENTRIES:]
    
    # Log to console as well
    if error:
        logger.error(f"Button error: {callback_data} - {error}")
    else:
        logger.info(f"Button interaction: {callback_data}")
    
    # Write to debug log file
    try:
        save_debug_log()
    except Exception as e:
        logger.error(f"Error saving debug log: {e}")

def save_debug_log() -> None:
    """Save the current debug log to a file."""
    with open(DEBUG_LOG_FILE, 'w') as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "entries": button_interactions
        }, f, indent=2)
    
    logger.debug(f"Debug log saved with {len(button_interactions)} entries")

def get_button_logs(
    user_id: Optional[int] = None,
    callback_data_prefix: Optional[str] = None,
    limit: int = 100,
    include_errors_only: bool = False
) -> List[Dict[str, Any]]:
    """
    Get filtered button interaction logs.
    
    Args:
        user_id: Optional filter by user ID
        callback_data_prefix: Optional filter by callback data prefix
        limit: Maximum number of entries to return
        include_errors_only: Whether to include only error entries
        
    Returns:
        Filtered log entries
    """
    filtered = button_interactions
    
    # Filter by user ID if specified
    if user_id is not None:
        filtered = [entry for entry in filtered if entry["user_id"] == user_id]
    
    # Filter by callback data prefix if specified
    if callback_data_prefix is not None:
        filtered = [entry for entry in filtered if entry["callback_data"].startswith(callback_data_prefix)]
    
    # Filter by errors if specified
    if include_errors_only:
        filtered = [entry for entry in filtered if entry.get("error")]
    
    # Return the most recent entries up to the limit
    return filtered[-limit:]

def generate_summary_report() -> str:
    """
    Generate a readable summary report of button interactions.
    
    Returns:
        Formatted summary report
    """
    # Count total interactions
    total_interactions = len(button_interactions)
    
    # Count successful and failed interactions
    successful = len([e for e in button_interactions if e.get("success", False)])
    failed = total_interactions - successful
    
    # Count interactions by button type
    button_counts = {}
    for entry in button_interactions:
        callback_data = entry["callback_data"]
        
        # Extract button type (part before first underscore or whole string)
        button_type = callback_data.split("_")[0] + "_" if "_" in callback_data else callback_data
        
        button_counts[button_type] = button_counts.get(button_type, 0) + 1
    
    # Count errors by type
    error_counts = {}
    for entry in button_interactions:
        error = entry.get("error")
        if error:
            error_type = error.split(":")[0] if ":" in error else error
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
    
    # Generate report
    report = []
    report.append("====== BUTTON INTERACTION SUMMARY ======")
    report.append(f"Total interactions: {total_interactions}")
    report.append(f"Successful: {successful} ({(successful/total_interactions*100) if total_interactions else 0:.1f}%)")
    report.append(f"Failed: {failed} ({(failed/total_interactions*100) if total_interactions else 0:.1f}%)")
    
    report.append("\n--- Button Types ---")
    for button_type, count in sorted(button_counts.items(), key=lambda x: x[1], reverse=True):
        report.append(f"{button_type}: {count} interactions")
    
    if error_counts:
        report.append("\n--- Error Types ---")
        for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
            report.append(f"{error_type}: {count} occurrences")
    
    report.append("\n--- Recent Errors ---")
    recent_errors = get_button_logs(include_errors_only=True, limit=5)
    if recent_errors:
        for i, entry in enumerate(recent_errors):
            report.append(f"{i+1}. {entry['callback_data']} - {entry['error']}")
    else:
        report.append("No recent errors")
    
    report.append("=======================================")
    
    return "\n".join(report)

def clear_logs() -> None:
    """Clear all button interaction logs."""
    global button_interactions
    button_interactions = []
    
    # Delete log file if it exists
    if os.path.exists(DEBUG_LOG_FILE):
        os.remove(DEBUG_LOG_FILE)
    
    logger.info("Button interaction logs cleared")

# Initialize when module is loaded
if os.path.exists(DEBUG_LOG_FILE):
    try:
        with open(DEBUG_LOG_FILE, 'r') as f:
            data = json.load(f)
            button_interactions = data.get("entries", [])
        logger.info(f"Loaded {len(button_interactions)} button interactions from debug log")
    except Exception as e:
        logger.error(f"Error loading debug log: {e}")
        button_interactions = []
else:
    logger.info("No existing debug log found, starting fresh")
    button_interactions = []