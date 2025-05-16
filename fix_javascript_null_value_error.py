"""
Fix for JavaScript "Cannot read properties of null (reading 'value')" error in FiLot.

This script provides specialized wallet, profile, and menu button handlers
that protect against JavaScript errors by properly initializing values
and validating all data before access.
"""

import logging
import traceback
import time
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Storage for safety checks
checked_values = {}  # {key: {"timestamp": time, "value": data}}
CHECK_TTL = 300  # Time to live for checks (5 minutes)

def ensure_value_exists(key: str, default_value: Any = None) -> Any:
    """
    Ensure a value exists for a key, initializing with default if needed.
    
    Args:
        key: The key to check
        default_value: Default value to use if none exists
        
    Returns:
        The existing or default value
    """
    current_time = time.time()
    
    # Clean expired values
    keys_to_remove = []
    for k in checked_values:
        if current_time - checked_values[k].get("timestamp", 0) > CHECK_TTL:
            keys_to_remove.append(k)
            
    for k in keys_to_remove:
        del checked_values[k]
    
    # Get or create value
    if key not in checked_values:
        checked_values[key] = {
            "timestamp": current_time,
            "value": default_value
        }
        
    return checked_values[key]["value"]

def fix_javascript_null_references(user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fix any potential JavaScript null references by ensuring all
    required values are present.
    
    Args:
        user_id: The user ID
        data: The data dictionary to fix
        
    Returns:
        The fixed data dictionary
    """
    try:
        # Ensure we have a value for user_id
        user_key = f"user_{user_id}"
        user_data = ensure_value_exists(user_key, {
            "profile": "moderate",
            "wallet": None,
            "balance": 0,
            "session": None
        })
        
        # Make sure all expected fields exist in the data
        if "success" not in data:
            data["success"] = True
            
        if "action" not in data:
            data["action"] = "default_action"
            
        if "message" not in data:
            data["message"] = "Processing your request..."
            
        # Specifically fix wallet data which is causing the JS error
        if data.get("action") == "connect_wallet" and "connection_data" not in data:
            logger.warning(f"Missing connection_data for connect_wallet action for user {user_id}")
            
            # Create a safe default connection data object
            data["connection_data"] = {
                "session_id": f"session_{user_id}_{int(time.time())}",
                "redirect_url": "#",
                "qr_code_url": "https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=https://filot.finance/fallback",
                "expires_in": 300,
                "fallback": True
            }
            
        # Ensure connection_data has all required fields if it exists
        if "connection_data" in data:
            conn_data = data["connection_data"]
            
            # Make sure session_id exists
            if "session_id" not in conn_data:
                conn_data["session_id"] = f"session_{user_id}_{int(time.time())}"
                
            # Make sure redirect_url exists
            if "redirect_url" not in conn_data:
                conn_data["redirect_url"] = "#"
                
            # Make sure qr_code_url exists
            if "qr_code_url" not in conn_data:
                conn_data["qr_code_url"] = "https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=https://filot.finance/fallback"
                
            # Make sure expires_in exists
            if "expires_in" not in conn_data:
                conn_data["expires_in"] = 300
        
        # Ensure profile_type exists for profile action
        if data.get("action") == "profile" and "profile_type" not in data:
            data["profile_type"] = "moderate"  # Default to moderate risk
            
        # Add a version indicator to help with debugging
        data["handler_version"] = "js_null_fix_v1"
            
        return data
        
    except Exception as e:
        logger.error(f"Error in fix_javascript_null_references: {e}")
        logger.error(traceback.format_exc())
        
        # Return original data as fallback
        return data

def fix_wallet_connection_data(user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fix wallet connection data specifically, which is likely causing the null.value JS error.
    
    Args:
        user_id: The user ID
        data: The data dictionary to fix
        
    Returns:
        The fixed data dictionary
    """
    try:
        # Safety checks for wallet connect action
        if data.get("action") == "connect_wallet":
            # If we're missing connection_data, create a fallback
            if "connection_data" not in data or not data["connection_data"]:
                logger.warning(f"Missing connection_data for connect_wallet, creating fallback for user {user_id}")
                
                session_id = f"session_{user_id}_{int(time.time())}"
                data["connection_data"] = {
                    "session_id": session_id,
                    "redirect_url": f"https://phantom.app/ul/browse/https://filot.finance/connect?session={session_id}&user={user_id}",
                    "qr_code_url": f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=https://filot.finance/connect?session={session_id}%26user={user_id}",
                    "expires_in": 300,
                    "fallback": True,
                    "wallet_address": None,
                    "balance": 0
                }
            else:
                # Make sure connection_data is a dictionary and not some other type
                if not isinstance(data["connection_data"], dict):
                    logger.warning(f"connection_data is not a dictionary for user {user_id}, fixing")
                    
                    session_id = f"session_{user_id}_{int(time.time())}"
                    data["connection_data"] = {
                        "session_id": session_id,
                        "redirect_url": f"https://phantom.app/ul/browse/https://filot.finance/connect?session={session_id}&user={user_id}",
                        "qr_code_url": f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=https://filot.finance/connect?session={session_id}%26user={user_id}",
                        "expires_in": 300,
                        "fallback": True,
                        "wallet_address": None,
                        "balance": 0
                    }
                else:
                    # Ensure all required fields exist in connection_data
                    conn_data = data["connection_data"]
                    
                    if "session_id" not in conn_data or not conn_data["session_id"]:
                        conn_data["session_id"] = f"session_{user_id}_{int(time.time())}"
                        
                    if "redirect_url" not in conn_data or not conn_data["redirect_url"]:
                        session_id = conn_data["session_id"]
                        conn_data["redirect_url"] = f"https://phantom.app/ul/browse/https://filot.finance/connect?session={session_id}&user={user_id}"
                        
                    if "qr_code_url" not in conn_data or not conn_data["qr_code_url"]:
                        session_id = conn_data["session_id"]
                        conn_data["qr_code_url"] = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=https://filot.finance/connect?session={session_id}%26user={user_id}"
                        
                    if "expires_in" not in conn_data:
                        conn_data["expires_in"] = 300
                        
                    # Add more safety fields that JavaScript might be trying to access
                    if "wallet_address" not in conn_data:
                        conn_data["wallet_address"] = None
                        
                    if "balance" not in conn_data:
                        conn_data["balance"] = 0
                        
                    # Ensure the value field exists to prevent "Cannot read properties of null (reading 'value')"
                    if "value" not in conn_data:
                        conn_data["value"] = {
                            "address": None,
                            "balance": 0,
                            "status": "pending"
                        }
                        
        return data
        
    except Exception as e:
        logger.error(f"Error in fix_wallet_connection_data: {e}")
        logger.error(traceback.format_exc())
        
        # Return original data as fallback but add a minimal value field
        if "connection_data" in data and isinstance(data["connection_data"], dict):
            if "value" not in data["connection_data"]:
                data["connection_data"]["value"] = {
                    "address": None,
                    "balance": 0,
                    "status": "pending"
                }
                
        return data

def apply_all_fixes(user_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply all available JavaScript null value error fixes.
    
    Args:
        user_id: The user ID
        data: The data dictionary to fix
        
    Returns:
        The fixed data dictionary
    """
    data = fix_javascript_null_references(user_id, data)
    data = fix_wallet_connection_data(user_id, data)
    
    # Log what we've done for debugging
    logger.info(f"Applied JavaScript null value error fixes for user {user_id}, action: {data.get('action')}")
    
    return data