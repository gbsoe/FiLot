#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Centralized callback query handler for the Telegram bot.
This module consolidates all callback handling to prevent duplicate processing.
"""

import logging
import hashlib
import time
from typing import Dict, Any, Set, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Global tracking mechanisms
processed_callbacks: Set[str] = set()
callback_timestamps: Dict[str, float] = {}
MAX_CALLBACKS_MEMORY = 1000

class CallbackRegistry:
    """Registry of callbacks to prevent duplicate processing."""
    
    @staticmethod
    def is_callback_processed(callback_id: str, chat_id: int, callback_data: str) -> bool:
        """
        Check if a callback has already been processed and mark it as processed if not.
        
        Args:
            callback_id: The callback query ID
            chat_id: The chat ID
            callback_data: The callback data string
            
        Returns:
            bool: True if the callback has already been processed, False otherwise
        """
        global processed_callbacks, callback_timestamps
        
        # Create multiple unique identifiers for this callback
        unique_id = f"cb_{callback_id}"
        content_id = f"cb_data_{chat_id}_{hashlib.md5(callback_data.encode()).hexdigest()[:8]}"
        combined_id = f"{chat_id}_{callback_id}_{callback_data}"
        
        # Current time for timestamp tracking
        now = time.time()
        
        # Check if we've already seen this callback by any ID
        if unique_id in processed_callbacks or content_id in processed_callbacks:
            logger.info(f"Callback already processed: {callback_data}")
            return True
            
        # Also check for very similar callbacks in a short time window
        for existing_id, timestamp in callback_timestamps.items():
            # If identical callback_data within 10 seconds, consider it duplicate
            if existing_id.endswith(callback_data) and now - timestamp < 10:
                logger.info(f"Similar callback detected within time window: {callback_data}")
                return True
        
        # Not processed yet, add to tracking
        processed_callbacks.add(unique_id)
        processed_callbacks.add(content_id)
        callback_timestamps[combined_id] = now
        
        # Prune old data to prevent memory leaks
        CallbackRegistry.prune_old_data()
        
        return False
    
    @staticmethod
    def prune_old_data() -> None:
        """Prune old callbacks data to prevent memory leaks."""
        global processed_callbacks, callback_timestamps
        
        # Limit the size of processed_callbacks
        if len(processed_callbacks) > MAX_CALLBACKS_MEMORY:
            processed_callbacks_list = list(processed_callbacks)
            processed_callbacks = set(processed_callbacks_list[-MAX_CALLBACKS_MEMORY:])
        
        # Remove timestamps older than 30 seconds
        now = time.time()
        old_callbacks = [cb_id for cb_id, timestamp in callback_timestamps.items() 
                         if now - timestamp > 30]
        
        for cb_id in old_callbacks:
            callback_timestamps.pop(cb_id, None)

# Initialize registry
callback_registry = CallbackRegistry()

def route_callback(callback_data: str, handler_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Route a callback to the appropriate handler based on the callback_data.
    
    Args:
        callback_data: The callback data from the button press
        handler_context: Dictionary containing all needed context for handling
            (chat_id, user_id, message_id, etc.)
            
    Returns:
        Optional response data or None if no action was taken
    """
    # Extract key context values for easier access
    chat_id = handler_context.get('chat_id')
    callback_id = handler_context.get('callback_id')
    
    # Skip if already processed
    if callback_registry.is_callback_processed(callback_id, chat_id, callback_data):
        return None
    
    # Log the callback being handled
    logger.info(f"Routing callback: {callback_data} for chat_id: {chat_id}")
    
    # ---------- Menu Navigation ----------
    if callback_data.startswith("menu_"):
        menu_action = callback_data.replace("menu_", "")
        return handle_menu_navigation(menu_action, handler_context)
    
    # ---------- Investment Actions ----------
    elif callback_data == "start_invest":
        return handle_investment_start(handler_context)
        
    elif callback_data == "invest_back_to_profile":
        return handle_investment_back_to_profile(handler_context)
        
    elif callback_data.startswith("confirm_invest_"):
        pool_id = callback_data.replace("confirm_invest_", "")
        return handle_investment_confirmation(pool_id, handler_context)
        
    elif callback_data.startswith("invest_"):
        return handle_investment_option(callback_data, handler_context)
    
    # ---------- Wallet Actions ----------
    elif callback_data == "walletconnect":
        return handle_wallet_connect(handler_context)
        
    elif callback_data.startswith("check_wc_"):
        session_id = callback_data.replace("check_wc_", "")
        return handle_wallet_session_check(session_id, handler_context)
        
    elif callback_data.startswith("wallet_connect_"):
        try:
            amount = float(callback_data.split("_")[2])
            return handle_wallet_connect_with_amount(amount, handler_context)
        except (IndexError, ValueError):
            logger.error(f"Invalid wallet_connect callback format: {callback_data}")
            return {"error": "Invalid wallet connect format"}
    
    # ---------- Simulation Actions ----------
    elif callback_data.startswith("simulate_period_"):
        try:
            parts = callback_data.split("_")
            period = parts[2]  # daily, weekly, monthly, yearly
            amount = float(parts[3]) if len(parts) > 3 else 1000.0
            return handle_simulation(period, amount, handler_context)
        except (IndexError, ValueError):
            logger.error(f"Invalid simulate_period callback format: {callback_data}")
            return {"error": "Invalid simulation format"}
    
    # ---------- Unknown Action ----------
    logger.warning(f"Unknown callback type: {callback_data}")
    return {
        "message": "I received your selection, but I'm not sure how to process it. Please use /help to see available commands.",
        "error": "Unknown callback type"
    }

