"""
Investment flow manager for the simplified one-command UX
"""

import logging
import re
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import db_utils
from menus import get_invest_menu, get_main_menu
from keyboard_utils import MAIN_KEYBOARD, RISK_PROFILE_KEYBOARD, BACK_KEYBOARD, get_invest_confirmation_keyboard

# Configure logging
logger = logging.getLogger(__name__)

# User state constants
STATE_AWAITING_AMOUNT = "awaiting_amount"
STATE_AWAITING_PROFILE = "awaiting_profile"
STATE_AWAITING_CONFIRMATION = "awaiting_confirmation"

async def start_invest_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Start the investment flow by asking for amount
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    if not update or not context:
        logger.error("Update or context is None in start_invest_flow")
        return
    
    user = update.effective_user
    message = update.effective_message
    
    if not user or not message:
        logger.error("User or message is None in start_invest_flow")
        return
    
    # Log activity
    from app import app
    with app.app_context():
        db_utils.log_user_activity(user.id, "invest_flow_start")
    
    # Create inline keyboard with amount options
    keyboard = [
        [
            InlineKeyboardButton("$50", callback_data="amount_50"),
            InlineKeyboardButton("$100", callback_data="amount_100"),
            InlineKeyboardButton("$250", callback_data="amount_250")
        ],
        [
            InlineKeyboardButton("$500", callback_data="amount_500"),
            InlineKeyboardButton("$1,000", callback_data="amount_1000"),
            InlineKeyboardButton("$5,000", callback_data="amount_5000")
        ],
        [InlineKeyboardButton("Custom Amount", callback_data="amount_custom")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Ask for amount with a more engaging and button-focused message
    await message.reply_markdown(
        "💰 *Ready to Invest?* 💰\n\n"
        "With our One-Touch interface, simply select an investment amount below or choose 'Custom Amount' to enter a specific value.\n\n"
        "💡 *Tip:* All investment options can be managed through our convenient buttons - no typing required!",
        reply_markup=reply_markup
    )
    
    # Send follow-up with persistent keyboard as a reminder
    await message.reply_markdown(
        "👇 *Remember:* You can always use these buttons for quick navigation! 👇",
        reply_markup=MAIN_KEYBOARD
    )
    
    # Set state to await amount
    if hasattr(context, 'user_data'):
        context.user_data["state"] = STATE_AWAITING_AMOUNT

async def process_invest_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Process the investment amount from user input
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    user = update.effective_user
    message = update.effective_message
    text = message.text
    
    # Extract amount
    try:
        # First check if we have a clean number
        amount = float(text.strip())
    except ValueError:
        # Try to extract amount from text
        match = re.search(r'\$?(\d+(?:\.\d+)?)', text)
        if match:
            amount = float(match.group(1))
        else:
            # Create the amount keyboard for a more button-focused approach
            keyboard = [
                [
                    InlineKeyboardButton("$50", callback_data="amount_50"),
                    InlineKeyboardButton("$100", callback_data="amount_100"),
                    InlineKeyboardButton("$250", callback_data="amount_250")
                ],
                [
                    InlineKeyboardButton("$500", callback_data="amount_500"),
                    InlineKeyboardButton("$1,000", callback_data="amount_1000"),
                    InlineKeyboardButton("$5,000", callback_data="amount_5000")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await message.reply_markdown(
                "❓ *I couldn't understand that amount*\n\n"
                "With our One-Touch interface, you can simply select an amount below or type a specific number (e.g., 100):",
                reply_markup=reply_markup
            )
            
            # Also show the back button
            await message.reply_text(
                "Or go back to the main menu:",
                reply_markup=BACK_KEYBOARD
            )
            return
    
    # Validate amount
    if amount <= 0:
        # Create the amount keyboard again
        keyboard = [
            [
                InlineKeyboardButton("$50", callback_data="amount_50"),
                InlineKeyboardButton("$100", callback_data="amount_100"),
                InlineKeyboardButton("$250", callback_data="amount_250")
            ],
            [
                InlineKeyboardButton("$500", callback_data="amount_500"),
                InlineKeyboardButton("$1,000", callback_data="amount_1000"),
                InlineKeyboardButton("$5,000", callback_data="amount_5000")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_markdown(
            "⚠️ *Amount must be positive*\n\n"
            "Please select an investment amount from the options below or type a specific positive number:",
            reply_markup=reply_markup
        )
        return
    
    # Store amount in user data
    context.user_data["invest_amount"] = amount
    
    # Log activity
    from app import app
    with app.app_context():
        db_utils.log_user_activity(user.id, f"invest_amount_{amount}")
    
    # Ask for risk profile with improved one-command messaging
    await message.reply_markdown(
        f"✅ *Investment Amount: ${amount:,.2f}*\n\n"
        "Now, please select your risk profile with our One-Touch buttons below:\n\n"
        "• *High-Risk:* Higher potential returns with more volatility\n"
        "• *Stable:* Lower risk with more consistent returns",
        reply_markup=RISK_PROFILE_KEYBOARD
    )
    
    # Set state to await profile
    context.user_data["state"] = STATE_AWAITING_PROFILE

async def process_risk_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Process the risk profile selection - supports both button press and text input
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    user = update.effective_user
    message = update.effective_message
    text = message.text.lower() if message and message.text else ""
    
    # Normalize profile input - better handling of button text
    if "high" in text or "risk" in text or text == "🔴 high-risk":
        profile = "high-risk"
        profile_emoji = "🔴"
    elif "stable" in text or "safe" in text or "conservative" in text or text == "🟢 stable":
        profile = "stable"
        profile_emoji = "🟢"
    else:
        # Show the risk profile keyboard again with a clearer message that emphasizes buttons
        await message.reply_markdown(
            "🤔 *I didn't recognize that risk profile*\n\n"
            "With our One-Touch interface, please select one of these options:\n"
            "• *High-Risk:* Higher potential returns but more volatility\n"
            "• *Stable:* Lower risk with more consistent returns",
            reply_markup=RISK_PROFILE_KEYBOARD
        )
        return
    
    # Store profile in user data
    context.user_data["invest_profile"] = profile
    
    # Get investment amount
    amount = context.user_data.get("invest_amount", 100)  # Default to 100 if not specified
    
    # Log activity
    from app import app
    with app.app_context():
        db_utils.log_user_activity(user.id, f"invest_profile_{profile}")
        
        # Update user profile in database
        db_user = db_utils.get_or_create_user(user.id)
        db_user.risk_profile = profile
        from models import db
        db.session.commit()
    
    # Send confirmation with a more engaging message emphasizing one-command UX
    await message.reply_markdown(
        f"✅ *Risk Profile Selected: {profile.title()}* {profile_emoji}\n\n"
        f"With our One-Touch interface, I'll now find the best pools for your {profile} investment style.\n\n"
        f"💡 *Calculating optimal investment options...*"
    )
    
    # Get top pool recommendations for this profile
    pools = await get_top_pools_for_profile(profile, amount)
    
    # Store recommendations in user data
    context.user_data["invest_recommendations"] = pools
    
    # Format recommendations for display
    formatted_recommendations = format_pool_recommendations(pools, profile, amount)
    
    # Show recommendations with confirmation buttons
    if len(pools) >= 2:
        reply_markup = get_invest_confirmation_keyboard(pools[0], pools[1])
    else:
        # Fallback if we don't have enough recommendations
        reply_markup = get_invest_menu()
    
    await message.reply_markdown(
        f"*Investment Recommendations*\n\n"
        f"Based on your {profile} profile for ${amount:.2f}:\n\n"
        f"{formatted_recommendations}\n\n"
        f"Please select a pool to invest in:",
        reply_markup=reply_markup
    )
    
    # Set state to await confirmation
    context.user_data["state"] = STATE_AWAITING_CONFIRMATION

async def get_top_pools_for_profile(profile: str, amount: float) -> List[Dict[str, Any]]:
    """
    Get top pools based on risk profile and amount
    
    Args:
        profile: Risk profile ('high-risk' or 'stable')
        amount: Investment amount
        
    Returns:
        List of pool recommendations
    """
    from app import app
    
    try:
        with app.app_context():
            from models import Pool
            
            # Get top pools sorted by appropriate criteria
            if profile == "high-risk":
                # High risk favors higher APR
                pools = Pool.query.order_by(Pool.apr_24h.desc()).limit(5).all()
            else:
                # Stable favors higher TVL and moderate APR
                pools = Pool.query.filter(Pool.tvl > 10000).order_by(Pool.apr_24h.desc()).limit(5).all()
            
            # Convert to dictionaries
            pool_dicts = []
            for pool in pools:
                pool_dict = {
                    "id": pool.id,
                    "token_a": pool.token_a_symbol,
                    "token_b": pool.token_b_symbol,
                    "apr": pool.apr_24h,
                    "tvl": pool.tvl,
                    "fee": pool.fee
                }
                pool_dicts.append(pool_dict)
            
            return pool_dicts
    except Exception as e:
        logger.error(f"Error getting pool recommendations: {e}")
        # Return empty list on error
        return []

def format_pool_recommendations(pools: List[Dict[str, Any]], profile: str, amount: float) -> str:
    """
    Format pool recommendations for display
    
    Args:
        pools: List of pool recommendations
        profile: Risk profile
        amount: Investment amount
        
    Returns:
        Formatted text for display
    """
    if not pools:
        return "No pool recommendations available at this time."
    
    formatted_text = ""
    for i, pool in enumerate(pools[:3], 1):  # Show top 3 pools
        token_pair = f"{pool['token_a']}/{pool['token_b']}"
        apr = pool.get('apr', 0)
        tvl = pool.get('tvl', 0)
        fee = pool.get('fee', 0)
        
        # Calculate estimated returns
        daily_return = (apr / 365) * amount / 100
        monthly_return = daily_return * 30
        yearly_return = daily_return * 365
        
        formatted_text += (
            f"*{i}. {token_pair}*\n"
            f"• APR: {apr:.2f}%\n"
            f"• TVL: ${tvl:,.2f}\n"
            f"• Fee: {fee:.2f}%\n"
            f"• Est. Returns: ${yearly_return:.2f}/year (${monthly_return:.2f}/month)\n\n"
        )
    
    return formatted_text

async def confirm_investment(update: Update, context: ContextTypes.DEFAULT_TYPE, pool_id: str) -> None:
    """
    Confirm and execute an investment
    
    Args:
        update: Telegram update object
        context: Callback context
        pool_id: ID of the selected pool
    """
    user = update.effective_user
    query = update.callback_query
    
    # Get investment parameters from user data
    amount = context.user_data.get("invest_amount", 100)
    profile = context.user_data.get("invest_profile", "high-risk")
    recommendations = context.user_data.get("invest_recommendations", [])
    
    # Find the selected pool
    selected_pool = None
    for pool in recommendations:
        if pool["id"] == pool_id:
            selected_pool = pool
            break
    
    if not selected_pool:
        await query.message.reply_text(
            "Pool selection not found. Please start the investment process again.",
            reply_markup=MAIN_KEYBOARD
        )
        return
    
    # Log activity
    from app import app
    with app.app_context():
        db_utils.log_user_activity(user.id, f"invest_confirm_{pool_id}")
    
    # Get token pair
    token_pair = f"{selected_pool['token_a']}/{selected_pool['token_b']}"
    
    # Show processing message
    await query.message.reply_text(
        f"⏳ Processing your investment of ${amount:.2f} in {token_pair}...",
        reply_markup=MAIN_KEYBOARD
    )
    
    # Create a position in the database
    from app import app
    with app.app_context():
        try:
            # Import models
            from models import Position, PositionStatus, db
            
            # Create new position
            position = Position(
                user_id=user.id,
                pool_id=pool_id,
                token_a=selected_pool['token_a'],
                token_b=selected_pool['token_b'],
                amount=amount,
                entry_apr=selected_pool.get('apr', 0),
                entry_price_a=selected_pool.get('token_a_price', 0),
                entry_price_b=selected_pool.get('token_b_price', 0),
                created_at=datetime.now(),
                status=PositionStatus.ACTIVE
            )
            
            db.session.add(position)
            db.session.commit()
            
            # Show success message
            await query.message.reply_markdown(
                f"✅ *Investment Successful!*\n\n"
                f"You have invested ${amount:.2f} in {token_pair}.\n\n"
                f"• APR: {selected_pool.get('apr', 0):.2f}%\n"
                f"• Position ID: {position.id}\n"
                f"• Created: {position.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
                f"You can view your positions any time by typing 'my positions' or using the /positions command.",
                reply_markup=MAIN_KEYBOARD
            )
            
            # Add quick invest button for next steps
            from menus import get_main_menu
            await query.message.reply_text(
                "What would you like to do next?",
                reply_markup=get_main_menu()
            )
            
            # Reset state
            context.user_data.pop("state", None)
            
        except Exception as e:
            logger.error(f"Error creating position: {e}")
            await query.message.reply_text(
                "Sorry, there was an error processing your investment. Please try again later.",
                reply_markup=MAIN_KEYBOARD
            )

async def handle_back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle back to main menu button press with One-Touch Navigation
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    message = update.effective_message
    
    # Clear state
    context.user_data.pop("state", None)
    context.user_data.pop("invest_amount", None)
    context.user_data.pop("invest_profile", None)
    context.user_data.pop("invest_recommendations", None)
    
    # Import here to avoid circular imports
    from menus import get_main_menu
    
    # Show main menu options with One-Touch Navigation emphasis
    await message.reply_markdown(
        "🏠 *Back to Main Menu*\n\n"
        "Use our One-Touch Navigation to continue your journey. "
        "Just tap any button below to instantly access features!",
        reply_markup=get_main_menu()
    )
    
    # Also ensure the persistent keyboard is visible
    await message.reply_markdown(
        "👇 *Quick Access Buttons* 👇\n\n"
        "These persistent buttons are always available for one-tap navigation!",
        reply_markup=MAIN_KEYBOARD
    )

async def process_invest_amount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str) -> None:
    """
    Process amount selection from callback buttons in the investment flow
    
    Args:
        update: Telegram update object
        context: Callback context
        callback_data: The callback data containing the amount information
    """
    query = update.callback_query
    user = query.from_user
    
    if callback_data == "amount_custom":
        # User wants to enter a custom amount
        await query.message.reply_markdown(
            "💰 *Enter Your Investment Amount*\n\n"
            "Please enter how much you would like to invest. Just type a number (e.g. 100).\n\n"
            "💡 *Example:* 500 (represents $500 USD)",
            reply_markup=BACK_KEYBOARD
        )
        
        # Set state to await amount
        if hasattr(context, 'user_data'):
            context.user_data["state"] = STATE_AWAITING_AMOUNT
    else:
        # Parse the amount from the callback data
        amount = float(callback_data.replace("amount_", ""))
        
        # Store amount in user data
        if hasattr(context, 'user_data'):
            context.user_data["invest_amount"] = amount
        
        # Log activity
        from app import app
        with app.app_context():
            db_utils.log_user_activity(user.id, f"invest_amount_{amount}")
        
        # Ask for risk profile with improved one-command messaging
        await query.message.reply_markdown(
            f"✅ *Investment Amount: ${amount:,.2f}*\n\n"
            "Now, please select your risk profile with our One-Touch buttons below:\n\n"
            "• *High-Risk:* Higher potential returns with more volatility\n"
            "• *Stable:* Lower risk with more consistent returns",
            reply_markup=RISK_PROFILE_KEYBOARD
        )
        
        # Set state to await profile
        if hasattr(context, 'user_data'):
            context.user_data["state"] = STATE_AWAITING_PROFILE