# Invest Button Implementation Walkthrough

This document provides a detailed breakdown of the Invest button implementation, focusing on button behavior, database interactions, and error handling. It serves as a companion to the navigation map and provides implementation-specific details.

## Invest Button Main Menu

### Implementation Details

- **Entry Point**: `/invest` command or "💰 Invest" persistent button
- **Callback Data**: None (direct command) or embedded in `update.message`
- **Handler Function**: `invest_command` in `bot.py`

### Database Interactions

```python
# Log command activity
from app import app
with app.app_context():
    db_utils.log_user_activity(user.id, "invest_command")
```

### UI Elements

```python
# Import the investment menu keyboard
from menus import get_investment_menu
from keyboard_utils import MAIN_KEYBOARD

# Send the investment menu with inline buttons
await message.reply_markdown(
    "🧠 *Investment Recommendations*\n\n"
    "Select an investment amount or view your current positions:",
    reply_markup=get_investment_menu()
)

# Ensure persistent keyboard stays visible
await message.reply_text(
    "Choose an option above or use the menu below 👆",
    reply_markup=MAIN_KEYBOARD
)
```

## Preset Amount Selection Flow

### Implementation Details

- **Callback Data**: `amount_100`, `amount_250`, `amount_500`, `amount_1000`, `amount_5000`
- **Handler Function**: `process_invest_amount_callback` in `investment_flow.py`

### Database Interactions

The amount selection process interacts with the database to:
1. Store the selected amount in the user's temporary context
2. Log the user activity for analytics

```python
# Store investment amount in user context (memory or database)
with app.app_context():
    # Store amount in user data
    context.user_data["invest_amount"] = amount
    
    # Log this activity
    db_utils.log_user_activity(user.id, f"select_amount_{amount}")
```

### Pool Recommendations

```python
# Display top pool recommendations based on the amount and user's risk profile
async def display_pool_recommendations(update, context, amount):
    """Display top pool recommendations based on amount and risk profile."""
    try:
        # Get user's risk profile from database if available
        user = update.effective_user
        risk_profile = "moderate"  # Default
        
        from app import app
        with app.app_context():
            db_user = db_utils.get_or_create_user(user.id)
            if db_user and db_user.risk_profile:
                risk_profile = db_user.risk_profile
        
        # Get pool recommendations (simulated or from API)
        pools = await get_pool_recommendations(amount, risk_profile)
        
        # Format pool recommendations
        from pool_formatter import format_pool_recommendations
        recommendations_text = format_pool_recommendations(pools, amount)
        
        # Create pool selection buttons
        pool_buttons = []
        for i, pool in enumerate(pools[:5]):  # Limit to top 5
            pool_id = pool.get("id", f"pool_{i}")
            pool_name = pool.get("name", f"Pool {i+1}")
            pool_buttons.append([
                InlineKeyboardButton(f"{i+1}. {pool_name}", callback_data=f"pool_recommendation_{pool_id}")
            ])
        
        # Add navigation buttons
        pool_buttons.append([
            InlineKeyboardButton("⬅️ Back to Invest", callback_data="menu_invest"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main")
        ])
        
        # Send recommendations with pool selection buttons
        await update.effective_message.reply_markdown(
            f"💰 *Top Pool Recommendations for ${amount}*\n\n"
            f"{recommendations_text}\n\n"
            f"Select a pool number to view details and invest:",
            reply_markup=InlineKeyboardMarkup(pool_buttons)
        )
        
    except Exception as e:
        logger.error(f"Error displaying pool recommendations: {e}", exc_info=True)
        await update.effective_message.reply_text(
            "Sorry, there was an error getting pool recommendations. Please try again later."
        )
```

## Custom Amount Flow

### Implementation Details

- **Callback Data**: `amount_custom`
- **Handler Function**: Custom amount section in both `main.py` and `bot.py`

### User Input Handling

```python
# Handler for custom amount messages after the custom amount button
async def handle_custom_amount(update, context):
    """Handle custom amount input from user."""
    # Get the message text and parse it
    message_text = update.message.text.strip()
    
    # Remove $ sign and any commas if present
    amount_text = message_text.replace("$", "").replace(",", "")
    
    try:
        # Convert to float
        amount = float(amount_text)
        
        # Check if amount is within reasonable range
        if amount < 10:
            await update.message.reply_markdown(
                "⚠️ *Minimum investment amount is $10*\n\n"
                "Please enter a higher amount:"
            )
            return
        
        if amount > 1000000:
            await update.message.reply_markdown(
                "⚠️ *Maximum investment amount is $1,000,000*\n\n"
                "Please enter a lower amount:"
            )
            return
        
        # Show loading message
        await update.message.reply_markdown(
            "💰 *Processing Custom Amount*\n\n"
            "Getting the best pool recommendations for you..."
        )
        
        # Use same flow as preset amounts
        await display_pool_recommendations(update, context, amount)
        
    except ValueError:
        # Not a valid number
        await update.message.reply_markdown(
            "⚠️ *Invalid Amount Format*\n\n"
            "Please enter a valid number like `500` or `$1000`:"
        )
```

