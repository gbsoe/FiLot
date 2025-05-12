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
    user = update.effective_user
    message = update.effective_message
    
    # Log activity
    from app import app
    with app.app_context():
        db_utils.log_user_activity(user.id, "invest_flow_start")
    
    # Ask for amount
    await message.reply_text(
        "How much would you like to invest? Please reply with a number (e.g. 100).",
        reply_markup=BACK_KEYBOARD
    )
    
    # Set state to await amount
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
            await message.reply_text(
                "Please provide a valid amount. For example: 100",
                reply_markup=BACK_KEYBOARD
            )
            return
    
    # Validate amount
    if amount <= 0:
        await message.reply_text(
            "Amount must be positive. Please try again with a valid amount.",
            reply_markup=BACK_KEYBOARD
        )
        return
    
    # Store amount in user data
    context.user_data["invest_amount"] = amount
    
    # Log activity
    from app import app
    with app.app_context():
        db_utils.log_user_activity(user.id, f"invest_amount_{amount}")
    
    # Ask for risk profile
    await message.reply_text(
        f"Great! You want to invest ${amount:.2f}.\n\n"
        "What risk profile would you prefer?",
        reply_markup=RISK_PROFILE_KEYBOARD
    )
    
    # Set state to await profile
    context.user_data["state"] = STATE_AWAITING_PROFILE

async def process_risk_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Process the risk profile selection
    
    Args:
        update: Telegram update object
        context: Callback context
    """
    user = update.effective_user
    message = update.effective_message
    text = message.text.lower()
    
    # Normalize profile input
    if "high" in text or "risk" in text:
        profile = "high-risk"
    elif "stable" in text or "safe" in text or "conservative" in text:
        profile = "stable"
    else:
        await message.reply_text(
            "Please select either 'High-risk' or 'Stable' as your risk profile.",
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
    Handle back to main menu button press
    
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
    
    # Show main menu
    await message.reply_text(
        "Back to main menu. Please select an option:",
        reply_markup=MAIN_KEYBOARD
    )