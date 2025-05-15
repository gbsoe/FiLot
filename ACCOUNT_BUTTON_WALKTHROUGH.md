# Account Button Implementation Walkthrough

This document provides a detailed breakdown of the Account button implementation, focusing on button behavior, database interactions, and error handling. It serves as a companion to the navigation map and provides implementation-specific details.

## Account Button Main Menu

### Implementation Details

- **Entry Point**: `/account` command or "👤 Account" persistent button
- **Callback Data**: None (direct command) or embedded in `update.message`
- **Handler Function**: `account_command` in `bot.py`

### Database Interactions

```python
# Log command activity
from app import app
with app.app_context():
    db_utils.log_user_activity(user.id, "account_command")

# Get user information
from models import User
user_record = None
with app.app_context():
    user_record = User.query.filter_by(id=user.id).first()
```

### UI Elements

```python
# Create response message
response = (
    f"👤 *Your Account* 👤\n\n"
    f"*Wallet:* {wallet_status}\n"
    f"*Risk Profile:* {profile_type}\n"
    f"*Daily Updates:* {subscription_status}\n\n"
    f"Select an option below to manage your account:"
)

# Import keyboard modules
from keyboard_utils import MAIN_KEYBOARD
from menus import get_account_menu

# Show the account menu with inline buttons and attach persistent keyboard
await message.reply_markdown(response, reply_markup=get_account_menu())
await message.reply_text("Use the buttons above to manage your account 👆", reply_markup=MAIN_KEYBOARD)
```

## Connect Wallet Flow

### Implementation Details

- **Callback Data**: `account_wallet`
- **Handler Function**: Account section in `handle_callback_query` in `bot.py`
- **Route**: Redirects to `walletconnect_command`

### Code Walkthrough

```python
elif account_action == "wallet":
    # Redirect to walletconnect handler
    logger.info("Redirecting account_wallet to walletconnect handler")
    # Create a new context.args with empty list for the walletconnect command
    context.args = []
    await walletconnect_command(update, context)
```

### Error Cases

1. **WalletConnect Service Unavailable**:
   - Error logged to `logger.error(f"WalletConnect service error: {e}")`
   - User shown fallback message to try again later

2. **User Cancels Connection**:
   - Handled by timeout in `walletconnect_command`
   - User returned to Account menu

## Subscribe Button Flow

### Implementation Details

- **Callback Data**: `account_subscribe`
- **Handler Functions**: 
   - In `bot.py`: Account section in `handle_callback_query`
   - In `main.py`: Handlers for `callback_data == "subscribe"`

### Database Interactions

```python
# Actually update the database with subscription status
try:
    import db_utils
    user_id = update_obj.callback_query.from_user.id
    
    # Import app context to handle database operations
    from app import app
    with app.app_context():
        success = db_utils.subscribe_user(user_id)
        if success:
            db_utils.log_user_activity(user_id, "subscribe")
    
    # Message differs based on success
    if success:
        # Subscription successful message
    else:
        # Already subscribed message
except Exception as e:
    logger.error(f"Error handling subscribe callback: {e}", exc_info=True)
    # Error message
```

### Implementation Note

The `subscribe_user` function in `db_utils.py` handles idempotent operations:
- If user already subscribed: Returns `False`
- If user not subscribed: Updates status to subscribed, returns `True`

## Unsubscribe Button Flow

### Implementation Details

- **Callback Data**: `account_unsubscribe`
- **Handler Functions**: 
   - In `bot.py`: Account section in `handle_callback_query`
   - In `main.py`: Handlers for `callback_data == "unsubscribe"`

### Database Interactions

```python
# Actually update the database with unsubscription status
try:
    import db_utils
    user_id = update_obj.callback_query.from_user.id
    
    # Import app context to handle database operations
    from app import app
    with app.app_context():
        success = db_utils.unsubscribe_user(user_id)
        if success:
            db_utils.log_user_activity(user_id, "unsubscribe")
    
    # Message differs based on success
    if success:
        # Unsubscription successful message
    else:
        # Not subscribed message
except Exception as e:
    logger.error(f"Error handling unsubscribe callback: {e}", exc_info=True)
    # Error message
```

### Implementation Note

The `unsubscribe_user` function in `db_utils.py` also handles idempotent operations:
- If user not subscribed: Returns `False`
- If user subscribed: Updates status to unsubscribed, returns `True`

## Risk Profile Selection Flow

### Implementation Details

- **Callback Data**: `profile_high-risk` or `profile_stable`
- **Handler Function**: Risk profile section in `handle_callback_query` in both files

### Database Interactions

```python
# Update user's risk profile in the database
with app.app_context():
    # Get or create the user record
    db_user = db_utils.get_or_create_user(user.id)
    
    # Update risk profile
    db_user.risk_profile = profile_type
    db.session.commit()
    
    # Log the activity
    db_utils.log_user_activity(user.id, f"set_profile_{profile_type}")
```

## Status Button Flow

### Implementation Details

- **Callback Data**: `account_status`
- **Handler Functions**: 
   - In `bot.py`: Account section in `handle_callback_query`
   - In `main.py`: Handlers for `callback_data == "status"`

### Database & API Interactions

