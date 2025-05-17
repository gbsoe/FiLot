#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Emergency fix for profile buttons
"""

import sqlite3
import logging
import traceback
from typing import Dict, Any, Optional, Tuple

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
DB_FILE = "filot_bot.db"

def execute_direct_sql(query: str, params: Tuple = ()) -> bool:
    """
    Execute SQL directly to the database.
    
    Args:
        query: SQL query to execute
        params: Parameters for the query
        
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"SQL error: {e}")
        logger.error(traceback.format_exc())
        return False

def check_user_exists(user_id: int) -> bool:
    """
    Check if user exists in database.
    
    Args:
        user_id: User ID to check
        
    Returns:
        True if user exists, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone() is not None
        conn.close()
        return result
    except Exception as e:
        logger.error(f"Error checking user: {e}")
        return False

def ensure_user_exists(user_id: int) -> bool:
    """
    Make sure a user exists, create if not.
    
    Args:
        user_id: User ID to check/create
        
    Returns:
        True if successful, False otherwise
    """
    if check_user_exists(user_id):
        return True
        
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (id, username, first_name, last_name, risk_profile, investment_horizon) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, f"user_{user_id}", "User", "", "moderate", "medium")
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return False

def set_profile(user_id: int, profile_type: str) -> Dict[str, Any]:
    """
    Set user profile with direct SQL.
    
    Args:
        user_id: User ID
        profile_type: Profile type to set
        
    Returns:
        Dict with success status and message
    """
    try:
        # Validate profile type
        if profile_type not in ["high-risk", "stable"]:
            return {
                "success": False,
                "message": f"Invalid profile type: {profile_type}"
            }
            
        # Make sure user exists
        if not ensure_user_exists(user_id):
            return {
                "success": False,
                "message": "Could not find or create user account"
            }
            
        # Update profile
        success = execute_direct_sql(
            "UPDATE users SET risk_profile = ? WHERE id = ?",
            (profile_type, user_id)
        )
        
        if not success:
            return {
                "success": False,
                "message": "Database error updating profile"
            }
            
        # Prepare response message
        if profile_type == "high-risk":
            message = """
🔴 *High-Risk Profile Selected*

Your investment recommendations will now focus on:
• Higher APR opportunities
• Newer pools with growth potential
• More volatile but potentially rewarding options

_Note: Higher returns come with increased risk_
"""
        else:  # stable
            message = """
🟢 *Stable Profile Selected*

Your investment recommendations will now focus on:
• Established, reliable pools
• Lower volatility options
• More consistent but potentially lower APR

_Note: Stability typically means more moderate returns_
"""
        
        return {
            "success": True,
            "message": message
        }
    except Exception as e:
        logger.error(f"Error setting profile: {e}")
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "message": "System error setting profile"
        }

def high_risk_profile(user_id: int) -> Dict[str, Any]:
    """
    Set user profile to high-risk.
    
    Args:
        user_id: User ID
        
    Returns:
        Result dict
    """
    return set_profile(user_id, "high-risk")
    
def stable_profile(user_id: int) -> Dict[str, Any]:
    """
    Set user profile to stable.
    
    Args:
        user_id: User ID
        
    Returns:
        Result dict
    """
    return set_profile(user_id, "stable")

def handle_button(callback_data: str, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Handle button press for profile buttons.
    
    Args:
        callback_data: Button callback data
        user_id: User ID
        
    Returns:
        Response dict or None if not handled
    """
    # Check what kind of button this is
    if callback_data in ["profile_high-risk", "account_profile_high-risk"]:
        logger.info(f"Setting high-risk profile for user {user_id}")
        return high_risk_profile(user_id)
    elif callback_data in ["profile_stable", "account_profile_stable"]:
        logger.info(f"Setting stable profile for user {user_id}")
        return stable_profile(user_id)
    
    # Not a button we handle
    return None

# Main function for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python fix_buttons_force.py <user_id> <profile_type>")
        sys.exit(1)
        
    user_id = int(sys.argv[1])
    profile_type = sys.argv[2]
    
    if profile_type == "high-risk":
        result = high_risk_profile(user_id)
    elif profile_type == "stable":
        result = stable_profile(user_id)
    else:
        print(f"Invalid profile type: {profile_type}")
        sys.exit(1)
        
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")