# FiLot Telegram Bot Message Loop Bugfix

## Issue Description
The FiLot Telegram bot was experiencing message loops and duplicate responses when users clicked menu buttons or sent messages. This created a poor user experience where:
- Multiple identical responses were sent for a single button click
- The same message would trigger repeated responses
- Clicking buttons could cause an endless loop of messages

## Root Cause Analysis
After investigating the code, several issues were identified that contributed to message looping:

1. **Insufficient Message Tracking**: Messages weren't properly tracked, allowing duplicate processing
2. **Missing Callback Checking**: Callback queries lacked proper duplicate detection
3. **Parallel Processing Conflicts**: Both main.py and bot.py were handling the same events
4. **No Content-Based Detection**: Similar messages weren't detected as duplicates 
5. **Memory Leaks**: Tracking systems didn't manage memory efficiently

## Implemented Fixes

### 1. Comprehensive Message Tracking System
- Added global tracking with unique IDs for all message and callback types
- Implemented both message ID and content-based tracking for redundancy
- Created memory management to prevent tracking set from growing unbounded

```python
# Global tracking systems
processed_messages = set()
MAX_PROCESSED_MESSAGES = 1000
recent_messages = {}

def is_message_processed(chat_id, message_id):
    """Check if a message has already been processed and mark it as processed if not."""
    global processed_messages
    
    # Create a unique tracking ID for this message
    tracking_id = f"{chat_id}_{message_id}"
    
    # Check if we've seen this message before
    if tracking_id in processed_messages:
        return True
        
    # Mark message as processed
    processed_messages.add(tracking_id)
    
    # Maintain max size for processed_messages
    if len(processed_messages) > MAX_PROCESSED_MESSAGES:
        processed_messages_list = list(processed_messages)
        processed_messages = set(processed_messages_list[-MAX_PROCESSED_MESSAGES:])
        
    return False
```

### 2. Enhanced Callback Query Protection
- Added multiple tracking IDs for each callback query
- Created both ID-based and content-based checks
- Implemented redundant protection in both main.py and bot.py

```python
# Create multiple tracking IDs to robustly prevent duplicate processing
query_track_id = f"cb_{query_id}"
data_track_id = f"cb_data_{chat_id}_{hashlib.md5(callback_data.encode()).hexdigest()[:8]}"

# Check if we've already processed this callback using any of our tracking methods
if is_message_processed(chat_id, query_track_id) or is_message_processed(chat_id, data_track_id):
    logger.info(f"Skipping already processed callback query {query_id} with data {callback_data}")
    # Skip further processing for this callback
    return
    
# Mark both IDs as processed
is_message_processed(chat_id, query_track_id)
is_message_processed(chat_id, data_track_id)
```

### 3. Duplicate Message Content Detection
- Added hash-based message content fingerprinting
- Created time-windowed tracking to prevent similar messages within 10 seconds
- Implemented memory management for the tracking system

```python
def send_response(chat_id, text, parse_mode=None, reply_markup=None, message_id=None):
    try:
        # Create a unique identifier for this message to prevent duplicates
        msg_hash = f"{chat_id}_{hashlib.md5(text.encode()).hexdigest()[:8]}"
        
        # Check if we've already sent a very similar message in the last 10 seconds
        now = time.time()
        if msg_hash in recent_messages:
            if now - recent_messages[msg_hash] < 10:
                logger.warning(f"Preventing duplicate message: {text[:30]}...")
                return
        
        # Update the recent messages tracker
        recent_messages[msg_hash] = now
        
        # Clean up old messages to prevent memory leak
        old_msgs = [k for k, v in recent_messages.items() if now - v > 30]
        for k in old_msgs:
            recent_messages.pop(k, None)
```

### 4. Regular Message Enhanced Tracking
- Implemented multiple tracking methods for regular text messages
- Added content hash-based tracking to prevent processing similar messages
- Created redundant protection across different message handlers

```python
# Create multiple tracking IDs for this message
msg_track_id = f"msg_{message_id}"
msg_content_id = f"msg_content_{chat_id}_{hashlib.md5(message_text.encode()).hexdigest()[:8]}"

# Check if we've already processed this message using any tracking method
if is_message_processed(chat_id, msg_track_id) or is_message_processed(chat_id, msg_content_id):
    logger.info(f"Skipping already processed message {message_id}: {message_text[:30]}...")
    # Skip further processing for this message
    return
    
# Mark both IDs as processed
is_message_processed(chat_id, msg_track_id)
is_message_processed(chat_id, msg_content_id)
```

### 5. User Data Context Tracking
- Added user_data context flags to track message handling status
- Implemented redundant checks in handler functions 
- Created multiple tracking mechanisms in both main.py and bot.py

```python
# Store callback tracking IDs for additional protection
if not hasattr(context, 'user_data'):
    context.user_data = {}

# Check multiple ways to detect duplicates
if context.user_data.get("callback_handled", False):
    logger.info("Skipping already handled callback query (user_data flag)")
    return
    
if context.user_data.get(callback_id, False) or context.user_data.get(content_id, False):
    logger.info(f"Skipping duplicate callback: {callback_data[:30]}...")
    return
    
# Mark as being handled using multiple methods for redundancy
context.user_data["callback_handled"] = True
context.user_data["message_response_sent"] = False
context.user_data[callback_id] = True
context.user_data[content_id] = True
```

## Testing Procedures
1. Click menu buttons repeatedly to verify no duplicate messages
2. Send the same message multiple times to ensure single processing
3. Use inline keyboards to verify callbacks are processed once
4. Restart the bot and check message handling remains stable
5. Monitor logs for "Skipping already processed" indicators

## Conclusion
The implemented changes provide multiple layers of protection against message looping and duplicate responses. By using redundant tracking methods and content-based fingerprinting, the bot now provides a more stable and predictable user experience when interacting with buttons and commands.