```python
# Get user information and system status
try:
    import db_utils
    from datetime import datetime
    from coingecko_utils import is_api_accessible
    from raydium_client import get_client
    
    # Get user information from database
    user_id = update_obj.callback_query.from_user.id
    from app import app
    
    # Default values
    subscription_status = "❌ Not Subscribed"
    verification_status = "❌ Not Verified"
    risk_profile = "Not Set"
    created_date = "Unknown"
    wallet_status = "❌ Not Connected"
    
    # Get user data from database
    with app.app_context():
        # Get user record
        db_user = db_utils.get_or_create_user(user_id)
        
        # Update status information
        if db_user:
            subscription_status = "✅ Subscribed" if db_user.is_subscribed else "❌ Not Subscribed"
            verification_status = "✅ Verified" if db_user.is_verified else "❌ Not Verified"
            risk_profile = db_user.risk_profile.capitalize() if db_user.risk_profile else "Not Set"
            created_date = db_user.created_at.strftime('%Y-%m-%d') if db_user.created_at else "Unknown"
        
        # Log this activity
        db_utils.log_user_activity(user_id, "status_command")
    
    # Check system services
    coingecko_status = "✅ Connected" if is_api_accessible() else "❌ Disconnected"
    
    # Try to get a Raydium client and check connection
    raydium_client = get_client()
    raydium_status = "✅ Connected" if raydium_client else "❌ Disconnected"
    
    # Combine system and user status in message
    # ...
```

### Error Handling

The status handler has robust error handling to ensure it always returns something useful:

```python
except Exception as e:
    logger.error(f"Error handling status callback: {e}", exc_info=True)
    
    # Fallback simple status message on error
    status_message = (
        "📊 *FiLot Status* 📊\n\n"
        "✅ Bot: Operational\n\n"
        "If you're experiencing issues, please try:\n"
        "1. Restarting the conversation with /start\n"
        "2. Checking your internet connection\n"
        "3. Contacting support if problems persist"
    )
```

## Help Button Flow

### Implementation Details

- **Callback Data**: `account_help`
- **Handler Functions**: Account section in `handle_callback_query` in `bot.py`

### Implementation Note

The help handler is straightforward and doesn't interact with the database:

```python
elif account_action == "help":
    # Process help through a callback-friendly approach
    logger.info("Processing account_help button")
    # Simply send a direct reply with the help text
    await query.message.reply_markdown(
        "🤖 *FiLot Bot Commands* 🤖\n\n"
        "*/invest* - Start the investment process\n"
        "*/explore* - Explore top pools and simulate returns\n"
        "*/account* - Manage your account and preferences\n"
        "*/subscribe* - Get daily updates on best pools\n"
        "*/unsubscribe* - Stop receiving daily updates\n"
        "*/wallet* - Connect your crypto wallet\n"
        "*/profile* - Set your investment profile\n"
        "*/status* - Check bot and account status\n"
        "*/help* - Show this help message\n\n"
        "Simply type any question to get AI-assisted answers!"
    )
```

## Back to Main Menu Flow

### Implementation Details

- **Callback Data**: `back_to_main`
- **Handler Function**: Dedicated handler in `main.py` and `bot.py`

### Code Walkthrough

```python
# Handle back to main menu callback
elif callback_data == "back_to_main":
    # Import keyboard for consistent UI
    from keyboard_utils import MAIN_KEYBOARD
    from menus import get_main_menu
    
    # Create a welcome message with main menu
    welcome_message = (
        "🏠 *Welcome to FiLot Main Menu*\n\n"
        "Select an option from the main menu below:"
    )
    
    # Send welcome message with main menu buttons main menu
    send_response(
        chat_id,
        welcome_message,
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )
    logger.info(f"Sent main menu to user {update_obj.callback_query.from_user.id} via back_to_main")
```

## Anti-Loop Protection

All handlers are wrapped with anti-loop protection to prevent message loops:

```python
# In anti_loop.py
def safe_handle_callback(original_callback_func):
    """
    Decorator to make callback handling safe against loops.
    """
    def wrapped_callback(update, context, *args, **kwargs):
        # Get chat ID and callback data
        if update and update.callback_query:
            chat_id = update.callback_query.message.chat_id
            callback_id = update.callback_query.data
            
            # Check if this appears to be a repeated callback
            if is_message_looping(chat_id, callback_id=callback_id):
                logger.warning(f"Prevented potential callback loop: {callback_id} in chat {chat_id}")
                return None
                
            # Otherwise, process normally
            return original_callback_func(update, context, *args, **kwargs)
        return original_callback_func(update, context, *args, **kwargs)
    return wrapped_callback
```

## Database Synchronization

To ensure database operations are safe, we consistently:

1. Import app within functions to avoid circular imports
2. Use `app.app_context()` for all database operations
3. Log all user activities for auditing and debugging
4. Handle exceptions consistently with proper error reporting

Example pattern:

```python
try:
    from app import app
    with app.app_context():
        # Perform database operations
        result = db_operation()
        db_utils.log_user_activity(user_id, "operation_name")
    
    # Use result outside app context (no db operations)
    if result:
        # Success response
    else:
        # Alternative response
except Exception as e:
    logger.error(f"Error in operation: {e}", exc_info=True)
    # Error response to user
```

This pattern ensures safe database transactions that don't block the Telegram response.