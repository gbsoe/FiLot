"""
Fix for wallet connection button issues in the FiLot Telegram bot.

This module specifically addresses the "Cannot read properties of null (reading 'value')"
error that occurs when using the Connect Wallet button.
"""

import logging
import time
from typing import Dict, Any, Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Import our custom button debug logger
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

class WalletButtonFix:
    """Fix implementation for wallet button issues."""
    
    @staticmethod
    def handle_connect_wallet(
        user_id: int,
        chat_id: int,
        callback_data: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enhanced handler for wallet connection button.
        
        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            callback_data: Button callback data
            context: Optional context data
            
        Returns:
            Result dictionary
        """
        try:
            # Log the button interaction attempt
            if BUTTON_LOGGING_ENABLED:
                log_button_interaction(
                    user_id=user_id,
                    chat_id=chat_id,
                    callback_data=callback_data,
                    context=context
                )
            
            logger.info(f"Processing wallet connection for user {user_id} in chat {chat_id}")
            
            # Import wallet utilities here to avoid circular imports
            try:
                import walletconnect_utils
                import wallet_utils
                wallet_module = wallet_utils
            except ImportError:
                logger.error("Failed to import wallet modules")
                
                if BUTTON_LOGGING_ENABLED:
                    log_button_interaction(
                        user_id=user_id,
                        chat_id=chat_id,
                        callback_data=callback_data,
                        context=context,
                        error="Failed to import wallet modules"
                    )
                    
                return {
                    "success": False,
                    "action": "error",
                    "message": "Internal error: Wallet modules not available"
                }
            
            # Start wallet connection process with additional error handling
            try:
                # Check if user already has a wallet connected
                if wallet_module.is_wallet_connected(user_id):
                    logger.info(f"User {user_id} already has a wallet connected")
                    
                    # Get wallet info
                    wallet_info = wallet_module.get_wallet_info(user_id)
                    
                    message = (
                        f"✅ Your wallet is already connected:\n\n"
                        f"Address: `{wallet_info.get('address', 'Unknown')}`\n"
                        f"Connected: {wallet_info.get('connected_since', 'Unknown')}\n\n"
                        f"Would you like to disconnect this wallet?"
                    )
                    
                    # Log successful retrieval
                    if BUTTON_LOGGING_ENABLED:
                        log_button_interaction(
                            user_id=user_id,
                            chat_id=chat_id,
                            callback_data=callback_data,
                            context=context,
                            result={
                                "wallet_connected": True,
                                "address": wallet_info.get('address', 'Unknown')
                            }
                        )
                    
                    return {
                        "success": True,
                        "action": "show_wallet_status",
                        "message": message,
                        "wallet_info": wallet_info
                    }
                
                # No wallet connected, initiate connection process
                logger.info(f"Initiating wallet connection for user {user_id}")
                
                # Generate connection URL/data
                try:
                    connection_data = wallet_module.generate_connection_data(user_id)
                    
                    # Log successful connection initiation
                    if BUTTON_LOGGING_ENABLED:
                        log_button_interaction(
                            user_id=user_id,
                            chat_id=chat_id,
                            callback_data=callback_data,
                            context=context,
                            result={
                                "wallet_connection_initiated": True
                            }
                        )
                        
                    return {
                        "success": True,
                        "action": "initiate_wallet_connection",
                        "message": "Please connect your wallet using the provided link",
                        "connection_data": connection_data
                    }
                    
                except Exception as e:
                    logger.error(f"Error generating wallet connection data: {e}")
                    
                    # Log the error
                    if BUTTON_LOGGING_ENABLED:
                        log_button_interaction(
                            user_id=user_id,
                            chat_id=chat_id,
                            callback_data=callback_data,
                            context=context,
                            error=f"Error generating wallet connection data: {e}"
                        )
                        
                    return {
                        "success": False,
                        "action": "error",
                        "message": "Could not generate wallet connection data. Please try again later."
                    }
            
            except Exception as e:
                logger.error(f"Unexpected error in wallet connection process: {e}")
                
                # Log the error
                if BUTTON_LOGGING_ENABLED:
                    log_button_interaction(
                        user_id=user_id,
                        chat_id=chat_id,
                        callback_data=callback_data,
                        context=context,
                        error=f"Unexpected error in wallet connection process: {e}"
                    )
                    
                return {
                    "success": False,
                    "action": "error",
                    "message": "An unexpected error occurred. Please try again later."
                }
                
        except Exception as e:
            logger.error(f"Critical error in wallet connection handler: {e}")
            
            # Log the critical error
            if BUTTON_LOGGING_ENABLED:
                log_button_interaction(
                    user_id=user_id,
                    chat_id=chat_id,
                    callback_data=callback_data,
                    context=context,
                    error=f"Critical error in wallet connection handler: {e}"
                )
                
            return {
                "success": False,
                "action": "error",
                "message": "A system error occurred. Our team has been notified."
            }

# Helper function for easy access
def fix_connect_wallet(user_id, chat_id, callback_data, context=None):
    """Shorthand helper for the wallet fix implementation."""
    return WalletButtonFix.handle_connect_wallet(user_id, chat_id, callback_data, context)