# Explore Button Implementation Walkthrough

This document provides a detailed breakdown of the Explore button implementation, focusing on button behavior, database interactions, and error handling. It serves as a companion to the navigation map and provides implementation-specific details.

## Explore Button Main Menu

### Implementation Details

- **Entry Point**: `/explore` command or "🔍 Explore" persistent button
- **Callback Data**: None (direct command) or embedded in `update.message`
- **Handler Function**: `explore_command` in `bot.py`

### Database Interactions

```python
# Log command activity
from app import app
with app.app_context():
    db_utils.log_user_activity(user.id, "explore_command")
```

### UI Elements

```python
# Import the explore menu keyboard
from menus import get_explore_menu
from keyboard_utils import MAIN_KEYBOARD

# Send the explore menu with inline buttons
await message.reply_markdown(
    "🔍 *Explore FiLot Opportunities*\n\n"
    "What would you like to explore today?",
    reply_markup=get_explore_menu()
)

# Ensure persistent keyboard stays visible
await message.reply_text(
    "Choose an option above or use the menu below 👆",
    reply_markup=MAIN_KEYBOARD
)
```

## Top Pools Flow

### Implementation Details

- **Callback Data**: `explore_pools`
- **Handler Function**: Explore pools section in `handle_callback_query`

### Pool Data Retrieval

```python
# Get top pools data from API or cached data
async def get_top_pools(limit=10, sort_by="apr"):
    """Retrieve top-performing liquidity pools."""
    try:
        # Try to get from Raydium API
        from raydium_client import get_client
        client = get_client()
        if client:
            pools = await client.get_pools(limit=limit)
            if pools:
                # Sort by specified criteria
                if sort_by == "apr":
                    pools = sorted(pools, key=lambda p: float(p.get("apr", 0)), reverse=True)
                elif sort_by == "tvl":
                    pools = sorted(pools, key=lambda p: float(p.get("tvl", 0)), reverse=True)
                return pools[:limit]
        
        # Fallback to cached data
        from api_mock_data import get_mock_pools
        return get_mock_pools(limit=limit)
    except Exception as e:
        logger.error(f"Error getting top pools: {e}", exc_info=True)
        # Fallback to predefined data in case of error
        from response_data import get_pool_data as get_predefined_pool_data
        return get_predefined_pool_data()
```

### UI Elements

```python
# Format pools for display
pools_message = "🏆 *Top Performing Pools*\n\n"

for i, pool in enumerate(pools[:5], 1):
    name = pool.get("name", "Unknown Pool")
    apr = pool.get("apr", 0)
    tvl = pool.get("tvl", 0)
    token_pair = pool.get("token_pair", "Unknown/Unknown")
    
    pools_message += (
        f"*{i}. {name}*\n"
        f"APR: {apr:.2f}%\n"
        f"TVL: ${tvl:,.2f}\n"
        f"Tokens: {token_pair}\n\n"
    )

pools_message += "_Select a pool below for more details_"

# Create pool selection buttons
pool_buttons = []
for i, pool in enumerate(pools[:5]):
    pool_id = pool.get("id", f"pool_{i}")
    pool_name = pool.get("name", f"Pool {i+1}")
    pool_buttons.append([
        InlineKeyboardButton(f"{i+1}. {pool_name}", callback_data=f"pool_detail_{pool_id}")
    ])

# Add filter and navigation buttons
filter_buttons = [
    InlineKeyboardButton("📊 Sort by APR", callback_data="sort_pools_apr"),
    InlineKeyboardButton("💰 Sort by TVL", callback_data="sort_pools_tvl")
]
pool_buttons.append(filter_buttons)

navigation_buttons = [
    InlineKeyboardButton("⬅️ Back to Explore", callback_data="menu_explore"),
    InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main")
]
pool_buttons.append(navigation_buttons)
```

## Simulate Returns Flow

### Implementation Details

- **Callback Data**: `explore_simulate`
- **Handler Function**: Explore simulate section in `handle_callback_query`

### UI Elements - Simulation Amount Selection

