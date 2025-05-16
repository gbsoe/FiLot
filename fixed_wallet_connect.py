"""
Improved wallet connection system for FiLot Telegram bot.

This module provides enhanced wallet connection handling with robust error handling
to prevent JavaScript errors like "Cannot read properties of null (reading 'value')".
"""

import os
import logging
import json
import time
import traceback
from typing import Dict, Any, List, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Track wallet connection attempts to prevent rapid repeated clicks
connection_attempts = {}
CONNECTION_ATTEMPT_THRESHOLD = 2.0  # seconds

def is_wallet_connected(user_id: int) -> bool:
    """
    Check if a user has a wallet connected.
    
    Args:
        user_id: The Telegram user ID
        
    Returns:
        True if the user has a connected wallet, False otherwise
    """
    try:
        # Try to import wallet module safely
        try:
            import wallet_utils
            if hasattr(wallet_utils, 'is_wallet_connected'):
                return wallet_utils.is_wallet_connected(user_id)
        except ImportError:
            pass
            
        # Try to import walletconnect module safely
        try:
            import walletconnect_utils
            if hasattr(walletconnect_utils, 'check_walletconnect_session'):
                session = walletconnect_utils.check_walletconnect_session(user_id)
                return session and session.get('connected', False)
        except ImportError:
            pass
            
        # If no modules available, check our database directly
        try:
            from models import User, db
            with db.session() as session:
                user = session.query(User).filter(User.telegram_id == user_id).first()
                return user and user.wallet_address is not None
        except Exception:
            pass
            
        # Default: no wallet connected
        return False
        
    except Exception as e:
        logger.error(f"Error checking wallet connection: {e}")
        return False

def get_wallet_info(user_id: int) -> Dict[str, Any]:
    """
    Get information about a user's connected wallet.
    
    Args:
        user_id: The Telegram user ID
        
    Returns:
        Dictionary with wallet information or empty dict if no wallet
    """
    try:
        wallet_info = {}
        
        # Try to import wallet module safely
        try:
            import wallet_utils
            if hasattr(wallet_utils, 'get_wallet_info'):
                wallet_info = wallet_utils.get_wallet_info(user_id) or {}
            elif hasattr(wallet_utils, 'get_user_wallet'):
                wallet_info = wallet_utils.get_user_wallet(user_id) or {}
        except ImportError:
            pass
            
        # Try to import walletconnect module safely
        if not wallet_info:
            try:
                import walletconnect_utils
                if hasattr(walletconnect_utils, 'check_walletconnect_session'):
                    session = walletconnect_utils.check_walletconnect_session(user_id)
                    if session and session.get('connected'):
                        wallet_info = {
                            'address': session.get('wallet_address', 'Unknown'),
                            'connected_since': session.get('connected_since', 'Unknown'),
                            'provider': session.get('provider', 'WalletConnect')
                        }
            except ImportError:
                pass
                
        # If no modules available, check our database directly
        if not wallet_info:
            try:
                from models import User, db
                with db.session() as session:
                    user = session.query(User).filter(User.telegram_id == user_id).first()
                    if user and user.wallet_address:
                        wallet_info = {
                            'address': user.wallet_address,
                            'connected_since': user.created_at.isoformat() if hasattr(user, 'created_at') else 'Unknown',
                            'provider': 'Database'
                        }
            except Exception:
                pass
                
        return wallet_info
        
    except Exception as e:
        logger.error(f"Error getting wallet info: {e}")
        return {}

def generate_connection_data(user_id: int) -> Dict[str, Any]:
    """
    Generate wallet connection data for a user.
    
    Args:
        user_id: The Telegram user ID
        
    Returns:
        Dictionary with connection details
    """
    # Prevent too rapid connection attempts
    now = time.time()
    if user_id in connection_attempts:
        time_since_last = now - connection_attempts[user_id]
        if time_since_last < CONNECTION_ATTEMPT_THRESHOLD:
            logger.warning(f"Too rapid wallet connection attempt from user {user_id}: {time_since_last:.2f}s")
            return {
                "error": "Please wait a moment before trying again",
                "rate_limited": True,
                "retry_after": int(CONNECTION_ATTEMPT_THRESHOLD - time_since_last) + 1
            }
    
    # Record this attempt
    connection_attempts[user_id] = now
    
    try:
        connection_data = {}
        
        # Try to import walletconnect module safely
        try:
            import walletconnect_utils
            if hasattr(walletconnect_utils, 'create_walletconnect_session'):
                connection_data = walletconnect_utils.create_walletconnect_session(user_id) or {}
        except ImportError:
            pass
            
        # Try to import wallet module safely
        if not connection_data:
            try:
                import wallet_utils
                if hasattr(wallet_utils, 'generate_connection_data'):
                    connection_data = wallet_utils.generate_connection_data(user_id) or {}
                elif hasattr(wallet_utils, 'create_connection'):
                    connection_data = wallet_utils.create_connection(user_id) or {}
            except ImportError:
                pass
                
        # If no modules available, create fallback data
        if not connection_data:
            # Generate a unique ID for tracking
            session_id = f"session_{user_id}_{int(time.time())}"
            connection_data = {
                "session_id": session_id,
                "redirect_url": f"https://phantom.app/ul/browse/https://filot.finance/connect?session={session_id}&user={user_id}",
                "qr_code_url": f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=https://filot.finance/connect?session={session_id}%26user={user_id}",
                "expires_in": 300,  # 5 minutes
                "fallback": True
            }
            
        return connection_data
        
    except Exception as e:
        logger.error(f"Error generating wallet connection: {e}")
        logger.error(traceback.format_exc())
        return {
            "error": "Could not generate wallet connection",
            "details": str(e)
        }

