#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Navigation context management for the Telegram bot.
This module provides improved tracking of a user's navigation state to improve the button experience.
"""

import logging
import time
import sqlite3
from typing import Dict, Any, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
DB_PATH = 'filot_bot.db'
NAV_TABLE = 'navigation_context'
MAX_HISTORY = 20  # Maximum navigation steps to store per user
PURGE_THRESHOLD = 3600  # Purge data older than 1 hour

class NavigationContextManager:
    """Manages the navigation context for users to improve button interactions."""
    
    @staticmethod
    def initialize_db() -> bool:
        """Initialize the database table for navigation context tracking."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Create table if it doesn't exist
            cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {NAV_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                callback_data TEXT NOT NULL,
                context TEXT,
                timestamp REAL NOT NULL,
                navigation_step INTEGER,
                session_id TEXT
            )
            ''')
            
            # Create index for faster lookups
            cursor.execute(f'''
            CREATE INDEX IF NOT EXISTS idx_nav_chat_id 
            ON {NAV_TABLE} (chat_id)
            ''')
            
            # Create timestamp index for cleanup
            cursor.execute(f'''
            CREATE INDEX IF NOT EXISTS idx_nav_timestamp
            ON {NAV_TABLE} (timestamp)
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Navigation context database initialized")
            return True
        except Exception as e:
            logger.error(f"Error initializing navigation context database: {e}")
            return False
    
    @staticmethod
    def record_navigation_step(chat_id: int, callback_data: str, context: str = "") -> bool:
        """
        Record a navigation step for a user.
        
        Args:
            chat_id: The user's chat ID
            callback_data: The callback data of the button pressed
            context: Optional context about the navigation state
            
        Returns:
            bool: Whether the operation was successful
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get the current session ID (or create a new one)
            cursor.execute(f"""
            SELECT session_id FROM {NAV_TABLE} 
            WHERE chat_id = ? 
            ORDER BY timestamp DESC LIMIT 1
            """, (chat_id,))
            
            result = cursor.fetchone()
            if result:
                session_id = result[0]
            else:
                # Create a new session ID based on timestamp
                session_id = f"session_{chat_id}_{int(time.time())}"
            
            # Get the next navigation step for this session
            cursor.execute(f"""
            SELECT MAX(navigation_step) FROM {NAV_TABLE} 
            WHERE chat_id = ? AND session_id = ?
            """, (chat_id, session_id))
            
            result = cursor.fetchone()
            if result and result[0] is not None:
                next_step = result[0] + 1
            else:
                next_step = 1
            
            # Insert the navigation step
            timestamp = time.time()
            cursor.execute(f"""
            INSERT INTO {NAV_TABLE} (chat_id, callback_data, context, timestamp, navigation_step, session_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (chat_id, callback_data, context, timestamp, next_step, session_id))
            
            # Clean up old navigation data for this user
            cursor.execute(f"""
            DELETE FROM {NAV_TABLE} 
            WHERE chat_id = ? 
            AND id NOT IN (
                SELECT id FROM {NAV_TABLE} 
                WHERE chat_id = ? 
                ORDER BY timestamp DESC 
                LIMIT {MAX_HISTORY}
            )
            """, (chat_id, chat_id))
            
            # Periodically purge very old data (across all users)
            if next_step % 10 == 0:  # Only run this occasionally to save resources
                purge_timestamp = time.time() - PURGE_THRESHOLD
                cursor.execute(f"DELETE FROM {NAV_TABLE} WHERE timestamp < ?", (purge_timestamp,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error recording navigation step: {e}")
            return False
    
    @staticmethod
    def get_navigation_history(chat_id: int, steps: int = 5) -> List[Dict[str, Any]]:
        """
        Get the recent navigation history for a user.
        
        Args:
            chat_id: The user's chat ID
            steps: Number of recent steps to retrieve
            
        Returns:
            List of navigation steps with timestamps and context
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute(f"""
            SELECT callback_data, context, timestamp, navigation_step, session_id
            FROM {NAV_TABLE} 
            WHERE chat_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
            """, (chat_id, steps))
            
            results = cursor.fetchall()
            conn.close()
            
            # Convert to a list of dictionaries
            history = []
            for row in results:
                history.append({
                    'callback_data': row[0],
                    'context': row[1],
                    'timestamp': row[2],
                    'step': row[3],
                    'session_id': row[4]
                })
            
            return history
        except Exception as e:
            logger.error(f"Error retrieving navigation history: {e}")
            return []
    
    @staticmethod
    def detect_navigation_pattern(chat_id: int) -> Optional[str]:
        """
        Detect if the user is in a specific navigation pattern.
        
        Args:
            chat_id: The user's chat ID
            
        Returns:
            Optional string describing the detected pattern, or None
        """
        try:
            history = NavigationContextManager.get_navigation_history(chat_id, 5)
            
            if len(history) < 3:
                return None
            
            # Extract just the callback data for easier pattern matching
            callbacks = [step['callback_data'] for step in history]
            
            # Check for back-and-forth pattern (A-B-A)
            if len(callbacks) >= 3 and callbacks[0] == callbacks[2] and callbacks[0] != callbacks[1]:
                return "back_forth"
            
            # Check for circular navigation (A-B-C-A)
            if len(callbacks) >= 4 and callbacks[0] == callbacks[3] and len(set(callbacks[:4])) >= 3:
                return "circular"
            
            # Check for rapid menu switching
            menu_count = 0
            # Make sure we only check what's available in the history
            check_count = min(3, len(callbacks))
            for callback in callbacks[:check_count]:
                if callback.startswith("menu_"):
                    menu_count += 1
            
            if menu_count >= 2:
                return "menu_switching"
            
            return None
        except Exception as e:
            logger.error(f"Error detecting navigation pattern: {e}")
            return None
    
    @staticmethod
    def is_duplicate_navigation(chat_id: int, callback_data: str) -> bool:
        """
        Check if this navigation step would create a duplication.
        Helps prevent duplicate responses for the same action.
        
        Args:
            chat_id: The user's chat ID
            callback_data: The callback data to check
            
        Returns:
            bool: True if this would be a duplicate, False otherwise
        """
        try:
            history = NavigationContextManager.get_navigation_history(chat_id, 3)
            
            if not history:
                return False
            
            # Check if the exact same callback was used in the last 0.5 seconds
            # This helps catch true duplicates (like double-clicks)
            for step in history:
                if step['callback_data'] == callback_data:
                    time_diff = time.time() - step['timestamp']
                    if time_diff < 0.5:
                        logger.info(f"Detected duplicate navigation within 0.5s: {callback_data}")
                        return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking for duplicate navigation: {e}")
            return False
    
    @staticmethod
    def reset_navigation_session(chat_id: int) -> bool:
        """
        Reset a user's navigation session (for recovery from errors).
        
        Args:
            chat_id: The user's chat ID
            
        Returns:
            bool: Whether the operation was successful
        """
        try:
            # We don't delete the data, just create a new session ID for this user
            # which effectively starts a new navigation context
            new_session_id = f"session_{chat_id}_{int(time.time())}_reset"
            
            # Record a reset step with the new session
            NavigationContextManager.record_navigation_step(
                chat_id=chat_id,
                callback_data="session_reset",
                context="Navigation session reset"
            )
            
            logger.info(f"Reset navigation session for chat_id: {chat_id}")
            return True
        except Exception as e:
            logger.error(f"Error resetting navigation session: {e}")
            return False

# Initialize the database when the module is imported
NavigationContextManager.initialize_db()

# Export primary functions at module level
record_navigation = NavigationContextManager.record_navigation_step
get_navigation_history = NavigationContextManager.get_navigation_history
detect_pattern = NavigationContextManager.detect_navigation_pattern
is_duplicate = NavigationContextManager.is_duplicate_navigation
reset_session = NavigationContextManager.reset_navigation_session