```python
# Create simulation menu
simulation_message = (
    "📊 *Simulate Investment Returns*\n\n"
    "Select an amount to see potential returns across different pools:"
)

simulation_buttons = [
    [
        InlineKeyboardButton("$100 💸", callback_data="simulate_100"),
        InlineKeyboardButton("$500 💸", callback_data="simulate_500")
    ],
    [
        InlineKeyboardButton("$1,000 💰", callback_data="simulate_1000"),
        InlineKeyboardButton("$5,000 💰", callback_data="simulate_5000")
    ],
    [
        InlineKeyboardButton("✏️ Custom Amount", callback_data="simulate_custom")
    ],
    [
        InlineKeyboardButton("⬅️ Back to Explore", callback_data="menu_explore"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main")
    ]
]
```

### Simulation Calculation

```python
# Calculate returns for different time periods
async def calculate_returns(pools, amount):
    """Calculate potential returns for a list of pools based on investment amount."""
    simulation_results = []
    
    for pool in pools:
        apr = float(pool.get("apr", 0))
        pool_id = pool.get("id", "unknown")
        pool_name = pool.get("name", "Unknown Pool")
        token_pair = pool.get("token_pair", "Unknown/Unknown")
        
        # Calculate daily, weekly, monthly, and yearly returns
        daily_return = amount * (apr / 100 / 365)
        weekly_return = daily_return * 7
        monthly_return = daily_return * 30
        yearly_return = amount * (apr / 100)
        
        simulation_results.append({
            "pool_id": pool_id,
            "pool_name": pool_name,
            "token_pair": token_pair,
            "apr": apr,
            "investment": amount,
            "daily_return": daily_return,
            "weekly_return": weekly_return,
            "monthly_return": monthly_return,
            "yearly_return": yearly_return
        })
    
    # Sort by highest yearly return
    return sorted(simulation_results, key=lambda x: x["yearly_return"], reverse=True)
```

### UI Elements - Simulation Results

```python
# Format simulation results
simulation_message = f"💰 *Investment Simulation: ${amount:,.2f}*\n\n"

for i, result in enumerate(simulation_results[:5], 1):
    name = result["pool_name"]
    apr = result["apr"]
    monthly_return = result["monthly_return"]
    yearly_return = result["yearly_return"]
    
    simulation_message += (
        f"*{i}. {name}*\n"
        f"APR: {apr:.2f}%\n"
        f"Monthly: ${monthly_return:.2f}\n"
        f"Yearly: ${yearly_return:.2f}\n\n"
    )

simulation_message += "_Select a pool below for detailed simulation_"

# Create pool selection buttons
result_buttons = []
for i, result in enumerate(simulation_results[:5]):
    pool_id = result["pool_id"]
    pool_name = result["pool_name"]
    result_buttons.append([
        InlineKeyboardButton(
            f"{i+1}. {pool_name}", 
            callback_data=f"simulation_detail_{pool_id}_amount_{amount}"
        )
    ])

# Add action and navigation buttons
action_buttons = [
    InlineKeyboardButton("💰 Invest This Amount", callback_data=f"invest_amount_{amount}"),
    InlineKeyboardButton("📊 Try Different Amount", callback_data="explore_simulate")
]
result_buttons.append(action_buttons)

navigation_buttons = [
    InlineKeyboardButton("⬅️ Back to Explore", callback_data="menu_explore"),
    InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main")
]
result_buttons.append(navigation_buttons)
```

## Pool Details from Explore

### Implementation Details

- **Callback Data**: `pool_detail_X` (where X is the pool ID)
- **Handler Function**: Pool detail section in `handle_callback_query`

### Pool Data Retrieval and Analysis