## Pool Detail View

### Implementation Details

- **Callback Data**: `pool_recommendation_X` (where X is the pool ID)
- **Handler Function**: Pool recommendation section in `handle_callback_query`

### Pool Data Retrieval

```python
# Get pool details from API or cached data
async def get_pool_details(pool_id):
    """Retrieve detailed information about a specific pool."""
    try:
        # Try to get from Raydium API
        from raydium_client import get_client
        client = get_client()
        if client:
            pool_details = await client.get_pool_detail(pool_id)
            if pool_details:
                return pool_details
        
        # Fallback to cached data
        from api_mock_data import get_mock_pool_detail
        return get_mock_pool_detail(pool_id)
    except Exception as e:
        logger.error(f"Error getting pool details: {e}", exc_info=True)
        return None
```

### UI Elements

```python
# Format pool details for display
pool_message = (
    f"🏆 *{pool_name}*\n\n"
    f"*APR:* {apr_percentage}%\n"
    f"*Total Value Locked:* ${tvl_formatted}\n"
    f"*Tokens:* {token_pair}\n"
    f"*Volume (24h):* ${volume_24h_formatted}\n"
    f"*Risk Level:* {risk_level}\n\n"
    f"*Investment Summary:*\n"
    f"Amount: ${amount:.2f}\n"
    f"Estimated Daily: ${estimated_daily:.2f}\n"
    f"Estimated Monthly: ${estimated_monthly:.2f}\n"
    f"Estimated Yearly: ${estimated_yearly:.2f}\n\n"
    f"_Note: Returns are estimates based on current APR_"
)

# Create action buttons
action_buttons = [
    [InlineKeyboardButton("💰 Invest Now", callback_data=f"invest_in_pool_{pool_id}_amount_{amount}")],
    [InlineKeyboardButton("⬅️ Back to Recommendations", callback_data="back_to_recommendations")],
    [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="back_to_main")]
]
```

## View Positions Flow

### Implementation Details

- **Callback Data**: `menu_positions`
- **Handler Function**: Positions command in `bot.py` and position section in `investment_flow.py`

### Database Interactions

```python
# Get user's active positions from database
from app import app
from models import Position
positions = []

with app.app_context():
    # Get positions for the current user
    db_positions = Position.query.filter_by(user_id=user.id, is_active=True).all()
    
    # Convert to dictionary for easier handling
    for pos in db_positions:
        positions.append({
            "id": pos.id,
            "pool_id": pos.pool_id,
            "pool_name": pos.pool_name,
            "amount": pos.amount,
            "token_pair": pos.token_pair,
            "apr": pos.apr,
            "entry_date": pos.created_at.strftime("%Y-%m-%d")
        })
```

### UI Elements

```python
# Format positions or show empty state
if positions:
    # Create buttons for each position
    position_buttons = []
    for pos in positions:
        pos_id = pos.get("id")
        pool_name = pos.get("pool_name", "Unknown Pool")
        amount = pos.get("amount", 0)
        position_buttons.append([
            InlineKeyboardButton(
                f"{pool_name} (${amount:.2f})", 
                callback_data=f"position_detail_{pos_id}"
            )
        ])
    
    # Add navigation buttons
    position_buttons.append([
        InlineKeyboardButton("⬅️ Back to Invest", callback_data="menu_invest"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main")
    ])
    
    # Send positions list
    await message.reply_markdown(
        "👀 *Your Active Positions*\n\n"
        "Select a position to view details:",
        reply_markup=InlineKeyboardMarkup(position_buttons)
    )
else:
    # No positions message
    no_positions_buttons = [
        [InlineKeyboardButton("💰 Invest Now", callback_data="menu_invest")],
        [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="back_to_main")]
    ]
    
    await message.reply_markdown(
        "🔍 *No Active Positions*\n\n"
        "You don't have any active positions yet. Start investing to see your positions here!",
        reply_markup=InlineKeyboardMarkup(no_positions_buttons)
    )
```

## Position Detail View

### Implementation Details

- **Callback Data**: `position_detail_X` (where X is the position ID)
- **Handler Function**: Position detail section in `handle_callback_query`

