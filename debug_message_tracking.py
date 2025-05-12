#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Debugging tool for monitoring message tracking and detecting loops.
This can be run independently or imported to check the status of
message tracking systems.
"""

import sys
import os
import time
import hashlib
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('message_tracking_debug.log')
    ]
)

logger = logging.getLogger(__name__)

# Try to import from main with fallback defaults
try:
    from main import processed_messages, recent_messages, MAX_PROCESSED_MESSAGES
    logger.info(f"Successfully imported message tracking from main.py")
except ImportError:
    logger.warning("Failed to import from main.py, using default empty tracking sets")
    processed_messages = set()
    recent_messages = {}
    MAX_PROCESSED_MESSAGES = 1000

def display_message_tracking_stats():
    """Display statistics about the message tracking system."""
    logger.info("=== MESSAGE TRACKING STATISTICS ===")
    logger.info(f"Total processed messages: {len(processed_messages)}")
    logger.info(f"Recent message hashes: {len(recent_messages)}")
    
    # Process message types
    message_types = {}
    for msg_id in processed_messages:
        parts = msg_id.split('_')
        if len(parts) > 1:
            prefix = parts[1] if parts[1] in ('cb', 'msg') else 'other'
            message_types[prefix] = message_types.get(prefix, 0) + 1
    
    logger.info(f"Message types: {json.dumps(message_types, indent=2)}")
    
    # Check recent messages time range
    if recent_messages:
        now = time.time()
        times = [now - ts for ts in recent_messages.values()]
        oldest = max(times) if times else 0
        newest = min(times) if times else 0
        logger.info(f"Recent messages time range: {newest:.1f} - {oldest:.1f} seconds ago")
    
    # Check if any messages are potentially looping
    potential_loops = {}
    for msg_hash, timestamp in recent_messages.items():
        # Check for messages with similar prefixes
        for other_hash, other_timestamp in recent_messages.items():
            if msg_hash != other_hash and msg_hash[:15] == other_hash[:15]:
                if abs(timestamp - other_timestamp) < 5.0:  # within 5 seconds
                    if msg_hash not in potential_loops:
                        potential_loops[msg_hash] = []
                    potential_loops[msg_hash].append(other_hash)
    
    if potential_loops:
        logger.warning(f"Potential message loops detected: {len(potential_loops)} groups")
        for msg_hash, similar in potential_loops.items():
            logger.warning(f"  - {msg_hash} has {len(similar)} similar messages")
    else:
        logger.info("No potential message loops detected")
        
    logger.info("=" * 35)
    return {
        "processed_count": len(processed_messages),
        "recent_count": len(recent_messages),
        "message_types": message_types,
        "potential_loops": len(potential_loops) if potential_loops else 0
    }

def simulate_message_loop_detection():
    """Simulate message loop detection for testing."""
    # Create sample data for testing
    chat_id = 12345
    
    # Simulate 3 very similar messages sent quickly (potential loop)
    base_msg = "Hello, how are you?"
    msg1 = f"{base_msg} 1"
    msg2 = f"{base_msg} 2"
    msg3 = f"{base_msg} 3"
    
    # Create hashes
    now = time.time()
    msg1_hash = f"{chat_id}_{hashlib.md5(msg1.encode()).hexdigest()[:8]}"
    msg2_hash = f"{chat_id}_{hashlib.md5(msg2.encode()).hexdigest()[:8]}"
    msg3_hash = f"{chat_id}_{hashlib.md5(msg3.encode()).hexdigest()[:8]}"
    
    # Add to recent messages with timestamps close together
    recent_messages[msg1_hash] = now
    recent_messages[msg2_hash] = now - 0.5
    recent_messages[msg3_hash] = now - 1.0
    
    # Add some regular messages too
    processed_messages.add(f"{chat_id}_msg_100")
    processed_messages.add(f"{chat_id}_msg_101")
    processed_messages.add(f"{chat_id}_cb_abc123")
    
    # Run the detection
    logger.info("Simulating message loop detection...")
    stats = display_message_tracking_stats()
    
    # Clean up the test data
    recent_messages.pop(msg1_hash, None)
    recent_messages.pop(msg2_hash, None)
    recent_messages.pop(msg3_hash, None)
    
    return stats

def clean_old_messages(max_age_seconds=300):
    """Clean old messages to prevent memory leaks."""
    now = time.time()
    old_messages = [k for k, v in recent_messages.items() if now - v > max_age_seconds]
    for k in old_messages:
        recent_messages.pop(k, None)
    
    logger.info(f"Cleaned {len(old_messages)} messages older than {max_age_seconds} seconds")
    
    # If processed_messages is too large, trim it
    if len(processed_messages) > MAX_PROCESSED_MESSAGES:
        processed_messages_list = list(processed_messages)
        processed_messages.clear()
        processed_messages.update(processed_messages_list[-MAX_PROCESSED_MESSAGES:])
        logger.info(f"Trimmed processed_messages to {len(processed_messages)} entries")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--simulate":
        # Run simulation mode
        simulate_message_loop_detection()
    else:
        # Run real stats mode
        display_message_tracking_stats()
        
        # Offer to clean old messages
        if input("Clean old messages? (y/n): ").lower() == 'y':
            max_age = int(input("Max age in seconds (default 300): ") or "300")
            clean_old_messages(max_age)
            # Show updated stats
            display_message_tracking_stats()