```python
# Get detailed pool information and analytics
async def get_detailed_pool_analysis(pool_id):
    """Get comprehensive information about a pool including performance metrics."""
    try:
        # Get basic pool details
        pool_details = await get_pool_details(pool_id)
        if not pool_details:
            return None
        
        # Enhance with historical data if available
        from raydium_client import get_client
        client = get_client()
        if client:
            history = await client.get_pool_history(pool_id, days=30)
            if history:
                # Calculate volatility and trend from historical data
                apr_values = [float(entry.get("apr", 0)) for entry in history]
                
                # Calculate volatility (standard deviation)
                if len(apr_values) > 1:
                    import numpy as np
                    volatility = np.std(apr_values)
                    pool_details["apr_volatility"] = volatility
                
                # Calculate trend (positive or negative)
                if len(apr_values) > 5:
                    trend = apr_values[-1] - apr_values[0]
                    pool_details["apr_trend"] = trend
                    pool_details["apr_trend_percentage"] = (trend / apr_values[0]) * 100 if apr_values[0] > 0 else 0
        
        # Add risk assessment
        pool_details["risk_level"] = assess_pool_risk(pool_details)
        
        return pool_details
    except Exception as e:
        logger.error(f"Error getting detailed pool analysis: {e}", exc_info=True)
        return None
```

### Risk Assessment

```python
def assess_pool_risk(pool_details):
    """Assess the risk level of a pool based on various factors."""
    # Default to medium risk
    risk_level = "Medium"
    
    # Extract relevant metrics
    apr = float(pool_details.get("apr", 0))
    tvl = float(pool_details.get("tvl", 0))
    volume = float(pool_details.get("volume_24h", 0))
    volatility = float(pool_details.get("apr_volatility", 1))
    
    # Consider APR (very high APR often means higher risk)
    if apr > 100:
        risk_level = "High"
    elif apr < 15:
        risk_level = "Low"
    
    # Consider TVL (higher TVL usually means lower risk)
    if tvl > 10000000:  # $10M+
        risk_level = "Low" if risk_level != "High" else "Medium"
    elif tvl < 100000:  # <$100K
        risk_level = "High"
    
    # Consider volume (higher volume usually means lower risk due to liquidity)
    if volume > 1000000 and risk_level == "Medium":  # $1M+ daily volume
        risk_level = "Low"
    elif volume < 10000 and risk_level != "High":  # <$10K daily volume
        risk_level = "Medium"
    
    # Consider volatility if available
    if "apr_volatility" in pool_details:
        if volatility > 10 and risk_level != "High":
            risk_level = "Medium"
        elif volatility > 20:
            risk_level = "High"
    
    return risk_level
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
)

# Add trend information if available
if "apr_trend_percentage" in pool_details:
    trend = pool_details["apr_trend_percentage"]
    trend_emoji = "📈" if trend > 0 else "📉"
    pool_message += f"*APR Trend (30d):* {trend_emoji} {trend:.2f}%\n\n"

# Add historical context if available
if "apr_volatility" in pool_details:
    volatility = pool_details["apr_volatility"]
    pool_message += f"*APR Volatility:* {volatility:.2f}%\n\n"

pool_message += "*What would you like to do?*"

# Create action buttons
action_buttons = [
    [InlineKeyboardButton("📊 Simulate Investment", callback_data=f"simulate_pool_{pool_id}")],
    [InlineKeyboardButton("💰 Invest Now", callback_data=f"invest_in_pool_{pool_id}")],
    [InlineKeyboardButton("⬅️ Back to Pool List", callback_data="explore_pools")],
    [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="back_to_main")]
]
```

## Simulation Detail View

### Implementation Details

- **Callback Data**: `simulation_detail_X_amount_Y` (where X is pool ID, Y is amount)
- **Handler Function**: Simulation detail section in `handle_callback_query`

### Detailed Simulation Calculation