### Position Data Retrieval

```python
# Get position details from database
async def get_position_detail(position_id, user_id):
    """Get detailed information about a user's position."""
    try:
        from app import app
        from models import Position
        
        with app.app_context():
            # Ensure position belongs to the correct user (security check)
            position = Position.query.filter_by(id=position_id, user_id=user_id).first()
            
            if not position:
                return None
            
            # Calculate current value and gains
            current_apr = position.apr  # Get updated APR if available
            entry_date = position.created_at
            days_held = (datetime.now() - entry_date).days
            estimated_gain = (position.amount * current_apr / 100 / 365) * days_held
            
            return {
                "id": position.id,
                "pool_id": position.pool_id,
                "pool_name": position.pool_name,
                "amount": position.amount,
                "token_pair": position.token_pair,
                "apr": current_apr,
                "entry_date": entry_date.strftime("%Y-%m-%d"),
                "days_held": days_held,
                "estimated_gain": estimated_gain,
                "current_value": position.amount + estimated_gain
            }
    except Exception as e:
        logger.error(f"Error getting position detail: {e}", exc_info=True)
        return None
```

### UI Elements

```python
# Format position details for display
position_message = (
    f"💼 *Position Details: {position['pool_name']}*\n\n"
    f"*Investment Amount:* ${position['amount']:.2f}\n"
    f"*Token Pair:* {position['token_pair']}\n"
    f"*Current APR:* {position['apr']:.2f}%\n"
    f"*Entry Date:* {position['entry_date']}\n"
    f"*Days Held:* {position['days_held']}\n\n"
    f"*Performance:*\n"
    f"Estimated Gain: ${position['estimated_gain']:.2f}\n"
    f"Current Value: ${position['current_value']:.2f}\n\n"
    f"_Note: Values are estimates based on current APR_"
)

# Action buttons for position
position_buttons = [
    [InlineKeyboardButton("🚪 Exit Position", callback_data=f"exit_position_{position['id']}")],
    [InlineKeyboardButton("⬅️ Back to Positions", callback_data="menu_positions")],
    [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="back_to_main")]
]
```

## Exit Position Flow

### Implementation Details

- **Callback Data**: `exit_position_X` (where X is the position ID)
- **Handler Function**: Exit position section in `handle_callback_query`

### Confirmation UI

```python
# Create confirmation message and buttons
confirmation_message = (
    f"🚪 *Exit Position Confirmation*\n\n"
    f"You are about to exit your position in *{position['pool_name']}*\n\n"
    f"*Investment:* ${position['amount']:.2f}\n"
    f"*Current Value:* ${position['current_value']:.2f}\n"
    f"*Estimated Gain:* ${position['estimated_gain']:.2f}\n\n"
    f"Are you sure you want to exit this position?"
)

confirmation_buttons = [
    [InlineKeyboardButton("✅ Confirm Exit", callback_data=f"confirm_exit_{position_id}")],
    [InlineKeyboardButton("❌ Cancel", callback_data=f"position_detail_{position_id}")],
]
```

### Database Operations

```python
# Process the exit in the database
async def process_position_exit(position_id, user_id):
    """Process the exit of a position in the database."""
    try:
        from app import app
        from models import Position, db
        
        with app.app_context():
            # Find the position and verify ownership
            position = Position.query.filter_by(id=position_id, user_id=user_id).first()
            
            if not position:
                return {"success": False, "error": "Position not found"}
            
            # Record exit details before updating
            exit_details = {
                "pool_name": position.pool_name,
                "amount": position.amount,
                "entry_date": position.created_at.strftime("%Y-%m-%d"),
                "exit_date": datetime.now().strftime("%Y-%m-%d")
            }
            
            # Update position status
            position.is_active = False
            position.exited_at = datetime.now()
            
            # Calculate and store gains (in a real system)
            # position.exit_amount = calculated_exit_amount
            # position.gain = position.exit_amount - position.amount
            
            # Save changes
            db.session.commit()
            
            # Log activity
            db_utils.log_user_activity(user_id, f"exit_position_{position_id}")
            
            return {"success": True, "details": exit_details}
    except Exception as e:
        logger.error(f"Error processing position exit: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

## Invest in Pool Flow

### Implementation Details

- **Callback Data**: `invest_in_pool_X_amount_Y` (where X is pool ID, Y is amount)
- **Handler Function**: Invest in pool section in `handle_callback_query`

### Wallet Connection Check

```python
# Check if user has a connected wallet
async def has_connected_wallet(user_id):
    """Check if the user has a connected wallet."""
    try:
        # Import wallet utils at function level to avoid circular imports
        from wallet_utils import get_wallet_address
        
        # Check if user has a connected wallet
        wallet_address = await get_wallet_address(user_id)
        return bool(wallet_address)
    except Exception as e:
        logger.error(f"Error checking wallet connection: {e}", exc_info=True)
        return False
