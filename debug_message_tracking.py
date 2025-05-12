#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Debug tool for tracking and troubleshooting message handling issues with the Telegram bot.
This module provides functions to track message processing and detect duplicate messages.
"""

import os
import time
import logging
import json
import hashlib
import sqlite3
import threading
import fcntl
from typing import Dict, Set, Any, Optional, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("debug_message_tracking")

# Constants
DB_PATH = 'bot_status.db'
LOCK_FILE = '.bot_instance.lock'
MAX_MESSAGE_AGE = 60  # seconds
TRACKING_TABLE = 'message_tracking'

# Initialize globals
_message_lock = threading.RLock()
_instance_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
_process_lock_acquired = False

class MessageTracker:
    """Tracks message processing to prevent duplicate handling and message loops."""
    
    @staticmethod
    def initialize_db():
        """Initialize the SQLite database for message tracking."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Create table if it doesn't exist
            cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS {TRACKING_TABLE} (
                tracking_id TEXT PRIMARY KEY,
                chat_id INTEGER,
                message_hash TEXT,
                timestamp REAL,
                instance_id TEXT,
                message_preview TEXT
            )
            ''')
            
            # Create index for faster lookups
            cursor.execute(f'''
            CREATE INDEX IF NOT EXISTS idx_chat_hash 
            ON {TRACKING_TABLE} (chat_id, message_hash)
            ''')
            
            # Create timestamp index for cleanup
            cursor.execute(f'''
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON {TRACKING_TABLE} (timestamp)
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Message tracking database initialized")
            return True
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            return False
    
    @staticmethod
    def cleanup_old_messages():
        """Remove old messages from the tracking database."""
        try:
            cutoff_time = time.time() - MAX_MESSAGE_AGE
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute(f"DELETE FROM {TRACKING_TABLE} WHERE timestamp < ?", (cutoff_time,))
            deleted_count = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old message tracking entries")
            
            return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up old messages: {e}")
            return 0
    
    @staticmethod
    def is_message_tracked(chat_id: int, message_content: str) -> bool:
        """
        Check if a message has already been processed recently.
        
        Args:
            chat_id: The chat ID
            message_content: The message content to check
            
        Returns:
            bool: True if the message has been seen recently, False otherwise
        """
        with _message_lock:
            try:
                # Create a hash of the message content
                message_hash = hashlib.md5(message_content.encode()).hexdigest()
                tracking_id = f"{chat_id}_{message_hash}"
                
                # Connect to the database
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                # Check if this message hash exists for this chat
                cursor.execute(
                    f"SELECT COUNT(*) FROM {TRACKING_TABLE} WHERE chat_id = ? AND message_hash = ?",
                    (chat_id, message_hash)
                )
                result = cursor.fetchone()
                exists = result[0] > 0
                
                if exists:
                    logger.warning(f"Duplicate message detected for chat {chat_id}: {message_content[:30]}...")
                    return True
                
                # Add this message to tracking
                now = time.time()
                message_preview = message_content[:50] + "..." if len(message_content) > 50 else message_content
                
                cursor.execute(
                    f"INSERT INTO {TRACKING_TABLE} VALUES (?, ?, ?, ?, ?, ?)",
                    (tracking_id, chat_id, message_hash, now, _instance_id, message_preview)
                )
                
                conn.commit()
                conn.close()
                
                # Periodically clean up old messages
                if random.random() < 0.1:  # ~10% chance to clean up on each check
                    MessageTracker.cleanup_old_messages()
                
                return False
            except Exception as e:
                logger.error(f"Error tracking message: {e}")
                return False

def acquire_instance_lock() -> bool:
    """
    Try to acquire an exclusive lock to ensure only one bot instance runs.
    
    Returns:
        bool: True if lock was acquired, False otherwise
    """
    global _process_lock_acquired
    
    try:
        # Create or open the lock file
        lock_fd = open(LOCK_FILE, 'w')
        
        # Try to acquire an exclusive lock (non-blocking)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _process_lock_acquired = True
            
            # Write our instance ID to the lock file
            lock_fd.seek(0)
            lock_fd.write(f"{_instance_id}\n{os.getpid()}\n{time.time()}")
            lock_fd.flush()
            
            logger.info(f"Acquired exclusive bot instance lock (ID: {_instance_id})")
            return True
        except IOError:
            # Another instance already holds the lock
            _process_lock_acquired = False
            logger.error("Failed to acquire bot instance lock - another instance is running")
            return False
    except Exception as e:
        logger.error(f"Error acquiring instance lock: {e}")
        _process_lock_acquired = False
        return False

def release_instance_lock() -> bool:
    """
    Release the exclusive lock if we hold it.
    
    Returns:
        bool: True if lock was released, False otherwise
    """
    global _process_lock_acquired
    
    if not _process_lock_acquired:
        return True  # Nothing to release
        
    try:
        # Open the lock file
        lock_fd = open(LOCK_FILE, 'r+')
        
        # Release the lock
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        
        # Clear the lock file
        lock_fd.seek(0)
        lock_fd.truncate()
        lock_fd.close()
        
        _process_lock_acquired = False
        logger.info("Released bot instance lock")
        return True
    except Exception as e:
        logger.error(f"Error releasing instance lock: {e}")
        return False

def force_kill_competing_instances() -> int:
    """
    Forcibly kill any competing bot instances.
    
    Returns:
        int: Number of instances killed
    """
    try:
        import psutil
        current_pid = os.getpid()
        killed_count = 0
        
        # Find all Python processes
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Skip our own process
                if proc.info['pid'] == current_pid:
                    continue
                    
                cmdline = proc.info['cmdline'] if proc.info['cmdline'] else []
                cmdline_str = ' '.join(cmdline)
                
                # Check if it's a competing bot process
                if 'python' in proc.info['name'].lower() and ('main.py' in cmdline_str or 'telegram' in cmdline_str):
                    logger.warning(f"Killing competing bot process: PID {proc.info['pid']}")
                    proc.kill()
                    killed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        if killed_count > 0:
            logger.info(f"Killed {killed_count} competing bot processes")
        return killed_count
    except Exception as e:
        logger.error(f"Error killing competing processes: {e}")
        return 0

# Initialize tracking on module import
try:
    import random  # for random cleanup
    MessageTracker.initialize_db()
    logger.info("Message tracking system initialized")
except Exception as e:
    logger.error(f"Failed to initialize message tracking: {e}")

# Export main functions at module level
is_message_tracked = MessageTracker.is_message_tracked
cleanup_tracking = MessageTracker.cleanup_old_messages