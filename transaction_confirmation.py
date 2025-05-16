"""
Transaction confirmation module for FiLot Telegram bot.

This module provides UI components and handlers for secure transaction confirmation
before execution, satisfying the requirement for explicit user confirmation.
"""

import logging
from typing import Dict, Any, Callable, Awaitable, Optional, Union

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CallbackContext

logger = logging.getLogger(__name__)

# Dictionary to store pending transactions by callback_data ID
# Format: {callback_id: {"transaction_data": {...}, "created_at": timestamp, "user_id": user_id}}
PENDING_CONFIRMATIONS = {}

async def create_confirmation_request(
    transaction_preview: str,
    transaction_data: Dict[str, Any],
    user_id: int,
    transaction_type: str
) -> InlineKeyboardMarkup:
    """
    Create a confirmation UI with a unique confirmation ID.
    
    Args:
        transaction_preview: Text preview of the transaction
        transaction_data: Transaction data for execution after confirmation
        user_id: Telegram user ID
        transaction_type: Type of transaction (add_liquidity, remove_liquidity, swap)
        
    Returns:
        Inline keyboard markup for confirmation
    """
    import time
    import uuid
    
    # Generate a unique confirmation ID
    confirmation_id = f"txconf_{str(uuid.uuid4())[:8]}"
    
    # Store the pending confirmation
    PENDING_CONFIRMATIONS[confirmation_id] = {
        "transaction_data": transaction_data,
        "created_at": time.time(),
        "user_id": user_id,
        "transaction_type": transaction_type
    }
    
    # Create confirmation buttons
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_{confirmation_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel_{confirmation_id}")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

async def handle_confirmation_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    execute_func: Callable[[Dict[str, Any], int], Awaitable[Dict[str, Any]]]
) -> bool:
    """
    Handle confirmation callback from inline keyboard.
    
    Args:
        update: Telegram update
        context: Callback context
        execute_func: Function to execute the transaction if confirmed
        
    Returns:
        True if handled, False otherwise
    """
    query = update.callback_query
    if not query:
        return False
        
    # Get callback data
    callback_data = query.data
    
    # Check if this is a confirmation callback
    if not (callback_data.startswith("confirm_") or callback_data.startswith("cancel_")):
        return False
        
    # Extract confirmation ID
    confirmation_id = callback_data[8:]  # Remove "confirm_" or "cancel_"
    
    # Acknowledge the callback query to stop loading indicator
    await query.answer()
    
    # Check if the transaction exists
    if confirmation_id not in PENDING_CONFIRMATIONS:
        await query.edit_message_text(
            "⚠️ This transaction confirmation has expired or was already processed.",
            reply_markup=None
        )
        return True
        
    # Get transaction data
    transaction_info = PENDING_CONFIRMATIONS[confirmation_id]
    transaction_data = transaction_info["transaction_data"]
    stored_user_id = transaction_info["user_id"]
    
    # Security check: Ensure the user confirming is the one who initiated
    current_user_id = update.effective_user.id
    if current_user_id != stored_user_id:
        logger.warning(f"User {current_user_id} tried to confirm transaction for user {stored_user_id}")
        await query.edit_message_text(
            "⚠️ Security error: You cannot confirm a transaction initiated by another user.",
            reply_markup=None
        )
        return True
    
    if callback_data.startswith("confirm_"):
        # User confirmed the transaction
        # Remove the confirmation from pending list
        del PENDING_CONFIRMATIONS[confirmation_id]
        
        # Execute the transaction
        try:
            # Mark transaction as confirmed
            transaction_data["confirmed"] = True
            
            # Add user ID for security context
            transaction_data["user_id"] = current_user_id
            
            # Execute the transaction
            result = await execute_func(transaction_data, current_user_id)
            
            if result.get("success", False):
                # Transaction successful
                response_text = f"✅ *Transaction Successful*\n\n{result.get('message', '')}"
                
                # Add transaction details if available
                if "details" in result:
                    response_text += f"\n\n*Details:*\n{result['details']}"
            else:
                # Transaction failed
                error = result.get("error", "Unknown error")
                response_text = f"❌ *Transaction Failed*\n\n{error}"
            
            # Update the message with the result
            await query.edit_message_text(
                response_text,
                reply_markup=None,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error executing confirmed transaction: {e}")
            await query.edit_message_text(
                f"❌ *Error executing transaction*\n\n{str(e)}",
                reply_markup=None,
                parse_mode="Markdown"
            )
    else:
        # User cancelled the transaction
        # Remove the confirmation from pending list
        del PENDING_CONFIRMATIONS[confirmation_id]
        
        # Update the message
        await query.edit_message_text(
            "🚫 Transaction cancelled by user.",
            reply_markup=None
        )
    
    return True

def cleanup_expired_confirmations() -> None:
    """Clean up expired transaction confirmations."""
    import time
    
    # Current time
    now = time.time()
    
    # Find expired confirmations (older than 10 minutes)
    expired_ids = [
        conf_id for conf_id, conf_data in PENDING_CONFIRMATIONS.items()
        if now - conf_data["created_at"] > 600  # 10 minutes
    ]
    
    # Remove expired confirmations
    for conf_id in expired_ids:
        logger.info(f"Removing expired transaction confirmation: {conf_id}")
        del PENDING_CONFIRMATIONS[conf_id]