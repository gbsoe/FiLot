#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for verifying the message tracking functionality.
Run this script to test the anti-loop protection mechanisms.
"""

import os
import sys
import time
import random
import unittest
import threading
import sqlite3
import hashlib
from debug_message_tracking import (
    MessageTracker,
    is_message_tracked,
    acquire_instance_lock,
    release_instance_lock,
    force_kill_competing_instances
)
from anti_loop import (
    is_message_looping,
    lock_message_processing,
    reset_all_locks
)

class TestMessageTracking(unittest.TestCase):
    """Tests for the message tracking and anti-looping functionality."""
    
    def setUp(self):
        """Set up the test environment."""
        # Initialize the database
        MessageTracker.initialize_db()
        
        # Reset any existing locks
        reset_all_locks()
        
        # Make sure we release any instance locks
        if os.path.exists('.bot_instance.lock'):
            try:
                os.remove('.bot_instance.lock')
            except:
                pass
    
    def test_message_tracking_basic(self):
        """Test basic message tracking functionality."""
        # Generate a unique test message
        test_chat_id = 123456
        test_message = f"Test message {random.randint(1000, 9999)}"
        
        # First time should not be tracked
        result1 = is_message_tracked(test_chat_id, test_message)
        self.assertFalse(result1, "New message should not be marked as tracked")
        
        # Second time should be tracked
        result2 = is_message_tracked(test_chat_id, test_message)
        self.assertTrue(result2, "Repeated message should be marked as tracked")
    
    def test_message_tracking_similar(self):
        """Test tracking of similar messages."""
        # Generate a base test message
        test_chat_id = 789012
        base_message = f"Similar test {random.randint(1000, 9999)}"
        
        # First message should not be tracked
        result1 = is_message_tracked(test_chat_id, base_message)
        self.assertFalse(result1, "New message should not be marked as tracked")
        
        # Slightly different message should be tracked as new
        result2 = is_message_tracked(test_chat_id, base_message + " extra")
        self.assertFalse(result2, "Different message should not be marked as tracked")
    
    def test_instance_locking(self):
        """Test the instance locking mechanism."""
        # Should be able to acquire the lock initially
        lock_result1 = acquire_instance_lock()
        self.assertTrue(lock_result1, "Should be able to acquire the instance lock")
        
        # Create a thread that tries to acquire the same lock
        def try_lock():
            lock_result = acquire_instance_lock()
            self.assertFalse(lock_result, "Second attempt to acquire lock should fail")
        
        thread = threading.Thread(target=try_lock)
        thread.start()
        thread.join()
        
        # Release the lock
        release_result = release_instance_lock()
        self.assertTrue(release_result, "Should be able to release the instance lock")
        
        # Should be able to acquire again after release
        lock_result2 = acquire_instance_lock()
        self.assertTrue(lock_result2, "Should be able to acquire the lock after release")
        
        # Clean up
        release_instance_lock()
    
    def test_anti_loop_protection(self):
        """Test the anti-loop protection functionality."""
        test_chat_id = 345678
        test_message = f"Anti-loop test {random.randint(1000, 9999)}"
        
        # First check should pass
        loop_result1 = is_message_looping(test_chat_id, test_message)
        self.assertFalse(loop_result1, "New message should not be detected as looping")
        
        # Lock the chat explicitly
        lock_message_processing(test_chat_id)
        
        # Now the check should detect a potential loop
        loop_result2 = is_message_looping(test_chat_id, test_message)
        self.assertTrue(loop_result2, "Message after lock should be detected as looping")
        
        # Wait for lock to expire and test again
        time.sleep(6)  # Lock duration is 5 seconds
        
        loop_result3 = is_message_looping(test_chat_id, "New message after lock")
        self.assertFalse(loop_result3, "New message after lock expiry should not be detected as looping")
    
    def test_database_cleanup(self):
        """Test that old message tracking entries are cleaned up."""
        # Add a bunch of test messages
        test_chat_id = 901234
        for i in range(10):
            is_message_tracked(test_chat_id, f"Cleanup test message {i}")
        
        # Count entries in the database
        conn = sqlite3.connect('bot_status.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM message_tracking")
        initial_count = cursor.fetchone()[0]
        conn.close()
        
        # Run cleanup with a short cutoff
        global MAX_MESSAGE_AGE
        original_age = MAX_MESSAGE_AGE
        try:
            import debug_message_tracking
            debug_message_tracking.MAX_MESSAGE_AGE = 0.1  # Very short age
            time.sleep(0.2)  # Wait for messages to age
            
            # Force cleanup
            cleaned = MessageTracker.cleanup_old_messages()
            
            # Check that messages were cleaned
            conn = sqlite3.connect('bot_status.db')
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM message_tracking")
            final_count = cursor.fetchone()[0]
            conn.close()
            
            self.assertLess(final_count, initial_count, "Database cleanup should remove old messages")
        finally:
            # Restore original age
            debug_message_tracking.MAX_MESSAGE_AGE = original_age
    
    def tearDown(self):
        """Clean up after tests."""
        # Reset locks
        reset_all_locks()
        
        # Release instance lock if any
        release_instance_lock()
        
        # Optionally clean up the database
        MessageTracker.cleanup_old_messages()

if __name__ == "__main__":
    unittest.main()