# ====== Handler Implementation Functions ======

def handle_menu_navigation(menu_action: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle menu navigation callbacks."""
    # This would typically import and call the appropriate function from bot.py
    logger.info(f"Would trigger {menu_action} menu action")
    
    # Return an indication of what should happen
    # The main loop can then take the appropriate action
    return {
        "action": "menu_navigation",
        "menu": menu_action,
        "chat_id": context.get("chat_id")
    }

def handle_investment_start(context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle the start_invest callback."""
    logger.info(f"Would trigger investment flow start")
    return {
        "action": "start_invest_flow",
        "chat_id": context.get("chat_id")
    }

def handle_investment_back_to_profile(context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle going back to profile selection in investment flow."""
    logger.info(f"Would trigger back to profile in investment flow")
    return {
        "action": "invest_back_to_profile",
        "chat_id": context.get("chat_id")
    }

def handle_investment_confirmation(pool_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle investment confirmation in a specific pool."""
    logger.info(f"Would confirm investment in pool {pool_id}")
    return {
        "action": "confirm_investment",
        "pool_id": pool_id,
        "chat_id": context.get("chat_id")
    }

def handle_investment_option(callback_data: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle investment option selection."""
    logger.info(f"Would handle investment option {callback_data}")
    return {
        "action": "invest_option",
        "callback_data": callback_data,
        "chat_id": context.get("chat_id")
    }

def handle_wallet_connect(context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle wallet connect request."""
    logger.info(f"Would trigger wallet connect flow")
    return {
        "action": "walletconnect",
        "chat_id": context.get("chat_id")
    }

def handle_wallet_session_check(session_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle wallet session check."""
    logger.info(f"Would check wallet session {session_id}")
    return {
        "action": "check_wallet_session",
        "session_id": session_id,
        "chat_id": context.get("chat_id")
    }

def handle_wallet_connect_with_amount(amount: float, context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle wallet connect with investment amount."""
    logger.info(f"Would trigger wallet connect with amount ${amount:.2f}")
    return {
        "action": "wallet_connect_with_amount",
        "amount": amount,
        "chat_id": context.get("chat_id")
    }

def handle_simulation(period: str, amount: float, context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle investment simulation."""
    logger.info(f"Would simulate {period} returns for ${amount:.2f}")
    return {
        "action": "simulate",
        "period": period,
        "amount": amount,
        "chat_id": context.get("chat_id")
    }