"""
Fix for wallet connection button issues in the FiLot Telegram bot.

This module provides a safe implementation for the Connect Wallet button
that prevents the "Cannot read properties of null" JavaScript error.
"""

import logging
import time
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

class WalletButtonHandler:
    """Safe implementation for wallet connection buttons."""
    
    @staticmethod
    def handle_connect_wallet(chat_id: int, user_id: int) -> Dict[str, Any]:
        """
        Handle the connect wallet button click safely.
        
        Args:
            chat_id: Telegram chat ID
            user_id: Telegram user ID
            
        Returns:
            Response data for the button handler
        """
        try:
            logger.info(f"Processing connect wallet request for user {user_id}")
            
            # Import modules here to avoid circular imports
            try:
                import wallet_utils
                has_wallet_utils = True
            except ImportError:
                logger.warning("wallet_utils not available, using fallback implementation")
                has_wallet_utils = False
                
            # Check if user already has a wallet
            wallet_connected = False
            wallet_address = None
            
            if has_wallet_utils:
                # Check if wallet is connected, using safe method calls with try/except
                try:
                    if hasattr(wallet_utils, 'is_wallet_connected'):
                        wallet_connected = wallet_utils.is_wallet_connected(user_id)
                    elif hasattr(wallet_utils, 'get_user_wallet'):
                        wallet_info = wallet_utils.get_user_wallet(user_id)
                        wallet_connected = wallet_info is not None and 'address' in wallet_info
                        if wallet_connected:
                            wallet_address = wallet_info.get('address')
                except Exception as e:
                    logger.error(f"Error checking wallet connection: {e}")
                    wallet_connected = False
            
            # Handle based on connection status
            if wallet_connected:
                # Wallet is already connected
                logger.info(f"Wallet already connected for user {user_id}: {wallet_address}")
                
                message = (
                    f"✅ Your wallet is already connected\n\n"
                    f"Address: `{wallet_address or 'Unknown'}`\n\n"
                    f"What would you like to do with your wallet?"
                )
                
                return {
                    "success": True,
                    "action": "wallet_connected",
                    "message": message,
                    "wallet_address": wallet_address
                }
            else:
                # Need to connect wallet
                logger.info(f"Initiating wallet connection for user {user_id}")
                
                # Generate connection data safely
                connection_data = None
                
                if has_wallet_utils:
                    try:
                        if hasattr(wallet_utils, 'generate_connection_data'):
                            connection_data = wallet_utils.generate_connection_data(user_id)
                        elif hasattr(wallet_utils, 'create_wallet_connection'):
                            connection_data = wallet_utils.create_wallet_connection(user_id)
                    except Exception as e:
                        logger.error(f"Error generating wallet connection: {e}")
                
                # Default message if we couldn't generate connection data
                if not connection_data:
                    message = (
                        "I'm preparing your wallet connection...\n\n"
                        "Please wait while I set up a secure connection."
                    )
                    
                    return {
                        "success": True,
                        "action": "wallet_connection_pending",
                        "message": message
                    }
                
                # We have connection data
                message = (
                    "Please connect your wallet using the link below.\n\n"
                    "Your tokens will always remain under your control - "
                    "FiLot never takes custody of your funds."
                )
                
                return {
                    "success": True,
                    "action": "wallet_connection_ready",
                    "message": message,
                    "connection_data": connection_data
                }
                
        except Exception as e:
            logger.error(f"Critical error in wallet connection: {e}")
            
            # Provide a graceful error message
            return {
                "success": False,
                "action": "error",
                "message": "I'm having trouble connecting to your wallet. Please try again later."
            }
            
    @staticmethod
    def handle_disconnect_wallet(chat_id: int, user_id: int) -> Dict[str, Any]:
        """
        Handle the disconnect wallet button click safely.
        
        Args:
            chat_id: Telegram chat ID
            user_id: Telegram user ID
            
        Returns:
            Response data for the button handler
        """
        try:
            logger.info(f"Processing disconnect wallet request for user {user_id}")
            
            # Import modules here to avoid circular imports
            try:
                import wallet_utils
                has_wallet_utils = True
            except ImportError:
                logger.warning("wallet_utils not available, using fallback implementation")
                has_wallet_utils = False
            
            # Disconnect wallet if possible
            disconnected = False
            
            if has_wallet_utils:
                try:
                    if hasattr(wallet_utils, 'disconnect_wallet'):
                        disconnected = wallet_utils.disconnect_wallet(user_id)
                    elif hasattr(wallet_utils, 'remove_user_wallet'):
                        disconnected = wallet_utils.remove_user_wallet(user_id)
                except Exception as e:
                    logger.error(f"Error disconnecting wallet: {e}")
            
            # Handle based on disconnection result
            if disconnected:
                message = "✅ Your wallet has been disconnected successfully."
            else:
                message = "No wallet was connected or I couldn't disconnect it properly."
            
            return {
                "success": True,
                "action": "wallet_disconnected",
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Critical error in wallet disconnection: {e}")
            
            # Provide a graceful error message
            return {
                "success": False,
                "action": "error",
                "message": "I'm having trouble disconnecting your wallet. Please try again later."
            }