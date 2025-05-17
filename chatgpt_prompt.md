# Help Fix FiLot Telegram Bot Account Buttons

I'm working on a cryptocurrency investment Telegram bot called FiLot, and I'm having issues with the account section buttons. Specifically, the "High-Risk Profile" and "Stable Profile" buttons aren't properly updating user profiles when clicked.

I've identified a potential issue where the button callback data formats are inconsistent across the codebase - sometimes they're defined as `account_profile_high-risk` and other times as `profile_high-risk`.

Here's the analysis of the issue:

```markdown
# FiLot Telegram Bot Account Button Analysis

## The Problem
The profile buttons in the account section of the FiLot Telegram bot aren't working properly. Specifically, the "High-Risk Profile" and "Stable Profile" buttons don't update user profiles when clicked.

## Key Files and Code Snippets

### 1. How Buttons Are Defined
The account menu buttons are defined as follows:

```python
# In main.py
def get_account_menu():
    """Get the account menu buttons."""
    return {
        "inline_keyboard": [
            [{"text": "💼 Connect Wallet", "callback_data": "account_wallet"}],
            [{"text": "🔴 High-Risk Profile", "callback_data": "account_profile_high-risk"}],
            [{"text": "🟢 Stable Profile", "callback_data": "account_profile_stable"}],
            [{"text": "🔔 Subscribe", "callback_data": "account_subscribe"}],
            [{"text": "🔕 Unsubscribe", "callback_data": "account_unsubscribe"}],
            [{"text": "❓ Help", "callback_data": "account_help"}],
            [{"text": "📊 Status", "callback_data": "account_status"}],
            [{"text": "🏠 Back to Main Menu", "callback_data": "back_to_main"}]
        ]
    }
```

However, in some places they are accessed differently:

```python
# In test_button_functionality.py
# Expected buttons in the account menu
expected_buttons = [
    ("💼 Connect Wallet", "account_wallet"),
    ("🔴 High-Risk Profile", "profile_high-risk"),  # Note the different callback_data
    ("🟢 Stable Profile", "profile_stable"),  # Note the different callback_data
    # ... other buttons
]
```

### 2. Callback Handler
The central callback handler has this structure:

```python
# In callback_handler.py
def route_callback(handler_context):
    """
    Route a callback to the appropriate handler based on the callback_data.
    """
    # Extract key context values
    callback_data = handler_context.get('callback_data', '')
    user_id = handler_context.get('user_id', 0)
    
    # Various nested if-else blocks to handle different callbacks
    if callback_data.startswith("account_"):
        # Handle account section buttons
        if callback_data == "account_profile_high-risk":
            # Should handle high-risk profile button
            pass
        elif callback_data == "account_profile_stable":
            # Should handle stable profile button
            pass
        # ... more handlers
    # ... more handlers
```

### 3. Attempted Fixes
Several approaches have been attempted to fix the issue:

#### Direct SQL Approach
```python
# In fix_profile_buttons.py
def fix_profile_button(user_id: int, profile_type: str) -> Dict[str, Any]:
    """
    Directly handle profile button clicks without using the ORM.
    """
    try:
        # Connect to the database directly
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if user exists and update/create
        # ... database operations
        
        # Format message based on profile type
        # ... create response message
            
        return {
            'success': True,
            'message': profile_message
        }
        
    except Exception as e:
        logger.error(f"Error in profile button handler: {e}")
        return {
            'success': False,
            'message': "Sorry, there was an error setting your profile."
        }
```

#### Command-Based Approach
```python
# In direct_profile_commands.py
def set_risk_profile_command(update: Any, context: Any, profile_type: Optional[str] = None) -> None:
    """
    Direct command handler to set risk profile.
    """
    try:
        user = update.message.from_user
        user_id = user.id
        
        # Set the profile directly in the database
        success = set_user_profile(user_id, profile_type)
        
        if success:
            # Send success message
            update.message.reply_markdown(get_profile_message(profile_type))
        else:
            # Send error message
            update.message.reply_text(
                "Sorry, there was an error setting your profile."
            )
            
    except Exception as e:
        logger.error(f"Error in set_risk_profile_command: {e}")
        # ... error handling
```

## Inconsistency Issues

1. **Callback Data Format Mismatch**: The buttons are defined with `account_profile_high-risk` in some places but expected as `profile_high-risk` in others.

2. **Multiple Handlers**: Multiple modules try to handle the same buttons, potentially causing conflicts.

3. **Missing Integration**: The fixes are created but may not be properly integrated into the main callback handler flow.

4. **Database Access Conflicts**: Both ORM and direct SQL approaches are used, potentially causing data integrity issues.
```

Can you help me create a comprehensive fix for this problem? I need:

1. A solution that handles both callback data formats (`account_profile_high-risk` and `profile_high-risk`)
2. A reliable way to update the user profile in the database
3. A proper integration with the main callback handler
4. Any recommendations for standardizing the callback data format across the codebase

Please provide code examples and explain how each part works. Thank you!