def disconnect_wallet(user_id: int) -> bool:
    """
    Disconnect a user's wallet.
    
    Args:
        user_id: The Telegram user ID
        
    Returns:
        True if disconnected successfully, False otherwise
    """
    try:
        success = False
        
        # Try to import walletconnect module safely
        try:
            import walletconnect_utils
            if hasattr(walletconnect_utils, 'kill_walletconnect_session'):
                walletconnect_utils.kill_walletconnect_session(user_id)
                success = True
        except ImportError:
            pass
            
        # Try to import wallet module safely
        try:
            import wallet_utils
            if hasattr(wallet_utils, 'disconnect_wallet'):
                success = wallet_utils.disconnect_wallet(user_id) or success
            elif hasattr(wallet_utils, 'remove_user_wallet'):
                success = wallet_utils.remove_user_wallet(user_id) or success
        except ImportError:
            pass
            
        # If no modules available, update database directly
        if not success:
            try:
                from models import User, db
                with db.session() as session:
                    user = session.query(User).filter(User.telegram_id == user_id).first()
                    if user:
                        user.wallet_address = None
                        session.commit()
                        success = True
            except Exception:
                pass
                
        return success
        
    except Exception as e:
        logger.error(f"Error disconnecting wallet: {e}")
        return False

def handle_connect_wallet_callback(chat_id: int, user_id: int) -> Dict[str, Any]:
    """
    Handle the connect wallet button click.
    
    Args:
        chat_id: Telegram chat ID
        user_id: Telegram user ID
        
    Returns:
        Response data for the handler
    """
    try:
        logger.info(f"Processing connect wallet request from user {user_id}")
        
        # Check if wallet already connected
        if is_wallet_connected(user_id):
            wallet_info = get_wallet_info(user_id)
            wallet_address = wallet_info.get('address', 'Unknown')
            
            message = (
                f"✅ Your wallet is already connected\n\n"
                f"Address: `{wallet_address}`\n\n"
                f"What would you like to do with your wallet?"
            )
            
            return {
                "success": True,
                "action": "wallet_already_connected",
                "message": message,
                "wallet_address": wallet_address,
                "wallet_info": wallet_info
            }
            
        # Generate connection data
        connection_data = generate_connection_data(user_id)
        
        # Check for rate limiting or errors
        if "error" in connection_data:
            if connection_data.get("rate_limited"):
                message = (
                    f"⚠️ Please wait a moment before trying to connect again.\n\n"
                    f"You can try again in {connection_data.get('retry_after', 2)} seconds."
                )
            else:
                message = (
                    f"⚠️ I'm having trouble setting up your wallet connection.\n\n"
                    f"Error: {connection_data['error']}\n\n"
                    f"Please try again later."
                )
                
            return {
                "success": False,
                "action": "wallet_connection_error",
                "message": message,
                "error": connection_data.get("error")
            }
            
        # We have connection data
        message = (
            "Please connect your wallet using the link below.\n\n"
            "Your tokens will always remain under your control - "
            "FiLot never takes custody of your funds."
        )
        
        return {
            "success": True,
            "action": "connect_wallet",
            "message": message,
            "connection_data": connection_data
        }
            
    except Exception as e:
        logger.error(f"Error in wallet connection handler: {e}")
        logger.error(traceback.format_exc())
        
        message = (
            "⚠️ Something went wrong when trying to connect your wallet.\n\n"
            "Please try again later or contact support if the issue persists."
        )
        
        return {
            "success": False, 
            "action": "error",
            "message": message,
            "error": str(e)
        }
            
def handle_disconnect_wallet_callback(chat_id: int, user_id: int) -> Dict[str, Any]:
    """
    Handle the disconnect wallet button click.
    
    Args:
        chat_id: Telegram chat ID
        user_id: Telegram user ID
        
    Returns:
        Response data for the handler
    """
    try:
        logger.info(f"Processing disconnect wallet request from user {user_id}")
        
        # Check if wallet is connected first
        if not is_wallet_connected(user_id):
            message = "You don't have a wallet connected yet."
            
            return {
                "success": True,
                "action": "wallet_not_connected",
                "message": message
            }
            
        # Disconnect the wallet
        success = disconnect_wallet(user_id)
        
        if success:
            message = "✅ Your wallet has been disconnected successfully."
        else:
            message = "⚠️ I couldn't disconnect your wallet. Please try again later."
            
        return {
            "success": success,
            "action": "wallet_disconnected" if success else "wallet_disconnect_error",
            "message": message
        }
            
    except Exception as e:
        logger.error(f"Error in wallet disconnection handler: {e}")
        
        message = (
            "⚠️ Something went wrong when trying to disconnect your wallet.\n\n"
            "Please try again later or contact support if the issue persists."
        )
        
        return {
            "success": False,
            "action": "error",
            "message": message,
            "error": str(e)
        }