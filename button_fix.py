"""
Button fix module for solving JavaScript errors with the wallet connect button.
"""

import logging
import time
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Tracking for wallet button clicks
wallet_button_clicks = {}
CLICK_THRESHOLD = 0.5  # seconds
CLICK_EXPIRE = 60.0  # seconds

class ButtonFix:
    """
    Implements fixes for common button issues.
    """
    
    @staticmethod
    def is_wallet_button_click_allowed(user_id: int, button_name: str = "connect_wallet") -> bool:
        """
        Check if a wallet button click should be allowed based on rate limiting.
        
        Args:
            user_id: The user's ID
            button_name: The name of the button being clicked
            
        Returns:
            True if click should be allowed, False if too frequent
        """
        now = time.time()
        button_key = f"{user_id}_{button_name}"
        
        # Clean up expired clicks first
        for key in list(wallet_button_clicks.keys()):
            if now - wallet_button_clicks[key] > CLICK_EXPIRE:
                del wallet_button_clicks[key]
        
        # Check if this button was recently clicked
        if button_key in wallet_button_clicks:
            time_since_last = now - wallet_button_clicks[button_key]
            if time_since_last < CLICK_THRESHOLD:
                logger.info(f"Throttling wallet button click: {button_key}, {time_since_last:.2f}s since last click")
                return False
        
        # Record this click
        wallet_button_clicks[button_key] = now
        return True
    
    @staticmethod
    def get_safe_wallet_connection(user_id: int) -> Dict[str, Any]:
        """
        Get wallet connection data with safety checks to prevent JavaScript errors.
        
        Args:
            user_id: The user's ID
            
        Returns:
            Dictionary with connection data
        """
        try:
            # First check if we should allow this click
            if not ButtonFix.is_wallet_button_click_allowed(user_id):
                return {
                    "rate_limited": True,
                    "error": "Please wait a moment before trying again",
                    "message": "Please wait a moment before trying to connect again."
                }
            
            # First try our enhanced connection system
            try:
                from fixed_wallet_connect import generate_connection_data
                return generate_connection_data(user_id)
            except (ImportError, AttributeError):
                pass
            
            # Fall back to standard wallet utilities
            try:
                import wallet_utils
                if hasattr(wallet_utils, 'generate_connection_data'):
                    data = wallet_utils.generate_connection_data(user_id)
                    if not data:
                        return {"error": "Failed to generate wallet connection data"}
                    return data
                else:
                    logger.error("wallet_utils doesn't have generate_connection_data method")
            except ImportError:
                logger.error("wallet_utils module not found")
            
            # Try walletconnect as last resort
            try:
                import walletconnect_utils
                if hasattr(walletconnect_utils, 'create_walletconnect_session'):
                    data = walletconnect_utils.create_walletconnect_session(user_id)
                    if not data:
                        return {"error": "Failed to create WalletConnect session"}
                    return data
                else:
                    logger.error("walletconnect_utils doesn't have create_walletconnect_session method")
            except ImportError:
                logger.error("walletconnect_utils module not found")
            
            return {"error": "No wallet connection system is available"}
            
        except Exception as e:
            logger.error(f"Error getting wallet connection: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def fix_wallet_button_action(response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fix common issues with wallet button response data to prevent JavaScript errors.
        
        Args:
            response_data: The response data dictionary
            
        Returns:
            Fixed response data
        """
        try:
            # Check if we need to fix anything
            if not response_data:
                return {"error": "Empty wallet connection response"}
            
            # Make sure we have a valid action
            if "action" not in response_data:
                response_data["action"] = "connect_wallet"
            
            # Make sure session_id is always a string if present
            if "session_id" in response_data and response_data["session_id"] is not None:
                response_data["session_id"] = str(response_data["session_id"])
            
            # Fix missing connection_data
            if response_data.get("action") == "connect_wallet" and "connection_data" not in response_data:
                response_data["connection_data"] = {"error": "No connection data available"}
            
            # Fix null values in connection_data
            if "connection_data" in response_data and response_data["connection_data"] is not None:
                conn_data = response_data["connection_data"]
                
                # Ensure these fields exist with default values if needed
                required_fields = {
                    "session_id": lambda: "session_" + str(int(time.time())),
                    "redirect_url": lambda: "#",
                    "qr_code_url": lambda: "#",
                    "expires_in": lambda: 300
                }
                
                for field, default_fn in required_fields.items():
                    if field not in conn_data or conn_data[field] is None:
                        conn_data[field] = default_fn()
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error fixing wallet button response: {e}")
            return {
                "action": "error",
                "message": "Something went wrong with wallet connection. Please try again later.",
                "error": str(e)
            }

# Expose key functions at module level
is_wallet_button_click_allowed = ButtonFix.is_wallet_button_click_allowed
get_safe_wallet_connection = ButtonFix.get_safe_wallet_connection
fix_wallet_button_action = ButtonFix.fix_wallet_button_action