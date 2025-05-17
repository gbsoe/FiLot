"""
Simple direct implementation of profile commands.
This module provides simple command handlers for setting user risk profiles.
"""

import logging
import sqlite3
from typing import Dict, Any, Optional

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database file path
DB_FILE = 'filot_bot.db'

def set_profile_direct(user_id: int, profile_type: str) -> Dict[str, Any]:
    """
    Set a user's risk profile directly in the database using SQLite3.
    This bypasses the ORM to provide a more reliable update.
    
    Args:
        user_id: The user's ID
        profile_type: Either 'high-risk' or 'stable'
        
    Returns:
        Dict with success status and message
    """
    profile_type = profile_type.lower().strip()
    if profile_type not in ["high-risk", "stable"]:
        return {
            'success': False,
            'message': f"Invalid profile type: {profile_type}. Must be 'high-risk' or 'stable'."
        }
    
    try:
        # First make sure user exists in the database
        ensure_user_exists(user_id)
        
        # Then update their profile
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Update user's risk profile
        cursor.execute(
            "UPDATE users SET risk_profile = ? WHERE id = ?",
            (profile_type, user_id)
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully updated user {user_id} profile to {profile_type}")
        
        return {
            'success': True,
            'message': f"Profile updated to {profile_type}"
        }
    
    except Exception as e:
        logger.error(f"Error setting profile for user {user_id}: {e}")
        return {
            'success': False,
            'message': f"Error: {str(e)}"
        }

def ensure_user_exists(user_id: int) -> None:
    """
    Make sure a user record exists for the given ID.
    Creates one with defaults if not.
    
    Args:
        user_id: The user's ID
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    if user is None:
        # Create user record with defaults
        cursor.execute(
            "INSERT INTO users (id, username, first_name, last_name, risk_profile, investment_horizon, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
            (user_id, f"user_{user_id}", "User", "", "moderate", "medium")
        )
    
    conn.commit()
    conn.close()