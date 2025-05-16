"""
Fixed wallet connection handler for FiLot Telegram bot.

This module provides a specialized wallet handler that prevents the JavaScript error
"Cannot read properties of null (reading 'value')" by ensuring all return values
have properly initialized value properties.
"""

import logging
import traceback
import time
from typing import Dict, Any, Optional
import json
import base64

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Keep track of connection attempts to prevent rapid clicking
connection_attempts = {}  # {user_id: last_attempt_time}
CONNECTION_ATTEMPT_THRESHOLD = 2.0  # seconds

def handle_wallet_connection(user_id: int, chat_id: int) -> Dict[str, Any]:
    """
    Handle a wallet connection request with enhanced error handling.
    
    Args:
        user_id: The Telegram user ID
        chat_id: The Telegram chat ID
        
    Returns:
        Dict with response data
    """
    try:
        logger.info(f"User {user_id} requested wallet connection")
        
        # Check for rate limiting (prevent rapid clicks)
        current_time = time.time()
        if user_id in connection_attempts:
            time_diff = current_time - connection_attempts[user_id]
            
            # If clicking too rapidly, throttle
            if time_diff < CONNECTION_ATTEMPT_THRESHOLD:
                logger.warning(f"User {user_id} clicking wallet connect button too rapidly ({time_diff:.2f}s)")
                return {
                    "success": False,
                    "action": "error",
                    "message": "Please wait a moment before trying to connect again.",
                    "throttled": True,
                    "chat_id": chat_id
                }
        
        # Record this attempt
        connection_attempts[user_id] = current_time
        
        # Generate wallet connection data
        connection_data = generate_connection_data(user_id)
        
        if isinstance(connection_data, dict) and connection_data.get("error"):
            logger.error(f"Error generating wallet connection: {connection_data.get('error')}")
            return {
                "success": False,
                "action": "error",
                "message": connection_data.get("error", "Could not generate wallet connection."),
                "chat_id": chat_id,
                "error_source": "wallet_connection_generator"
            }
            
        # Create the success response
        result = {
            "success": True,
            "action": "connect_wallet",
            "message": "Please connect your wallet using the link below.",
            "connection_data": connection_data,
            "chat_id": chat_id
        }
        
        # Ensure the value field exists in connection_data to prevent JavaScript error
        if "connection_data" in result and isinstance(result["connection_data"], dict):
            if "value" not in result["connection_data"]:
                result["connection_data"]["value"] = {
                    "address": None,
                    "balance": 0,
                    "status": "pending"
                }
        
        logger.info(f"Generated wallet connection for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error handling wallet connection: {e}")
        logger.error(traceback.format_exc())
        
        # Fallback message if something goes wrong
        return {
            "success": False,
            "action": "error",
            "message": "Sorry, there was an error connecting to your wallet. Please try again in a moment.",
            "error": str(e),
            "chat_id": chat_id,
            # Add a value field to prevent JavaScript error
            "connection_data": {
                "error": str(e),
                "value": {
                    "address": None,
                    "balance": 0,
                    "status": "error"
                }
            }
        }

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
                "retry_after": int(CONNECTION_ATTEMPT_THRESHOLD - time_since_last) + 1,
                # Ensure value field exists to prevent JavaScript error
                "value": {
                    "address": None,
                    "balance": 0,
                    "status": "pending"
                }
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
            
        # Ensure the value field exists to prevent JavaScript error
        if "value" not in connection_data:
            connection_data["value"] = {
                "address": None,
                "balance": 0,
                "status": "pending"
            }
            
        return connection_data
        
    except Exception as e:
        logger.error(f"Error generating wallet connection: {e}")
        logger.error(traceback.format_exc())
        return {
            "error": "Could not generate wallet connection",
            "details": str(e),
            # Ensure value field exists to prevent JavaScript error
            "value": {
                "address": None,
                "balance": 0,
                "status": "error"
            }
        }

def handle_wallet_disconnection(user_id: int, chat_id: int) -> Dict[str, Any]:
    """
    Handle a wallet disconnection request with enhanced error handling.
    
    Args:
        user_id: The Telegram user ID
        chat_id: The Telegram chat ID
        
    Returns:
        Dict with response data
    """
    try:
        logger.info(f"User {user_id} requested wallet disconnection")
        
        # Try to disconnect using walletconnect_utils
        try:
            import walletconnect_utils
            if hasattr(walletconnect_utils, 'kill_walletconnect_session'):
                sessions = walletconnect_utils.get_user_walletconnect_sessions(user_id)
                if sessions:
                    for session_id in sessions:
                        walletconnect_utils.kill_walletconnect_session(session_id)
                    logger.info(f"Disconnected {len(sessions)} wallet sessions for user {user_id}")
        except ImportError:
            pass
            
        # Try to disconnect using wallet_utils
        try:
            import wallet_utils
            if hasattr(wallet_utils, 'disconnect_wallet'):
                wallet_utils.disconnect_wallet(user_id)
                logger.info(f"Disconnected wallet for user {user_id} using wallet_utils")
        except ImportError:
            pass
            
        # Create the success response
        return {
            "success": True,
            "action": "disconnect_wallet",
            "message": "Your wallet has been disconnected.",
            "chat_id": chat_id
        }
        
    except Exception as e:
        logger.error(f"Error handling wallet disconnection: {e}")
        logger.error(traceback.format_exc())
        
        # Fallback message if something goes wrong
        return {
            "success": False,
            "action": "error",
            "message": "Sorry, there was an error disconnecting your wallet. Please try again in a moment.",
            "error": str(e),
            "chat_id": chat_id
        }

def cleanup_connection_data(max_age: int = 3600) -> None:
    """
    Clean up old connection attempt data.
    
    Args:
        max_age: Maximum age in seconds to keep connection data
    """
    current_time = time.time()
    
    for user_id in list(connection_attempts.keys()):
        timestamp = connection_attempts[user_id]
        if current_time - timestamp > max_age:
            del connection_attempts[user_id]
            
    logger.debug(f"Cleaned up connection attempts data, now tracking {len(connection_attempts)} users")