```

### Investment Execution

```python
# Process the investment in the database
async def process_investment(user_id, pool_id, pool_name, amount, token_pair, apr):
    """Record a new investment position in the database."""
    try:
        from app import app
        from models import Position, db
        
        with app.app_context():
            # Create new position
            new_position = Position(
                user_id=user_id,
                pool_id=pool_id,
                pool_name=pool_name,
                amount=amount,
                token_pair=token_pair,
                apr=apr,
                is_active=True
            )
            
            # Add to database
            db.session.add(new_position)
            db.session.commit()
            
            # Get the new position ID
            position_id = new_position.id
            
            # Log activity
            db_utils.log_user_activity(user_id, f"invest_pool_{pool_id}_amount_{amount}")
            
            return {"success": True, "position_id": position_id}
    except Exception as e:
        logger.error(f"Error processing investment: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
```

## Error Handling

### Common Error Patterns

Throughout the investment flows, we consistently handle errors using try-except blocks with:

1. Detailed error logging with full stack traces
2. User-friendly error messages that don't expose internal details
3. Fallback options to allow users to navigate away from error states

Example pattern:

```python
try:
    # Attempt investment-related operation
    result = await investment_operation()
    
    if result["success"]:
        # Handle success case
        await handle_success(result)
    else:
        # Handle known failure case
        await handle_known_failure(result)
        
except Exception as e:
    # Log detailed error for debugging
    logger.error(f"Error in investment flow: {e}", exc_info=True)
    
    # Show user-friendly message
    await update.effective_message.reply_markdown(
        "❌ *Investment Error*\n\n"
        "Sorry, we encountered an error while processing your investment. "
        "Please try again later or contact support if the issue persists.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Invest Menu", callback_data="menu_invest")],
            [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="back_to_main")]
        ])
    )
```

### API Connection Failures

When connections to external APIs fail, we implement graceful fallbacks:

```python
# Try to get pool data from API
try:
    pools = await raydium_client.get_pools(min_tvl=min_tvl, min_apr=min_apr)
    if not pools:
        # Fallback to cached data
        raise Exception("Empty response from API")
except Exception as api_error:
    logger.warning(f"Failed to get live pool data: {api_error}. Using cached data.")
    # Use cached data as fallback
    pools = get_predefined_pool_data()
```

## Session State Management

To maintain session state between different callbacks, we use a combination of:

1. Context user data for ephemeral information
2. Database for persistent state that should survive restarts

Example of context-based state:

```python
# Store temporary information for the current session
context.user_data["invest_flow"] = {
    "amount": amount,
    "selected_pool": pool_id,
    "risk_profile": user_risk_profile,
    "last_screen": "pool_detail"
}
```

Example of database-based state:

```python
# Store persistent information in the database
with app.app_context():
    user_record = db_utils.get_or_create_user(user.id)
    user_record.last_interaction = datetime.now()
    user_record.last_action = "view_pool"
    db.session.commit()
```

## Anti-Loop Protection

All investment flows are protected against message loops using the global anti-loop system:

```python
from anti_loop import is_message_looping, lock_message_processing

# Check if this is potentially a repeated message
if is_message_looping(chat_id, callback_id=callback_data):
    logger.warning(f"Prevented potential callback loop: {callback_data} in chat {chat_id}")
    return None
```

## Navigation Consistency

To maintain consistent navigation throughout the investment flow, we implement:

1. Back buttons on every screen that return to the logical previous screen
2. Main menu button on every screen for quick escape
3. Breadcrumb-style indications in message titles to show current location

```python
# Standard navigation pattern used in all investment screens
navigation_buttons = []

# Add contextual back button (varies based on current screen)
if current_screen == "pool_detail":
    navigation_buttons.append(
        InlineKeyboardButton("⬅️ Back to Recommendations", callback_data="back_to_recommendations")
    )
elif current_screen == "position_detail":
    navigation_buttons.append(
        InlineKeyboardButton("⬅️ Back to Positions", callback_data="menu_positions")
    )
else:
    navigation_buttons.append(
        InlineKeyboardButton("⬅️ Back to Invest", callback_data="menu_invest")
    )

# Always add main menu button
navigation_buttons.append(
    InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main")
)

# Add row to keyboard
keyboard.append(navigation_buttons)
```