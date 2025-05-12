#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for message tracking functions to prevent duplicate messages and loops.
"""

import unittest
import hashlib
import time
import sys
import os

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the functions to test
from main import is_message_processed, processed_messages, recent_messages

class TestMessageTracking(unittest.TestCase):
    """Test cases for message tracking functions."""

    def setUp(self):
        """Set up test cases."""
        # Clear the global tracking data before each test
        global processed_messages, recent_messages
        processed_messages.clear()
        recent_messages.clear()

    def test_is_message_processed_first_time(self):
        """Test that a first-time message is not considered as processed."""
        chat_id = 12345
        message_id = 67890
        result = is_message_processed(chat_id, message_id)
        self.assertFalse(result, "First-time message should not be considered as processed")
        self.assertIn(f"{chat_id}_{message_id}", processed_messages)

    def test_is_message_processed_duplicate(self):
        """Test that a duplicate message is detected as processed."""
        chat_id = 12345
        message_id = 67890
        
        # First call should return False and add to processed_messages
        is_message_processed(chat_id, message_id)
        
        # Second call should return True
        result = is_message_processed(chat_id, message_id)
        self.assertTrue(result, "Duplicate message should be detected as processed")

    def test_memory_management(self):
        """Test that memory management for processed_messages works correctly."""
        # Add MAX_PROCESSED_MESSAGES + 10 messages
        from main import MAX_PROCESSED_MESSAGES
        
        for i in range(MAX_PROCESSED_MESSAGES + 10):
            is_message_processed(12345, i)
            
        # Check that the size is limited to MAX_PROCESSED_MESSAGES
        self.assertLessEqual(len(processed_messages), MAX_PROCESSED_MESSAGES)
        
        # Verify the most recent messages are kept (not the oldest)
        self.assertIn("12345_" + str(MAX_PROCESSED_MESSAGES + 9), processed_messages)
        self.assertNotIn("12345_0", processed_messages)

    def test_message_content_hash(self):
        """Test hash-based message content duplicate detection."""
        chat_id = 12345
        message_text1 = "Hello, world!"
        message_text2 = "Hello, universe!"
        
        # Create message hashes
        msg_hash1 = f"{chat_id}_{hashlib.md5(message_text1.encode()).hexdigest()[:8]}"
        msg_hash2 = f"{chat_id}_{hashlib.md5(message_text2.encode()).hexdigest()[:8]}"
        
        # Add messages to recent_messages
        now = time.time()
        recent_messages[msg_hash1] = now
        
        # Different content should have different hashes
        self.assertNotEqual(msg_hash1, msg_hash2)
        
        # Check if the first message is considered recent
        self.assertIn(msg_hash1, recent_messages)
        self.assertNotIn(msg_hash2, recent_messages)

    def test_time_window_detection(self):
        """Test time window based duplicate detection."""
        chat_id = 12345
        message_text = "Hello, world!"
        
        # Create message hash
        msg_hash = f"{chat_id}_{hashlib.md5(message_text.encode()).hexdigest()[:8]}"
        
        # Add message to recent_messages with timestamp 30 seconds ago
        past_time = time.time() - 30
        recent_messages[msg_hash] = past_time
        
        # Simulate send_response logic
        now = time.time()
        is_duplicate = False
        if msg_hash in recent_messages:
            if now - recent_messages[msg_hash] < 10:
                is_duplicate = True
                
        # 30 seconds is > 10 seconds, so not a duplicate
        self.assertFalse(is_duplicate)
        
        # Now update the timestamp to be 5 seconds ago
        recent_time = time.time() - 5
        recent_messages[msg_hash] = recent_time
        
        # Check again
        is_duplicate = False
        if msg_hash in recent_messages:
            if now - recent_messages[msg_hash] < 10:
                is_duplicate = True
                
        # 5 seconds is < 10 seconds, so it's a duplicate
        self.assertTrue(is_duplicate)

    def test_callback_query_tracking(self):
        """Test callback query duplicate detection."""
        chat_id = 12345
        query_id = "abcdef"
        callback_data = "menu_invest"
        
        # Create tracking IDs
        query_track_id = f"cb_{query_id}"
        data_track_id = f"cb_data_{chat_id}_{hashlib.md5(callback_data.encode()).hexdigest()[:8]}"
        
        # First check should return False for both
        result1 = is_message_processed(chat_id, query_track_id)
        result2 = is_message_processed(chat_id, data_track_id)
        
        self.assertFalse(result1, "First query ID check should return False")
        self.assertFalse(result2, "First data ID check should return False")
        
        # Second check should return True for both
        result1 = is_message_processed(chat_id, query_track_id)
        result2 = is_message_processed(chat_id, data_track_id)
        
        self.assertTrue(result1, "Second query ID check should return True")
        self.assertTrue(result2, "Second data ID check should return True")

if __name__ == "__main__":
    unittest.main()