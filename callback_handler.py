#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Centralized callback query handler for the Telegram bot.
This module consolidates all callback handling to prevent duplicate processing.
"""

import logging
import hashlib
import time
from typing import Dict, Any, Set, Optional, List
import random

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Import button debug logger
try:
    from button_debug_logger import log_button_interaction
    BUTTON_LOGGING_ENABLED = True
    logger.info("Button debug logging is enabled")
except ImportError:
    logger.warning("Button debug logger not available")
    BUTTON_LOGGING_ENABLED = False
    
    # Create a dummy function if the real one is not available
    def log_button_interaction(*args, **kwargs):
        pass

# Import wallet button fix
try:
    from fix_wallet_button import fix_connect_wallet
    WALLET_FIX_ENABLED = True
    logger.info("Wallet button fix is enabled")
except ImportError:
    logger.warning("Wallet button fix not available")
    WALLET_FIX_ENABLED = False

# Import enhanced navigation systems
try:
    # First try our new improved system
    import fix_navigation
    IMPROVED_NAVIGATION = True
    logger.info("Using improved navigation system")
except ImportError:
    # Fall back to original system if not available
    import navigation_context
    IMPROVED_NAVIGATION = False
    logger.info("Using original navigation system")

# Define some helper handler functions
def handle_wallet_connect(handler_context):
    """Handle wallet connection request."""
    logger.info("Standard wallet connect handler called")
    
    try:
        user_id = handler_context.get('user_id', 0)
        chat_id = handler_context.get('chat_id', 0)
        
        # Try to import wallet utils safely
        try:
            import wallet_utils
            
            # Check if wallet is connected
            is_connected = False
            wallet_address = None
            
            if hasattr(wallet_utils, 'is_wallet_connected'):
                is_connected = wallet_utils.is_wallet_connected(user_id)
                
                if is_connected and hasattr(wallet_utils, 'get_wallet_info'):
                    wallet_info = wallet_utils.get_wallet_info(user_id) or {}
                    wallet_address = wallet_info.get('address', 'Unknown')
            
            # If already connected, show status instead
            if is_connected:
                logger.info(f"Wallet already connected for user {user_id}: {wallet_address}")
                
                return {
                    "success": True,
                    "action": "wallet_already_connected",
                    "message": f"Your wallet is already connected:\n\nAddress: `{wallet_address}`",
                    "wallet_address": wallet_address
                }
            
            # Generate connection data safely
            connection_data = None
            if hasattr(wallet_utils, 'generate_connection_data'):
                connection_data = wallet_utils.generate_connection_data(user_id)
            
            if not connection_data:
                logger.error("Failed to generate wallet connection data")
                return {
                    "success": False,
                    "action": "error",
                    "message": "Could not generate wallet connection data. Please try again later."
                }
            
            logger.info(f"Generated wallet connection data for user {user_id}")
            return {
                "success": True,
                "action": "connect_wallet",
                "message": "Please connect your wallet using the link below.",
                "connection_data": connection_data
            }
            
        except Exception as e:
            logger.error(f"Error in wallet connection: {e}")
            return {
                "success": False,
                "action": "error",
                "message": "An error occurred when trying to connect your wallet. Please try again later."
            }
            
    except Exception as e:
        logger.error(f"Critical error in wallet connection: {e}")
        return {
            "success": False,
            "action": "error",
            "message": "A system error occurred. Please try again later."
        }

def handle_wallet_disconnect(handler_context):
    """Handle wallet disconnection request."""
    logger.info("Standard wallet disconnect handler called")
    
    try:
        user_id = handler_context.get('user_id', 0)
        
        # Try to import wallet utils safely
        try:
            import wallet_utils
            
            # Check if the wallet is connected
            is_connected = False
            if hasattr(wallet_utils, 'is_wallet_connected'):
                is_connected = wallet_utils.is_wallet_connected(user_id)
            
            if not is_connected:
                return {
                    "success": True,
                    "action": "wallet_not_connected",
                    "message": "You don't have a wallet connected."
                }
            
            # Disconnect the wallet
            success = False
            if hasattr(wallet_utils, 'disconnect_wallet'):
                success = wallet_utils.disconnect_wallet(user_id)
            
            if success:
                return {
                    "success": True,
                    "action": "wallet_disconnected",
                    "message": "Your wallet has been disconnected successfully."
                }
            else:
                return {
                    "success": False,
                    "action": "error",
                    "message": "Could not disconnect the wallet. Please try again later."
                }
                
        except Exception as e:
            logger.error(f"Error in wallet disconnection: {e}")
            return {
                "success": False,
                "action": "error",
                "message": "An error occurred when trying to disconnect your wallet. Please try again later."
            }
            
    except Exception as e:
        logger.error(f"Critical error in wallet disconnection: {e}")
        return {
            "success": False,
            "action": "error",
            "message": "A system error occurred. Please try again later."
        }

def handle_wallet_session_check(session_id, handler_context):
    """Handle checking wallet session status."""
    logger.info(f"Checking wallet session: {session_id}")
    
    try:
        # Import necessary modules
        try:
            import walletconnect_utils
            
            user_id = handler_context.get('user_id', 0)
            
            # Convert session_id to string if needed
            if not isinstance(session_id, str):
                session_id = str(session_id)
            
            # Check session status
            session = walletconnect_utils.check_walletconnect_session(user_id, session_id)
            
            if not session:
                return {
                    "success": False,
                    "action": "session_not_found",
                    "message": "Wallet connection session not found or expired."
                }
            
            # Check if connected
            is_connected = session.get('connected', False)
            
            if is_connected:
                wallet_address = session.get('wallet_address', 'Unknown')
                return {
                    "success": True,
                    "action": "wallet_connected",
                    "message": f"Your wallet is now connected:\n\nAddress: `{wallet_address}`",
                    "wallet_address": wallet_address
                }
            else:
                return {
                    "success": True,
                    "action": "session_pending",
                    "message": "Waiting for wallet connection...",
                    "session_id": session_id
                }
                
        except ImportError:
            logger.error("WalletConnect utils not available")
            return {
                "success": False,
                "action": "error", 
                "message": "Wallet connection feature is currently unavailable."
            }
            
        except Exception as e:
            logger.error(f"Error checking wallet session: {e}")
            return {
                "success": False,
                "action": "error",
                "message": "Error checking wallet connection status."
            }
            
    except Exception as e:
        logger.error(f"Critical error in session check: {e}")
        return {
            "success": False,
            "action": "error",
            "message": "A system error occurred. Please try again later."
        }

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Global tracking mechanisms
processed_callbacks: Set[str] = set()
callback_timestamps: Dict[str, float] = {}
recent_navigation_contexts: Dict[int, List[Dict[str, Any]]] = {}  # Track navigation context by chat_id
MAX_CALLBACKS_MEMORY = 1000
MAX_CONTEXT_MEMORY = 20  # Keep track of last 20 navigation steps per chat

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
        global processed_callbacks, callback_timestamps, recent_navigation_contexts
        
        # Create multiple unique identifiers for this callback
        unique_id = f"cb_{callback_id}"
        content_id = f"cb_data_{chat_id}_{hashlib.md5(callback_data.encode()).hexdigest()[:8]}"
        combined_id = f"{chat_id}_{callback_id}_{callback_data}"
        
        # Current time for timestamp tracking
        now = time.time()
        
        # Check if we've already seen this exact callback by ID
        if unique_id in processed_callbacks:
            logger.info(f"Exact callback ID already processed: {callback_data}")
            return True
        
        # Check for content-based duplication
        # Only block if it's the exact same callback content in a very short window (1 second)
        # This prevents actual duplicate button presses but allows sequential navigation
        content_duplication = False
        for existing_id, timestamp in callback_timestamps.items():
            if existing_id.startswith(f"{chat_id}_") and existing_id.endswith(callback_data):
                time_diff = now - timestamp
                # Only consider duplicates if they happen within 1 second
                if time_diff < 1.0:
                    logger.info(f"Similar callback detected within 1s window: {callback_data}")
                    content_duplication = True
                    break
        
        if content_duplication:
            return True
            
        # Get the navigation context for this chat
        chat_context = recent_navigation_contexts.get(chat_id, [])
        
        # Determine if this callback is part of a complex navigation pattern
        is_navigation_button = any(callback_data.startswith(prefix) for prefix in 
                                  ['menu_', 'back_to_', 'explore_', 'account_'])
        
        # Special handling for back-and-forth and complex navigation patterns
        if is_navigation_button and chat_context:
            # Get the last few navigation steps
            last_steps = [step.get('callback_data') for step in chat_context[-3:] 
                         if step.get('timestamp', 0) > now - 30]  # Consider only last 30 seconds
            
            # If this forms a back-and-forth pattern, make sure we process it
            if len(last_steps) >= 2:
                # Check if we're in an alternating A-B-A pattern
                if last_steps[-2] == callback_data and len(last_steps) >= 3:
                    # We have an A-B-A pattern, always allow this for improved navigation
                    logger.info(f"Allowing back-forth navigation pattern: {last_steps[-2]} -> {last_steps[-1]} -> {callback_data}")
                    # Don't mark as duplicate, fall through to processing
                
        # Not processed yet, add to tracking
        processed_callbacks.add(unique_id)
        
        # We'll still add content_id but with a much shorter timeout for complex navigation
        processed_callbacks.add(content_id)
        callback_timestamps[combined_id] = now
        
        # Update navigation context for this chat
        if chat_id not in recent_navigation_contexts:
            recent_navigation_contexts[chat_id] = []
            
        # Add this step to the context
        recent_navigation_contexts[chat_id].append({
            'callback_data': callback_data,
            'timestamp': now,
            'context': 'navigation' if is_navigation_button else 'action'
        })
        
        # Limit the context size
        if len(recent_navigation_contexts[chat_id]) > MAX_CONTEXT_MEMORY:
            recent_navigation_contexts[chat_id] = recent_navigation_contexts[chat_id][-MAX_CONTEXT_MEMORY:]
        
        # Prune old data to prevent memory leaks
        CallbackRegistry.prune_old_data()
        
        return False
    
    @staticmethod
    def prune_old_data() -> None:
        """Prune old callbacks data to prevent memory leaks."""
        global processed_callbacks, callback_timestamps, recent_navigation_contexts
        
        # Limit the size of processed_callbacks
        if len(processed_callbacks) > MAX_CALLBACKS_MEMORY:
            processed_callbacks_list = list(processed_callbacks)
            processed_callbacks = set(processed_callbacks_list[-MAX_CALLBACKS_MEMORY:])
        
        # Current time for cleanup decisions
        now = time.time()
        
        # Remove timestamps older than 30 seconds
        old_callbacks = [cb_id for cb_id, timestamp in callback_timestamps.items() 
                         if now - timestamp > 30]
        
        for cb_id in old_callbacks:
            callback_timestamps.pop(cb_id, None)
            
        # Clean up old navigation contexts as well
        for chat_id in list(recent_navigation_contexts.keys()):
            # Keep only steps within the last 5 minutes (300 seconds)
            recent_navigation_contexts[chat_id] = [
                step for step in recent_navigation_contexts[chat_id]
                if step.get('timestamp', 0) > now - 300
            ]
            
            # If the list is empty, remove the chat_id entry
            if not recent_navigation_contexts[chat_id]:
                recent_navigation_contexts.pop(chat_id, None)

# Initialize registry
callback_registry = CallbackRegistry()

def route_callback(handler_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
    chat_id = handler_context.get('chat_id', 0)  # Default to 0 if not provided
    callback_id = handler_context.get('callback_id', f"default_{time.time()}")  # Generate a unique ID if not provided
    
    # Validate inputs to prevent type errors
    if not isinstance(chat_id, int):
        try:
            chat_id = int(chat_id)
        except (ValueError, TypeError):
            chat_id = 0
            logger.warning(f"Invalid chat_id type, using default: {chat_id}")
    
    if not isinstance(callback_id, str):
        try:
            callback_id = str(callback_id)
        except (ValueError, TypeError):
            callback_id = f"default_{time.time()}"
            logger.warning(f"Invalid callback_id type, using generated: {callback_id}")
    
    # Get the callback data from the context
    callback_data = handler_context.get('callback_data', '')
    user_id = handler_context.get('user_id', 0)
    
    # Log this button interaction
    if BUTTON_LOGGING_ENABLED:
        log_button_interaction(
            user_id=user_id,
            chat_id=chat_id,
            callback_data=callback_data,
            context=handler_context
        )
    
    # Enhanced duplicate detection using navigation context - only for non-wallet buttons
    if callback_data not in ['connect_wallet', 'disconnect_wallet']:
        if IMPROVED_NAVIGATION:
            if fix_navigation.is_duplicate(chat_id, callback_data):
                logger.info(f"Navigation context detected duplicate: {callback_data}")
                return None
        else:
            if is_duplicate(chat_id, callback_data):
                logger.info(f"Navigation context detected duplicate: {callback_data}")
                return None
    
    # Also use the legacy processing check to ensure backward compatibility
    if callback_registry.is_callback_processed(callback_id, chat_id, callback_data):
        return None
    
    # Record this navigation step in our enhanced tracking system
    if IMPROVED_NAVIGATION:
        fix_navigation.record_navigation(chat_id, callback_data)
    else:
        navigation_context.record_navigation(chat_id, callback_data)
    
    # Detect if we're in a special navigation pattern that needs handling
    pattern = None
    if IMPROVED_NAVIGATION:
        pattern = fix_navigation.detect_pattern(chat_id)
    else:
        pattern = navigation_context.detect_pattern(chat_id)
    if pattern:
        handler_context['navigation_pattern'] = pattern
        logger.info(f"Detected navigation pattern: {pattern} for chat_id: {chat_id}")
    
    # Import our wallet fixes if available
    try:
        from fixed_wallet_connect import handle_connect_wallet_callback, handle_disconnect_wallet_callback
        HAS_FIXED_WALLET = True
        logger.info("Fixed wallet connection system is available")
    except ImportError:
        HAS_FIXED_WALLET = False
        logger.warning("Fixed wallet connection system not available")
    
    # Add a test/debugging parameter to handler context
    handler_context['is_test'] = handler_context.get('test_mode', False)
    
    # Log the callback being handled
    logger.info(f"Routing callback: {callback_data} for chat_id: {chat_id}")
    
    # ---------- Menu Navigation ----------
    if callback_data == "back_to_main":
        # Special case for main menu button
        try:
            # First try using our specialized fixed main menu handler
            from fixed_main_menu import handle_back_to_main_menu
            user_id = handler_context.get('user_id', 0)
            chat_id = handler_context.get('chat_id', 0)
            logger.info(f"Using fixed main menu handler for back_to_main from user {user_id}")
            
            # Use the specialized handler
            result = handle_back_to_main_menu(user_id, chat_id)
            
            # If we got a result, return it
            if result:
                return result
        except ImportError:
            logger.warning("Fixed main menu handler not available, falling back to button fix")
            
        try:
            # Try using our button fix system if available
            import button_fix
            user_id = handler_context.get('user_id', 0)
            logger.info(f"Using button fix system for back_to_main from user {user_id}")
            
            if not button_fix.is_wallet_button_click_allowed(user_id, "back_to_main"):
                logger.info(f"Throttling back_to_main button click for user {user_id}")
                return {
                    "action": "back_to_main",
                    "message": "Returning to main menu...",
                    "chat_id": handler_context.get("chat_id")
                }
                
            result = {
                "action": "back_to_main",
                "chat_id": handler_context.get("chat_id")
            }
            return button_fix.fix_wallet_button_action(result)
        except ImportError:
            # Default behavior if button_fix not available
            logger.info("Button fix system not available for back_to_main button")
            return {
                "action": "back_to_main",
                "message": "🏠 Returning to main menu...",
                "chat_id": handler_context.get("chat_id"),
                "success": True
            }
    elif callback_data == "back_to_explore":
        # Special case for back to explore menu button
        return {
            "action": "menu_navigation",
            "menu": "explore",
            "chat_id": handler_context.get("chat_id")
        }
    elif callback_data == "menu_invest" or callback_data == "back_to_invest":
        # Back to invest menu button
        return {
            "action": "menu_navigation",
            "menu": "invest",
            "chat_id": handler_context.get("chat_id")
        }
    elif callback_data.startswith("menu_"):
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
        
    elif callback_data.startswith("amount_"):
        amount_str = callback_data.replace("amount_", "")
        if amount_str == "custom":
            return handle_custom_amount(handler_context)
        else:
            try:
                amount = float(amount_str)
                return handle_investment_amount(amount, handler_context)
            except ValueError:
                logger.error(f"Invalid amount format in callback: {callback_data}")
                return {"error": "Invalid amount format"}
        
    elif callback_data.startswith("invest_"):
        return handle_investment_option(callback_data, handler_context)
    
    # ---------- Wallet Actions ----------
    elif callback_data == "connect_wallet":
        user_id = handler_context.get('user_id', 0)
        chat_id = handler_context.get('chat_id', 0)
        
        # First try using our button fix system
        try:
            import button_fix
            logger.info(f"Using button fix system for connect_wallet from user {user_id}")
            
            if not button_fix.is_wallet_button_click_allowed(user_id, "connect_wallet"):
                logger.info(f"Throttling wallet button click for user {user_id}")
                return {
                    "action": "error",
                    "message": "Please wait a moment before trying to connect again."
                }
            
            # Try our fixed wallet system if available
            if HAS_FIXED_WALLET:
                logger.info(f"Using fixed wallet system for connect_wallet from user {user_id}")
                try:
                    result = handle_connect_wallet_callback(chat_id, user_id)
                    if result and "error" in result:
                        logger.error(f"Error in fixed wallet system: {result['error']}")
                    # Apply fixes to prevent JavaScript errors
                    return button_fix.fix_wallet_button_action(result)
                except Exception as e:
                    logger.error(f"Error in fixed wallet system: {e}")
                    # Fall through to standard handler
            
            # Standard wallet connection handler with fixes applied
            result = handle_wallet_connect(handler_context)
            return button_fix.fix_wallet_button_action(result)
                
        except ImportError:
            logger.warning("Button fix system not available, using standard path")
            
            # Use our fixed wallet system if available
            if HAS_FIXED_WALLET:
                logger.info(f"Using fixed wallet system for connect_wallet from user {user_id}")
                try:
                    result = handle_connect_wallet_callback(chat_id, user_id)
                    if result and "error" in result:
                        logger.error(f"Error in fixed wallet system: {result['error']}")
                    return result
                except Exception as e:
                    logger.error(f"Error in fixed wallet system: {e}")
                    # Fall through to standard handler
            
            # Standard wallet connection handler
            return handle_wallet_connect(handler_context)
    
    elif callback_data == "disconnect_wallet":
        user_id = handler_context.get('user_id', 0)
        chat_id = handler_context.get('chat_id', 0)
        
        # First try using our button fix system
        try:
            import button_fix
            logger.info(f"Using button fix system for disconnect_wallet from user {user_id}")
            
            if not button_fix.is_wallet_button_click_allowed(user_id, "disconnect_wallet"):
                logger.info(f"Throttling wallet disconnect button click for user {user_id}")
                return {
                    "action": "error",
                    "message": "Please wait a moment before trying again."
                }
            
            # Try our fixed wallet system if available
            if HAS_FIXED_WALLET:
                logger.info(f"Using fixed wallet system for disconnect_wallet from user {user_id}")
                try:
                    result = handle_disconnect_wallet_callback(chat_id, user_id)
                    if result and "error" in result:
                        logger.error(f"Error in fixed wallet system: {result['error']}")
                    # Apply fixes to prevent JavaScript errors
                    return button_fix.fix_wallet_button_action(result)
                except Exception as e:
                    logger.error(f"Error in fixed wallet system: {e}")
                    # Fall through to standard handler
            
            # Standard wallet connection handler with fixes applied
            result = handle_wallet_disconnect(handler_context)
            return button_fix.fix_wallet_button_action(result)
                
        except ImportError:
            logger.warning("Button fix system not available, using standard path")
            
            # Use our fixed wallet system if available
            if HAS_FIXED_WALLET:
                logger.info(f"Using fixed wallet system for disconnect_wallet from user {user_id}")
                try:
                    result = handle_disconnect_wallet_callback(chat_id, user_id)
                    if result and "error" in result:
                        logger.error(f"Error in fixed wallet system: {result['error']}")
                    return result
                except Exception as e:
                    logger.error(f"Error in fixed wallet system: {e}")
                    # Fall through to standard handler
            
            # Standard wallet disconnection handler
            return handle_wallet_disconnect(handler_context)
        
    elif callback_data == "walletconnect":
        return handle_wallet_connect(handler_context)
        
    elif callback_data.startswith("check_wc_"):
        # Get session ID safely
        try:
            session_id = callback_data.replace("check_wc_", "")
            
            # Try using our button fix system if available
            try:
                import button_fix
                user_id = handler_context.get('user_id', 0)
                chat_id = handler_context.get('chat_id', 0)
                logger.info(f"Using button fix system for session check {session_id} from user {user_id}")
                
                # Check if this is a rapid repeated click
                if not button_fix.is_wallet_button_click_allowed(user_id, f"check_wc_{session_id}"):
                    logger.info(f"Throttling wallet session check button click for user {user_id}")
                    return {
                        "action": "session_pending",
                        "message": "Still checking your wallet connection status. Please wait...",
                        "session_id": session_id
                    }
                
                # Call the regular handler but fix the response
                result = handle_wallet_session_check(session_id, handler_context)
                return button_fix.fix_wallet_button_action(result)
                
            except ImportError:
                # Just use the standard handler if button_fix not available
                logger.warning("Button fix system not available for session check")
            
            # Standard session check
            return handle_wallet_session_check(session_id, handler_context)
            
        except Exception as e:
            logger.error(f"Error in session check handler: {e}")
            return {
                "action": "error",
                "message": "Error checking wallet connection status. Please try again."
            }
        
    elif callback_data.startswith("wallet_connect_"):
        try:
            amount = float(callback_data.split("_")[2])
            return handle_wallet_connect_with_amount(amount, handler_context)
        except (IndexError, ValueError):
            logger.error(f"Invalid wallet_connect callback format: {callback_data}")
            return {"error": "Invalid wallet connect format"}
    
    # ---------- Explore Actions ----------
    elif callback_data.startswith("explore_"):
        explore_action = callback_data.replace("explore_", "")
        return handle_explore_action(explore_action, handler_context)
        
    # ---------- Simulation Actions ----------
    elif callback_data.startswith("simulate_"):
        try:
            if callback_data.startswith("simulate_period_"):
                # Handle period-specific simulations
                parts = callback_data.split("_")
                period = parts[2]  # daily, weekly, monthly, yearly
                amount = float(parts[3]) if len(parts) > 3 else 1000.0
                return handle_simulation(period, amount, handler_context)
            elif callback_data == "simulate_custom":
                # Handle custom amount simulation request
                return handle_custom_simulation(handler_context)
            else:
                # Handle direct amount simulations (e.g., simulate_100, simulate_500)
                amount_str = callback_data.replace("simulate_", "")
                amount = float(amount_str)
                return handle_simulation("default", amount, handler_context)
        except (IndexError, ValueError):
            logger.error(f"Invalid simulation callback format: {callback_data}")
            return {"error": "Invalid simulation format"}
    
    # ---------- Account Actions ----------
    elif callback_data.startswith("account_"):
        action = callback_data.replace("account_", "")
        return handle_account_action(action, handler_context)
        
    # ---------- Profile Actions ----------
    elif callback_data.startswith("profile_"):
        profile_type = callback_data.replace("profile_", "")
        return handle_profile_action(profile_type, handler_context)
            
    # ---------- Navigation pattern recovery ----------
    # If we reach here, it might be because we're in a complex navigation pattern
    # Let's try to determine if this is a navigation action we can recover
    
    # ---------- Secure Transaction Confirmation ----------
    elif callback_data.startswith("confirm_") or callback_data.startswith("cancel_"):
        try:
            # Import transaction confirmation module
            import transaction_confirmation
            
            # Create a transaction executor based on transaction type - needs to be defined outside this function
            # This function will be passed to handle_confirmation_callback
            # Note: Actual execution happens in transaction_confirmation.py which is async-ready
            def create_transaction_executor():
                """Return a function that can execute the right transaction type based on the data."""
                import wallet_utils
                
                # Define our executor function that transaction_confirmation will call
                async def executor_func(tx_data, user_id):
                    # Get transaction type and execute appropriate function
                    tx_type = tx_data.get("transaction_type", "unknown")
                    
                    if tx_type == "add_liquidity":
                        # Execute add liquidity transaction
                        return await wallet_utils.join_pool_transaction(
                            wallet_address=tx_data.get("wallet_address", ""),
                            pool_id=tx_data.get("pool_id", ""),
                            token_a=tx_data.get("token_a", "SOL"),
                            token_b=tx_data.get("token_b", "USDC"),
                            deposit_sol=tx_data.get("deposit_sol", 0.0),
                            deposit_usdc=tx_data.get("deposit_usdc", 0.0),
                            user_id=user_id,
                            slippage_tolerance=tx_data.get("slippage_tolerance", 0.5),
                            confirmed=True
                        )
                    elif tx_type == "remove_liquidity":
                        # Execute remove liquidity transaction
                        return await wallet_utils.stop_pool_transaction(
                            wallet_address=tx_data.get("wallet_address", ""),
                            pool_id=tx_data.get("pool_id", ""),
                            user_id=user_id,
                            percentage=tx_data.get("percentage", 100.0),
                            slippage_tolerance=tx_data.get("slippage_tolerance", 0.5),
                            confirmed=True
                        )
                    else:
                        return {
                            "success": False,
                            "error": f"Unknown transaction type: {tx_type}"
                        }
                
                return executor_func
            
            # Get the callback query to handle the callback properly
            query = handler_context.get("callback_query")
            
            if query is None:
                logger.error("Missing callback query in handler context")
                return {"error": "Missing callback query"}
            
            # Get access to update and context
            telegram_update = handler_context.get("update")
            context_types = handler_context.get("context")
            
            if telegram_update is None or context_types is None:
                logger.error("Missing update or context in handler context")
                return {"error": "Missing update or context"}
            
            # Create our executor function
            execute_transaction = create_transaction_executor()
            
            # This will be handled by the async-ready transaction_confirmation module
            # which will properly await the executor function
            handler_result = {
                "transaction_type": "confirmation",
                "callback_data": callback_data,
                "executor": execute_transaction
            }
            
            # Note: We delegate to transaction_confirmation.py which handles async properly
            return handler_result
                
        except ImportError as e:
            logger.error(f"Error importing transaction confirmation module: {e}")
            
            # Get the callback query to handle errors properly
            query = handler_context.get("callback_query")
            if query:
                # This will be handled downstream with proper await
                return {
                    "error_message": "⚠️ Transaction confirmation is not available.",
                    "error_type": "import_error"
                }
            return {"error": "Transaction confirmation not available"}
        except Exception as e:
            logger.error(f"Error handling transaction confirmation: {e}")
            return {"error": f"Error in transaction confirmation: {str(e)}"}
                
    # ---------- Position Operation Security ----------
    elif callback_data.startswith("position_confirm_") or callback_data.startswith("position_cancel_"):
        try:
            # Import position security module
            import position_security
            
            # Extract operation details
            action, operation, token = position_security.extract_operation_token(callback_data)
            
            if not action or not operation or not token:
                logger.error(f"Invalid position operation format: {callback_data}")
                return {"error": "Invalid position operation format"}
                
            # Get user ID safely from handler context
            user = handler_context.get("user")
            user_id = user.id if user else 0
            
            if not user_id:
                logger.error("Missing user ID in position operation")
                return {"error": "Missing user identification"}
                
            # Validate operation token
            is_valid, operation_details = position_security.validate_position_operation(token, user_id)
            
            if not is_valid:
                # Return error message that will be handled downstream with proper await
                return {
                    "error": operation_details.get('error', 'Security error: Invalid operation'),
                    "operation_type": "position",
                    "callback_data": callback_data
                }
                
            # Get position ID from operation details
            position_id = operation_details["position_id"]
            
            # Handle the operation based on action and operation type
            if action == "confirm":
                if operation == "close":
                    # Close position with enhanced security
                    import wallet_utils
                    
                    # Process position closing - this will be handled downstream
                    return {
                        "success": True,
                        "action": "position_close",
                        "position_id": position_id,
                        "operation_type": "position",
                        "message": f"Position {position_id} closed successfully with enhanced security"
                    }
                    
            elif action == "cancel":
                # Return cancellation message that will be handled downstream with proper await
                return {
                    "cancelled": True,
                    "operation_type": "position",
                    "message": f"Operation cancelled: {operation} position {position_id}"
                }
                
        except ImportError as e:
            logger.error(f"Error importing position security module: {e}")
            return {"error": "Position security not available"}
        except Exception as e:
            logger.error(f"Error in position operation: {e}")
            return {"error": f"Error in position operation: {str(e)}"}
                
    # Check if it's a navigation button by prefix
    is_navigation_button = any(callback_data.startswith(prefix) for prefix in [
        'menu_', 'explore_', 'account_', 'back_to_', 'profile_', 'simulate_', 
        'confirm_', 'cancel_', 'position_confirm_', 'position_cancel_'
    ])
    
    if is_navigation_button:
        # For navigation buttons, try to determine the menu target
        if callback_data.startswith('menu_'):
            menu_target = callback_data[5:]  # Remove 'menu_' prefix
            logger.info(f"Navigation recovery: Handling menu navigation to {menu_target}")
            return {
                "action": "menu_navigation",
                "menu": menu_target,
                "chat_id": chat_id,
                "recovered": True
            }
        elif callback_data.startswith('explore_'):
            action = callback_data[8:]  # Remove 'explore_' prefix
            logger.info(f"Navigation recovery: Handling explore action {action}")
            return {
                "action": "explore_action",
                "explore_type": action,
                "chat_id": chat_id,
                "recovered": True
            }
        elif callback_data.startswith('account_'):
            action = callback_data[8:]  # Remove 'account_' prefix
            logger.info(f"Navigation recovery: Handling account action {action}")
            return {
                "action": "account_action",
                "account_type": action,
                "chat_id": chat_id,
                "recovered": True
            }
        elif callback_data.startswith('back_to_'):
            target = callback_data[8:]  # Remove 'back_to_' prefix
            logger.info(f"Navigation recovery: Handling back navigation to {target}")
            return {
                "action": "navigation_back",
                "target": target,
                "chat_id": chat_id,
                "recovered": True
            }
    
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

def handle_explore_action(action: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle explore-related actions."""
    logger.info(f"Handling explore action: {action}")
    
    return {
        "action": "explore_action",
        "explore_type": action,
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
    
def handle_custom_simulation(context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle custom amount simulation request."""
    logger.info(f"Would request custom simulation amount")
    return {
        "action": "custom_simulation",
        "chat_id": context.get("chat_id")
    }
    
def handle_custom_amount(context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle custom investment amount request."""
    logger.info(f"Processing custom amount investment request")
    return {
        "action": "amount_custom",
        "chat_id": context.get("chat_id")
    }
    
def handle_investment_amount(amount: float, context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle specific investment amount selection."""
    logger.info(f"Processing investment amount selection: ${amount:.2f}")
    return {
        "action": "amount_selected",
        "amount": amount,
        "chat_id": context.get("chat_id")
    }

def handle_account_action(action: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle account-related actions."""
    logger.info(f"Handling account action: {action}")
    
    if action == "subscribe":
        return {
            "action": "subscribe",
            "chat_id": context.get("chat_id")
        }
    elif action == "unsubscribe":
        return {
            "action": "unsubscribe",
            "chat_id": context.get("chat_id")
        }
    elif action == "help":
        return {
            "action": "help",
            "chat_id": context.get("chat_id")
        }
    elif action == "status":
        return {
            "action": "status",
            "chat_id": context.get("chat_id")
        }
    elif action == "wallet":
        return {
            "action": "wallet",
            "chat_id": context.get("chat_id")
        }
    else:
        logger.warning(f"Unknown account action: {action}")
        return {
            "action": "unknown_account_action",
            "requested_action": action,
            "chat_id": context.get("chat_id")
        }

def handle_profile_action(profile_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """Handle profile-related actions."""
    logger.info(f"Handling profile action: {profile_type}")
    
    user_id = context.get('user_id', 0)
    chat_id = context.get('chat_id', 0)
    
    # First try using our specialized fixed profile handler if available
    try:
        # Import the fixed profile handler
        from fixed_profile_handler import handle_profile_selection
        logger.info(f"Using fixed profile handler for profile_{profile_type} from user {user_id}")
        
        # Use the specialized handler
        result = handle_profile_selection(user_id, chat_id, profile_type)
        
        # If we got a result, return it
        if result:
            if not result.get("action"):
                result["action"] = "profile"
            return result
    except ImportError:
        logger.warning("Fixed profile handler not available, falling back to button fix")
    
    # If we get here, either the import failed or the handler returned None
    # Try using our button fix system as fallback
    try:
        import button_fix
        logger.info(f"Using button fix system for profile_{profile_type} from user {user_id}")
        
        # Check if this is a rapid repeated click
        if not button_fix.is_wallet_button_click_allowed(user_id, f"profile_{profile_type}"):
            logger.info(f"Throttling profile button click for user {user_id}")
            return {
                "action": "profile",
                "profile_type": profile_type,
                "message": f"Processing your {profile_type} risk profile selection...",
                "chat_id": chat_id
            }
        
        # Apply standard response with fixes
        result = {
            "action": "profile",
            "profile_type": profile_type,
            "chat_id": chat_id
        }
        return button_fix.fix_wallet_button_action(result)
        
    except ImportError:
        # Standard response without fixes if button_fix not available
        logger.info("Button fix system not available for profile buttons")
        
        # Make sure we have a valid response with all required fields
        emoji = "🔴" if profile_type == "high-risk" else "🟢" if profile_type == "stable" else "🟡"
        return {
            "action": "profile",
            "profile_type": profile_type,
            "chat_id": chat_id,
            "message": f"{emoji} You've selected the {profile_type} risk profile.",
            "success": True
        }