```python
# Calculate detailed simulation with compounding options
async def calculate_detailed_simulation(pool_id, amount):
    """Calculate detailed simulation for a specific pool with different compounding strategies."""
    try:
        # Get pool details
        pool_details = await get_pool_details(pool_id)
        if not pool_details:
            return None
        
        apr = float(pool_details.get("apr", 0))
        pool_name = pool_details.get("name", "Unknown Pool")
        token_pair = pool_details.get("token_pair", "Unknown/Unknown")
        
        # Calculate daily, weekly, monthly returns
        daily_return = amount * (apr / 100 / 365)
        weekly_return = daily_return * 7
        monthly_return = daily_return * 30
        
        # Calculate yearly returns with different compounding frequencies
        no_compound = amount * (apr / 100)  # Simple interest
        annual_compound = amount * ((1 + (apr / 100)) - 1)  # Annual compounding
        monthly_compound = amount * ((1 + (apr / 100 / 12)) ** 12 - 1)  # Monthly compounding
        daily_compound = amount * ((1 + (apr / 100 / 365)) ** 365 - 1)  # Daily compounding
        
        # Calculate potential impermanent loss scenarios
        # (This is simplified - real IL calculations are more complex)
        il_low = amount * 0.01  # 1% price change scenario
        il_medium = amount * 0.05  # 5% price change scenario
        il_high = amount * 0.15  # 15% price change scenario
        
        return {
            "pool_id": pool_id,
            "pool_name": pool_name,
            "token_pair": token_pair,
            "apr": apr,
            "investment": amount,
            "daily_return": daily_return,
            "weekly_return": weekly_return,
            "monthly_return": monthly_return,
            "yearly_simple": no_compound,
            "yearly_annual_compound": annual_compound,
            "yearly_monthly_compound": monthly_compound,
            "yearly_daily_compound": daily_compound,
            "il_low": il_low,
            "il_medium": il_medium,
            "il_high": il_high,
            "risk_level": assess_pool_risk(pool_details)
        }
    except Exception as e:
        logger.error(f"Error calculating detailed simulation: {e}", exc_info=True)
        return None
```

### UI Elements

```python
# Format detailed simulation results
simulation_detail_message = (
    f"📊 *Detailed Simulation: {pool_name}*\n\n"
    f"*Investment:* ${amount:,.2f}\n"
    f"*APR:* {apr:.2f}%\n"
    f"*Token Pair:* {token_pair}\n"
    f"*Risk Level:* {risk_level}\n\n"
    
    f"*Estimated Returns:*\n"
    f"Daily: ${daily_return:.2f}\n"
    f"Weekly: ${weekly_return:.2f}\n"
    f"Monthly: ${monthly_return:.2f}\n\n"
    
    f"*Yearly Returns (Compounding):*\n"
    f"Simple Interest: ${yearly_simple:.2f}\n"
    f"Annual Compounding: ${yearly_annual_compound:.2f}\n"
    f"Monthly Compounding: ${yearly_monthly_compound:.2f}\n"
    f"Daily Compounding: ${yearly_daily_compound:.2f}\n\n"
    
    f"*Potential Impermanent Loss:*\n"
    f"Low Volatility: -${il_low:.2f}\n"
    f"Medium Volatility: -${il_medium:.2f}\n"
    f"High Volatility: -${il_high:.2f}\n\n"
    
    f"_Note: Returns are estimates based on current APR. Actual returns may vary._"
)

# Create action buttons
action_buttons = [
    [InlineKeyboardButton("💰 Invest Now", callback_data=f"invest_in_pool_{pool_id}_amount_{amount}")],
    [InlineKeyboardButton("⬅️ Back to Simulation", callback_data=f"simulate_{amount}")],
    [InlineKeyboardButton("🔍 Back to Explore", callback_data="menu_explore")],
    [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="back_to_main")]
]
```

## Pool Filtering Flow

### Implementation Details

- **Callback Data**: `sort_pools_apr`, `sort_pools_tvl`, `filter_pools_risk_X`
- **Handler Function**: Pool sorting and filtering sections in `handle_callback_query`

### Sort Implementation

```python
# Sort pools based on specified criteria
async def sort_and_filter_pools(criteria="apr", risk_filter=None):
    """Get pools sorted by the specified criteria and optional risk filter."""
    try:
        # Get all pools
        all_pools = await get_top_pools(limit=20)
        
        # Apply risk filter if specified
        if risk_filter:
            filtered_pools = []
            for pool in all_pools:
                # Assess risk if not already present
                if "risk_level" not in pool:
                    pool["risk_level"] = assess_pool_risk(pool)
                
                # Add to filtered list if risk matches
                if pool["risk_level"].lower() == risk_filter.lower():
                    filtered_pools.append(pool)
            all_pools = filtered_pools
        
        # Sort by specified criteria
        if criteria == "apr":
            sorted_pools = sorted(all_pools, key=lambda p: float(p.get("apr", 0)), reverse=True)
        elif criteria == "tvl":
            sorted_pools = sorted(all_pools, key=lambda p: float(p.get("tvl", 0)), reverse=True)
        else:
            # Default to APR sorting
            sorted_pools = sorted(all_pools, key=lambda p: float(p.get("apr", 0)), reverse=True)
        
        return sorted_pools
    except Exception as e:
        logger.error(f"Error sorting and filtering pools: {e}", exc_info=True)
        # Fallback to predefined data
        from response_data import get_pool_data
        return get_pool_data()
```

