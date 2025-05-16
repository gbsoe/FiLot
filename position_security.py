"""
Position security module for FiLot Telegram bot.

This module provides security controls for investment position management,
ensuring that all position manipulations (creation, closure, etc.) are
properly secured against unauthorized access and manipulation.
"""

import logging
import uuid
import time
from typing import Dict, Any, Optional, List, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Configure logging
logger = logging.getLogger(__name__)

# Registry of authorized position operations
# Format: {operation_id: {"user_id": user_id, "position_id": id, "operation": operation, "created_at": timestamp}}
POSITION_OPERATIONS = {}

# Operation expiry in seconds (5 minutes)
OPERATION_EXPIRY = 300

def create_position_security_token(user_id: int, position_id: int, operation: str) -> str:
    """
    Create a secure token for position operations.
    
    Args:
        user_id: Telegram user ID
        position_id: Position ID in database
        operation: Operation type (close, modify, etc)
        
    Returns:
        Security token for this operation
    """
    # Generate a unique operation ID
    operation_id = str(uuid.uuid4())[:8]
    
    # Store the operation details
    POSITION_OPERATIONS[operation_id] = {
        "user_id": user_id,
        "position_id": position_id,
        "operation": operation,
        "created_at": time.time()
    }
    
    return operation_id

def validate_position_operation(operation_id: str, user_id: int) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate a position operation token.
    
    Args:
        operation_id: Operation ID token
        user_id: User ID requesting the operation
        
    Returns:
        Tuple of (is_valid, operation_details)
    """
    # Clean up expired operations first
    cleanup_expired_operations()
    
    # Check if operation exists
    if operation_id not in POSITION_OPERATIONS:
        logger.warning(f"Position operation {operation_id} not found")
        return False, {"error": "Operation not found or expired"}
    
    # Get operation details
    operation = POSITION_OPERATIONS[operation_id]
    
    # Check if user is authorized
    if operation["user_id"] != user_id:
        logger.warning(f"Unauthorized position operation: user {user_id} tried to access operation for user {operation['user_id']}")
        return False, {"error": "Unauthorized operation"}
    
    # Operation is valid
    return True, operation

def create_position_confirmation_keyboard(position_id: int, user_id: int, operation: str = "close") -> InlineKeyboardMarkup:
    """
    Create a confirmation keyboard for position operations.
    
    Args:
        position_id: Position ID
        user_id: User ID
        operation: Operation type
        
    Returns:
        Telegram inline keyboard markup
    """
    # Create security token
    token = create_position_security_token(user_id, position_id, operation)
    
    # Build callback data with security token
    confirm_callback = f"position_confirm_{operation}_{token}"
    cancel_callback = f"position_cancel_{operation}_{token}"
    
    # Create keyboard
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=confirm_callback),
            InlineKeyboardButton("❌ Cancel", callback_data=cancel_callback)
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def cleanup_expired_operations() -> None:
    """Remove expired position operations."""
    current_time = time.time()
    expired_ids = []
    
    # Find expired operations
    for op_id, op_data in POSITION_OPERATIONS.items():
        if current_time - op_data["created_at"] > OPERATION_EXPIRY:
            expired_ids.append(op_id)
    
    # Remove expired operations
    for op_id in expired_ids:
        logger.info(f"Cleaning up expired position operation: {op_id}")
        POSITION_OPERATIONS.pop(op_id, None)

def extract_operation_token(callback_data: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract operation details from callback data.
    
    Args:
        callback_data: Callback data string
        
    Returns:
        Tuple of (action, operation, token) or (None, None, None) if invalid
    """
    # Expected format: position_{action}_{operation}_{token}
    # Example: position_confirm_close_a1b2c3d4
    parts = callback_data.split('_')
    
    if len(parts) < 4 or parts[0] != "position":
        return None, None, None
        
    action = parts[1]  # confirm or cancel
    operation = parts[2]  # close, modify, etc
    token = parts[3]  # security token
    
    return action, operation, token