### UI Elements - Filter Menu

```python
# Create filter menu
filter_message = (
    "🔍 *Filter Pools*\n\n"
    "Select filtering and sorting options:"
)

filter_buttons = [
    [
        InlineKeyboardButton("📈 Sort by APR", callback_data="sort_pools_apr"),
        InlineKeyboardButton("💰 Sort by TVL", callback_data="sort_pools_tvl")
    ],
    [
        InlineKeyboardButton("🟢 Low Risk", callback_data="filter_pools_risk_low"),
        InlineKeyboardButton("🟡 Medium Risk", callback_data="filter_pools_risk_medium"),
        InlineKeyboardButton("🔴 High Risk", callback_data="filter_pools_risk_high")
    ],
    [
        InlineKeyboardButton("🔄 Reset Filters", callback_data="reset_filters")
    ],
    [
        InlineKeyboardButton("⬅️ Back to Pools", callback_data="explore_pools"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main")
    ]
]
```

## Custom Amount Simulation

### Implementation Details

- **Callback Data**: `simulate_custom`
- **Handler Function**: Custom simulation amount section in `handle_callback_query`

### User Input Handling

```python
# Handler for custom simulation amount messages
async def handle_custom_simulation_amount(update, context):
    """Handle custom simulation amount input from user."""
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
                "⚠️ *Minimum simulation amount is $10*\n\n"
                "Please enter a higher amount:"
            )
            return
        
        if amount > 1000000:
            await update.message.reply_markdown(
                "⚠️ *Maximum simulation amount is $1,000,000*\n\n"
                "Please enter a lower amount:"
            )
            return
        
        # Show loading message
        await update.message.reply_markdown(
            "📊 *Processing Simulation*\n\n"
            "Calculating potential returns across different pools..."
        )
        
        # Run the simulation with the custom amount
        await simulate_investment_returns(update, context, amount)
        
    except ValueError:
        # Not a valid number
        await update.message.reply_markdown(
            "⚠️ *Invalid Amount Format*\n\n"
            "Please enter a valid number like `500` or `$1000`:"
        )
```

## Pool Simulator for a Specific Pool

### Implementation Details

- **Callback Data**: `simulate_pool_X` (where X is the pool ID)
- **Handler Function**: Pool simulation section in `handle_callback_query`

### UI Elements - Amount Selection for Specific Pool

```python
# Create simulation amount menu for a specific pool
pool_simulation_message = (
    f"📊 *Simulate Investment in {pool_name}*\n\n"
    f"Select an amount to see potential returns for this pool:"
)

pool_simulation_buttons = [
    [
        InlineKeyboardButton("$100 💸", callback_data=f"simulation_detail_{pool_id}_amount_100"),
        InlineKeyboardButton("$500 💸", callback_data=f"simulation_detail_{pool_id}_amount_500")
    ],
    [
        InlineKeyboardButton("$1,000 💰", callback_data=f"simulation_detail_{pool_id}_amount_1000"),
        InlineKeyboardButton("$5,000 💰", callback_data=f"simulation_detail_{pool_id}_amount_5000")
    ],
    [
        InlineKeyboardButton("✏️ Custom Amount", callback_data=f"simulate_pool_custom_{pool_id}")
    ],
    [
        InlineKeyboardButton("⬅️ Back to Pool Details", callback_data=f"pool_detail_{pool_id}"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main")
    ]
]
```

## Error Handling

### Common Error Patterns

Similar to the investment flows, we use try-except blocks with detailed logging and user-friendly messages:

```python
try:
    # Attempt exploration-related operation
    result = await exploration_operation()
    
    if result:
        # Handle success case
        await handle_success(result)
    else:
        # Handle empty result case
        await handle_empty_result()
        
except Exception as e:
    # Log detailed error for debugging
    logger.error(f"Error in exploration flow: {e}", exc_info=True)
    
    # Show user-friendly message
    await update.effective_message.reply_markdown(
        "❌ *Exploration Error*\n\n"
        "Sorry, we encountered an error while retrieving pool information. "
        "Please try again later or explore other options.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back to Explore Menu", callback_data="menu_explore")],
            [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="back_to_main")]
        ])
    )
```

### API Fallbacks

When external API requests fail, we use fallback data to ensure seamless user experience:

```python
# Attempt to get live data first
try:
    pools = await raydium_client.get_pools()
    if not pools:
        # Fallback to cached data if empty response
        raise Exception("Empty response from API")
except Exception as api_error:
    logger.warning(f"Failed to get live pool data: {api_error}. Using cached data.")
    
    # Use cached data as fallback
    pools = get_predefined_pool_data()
    
    # Add a note to the message
    message_prefix = (
        "ℹ️ _Using cached data - latest live data unavailable_\n\n"
    )
```

## Session State Management

To maintain context between different parts of the exploration flow:

```python
# Store exploration context in user data
context.user_data["explore_context"] = {
    "last_view": "pools_list",
    "sort_by": "apr",
    "risk_filter": None,
    "last_simulation_amount": amount if "amount" in locals() else None
}

# Retrieve context when needed
explore_context = context.user_data.get("explore_context", {})
last_view = explore_context.get("last_view", "pools_list")
sort_by = explore_context.get("sort_by", "apr")
```

## Database Logging

We log all user interactions with the explore features for analytics and personalization:

```python
# Log exploration activity in database
with app.app_context():
    # Log the activity
    db_utils.log_user_activity(user.id, f"explore_{activity_type}")
    
    # Update user's last explored pools and simulations
    if activity_type == "pool_view" and pool_id:
        user_record = db_utils.get_or_create_user(user.id)
        
        # Update last viewed pools list (keep last 5)
        last_viewed = user_record.last_viewed_pools or []
        if isinstance(last_viewed, str):
            import json
            last_viewed = json.loads(last_viewed)
        
        # Remove if already in list
        last_viewed = [p for p in last_viewed if p.get("id") != pool_id]
        
        # Add to front of list
        last_viewed.insert(0, {"id": pool_id, "name": pool_name, "timestamp": datetime.now().isoformat()})
        
        # Keep last 5
        last_viewed = last_viewed[:5]
        
        # Update in database
        user_record.last_viewed_pools = json.dumps(last_viewed)
        db.session.commit()
```

## Anti-Loop Protection

As with all other flows, exploration paths are protected against message loops:

```python
from anti_loop import is_message_looping, lock_message_processing

# Check if this is potentially a repeated message
if is_message_looping(chat_id, callback_id=callback_data):
    logger.warning(f"Prevented potential callback loop: {callback_data} in chat {chat_id}")
    return None
```

## Navigation Consistency

We maintain consistent navigation patterns for the exploration flow:

```python
# Standard navigation pattern for all explore screens
def get_explore_navigation_buttons(current_screen, pool_id=None):
    """Get standard navigation buttons based on current screen."""
    navigation_buttons = []
    
    # Add contextual back button
    if current_screen == "pool_detail" and pool_id:
        navigation_buttons.append(
            InlineKeyboardButton("⬅️ Back to Pools", callback_data="explore_pools")
        )
    elif current_screen == "simulation_detail":
        navigation_buttons.append(
            InlineKeyboardButton("⬅️ Back to Simulation", callback_data="explore_simulate")
        )
    else:
        navigation_buttons.append(
            InlineKeyboardButton("⬅️ Back to Explore", callback_data="menu_explore")
        )
    
    # Always add main menu button
    navigation_buttons.append(
        InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main")
    )
    
    return [navigation_buttons]  # Return as a row in a keyboard
```