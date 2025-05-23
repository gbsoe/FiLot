"""
Core bot functionality for the Telegram cryptocurrency pool bot
"""

import os
import logging
import re
import datetime
import asyncio
import io
import qrcode
from typing import Dict, List, Any, Optional, Union, Tuple
import traceback

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from dotenv import load_dotenv

# Import local modules
import db_utils
from models import User, Pool, UserQuery, CompositeSignal, Position, PositionStatus, db
from question_detector import get_predefined_response, is_question
from intent_detector import (
    is_investment_intent, is_position_inquiry, is_pool_inquiry, 
    is_wallet_inquiry, extract_amount
)
from raydium_client import get_client
from utils import format_pool_info, format_simulation_results, format_daily_update
from wallet_utils import connect_wallet, check_wallet_balance, calculate_deposit_strategy, get_wallet_balances
from investment_flow import (
    start_invest_flow, handle_back_to_main, 
    STATE_AWAITING_AMOUNT, STATE_AWAITING_PROFILE, STATE_AWAITING_CONFIRMATION,
    process_invest_amount, process_risk_profile, confirm_investment,
    get_top_pools_for_profile
)
from keyboard_utils import (
    MAIN_KEYBOARD, RISK_PROFILE_KEYBOARD, BACK_KEYBOARD, 
    INVEST_INLINE, get_invest_confirmation_keyboard, get_main_menu_inline
)
from walletconnect_utils import (
    create_walletconnect_session, 
    check_walletconnect_session, 
    kill_walletconnect_session,
    get_user_walletconnect_sessions,
    get_db_connection
)
from anthropic_service import AnthropicAI

# Import agentic components
from orchestrator import get_orchestrator
from scheduler import init_scheduler
from bot_commands import (
    recommend_command,
    execute_command,
    positions_command,
    exit_command,
    handle_agentic_callback_query,
    handle_position_alert
)

# Import menu utilities
from menus import (
    get_invest_menu,
    get_explore_menu,
    get_account_menu,
    get_custom_amount_menu,
    get_simulate_menu,
    get_exit_position_menu,
    get_main_menu
)

# Import keyboard utilities for persistent keyboards
from keyboard_utils import (
    MAIN_KEYBOARD,
    RISK_PROFILE_KEYBOARD,
    BACK_KEYBOARD,
    INVEST_INLINE
)

# Import investment flow handlers
from investment_flow import (
    start_invest_flow,
    process_invest_amount,
    process_risk_profile,
    confirm_investment,
    handle_back_to_main,
    STATE_AWAITING_AMOUNT,
    STATE_AWAITING_PROFILE,
    STATE_AWAITING_CONFIRMATION
)

# Initialize AI service
anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
ai_advisor = AnthropicAI(api_key=anthropic_api_key)

# Initialize orchestrator and scheduler
orchestrator = get_orchestrator()

# Load environment variables
load_dotenv()

# Configure logging to file
import os
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),  # Log to console
        logging.FileHandler('logs/bot.log')  # Log to file
    ]
)
logger = logging.getLogger(__name__)

# Helper function to update query response in database
async def update_query_response(query_id: int, response_text: str, processing_time: float) -> None:
    """
    Update a query in the database with its response and processing time.
    """
    try:
        # Import here to avoid circular imports
        from sqlalchemy.orm import Session
        from models import db, UserQuery
        
        # Create new session for thread safety
        with Session(db.engine) as session:
            query = session.query(UserQuery).filter(UserQuery.id == query_id).first()
            if query:
                query.response_text = response_text
                query.processing_time = processing_time
                session.commit()
                logger.debug(f"Updated query {query_id} with response")
    except Exception as e:
        logger.error(f"Error updating query response: {e}")

# Helper function to get pool data
async def get_pool_data() -> List[Any]:
    """Get pool data for display in commands."""
    try:
        # Import app and db here to avoid circular imports
        from app import app, db
        from models import Pool
        
        with app.app_context():
            try:
                # Try to get pools from database first
                pools = Pool.query.order_by(Pool.apr_24h.desc()).limit(5).all()
                
                # If no pools in database, use the predefined data
                if not pools or len(pools) == 0:
                    try:
                        # Import here to avoid circular imports
                        from response_data import get_pool_data as get_predefined_pool_data
                        
                        # Get predefined pool data
                        predefined_data = get_predefined_pool_data()
                        
                        # Process top APR pools from the predefined data
                        api_pools = predefined_data.get('topAPR', [])
                        
                        # Convert pools to Pool objects for formatting
                        pools = []
                        for pool_data in api_pools:
                            pool = Pool()
                            pool.id = pool_data.get("id", "unknown")
                            
                            # Extract token symbols from pair name
                            pair_name = pool_data.get("pairName", "UNKNOWN/UNKNOWN")
                            token_symbols = pair_name.split("/")
                            
                            pool.token_a_symbol = token_symbols[0] if len(token_symbols) > 0 else "Unknown"
                            pool.token_b_symbol = token_symbols[1] if len(token_symbols) > 1 else "Unknown"
                            
                            # Get token prices if available
                            token_prices = pool_data.get("tokenPrices", {})
                            pool.token_a_price = token_prices.get(pool.token_a_symbol, 0)
                            pool.token_b_price = token_prices.get(pool.token_b_symbol, 0)
                            
                            # Extract other pool data
                            pool.apr_24h = pool_data.get("apr", 0)
                            pool.apr_7d = pool_data.get("aprWeekly", 0)
                            pool.apr_30d = pool_data.get("aprMonthly", 0)
                            pool.tvl = pool_data.get("liquidity", 0)
                            pool.fee = pool_data.get("fee", 0) * 100  # Convert from decimal to percentage
                            pool.volume_24h = pool_data.get("volume24h", 0)
                            pool.tx_count_24h = pool_data.get("txCount", 0)
                            pools.append(pool)
                        
                        # Save pools to database for future use
                        db.session.add_all(pools)
                        db.session.commit()
                        logger.info(f"Saved {len(pools)} pools to database from predefined data")
                    except Exception as e:
                        logger.error(f"Error using predefined pool data: {e}")
                        pools = []
            except Exception as e:
                logger.error(f"Database error: {e}")
                # Fallback to using predefined data directly if database access fails
                try:
                    from response_data import get_pool_data as get_predefined_pool_data
                    from models import Pool
                    
                    predefined_data = get_predefined_pool_data()
                    api_pools = predefined_data.get('topAPR', [])
                    
                    pools = []
                    for pool_data in api_pools:
                        pool = Pool()
                        pool.id = pool_data.get("id", "unknown")
                        
                        # Extract token symbols from pair name
                        pair_name = pool_data.get("pairName", "UNKNOWN/UNKNOWN")
                        token_symbols = pair_name.split("/")
                        
                        pool.token_a_symbol = token_symbols[0] if len(token_symbols) > 0 else "Unknown"
                        pool.token_b_symbol = token_symbols[1] if len(token_symbols) > 1 else "Unknown"
                        
                        # Get token prices if available
                        token_prices = pool_data.get("tokenPrices", {})
                        pool.token_a_price = token_prices.get(pool.token_a_symbol, 0)
                        pool.token_b_price = token_prices.get(pool.token_b_symbol, 0)
                        
                        # Extract other pool data
                        pool.apr_24h = pool_data.get("apr", 0)
                        pool.apr_7d = pool_data.get("aprWeekly", 0)
                        pool.apr_30d = pool_data.get("aprMonthly", 0)
                        pool.tvl = pool_data.get("liquidity", 0)
                        pool.fee = pool_data.get("fee", 0) * 100  # Convert from decimal to percentage
                        pool.volume_24h = pool_data.get("volume24h", 0)
                        pool.tx_count_24h = pool_data.get("txCount", 0)
                        pools.append(pool)
                    
                    logger.info(f"Using {len(pools)} pools from predefined data without database")
                except Exception as e:
                    logger.error(f"Error creating fallback pool objects: {e}")
                    pools = []
                    
        return pools
    except Exception as e:
        logger.error(f"Error getting pool data: {e}")
        return []

# Command Handlers

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the command /start is issued."""
    try:
        logger.info("Starting command /start execution")
        user = update.effective_user
        logger.info(f"User info retrieved: {user.id} - {user.username}")
        
        # Use app context for database operations
        from app import app
        with app.app_context():
            # Log user activity
            db_utils.get_or_create_user(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            logger.info(f"User {user.id} created or retrieved from database")
            
            db_utils.log_user_activity(user.id, "start_command")
            logger.info(f"Activity logged for user {user.id}")
        
        # Import here to avoid circular imports
        from menus import get_main_menu
        
        logger.info(f"Sending welcome message to user {user.id}")
        
        # Import keyboard utilities
        from keyboard_utils import MAIN_KEYBOARD, get_main_menu_inline
        
        # Send a single welcome message with persistent keyboard
        await update.message.reply_markdown(
            f"👋 Welcome to FiLot, {user.first_name}!\n\n"
            "I'm your AI-powered investment assistant for cryptocurrency liquidity pools. "
            "With just one tap, you can now invest, explore, and manage your account!\n\n"
            "🤖 *New One-Touch Interface*\n"
            "• Tap 💰 *Invest* to get personalized investment recommendations\n"
            "• Tap 🔍 *Explore* to discover top pools and simulate returns\n"
            "• Tap 👤 *Account* to connect wallet and set preferences\n\n"
            "I can also answer any questions about cryptocurrencies and help guide your investment decisions!",
            reply_markup=MAIN_KEYBOARD
        )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        from keyboard_utils import MAIN_KEYBOARD
        await update.message.reply_markdown(
            "Sorry, an error occurred while processing your request.\n\n"
            "Please try the buttons below to access features:",
            reply_markup=MAIN_KEYBOARD
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when the command /help is issued."""
    try:
        from app import app
        with app.app_context():
            user = update.effective_user
            db_utils.log_user_activity(user.id, "help_command")
        
        # Import our keyboard utilities
        from keyboard_utils import get_main_menu_inline, MAIN_KEYBOARD
        
        # Send help message with focus on the enhanced One-Touch UX approach
        await update.message.reply_markdown(
            "✨ *Welcome to FiLot's One-Touch Navigation* ✨\n\n"
            "*Our new interface requires just a single tap:*\n"
            "• 💰 *Invest* - Quick access to investment options with preset amounts\n"
            "• 🔍 *Explore* - Discover top pools, simulate returns, and find answers\n"
            "• 👤 *Account* - Connect wallet, set preferences, and manage subscriptions\n\n"
            "*The persistent buttons are always available* - no more typing commands!\n\n"
            "*Smart Text Recognition:*\n"
            "• \"I want to invest $500\" - Automatically recognizes your intention\n"
            "• \"Show my positions\" - Detects portfolio requests in natural language\n"
            "• \"What are the best pools now?\" - Understands market inquiries\n"
            "• \"Help with my wallet\" - Intelligently routes to account features\n\n"
            "💡 *Pro tip:* Use the buttons below for the fastest experience!",
            reply_markup=MAIN_KEYBOARD
        )
        
        # No need to send a separate message for persistent keyboard
        # It will be shown automatically with the main help message
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        from keyboard_utils import MAIN_KEYBOARD
        await update.message.reply_markdown(
            "Sorry, an error occurred while processing your request.\n\n"
            "Please use the buttons below to access features:",
            reply_markup=MAIN_KEYBOARD
        )

async def account_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the account management flow:
    Shows a menu with options for wallet connection, profile settings, and subscriptions
    """
    try:
        user = update.effective_user
        message = update.effective_message
        
        # Log command activity
        from app import app
        with app.app_context():
            db_utils.log_user_activity(user.id, "account_command")
        
        # Get user information
        from models import User
        user_record = None
        
        with app.app_context():
            user_record = User.query.filter_by(id=user.id).first()
        
        wallet_status = "❌ Not Connected"
        profile_type = "Not Set"
        subscription_status = "❌ Not Subscribed"
        
        if user_record:
            # Check wallet connection
            orchestrator = get_orchestrator()
            wallet_info = await orchestrator.get_wallet_info(user.id)
            if wallet_info.get("success", False):
                wallet_address = wallet_info.get("address", "")
                if wallet_address:
                    wallet_status = f"✅ Connected ({wallet_address[:6]}...{wallet_address[-4:]})"
            
            # Get profile settings
            if user_record.risk_profile:
                profile_type = user_record.risk_profile.capitalize()
            
            # Check subscription status
            if user_record.is_subscribed:
                subscription_status = "✅ Subscribed"
        
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
        
        # Show the account menu with inline buttons (for account options) and attach persistent keyboard
        # First message with the account options menu
        await message.reply_markdown(response, reply_markup=get_account_menu())
        
        # Second message to ensure the persistent keyboard stays
        await message.reply_text("Use the buttons above to manage your account 👆", reply_markup=MAIN_KEYBOARD)
        
    except Exception as e:
        logger.error(f"Error in account_command: {e}", exc_info=True)
        from keyboard_utils import MAIN_KEYBOARD, get_main_menu_inline
        
        # First show error message with inline buttons
        await update.message.reply_markdown(
            "❗ *Account Access Error*\n\n"
            "Sorry, an error occurred while accessing your account information.\n\n"
            "Please select an option to continue:",
            reply_markup=get_main_menu_inline()
        )
        
        # Persistent keyboard is already applied to the previous message

async def explore_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the exploration flow with several options:
    1. No arguments: Shows a menu with options (pools, simulate, faq)
    2. 'pools': Shows top-performing pools (calls info_command)
    3. 'simulate [amount]': Simulates investment returns
    4. 'faq': Shows FAQ information
    """
    try:
        user = update.effective_user
        message = update.effective_message
        
        # Log command activity
        from app import app
        with app.app_context():
            db_utils.log_user_activity(user.id, "explore_command")
        
        # Get arguments
        args = context.args
        
        # Import keyboard modules
        from keyboard_utils import MAIN_KEYBOARD
        from menus import get_explore_menu
        
        # No arguments: Show menu with direct command instructions
        if not args:
            # Show the explore menu with inline buttons from get_explore_menu()
            # and attach persistent keyboard via reply_markup
            explore_menu = get_explore_menu()
            
            # Also include direct commands for FAQ and Community since those buttons are problematic
            await message.reply_markdown(
                "📊 *Explore DeFi Opportunities* 📊\n\n"
                "Select what you'd like to explore:\n\n"
                "• For *FAQ & Help*: Type `/explore faq`\n"
                "• For *Community*: Type `/explore social`\n"
                "• For *Top Pools*: Use the Top Pools button below\n"
                "• For *Simulations*: Use the Simulate Returns button below",
                reply_markup=explore_menu
            )
            
            # Send a follow-up message with direct command buttons for better UX
            keyboard = [
                [
                    InlineKeyboardButton("❓ See FAQ & Help", callback_data="direct_command_faq"),
                    InlineKeyboardButton("🌐 Join Community", callback_data="direct_command_social")
                ]
            ]
            inline_keyboard = InlineKeyboardMarkup(keyboard)
            
            await message.reply_markdown(
                "*Quick Access Commands:*\n\n"
                "Use these reliable buttons for direct access:",
                reply_markup=inline_keyboard
            )
            
            # Persistent keyboard will be shown automatically by main.py
            return
            
        # Parse the option
        option = args[0].lower()
        
        # Handle 'pools' option
        if option == "pools":
            # Call the existing info_command
            context.args = []  # Clear arguments for info_command
            await info_command(update, context)
            return
            
        # Handle 'simulate' option
        elif option == "simulate":
            # If there's a second argument, it's the amount
            if len(args) > 1:
                try:
                    amount = float(args[1])
                    context.args = [str(amount)]  # Set arguments for simulate_command
                    await simulate_command(update, context)
                except ValueError:
                    await message.reply_text(
                        "Invalid amount for simulation. Please provide a numeric value, for example:\n"
                        "/explore simulate 100",
                        reply_markup=get_simulate_menu()
                    )
            else:
                # No amount provided, show simulation options
                await message.reply_text(
                    "💰 *Simulate Investment Returns* 💰\n\n"
                    "Select an amount to simulate or enter a custom amount using:\n"
                    "`/explore simulate <amount>`",
                    parse_mode="Markdown",
                    reply_markup=get_simulate_menu()
                )
            return
            
        # Handle 'faq' option
        elif option == "faq":
            # Call the existing faq_command
            await faq_command(update, context)
            return
            
        # Handle 'social' option
        elif option == "social":
            # Call the existing social_command
            await social_command(update, context)
            return
            
        # Invalid option
        else:
            # First show the error with inline buttons
            await message.reply_markdown(
                "❗ *Option not recognized*\n\n"
                "Try using the buttons below instead - our new one-command interface "
                "makes navigation much simpler!",
                reply_markup=get_explore_menu()
            )
            
            # Persistent keyboard is automatically shown with the explore menu
            
    except Exception as e:
        logger.error(f"Error in explore_command: {e}", exc_info=True)
        from keyboard_utils import MAIN_KEYBOARD, get_main_menu_inline
        
        # First show error message with inline buttons
        await update.message.reply_markdown(
            "Sorry, an error occurred while processing your request.\n\n"
            "Please select an option to continue:",
            reply_markup=get_main_menu_inline()
        )
        
        # The persistent keyboard will be automatically shown with the error message

async def invest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles the consolidated investment flow with three modes:
    1. No arguments: Shows active positions with options to add more or exit
    2. Profile only (high-risk|stable): Shows recommended pools for that profile
    3. Profile and amount: Shows recommended pools to invest the specified amount
    """
    try:
        # Import keyboard utilities
        from keyboard_utils import MAIN_KEYBOARD
        user = update.effective_user
        message = update.effective_message
        
        # Log command activity
        from app import app
        with app.app_context():
            db_utils.log_user_activity(user.id, "invest_command")
        
        # Get arguments
        args = context.args
        profile = "high-risk"  # Default profile
        amount = None
        
        # Parse arguments
        if args:
            # First argument could be profile or amount
            if args[0].lower() in ["high-risk", "stable"]:
                profile = args[0].lower()
                # If there's a second argument, it's the amount
                if len(args) > 1:
                    try:
                        amount = float(args[1])
                    except ValueError:
                        from keyboard_utils import MAIN_KEYBOARD
                        await message.reply_markdown(
                            "❗ *Invalid Amount Format*\n\n"
                            "Please provide a numeric value when investing.\n\n"
                            "Or simply use the buttons for a smoother experience:",
                            reply_markup=MAIN_KEYBOARD
                        )
                        return
            else:
                # First argument is amount, use default profile
                try:
                    amount = float(args[0])
                except ValueError:
                    from keyboard_utils import MAIN_KEYBOARD
                    await message.reply_markdown(
                        "❗ *Command Format Not Recognized*\n\n"
                        "For a much simpler experience, try using the buttons below instead!",
                        reply_markup=MAIN_KEYBOARD
                    )
                    return
        
        # MODE 1: No arguments - show positions
        if not args:
            # Get positions from orchestrator
            orchestrator = get_orchestrator()
            result = await orchestrator.get_positions(user.id)
            
            if not result.get("success", False):
                # Import the proper keyboard
                from keyboard_utils import MAIN_KEYBOARD
                
                await message.reply_text(
                    f"❌ Sorry, I couldn't retrieve your positions at this time.\n\n"
                    f"Error: {result.get('error', 'Unknown error')}",
                    reply_markup=MAIN_KEYBOARD
                )
                return
                
            positions = result.get("positions", [])
            
            if not positions:
                # Use the already imported MAIN_KEYBOARD
                await message.reply_markdown(
                    "📈 *No Active Positions*\n\n"
                    "You don't have any active investments yet.\n\n"
                    "Choose an investment option below:",
                    reply_markup=MAIN_KEYBOARD
                )
                return
                
            # Format response
            response = "📊 *Your Liquidity Positions* 📊\n\n"
            
            for position in positions:
                # Format status with emoji
                status_emoji = {
                    PositionStatus.PENDING.value: "⏳",
                    PositionStatus.ACTIVE.value: "✅",
                    PositionStatus.MONITORED.value: "🔍",
                    PositionStatus.EXITING.value: "🚪",
                    PositionStatus.COMPLETED.value: "🏁",
                    PositionStatus.FAILED.value: "❌"
                }.get(position["status"], "❓")
                
                # Get values from position, using appropriate keys
                entry_value = position.get("entry_value", position.get("usd_value", 0))
                current_value = position.get("current_value", entry_value)
                profit_loss = position.get("pnl", current_value - entry_value)
                profit_loss_pct = position.get("pnl_percent", 0)
                
                # Format profit/loss
                profit_loss_text = (
                    f"Profit: ${profit_loss:.2f} ({profit_loss_pct:.2f}%)" 
                    if profit_loss >= 0 
                    else f"Loss: -${abs(profit_loss):.2f} ({profit_loss_pct:.2f}%)"
                )
                
                # Format date string
                date_str = position.get("entry_date", "")
                if isinstance(date_str, str):
                    date_formatted = date_str.split("T")[0] if "T" in date_str else date_str
                else:
                    # Import in function scope to avoid circular imports
                    from bot_commands import format_datetime
                    date_formatted = format_datetime(date_str)
                
                # Add position details
                response += (
                    f"{status_emoji} *Position {position['id']}*\n"
                    f"Pool: {position.get('token_a', 'Token A')}/{position.get('token_b', 'Token B')}\n"
                    f"Status: {position['status'].capitalize()}\n"
                    f"Invested: ${entry_value:.2f}\n"
                    f"Current Value: ${current_value:.2f}\n"
                    f"{profit_loss_text}\n"
                    f"Current APR: {position.get('current_apr', 0):.2f}%\n"
                    f"Created: {date_formatted}\n\n"
                )
            
            # Send response with exit position menu
            exit_menu = get_exit_position_menu(positions)
            await message.reply_markdown(response, reply_markup=exit_menu)
            return
            
        # MODE 2/3: Profile with or without amount - recommend pools
        # Send processing message
        processing_message = await message.reply_text(
            "🔍 Analyzing the market for the best pools based on your risk profile...\n"
            "This may take a moment as I'm checking on-chain data and market sentiment."
        )
        
        # Get recommendations from orchestrator
        orchestrator = get_orchestrator()
        result = await orchestrator.recommend(user.id, profile)
        
        # Delete processing message
        await processing_message.delete()
        
        if not result.get("success", False):
            await message.reply_markdown(
                f"❌ *Recommendation Error*\n\n"
                f"I couldn't generate investment recommendations right now.\n"
                f"Error: {result.get('error', 'Unknown error')}\n\n"
                f"Please try again using the buttons below:",
                reply_markup=MAIN_KEYBOARD
            )
            
            # Persistent keyboard will already be shown with the menu
            return
            
        # Get the recommended pools
        higher_return = result.get("higher_return")
        stable_return = result.get("stable_return")
        
        if not higher_return:
            await message.reply_text(
                "❌ Sorry, I couldn't find any suitable pools matching your profile.\n\n"
                "Please try again later when market conditions improve.",
                reply_markup=MAIN_KEYBOARD
            )
            return
            
        # Format response
        response = (
            f"🌟 *Recommended Pools for {profile}* 🌟\n\n"
            f"I've analyzed the market and found the following opportunities for you:\n\n"
        )
        
        # Import in function scope to avoid circular imports
        from bot_commands import format_sentiment_score
        
        # Add higher return pool details
        response += (
            f"🚀 *Higher Return Option*\n"
            f"Pool: {higher_return['token_a']}/{higher_return['token_b']}\n"
            f"Current APR: {higher_return['apr_current']:.2f}%\n"
            f"Prediction Score: {higher_return['sol_score']:.2f}\n"
            f"Market Sentiment: {format_sentiment_score(higher_return['sentiment_score'])}\n"
            f"TVL: ${higher_return['tvl']:,.2f}\n\n"
        )
        
        # Add stable return pool details if available
        if stable_return:
            response += (
                f"🛡️ *Stable Option*\n"
                f"Pool: {stable_return['token_a']}/{stable_return['token_b']}\n"
                f"Current APR: {stable_return['apr_current']:.2f}%\n"
                f"Prediction Score: {stable_return['sol_score']:.2f}\n"
                f"Market Sentiment: {format_sentiment_score(stable_return['sentiment_score'])}\n"
                f"TVL: ${stable_return['tvl']:,.2f}\n\n"
            )
        
        # If amount is provided, add investment buttons
        if amount is not None:
            response += (
                f"💰 *Ready to Invest ${amount:.2f}*\n\n"
                f"With our One-Touch interface, you can complete your investment with a single tap. "
                f"Choose one of these recommended pools below:"
            )
            
            # Create invest buttons for the specific amount
            keyboard = [
                [
                    InlineKeyboardButton(
                        f"Invest ${amount:.2f} in {higher_return['token_a']}/{higher_return['token_b']}", 
                        callback_data=f"execute_{amount}"
                    )
                ]
            ]
            
            if stable_return:
                keyboard.append([
                    InlineKeyboardButton(
                        f"Invest ${amount:.2f} in {stable_return['token_a']}/{stable_return['token_b']}", 
                        callback_data=f"execute_{amount}_stable"
                    )
                ])
                
            keyboard.append([
                InlineKeyboardButton("Back to Invest Menu", callback_data="menu_invest")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            # Without amount, show standard invest menu with One-Command approach
            response += (
                f"✨ *Ready to Invest?* ✨\n\n"
                f"With our One-Touch interface, just select an investment amount using the buttons below. "
                f"No need to type commands!"
            )
            # Import required menu correctly
            from menus import get_invest_menu
            reply_markup = get_invest_menu()
            
            # The persistent keyboard is already integrated into the response
        
        # Send response
        await message.reply_markdown(response, reply_markup=reply_markup)
        
        # The persistent keyboard is already included in the reply via MAIN_KEYBOARD
        # No need for additional keyboard messages
        
    except Exception as e:
        logger.error(f"Error in invest_command: {e}", exc_info=True)
        # Import the keyboards here to avoid circular imports
        from keyboard_utils import MAIN_KEYBOARD, get_main_menu_inline
        
        # First show error message with inline buttons for immediate navigation
        await update.message.reply_markdown(
            "❗ *Oops! Something went wrong*\n\n"
            "Sorry, I encountered an error processing your investment request.\n\n"
            "Please select an option to continue:",
            reply_markup=get_main_menu_inline()
        )
        
        # Add the persistent keyboard directly to the error message
        # No need for additional messages about the keyboard

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show information about cryptocurrency pools when the command /info is issued."""
    try:
        # Import app at function level to avoid circular imports
        from app import app
        
        # Get user info before entering app context
        user = update.effective_user
        
        # Use app context for database operations
        with app.app_context():
            # Log the activity inside app context
            db_utils.log_user_activity(user.id, "info_command")
        
        # Determine whether this is a direct command or a callback query
        is_callback = update.callback_query is not None
        
        # Handle both regular commands and callback queries
        if is_callback:
            # For callback queries (from buttons)
            message = update.callback_query.message
        else:
            # For direct commands
            message = update.message
            # Only send this initial message for direct commands
            await message.reply_text("Fetching the latest pool data...")
        
        # Import at function level to avoid circular imports
        from response_data import get_pool_data as get_predefined_pool_data
        
        # Get predefined pool data directly as dictionaries
        predefined_data = get_predefined_pool_data()
        
        # Process top performing pools and stable pools from the predefined data
        # These should be 2 best performance pools and 3 stable pools
        top_pools = predefined_data.get('bestPerformance', [])  # Get 2 best performance pools
        stable_pools = predefined_data.get('topStable', [])    # Get all 3 stable pools
        
        if not top_pools:
            await message.reply_text(
                "Sorry, I couldn't retrieve pool data at the moment. Please try again later."
            )
            return
            
        formatted_info = format_pool_info(top_pools, stable_pools)
        
        # Use regular reply_text to avoid markdown formatting issues
        await message.reply_text(formatted_info)
        logger.info("Sent pool info response")
    except Exception as e:
        logger.error(f"Error in info command: {e}", exc_info=True)
        
        # Handle errors for both command types
        try:
            if update.callback_query:
                await update.callback_query.message.reply_text(
                    "Sorry, an error occurred while processing your request. Please try again later."
                )
            else:
                await update.message.reply_text(
                    "Sorry, an error occurred while processing your request. Please try again later."
                )
        except Exception as reply_error:
            logger.error(f"Error sending error message: {reply_error}")

async def simulate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Simulate investment returns when the command /simulate is issued."""
    try:
        # Import app at function level to avoid circular imports
        from app import app
        
        # Get user info before entering app context
        user = update.effective_user
        
        # Use app context for database operations
        with app.app_context():
            # Log the activity inside app context
            db_utils.log_user_activity(user.id, "simulate_command")
        
        # Set default amount to 1000 if not provided
        amount = 1000.0
        
        # Check if amount is provided and parse it
        if context.args and context.args[0]:
            try:
                amount = float(context.args[0])
                if amount <= 0:
                    raise ValueError("Amount must be positive")
            except ValueError:
                await update.message.reply_text(
                    "Please provide a valid positive number. Example: /simulate 1000"
                )
                return
            
        await update.message.reply_text("Calculating potential returns...")
        
        # Import at function level to avoid circular imports
        from response_data import get_pool_data as get_predefined_pool_data
        
        # Get predefined pool data directly as dictionaries
        predefined_data = get_predefined_pool_data()
        
        # Process top APR pools from the predefined data (bestPerformance = topAPR)
        # These should be the 2 highest-performing pools
        pool_list = predefined_data.get('bestPerformance', [])
        
        if not pool_list:
            await update.message.reply_text(
                "Sorry, I couldn't retrieve pool data at the moment. Please try again later."
            )
            return
            
        # For simulation, we use the top performing pools (2 pools)
        formatted_simulation = format_simulation_results(pool_list, amount)
        
        # Add wallet connection options - both direct and WalletConnect
        keyboard = [
            [
                InlineKeyboardButton("Connect Wallet (Address)", callback_data="wallet_connect_address"),
                InlineKeyboardButton("Connect Wallet (QR Code)", callback_data="wallet_connect_qr")
            ],
            [InlineKeyboardButton("⬅️ Back to Explore", callback_data="back_to_explore")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Use regular reply_text to avoid markdown formatting issues
        await update.message.reply_text(formatted_simulation, reply_markup=reply_markup)
        logger.info(f"Sent simulation response for amount ${amount:.2f}")
    except Exception as e:
        logger.error(f"Error in simulate command: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, an error occurred while processing your request. Please try again later."
        )

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Subscribe to daily updates when the command /subscribe is issued."""
    try:
        # Import app at function level to avoid circular imports
        from app import app
        
        # Get user info before entering app context
        user = update.effective_user
        
        # Use app context for all database operations
        success = False
        with app.app_context():
            # Subscribe user in database
            success = db_utils.subscribe_user(user.id)
            
            if success:
                db_utils.log_user_activity(user.id, "subscribe")
        
        # Send response outside app context (no db operations)
        if success:
            await update.message.reply_markdown(
                "✅ You've successfully subscribed to daily updates!\n\n"
                "You'll receive daily insights about the best-performing liquidity pools "
                "and investment opportunities.\n\n"
                "Use /unsubscribe to stop receiving updates at any time."
            )
        else:
            await update.message.reply_markdown(
                "You're already subscribed to daily updates.\n\n"
                "Use /unsubscribe if you wish to stop receiving updates."
            )
    except Exception as e:
        logger.error(f"Error in subscribe command: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, an error occurred while processing your request. Please try again later."
        )

async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Unsubscribe from daily updates when the command /unsubscribe is issued."""
    try:
        # Import app at function level to avoid circular imports
        from app import app
        
        # Get user info before entering app context
        user = update.effective_user
        
        # Use app context for all database operations
        success = False
        with app.app_context():
            # Unsubscribe user in database
            success = db_utils.unsubscribe_user(user.id)
            
            if success:
                db_utils.log_user_activity(user.id, "unsubscribe")
        
        # Send response outside app context (no db operations)
        if success:
            await update.message.reply_markdown(
                "✅ You've successfully unsubscribed from daily updates.\n\n"
                "You'll no longer receive daily pool insights.\n\n"
                "Use /subscribe if you'd like to receive updates again in the future."
            )
        else:
            await update.message.reply_markdown(
                "You're not currently subscribed to daily updates.\n\n"
                "Use /subscribe if you'd like to receive daily insights."
            )
    except Exception as e:
        logger.error(f"Error in unsubscribe command: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, an error occurred while processing your request. Please try again later."
        )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check bot status when the command /status is issued."""
    try:
        # Import the app at function level to avoid circular imports
        from app import app
        
        # Get user info before entering app context
        user = update.effective_user
        
        # Use app context for all database operations
        with app.app_context():
            # Log the activity inside app context
            db_utils.log_user_activity(user.id, "status_command")
            
            # Get user status inside app context
            db_user = db_utils.get_or_create_user(user.id)
            
            # Format the status text with user data
            status_text = (
                "🤖 *FiLot Bot Status*\n\n"
                "✅ Bot is operational and ready to assist you!\n\n"
                "*Your Account Status:*\n"
                f"• User ID: {db_user.telegram_id}\n"
                f"• Subscription: {'Active ✅' if db_user.is_subscribed else 'Inactive ❌'}\n"
                f"• Verification: {'Verified ✅' if db_user.is_verified else 'Unverified ❌'}\n"
                f"• Account Created: {db_user.created_at.strftime('%Y-%m-%d')}\n\n"
                "Use /help to see available commands."
            )
        
        # Reply outside of app context (no db operations)
        await update.message.reply_markdown(status_text)
    except Exception as e:
        logger.error(f"Error in status command: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, an error occurred while processing your request. Please try again later."
        )

async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Verify the user when the command /verify is issued."""
    try:
        # Import app at function level to avoid circular imports
        from app import app
        
        # Get user info before entering app context
        user = update.effective_user
        
        # Check if code is provided
        if not context.args or not context.args[0]:
            # Use app context for database operations
            with app.app_context():
                # Generate verification code inside app context
                code = db_utils.generate_verification_code(user.id)
            
            if code:
                await update.message.reply_markdown(
                    "📱 *Verification Required*\n\n"
                    "To enhance your account security and unlock additional features, "
                    "please verify your account using the code below:\n\n"
                    f"`{code}`\n\n"
                    "Use the code with the /verify command like this:\n"
                    f"/verify {code}"
                )
            else:
                await update.message.reply_text(
                    "Error generating verification code. Please try again later."
                )
            return
            
        # Verify with provided code (inside app context)
        code = context.args[0]
        
        # Use app context for all database operations
        success = False
        with app.app_context():
            # Verify user with code
            success = db_utils.verify_user(user.id, code)
            
            if success:
                # Log the activity inside app context
                db_utils.log_user_activity(user.id, "verified")
        
        # Send response outside app context (no db operations)
        if success:
            await update.message.reply_markdown(
                "✅ *Verification Successful!*\n\n"
                "Your account has been verified. You now have access to all FiLot features.\n\n"
                "Explore FiLot's capabilities with /help."
            )
        else:
            await update.message.reply_markdown(
                "❌ *Verification Failed*\n\n"
                "The verification code is invalid or has expired.\n\n"
                "Please try again with a new code by typing /verify"
            )
    except Exception as e:
        logger.error(f"Error in verify command: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, an error occurred while processing your request. Please try again later."
        )

async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manage wallet when the command /wallet is issued."""
    try:
        # Import app at function level to avoid circular imports
        from app import app
        
        # Get user info before entering app context
        user = update.effective_user
        
        # Use app context for database operations
        with app.app_context():
            # Log the activity inside app context
            db_utils.log_user_activity(user.id, "wallet_command")
        
        # Check if a wallet address is provided
        if context.args and context.args[0]:
            wallet_address = context.args[0]
            
            try:
                # Validate wallet address
                wallet_address = connect_wallet(wallet_address)
                
                await update.message.reply_markdown(
                    f"✅ Wallet successfully connected: `{wallet_address}`\n\n"
                    "Fetching wallet balance..."
                )
                
                # Get wallet balance
                balance = await check_wallet_balance(wallet_address)
                
                if "error" in balance:
                    await update.message.reply_markdown(
                        f"❌ Error: {balance['error']}\n\n"
                        "Please try again with a valid wallet address."
                    )
                    return
                
                # Format balance information
                balance_text = "💼 *Wallet Balance* 💼\n\n"
                
                for token, amount in balance.items():
                    if token == "SOL":
                        balance_text += f"• SOL: *{amount:.4f}* (≈${amount * 133:.2f})\n"
                    elif token == "USDC" or token == "USDT":
                        balance_text += f"• {token}: *{amount:.2f}*\n"
                    else:
                        balance_text += f"• {token}: *{amount:.4f}*\n"
                
                # Add investment options
                keyboard = [
                    [InlineKeyboardButton("View Pool Opportunities", callback_data="view_pools")],
                    [InlineKeyboardButton("Connect with WalletConnect", callback_data="walletconnect")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_markdown(
                    balance_text + "\n\n💡 Use /simulate to see potential earnings with these tokens in liquidity pools.",
                    reply_markup=reply_markup
                )
                
            except ValueError as e:
                await update.message.reply_markdown(
                    f"❌ Error: {str(e)}\n\n"
                    "Please provide a valid Solana wallet address."
                )
            
        else:
            # No address provided, show wallet menu
            keyboard = [
                [InlineKeyboardButton("Connect with WalletConnect", callback_data="walletconnect")],
                [InlineKeyboardButton("Enter Wallet Address", callback_data="enter_address")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_markdown(
                "💼 *Wallet Management*\n\n"
                "Connect your wallet to view balances and interact with liquidity pools.\n\n"
                "Choose an option below, or provide your wallet address directly using:\n"
                "/wallet [your_address]",
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error in wallet command: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, an error occurred while processing your request. Please try again later."
        )

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set user investment profile when the command /profile is issued."""
    try:
        # Import app at function level to avoid circular imports
        from app import app
        
        # Get user info before entering app context
        user = update.effective_user
        profile_text = None
        db_user = None
        
        # Use app context for all database operations
        with app.app_context():
            # Log the activity inside app context
            db_utils.log_user_activity(user.id, "profile_command")
            
            # Get current user profile data inside app context
            db_user = db_utils.get_or_create_user(user.id)
            
            # If no parameters provided, prepare to show current profile
            if not context.args:
                # Format current profile info
                profile_text = (
                    "🔍 *Your Investment Profile*\n\n"
                    f"• Risk Tolerance: *{db_user.risk_profile.capitalize()}*\n"
                    f"• Investment Horizon: *{db_user.investment_horizon.capitalize()}*\n"
                    f"• Investment Goals: {db_user.investment_goals or 'Not specified'}\n\n"
                    "To update your profile, use one of these commands:\n"
                    "• `/profile risk [conservative/moderate/aggressive]`\n"
                    "• `/profile horizon [short/medium/long]`\n"
                    "• `/profile goals [your investment goals]`\n\n"
                    "Example: `/profile risk aggressive`"
                )
        
        # If we have profile text ready, send it and return
        if profile_text:
            await update.message.reply_markdown(profile_text)
            return
            
        # Process command parameters
        if len(context.args) >= 2:
            setting_type = context.args[0].lower()
            setting_value = " ".join(context.args[1:])
            
            # Process different setting types within app context
            with app.app_context():
                if setting_type == "risk":
                    if setting_value.lower() in ["conservative", "moderate", "aggressive"]:
                        # Update risk profile using db_utils
                        db_user.risk_profile = setting_value.lower()
                        db_utils.update_user_profile(db_user.id, "risk_profile", setting_value.lower())
                        
                        # Send confirmation
                        await update.message.reply_markdown(
                            f"✅ Risk profile updated to *{setting_value.capitalize()}*.\n\n"
                            f"Your AI financial advice will now be tailored to a {setting_value.lower()} risk tolerance."
                        )
                    else:
                        await update.message.reply_text(
                            "Invalid risk profile. Please choose from: conservative, moderate, or aggressive."
                        )
                        
                elif setting_type == "horizon":
                    if setting_value.lower() in ["short", "medium", "long"]:
                        # Update investment horizon using db_utils
                        db_user.investment_horizon = setting_value.lower()
                        db_utils.update_user_profile(db_user.id, "investment_horizon", setting_value.lower())
                        
                        # Send confirmation
                        await update.message.reply_markdown(
                            f"✅ Investment horizon updated to *{setting_value.capitalize()}*.\n\n"
                            f"Your AI financial advice will now be tailored to a {setting_value.lower()}-term investment horizon."
                        )
                    else:
                        await update.message.reply_text(
                            "Invalid investment horizon. Please choose from: short, medium, or long."
                        )
                        
                elif setting_type == "goals":
                    # Update investment goals using db_utils
                    goals_value = setting_value[:255]  # Limit to 255 chars
                    db_user.investment_goals = goals_value
                    db_utils.update_user_profile(db_user.id, "investment_goals", goals_value)
                    
                    # Send confirmation
                    await update.message.reply_markdown(
                        "✅ Investment goals updated successfully.\n\n"
                        "Your AI financial advice will take your goals into consideration."
                    )
                    
                else:
                    await update.message.reply_text(
                        "Invalid setting. Please use 'risk', 'horizon', or 'goals'."
                    )
        else:
            await update.message.reply_text(
                "Please provide both setting type and value. For example:\n"
                "/profile risk moderate"
            )
    except Exception as e:
        logger.error(f"Error in profile command: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, an error occurred while processing your request. Please try again later."
        )
        
async def faq_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display FAQ information when the command /faq is issued."""
    try:
        from app import app
        with app.app_context():
            user = update.effective_user
            db_utils.log_user_activity(user.id, "faq_command")
        
        # Get the fixed responses for FAQ content
        from fixed_responses import get_fixed_responses
        responses = get_fixed_responses()
        
        # Combine relevant educational content from fixed responses
        educational_content = [
            "*What is FiLot?*\n" + responses.get("what is filot", "FiLot is your AI-powered crypto investment advisor.").split("\n\n")[0],
            "*How does pool investment work?*\n" + responses.get("what is liquidity pool", "You provide liquidity to a pool and earn fees from trades.").split("\n\n")[0],
            "*What are the risks?*\n" + responses.get("impermanent loss", "Liquidity pools can have impermanent loss if token prices change significantly.").split("\n\n")[0],
            "*What's APR?*\n" + responses.get("what is apr", "Annual Percentage Rate - estimated yearly return. Pool APRs can be high (10-200%+) but fluctuate.").split("\n\n")[0],
            "*How do I start investing?*\n" + responses.get("how to use filot", "1. Connect your wallet\n2. Choose an investment amount\n3. Select a pool").split("\n\n")[0],
            "*When is FiLot launching?*\n" + responses.get("when does filot launch", "FiLot is currently in beta mode. The full launch will be available soon with one-click investment features.")
        ]
        
        # Create the complete FAQ message
        faq_text = """
❓ *Frequently Asked Questions*

""" + "\n\n".join(educational_content) + """

*How do updates work?*
Use /subscribe for automatic news. Use /unsubscribe to stop.

*How does /simulate work?*
It estimates earnings based on recent APRs: Earnings = Investment * (APR/100) * Time.

*How do I ask specific questions?*
Use /ask Your question here... for product details, or just type general questions.

Use /help to see all available commands!
"""
        
        # Create back button keyboard
        keyboard = [
            [
                InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="menu_main")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send the FAQ message with back button
        await update.message.reply_markdown(faq_text, reply_markup=reply_markup)
        
        logger.info(f"Sent FAQ to user {user.id}")
        
    except Exception as e:
        logger.error(f"Error in FAQ command: {e}")
        await update.message.reply_text(
            "Sorry, an error occurred while sending the FAQ. Please try again later."
        )

async def social_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display social media links when the command /social is issued."""
    try:
        # Import app at function level to avoid circular imports
        from app import app
        
        # Get user info before entering app context
        user = update.effective_user
        
        # Use app context for database operations
        with app.app_context():
            # Log the activity inside app context
            db_utils.log_user_activity(user.id, "social_command")
        
        # Format the social media content with emojis and links
        social_text = """
🌐 *Join Our Community* 🌐

Connect with fellow investors and get the latest updates:

• Telegram Group: @FilotCommunity
• Discord: discord.gg/filot
• Twitter: @FilotFinance

Share your experiences and learn from others!

⚡️ For technical support, email: support@filot.finance
"""
        
        # Create inline keyboard with social links and back button
        keyboard = [
            [
                InlineKeyboardButton("🌐 Website", url="https://filot.finance"),
                InlineKeyboardButton("𝕏 Twitter", url="https://twitter.com/filotfinance")
            ],
            [
                InlineKeyboardButton("💬 Telegram", url="https://t.me/filotcommunity"),
                InlineKeyboardButton("📱 Discord", url="https://discord.gg/filot")
            ],
            [
                InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="menu_main")
            ]
        ]
        
        # Send the social media message with inline buttons (outside app context)
        await update.message.reply_markdown(
            social_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True  # Disable preview to avoid showing preview images
        )
        
        logger.info(f"Sent social media links to user {user.id}")
        
    except Exception as e:
        logger.error(f"Error in social command: {e}", exc_info=True)
        await update.message.reply_text(
            "Sorry, an error occurred while sending the social media links. Please try again later."
        )

async def walletconnect_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create a WalletConnect session when the command /walletconnect is issued."""
    try:
        # Import app at function level to avoid circular imports
        from app import app
        
        # Get user info before entering app context
        user = update.effective_user
        
        # Use app context for database operations
        with app.app_context():
            # Log the activity inside app context
            db_utils.log_user_activity(user.id, "walletconnect_command")
        
        # Determine if this is a callback or direct command
        is_callback = update.callback_query is not None
        
        # Get the appropriate message object based on the update type
        if is_callback:
            message = update.callback_query.message
        else:
            message = update.message
        
        # Send security information message first
        security_msg = await message.reply_markdown(
            "🔒 *Secure Wallet Connection*\n\n"
            "Our wallet connection process is designed with your security in mind:\n\n"
            "• Your private keys remain in your wallet app\n"
            "• We only request permission to view balances\n"
            "• No funds will be transferred without your explicit approval\n"
            "• All connections use encrypted communication\n\n"
            "Creating your secure connection now..."
        )
        
        # Create a WalletConnect session
        result = await create_walletconnect_session(user.id)
        
        if not result["success"]:
            await security_msg.reply_markdown(
                f"❌ Error: {result.get('error', 'Unknown error')}\n\n"
                "Please try again later."
            )
            return
            
        # Format the QR code data
        uri = result["uri"]
        session_id = result["session_id"]
        
        # Save session to context if available
        try:
            # The correct way to access user_data is to just use it directly
            # We can't reassign the entire user_data object, just set values on it
            context.user_data["walletconnect_session"] = session_id
            logger.info(f"Saved session ID {session_id} to user context")
        except Exception as user_data_error:
            # Don't fail if we can't store in context
            logger.warning(f"Could not store session in user_data: {user_data_error}")
        
        # Create simplified keyboard without the unreliable "Open in Wallet App" button
        keyboard = [
            [InlineKeyboardButton("Check Connection Status", callback_data=f"check_wc_{session_id}")],
            [InlineKeyboardButton("Cancel Connection", callback_data=f"cancel_wc_{session_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Get the raw WalletConnect URI directly
        # Check if it's in the session result first
        session_data = result.get("session_data", {})
        
        # Get the raw WC URI from our stored session data
        raw_wc_uri = uri
        if "raw_wc_uri" in session_data:
            raw_wc_uri = session_data["raw_wc_uri"]
            
        # Send the main wallet connect message
        await security_msg.reply_markdown(
            "🔗 *WalletConnect Session Created*\n\n"
            "Copy the connection code below and paste it into your wallet app to connect.\n\n"
            f"Session ID: `{session_id}`\n\n"
            "✅ *What to expect in your wallet app:*\n"
            "• You'll be asked to approve a connection request\n"
            "• Your wallet app will show exactly what permissions are being requested\n"
            "• No funds will be transferred without your explicit approval\n\n"
            "Once connected, click 'Check Connection Status' to verify.",
            reply_markup=reply_markup
        )
        
        # Generate QR code for the WalletConnect URI
        try:
            # Make sure we're using the raw wc: URI for the QR code (not the deep link)
            wc_uri_for_qr = result.get('raw_wc_uri', raw_wc_uri)
            logger.info(f"Generating QR code for URI: {wc_uri_for_qr}")
            
            # Import directly to confirm PIL is available
            from PIL import Image
            logger.info("PIL is available")
            
            # Create QR code with explicit imports to ensure we have all needed components
            import qrcode
            from qrcode.image.pil import PilImage
            
            # Use the most basic qrcode creation method
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(wc_uri_for_qr)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            logger.info(f"QR code image created, type: {type(qr_img)}")
            
            # Save to a buffer
            buffer = io.BytesIO()
            qr_img.save(buffer, format="PNG")  # Explicitly set format
            buffer.seek(0)
            logger.info(f"QR saved to buffer, size: {len(buffer.getvalue())} bytes")
            
            # Send QR code as photo with more detailed caption
            current_time = datetime.datetime.now().strftime("%H:%M:%S")
            sent_msg = await message.reply_photo(
                photo=buffer,
                caption=f"📱 Scan this QR code with your wallet app to connect\n(Generated at {current_time})"
            )
            
            logger.info(f"QR code sent successfully: {sent_msg.message_id}")
        except ImportError as imp_err:
            logger.error(f"Import error for QR generation: {imp_err}")
            logger.error(traceback.format_exc())
            
            # Try alternative QR display via text
            await message.reply_text(
                "Unable to generate QR code image. Please use the text link below instead."
            )
        except Exception as qr_error:
            logger.error(f"Error generating QR code: {qr_error}")
            logger.error(traceback.format_exc())
            # If QR code generation fails, we'll still send the text version
        
        # Also send the raw WalletConnect URI as text for manual copying if needed
        # Format with code block and timestamp for better visibility
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Get the WalletConnect URI
        wallet_connect_uri = result.get('raw_wc_uri', raw_wc_uri)
        
        # Create a cleaner and more focused message with just the WalletConnect URI
        # Using a dedicated message specifically for copying
        # Using monospace font with a standalone message makes it easier to copy
        copy_msg = await message.reply_text(
            f"📋 *COPY THIS LINK* (tap to select):\n\n"
            f"`{wallet_connect_uri}`\n\n"
            f"Generated at {current_time}",
            parse_mode="Markdown"
        )
        
        # Add the detailed explanation in a separate message
        await security_msg.reply_text(
            "🔒 Remember: Only approve wallet connections from trusted sources and always verify the requested permissions.\n\n"
            "If the QR code doesn't work, manually copy the link above and paste it into your wallet app."
        )
    except Exception as e:
        logger.error(f"Error in walletconnect command: {e}")
        try:
            if update.callback_query:
                await update.callback_query.message.reply_text(
                    "Sorry, an error occurred while processing your request. Please try again later."
                )
            else:
                await update.message.reply_text(
                    "Sorry, an error occurred while processing your request. Please try again later."
                )
        except Exception as reply_error:
            logger.error(f"Error sending error message: {reply_error}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle user messages that are not commands.
    Intelligently detects questions, investing intent, button presses, or position inquiries
    and routes to the appropriate handlers or AI for specialized financial advice.
    Also handles simplified one-command UX with buttons.
    """
    try:
        user = update.effective_user
        message_text = update.message.text
        
        # Log the user's message
        logger.info(f"Received message from user {user.id}: {message_text}")
        
        # Mark this message as being handled to prevent duplicate acknowledgment messages
        if hasattr(context, 'user_data'):
            context.user_data["message_response_sent"] = True
        
        # We'll wrap all database operations in an app context
        from app import app
        with app.app_context():
            # Log the query in the database
            query = db_utils.log_user_query(
                user_id=user.id,
                command="message",  # Changed from None to avoid type error
                query_text=message_text
            )
            
        # Check if this is a button press from the persistent keyboard
        # Using exact matching for button texts
        if message_text == "💰 Invest":
            logger.info(f"User {user.id} pressed the Invest button")
            # Start the investment flow
            await start_invest_flow(update, context)
            return
            
        elif message_text == "🔍 Explore":
            logger.info(f"User {user.id} pressed the Explore button")
            
            # Import directly to ensure consistency with main.py
            from menus import get_explore_menu
            
            # Show the explore menu with options
            await update.message.reply_markdown(
                "📊 *Explore DeFi Opportunities* 📊\n\n"
                "Select what you'd like to explore:",
                reply_markup=get_explore_menu()
            )
            return
            
        elif message_text == "👤 Account":
            logger.info(f"User {user.id} pressed the Account button")
            # Trigger the account command
            context.args = []
            await account_command(update, context)
            return
            
        # Enhanced intelligent text matching for One-Touch Navigation
        # Using the improved intent recognition system to detect various ways users might
        # express their intention without exactly pressing buttons
        elif is_investment_intent(message_text) and message_text != "💰 Invest":
            logger.info(f"User {user.id} typed invest-related text: {message_text}")
            # Extract amount if present in the text for a smoother experience
            amount = extract_amount(message_text)
            if amount > 0:
                logger.info(f"Extracted investment amount from text: ${amount}")
                # Store the amount for the investment flow
                if not hasattr(context, 'user_data'):
                    context.user_data = {}
                context.user_data['investment_amount'] = amount
            await start_invest_flow(update, context)
            return
            
        elif is_pool_inquiry(message_text) and message_text != "🔍 Explore":
            logger.info(f"User {user.id} typed explore/pools-related text: {message_text}")
            context.args = []
            await explore_command(update, context)
            return
            
        elif is_wallet_inquiry(message_text) and message_text != "👤 Account":
            logger.info(f"User {user.id} typed account/wallet-related text: {message_text}")
            context.args = []
            await account_command(update, context)
            return
            
        elif is_position_inquiry(message_text):
            logger.info(f"User {user.id} asked to view positions: {message_text}")
            # Show positions using the enhanced recognition
            from bot_commands import positions_command
            await positions_command(update, context)
            return
            
        elif "back" in message_text.lower() or message_text == "⬅️ Back to Main Menu":
            logger.info(f"User {user.id} pressed the Back button")
            # Handle back to main menu
            await handle_back_to_main(update, context)
            return
            
        # Check if we're in an ongoing investment flow
        if hasattr(context, 'user_data') and 'state' in context.user_data:
            state = context.user_data['state']
            
            if state == STATE_AWAITING_AMOUNT:
                # We're waiting for an amount input
                await process_invest_amount(update, context)
                return
                
            elif state == STATE_AWAITING_PROFILE:
                # We're waiting for a profile selection
                await process_risk_profile(update, context)
                return
        
        # Check for specific investment phrases like "I want to invest $500"
        if "want to invest" in message_text.lower() or "invest " in message_text.lower():
            logger.info(f"Detected direct investment intent from user {user.id}")
            
            # Extract amount if present
            amount = extract_amount(message_text)
            
            # If amount is found, route to the investment flow with this amount preset
            if amount > 0:
                logger.info(f"Extracted investment amount: ${amount}")
                
                # Store the amount in user data for the investment flow
                if not hasattr(context, 'user_data'):
                    context.user_data = {}
                    
                context.user_data['investment_amount'] = amount
                
                # Start investment flow with this amount
                await start_invest_flow(update, context)
                
                # Skip the amount input step
                # Updated: Let's continue to risk profile selection
                await update.message.reply_text(
                    "Great! Now please select your risk profile:", 
                    reply_markup=RISK_PROFILE_KEYBOARD
                )
                context.user_data['state'] = STATE_AWAITING_PROFILE
                return
            else:
                # No amount, start the standard investment flow
                await start_invest_flow(update, context)
                return
                
        # Check for general investment intent (broader matching)
        elif is_investment_intent(message_text):
            logger.info(f"Detected general investment intent from user {user.id}")
            
            # Start the investment flow for guided process
            await start_invest_flow(update, context)
            return
        
        # Check for position inquiry (anyone asking about their positions)
        if is_position_inquiry(message_text) or "my position" in message_text.lower():
            logger.info(f"Detected position inquiry from user {user.id}")
            
            # Route to positions command to show positions
            from bot_commands import positions_command
            await positions_command(update, context)
            return
        
        # Check for pool inquiry
        if is_pool_inquiry(message_text):
            logger.info(f"Detected pool inquiry from user {user.id}")
            
            # Route to explore command with "pools" arg
            context.args = ["pools"]
            await explore_command(update, context)
            return
        
        # Check for wallet inquiry
        if is_wallet_inquiry(message_text):
            logger.info(f"Detected wallet inquiry from user {user.id}")
            
            # Route to account command
            await account_command(update, context)
            return
            
        # First, check if this is a question
        question_detected = is_question(message_text)
        logger.info(f"Is question detection: {question_detected}")
        
        # Check for predefined responses
        predefined_response = get_predefined_response(message_text)
        
        if predefined_response:
            logger.info(f"Found predefined response for: {message_text[:30]}...")
            
            # Send predefined response
            await update.message.reply_markdown(predefined_response)
            
            # Update the query with the response
            if query:
                query.response_text = predefined_response
                query.processing_time = (datetime.datetime.now() - query.timestamp).total_seconds() * 1000
                # Save to db in a non-blocking way
                asyncio.create_task(update_query_response(query.id, predefined_response, query.processing_time))
            
            # Log that we've responded with a predefined answer
            db_utils.log_user_activity(user.id, "predefined_response", details=f"Question: {message_text[:50]}")
            return
        
        # First, check if this might be a number input (investment amount)
        try:
            if message_text.strip().isdigit() or (message_text.strip().replace(',', '').isdigit()):
                # This looks like a pure number input, try to handle it as an investment amount
                logger.info(f"Detected numeric input: {message_text} - checking if in investment flow")
                
                # Check if we're in an ongoing investment flow again (double-check)
                if hasattr(context, 'user_data') and 'state' in context.user_data:
                    state = context.user_data['state']
                    if state == STATE_AWAITING_AMOUNT:
                        # We're waiting for an amount input
                        from investment_flow import process_invest_amount
                        await process_invest_amount(update, context)
                        return
                else:
                    # Even if not in a state, treat number inputs as investment attempts
                    logger.info(f"Treating numeric input {message_text} as investment amount")
                    # Initialize user_data if needed
                    if not hasattr(context, 'user_data'):
                        context.user_data = {}
                    
                    # Set state to await investment amount
                    context.user_data['state'] = STATE_AWAITING_AMOUNT
                    from investment_flow import process_invest_amount
                    await process_invest_amount(update, context)
                    return
        except Exception as e:
            logger.error(f"Error handling potential numeric input: {e}")
            # Continue with normal processing if error occurs
        
        # No predefined response available, use Anthropic AI for specialized financial advice
        logger.info(f"No predefined response for: {message_text}, using AI advisor")
        
        # Send typing indicator while processing
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        # Try to identify if this is a financial question
        classification = await ai_advisor.classify_financial_question(message_text)
        logger.info(f"AI classification: {classification}")
        
        # We need another app context for database operations
        from app import app
        
        # Get user profile details
        user_db = None
        risk_profile = "moderate"
        investment_horizon = "medium"
        
        with app.app_context():
            # Get user profile if available
            user_db = db_utils.get_or_create_user(user.id)
            risk_profile = getattr(user_db, 'risk_profile', 'moderate')
            investment_horizon = getattr(user_db, 'investment_horizon', 'medium')
        
        # Get pool data for context
        pools = await get_pool_data()
        
        ai_response = "I'm sorry, I couldn't process your request at this time."
        
        # Process based on classification
        if classification == "pool_advice":
            # Question about specific liquidity pools
            logger.info("Generating pool advice")
            ai_response = await ai_advisor.get_financial_advice(
                message_text, 
                pool_data=pools,
                risk_profile=risk_profile,
                investment_horizon=investment_horizon
            )
            
        elif classification == "strategy_help":
            # Question about investment strategies
            logger.info("Generating investment strategy")
            amount = 1000  # Default amount for strategy examples
            # Check if user mentioned an amount
            amount_match = re.search(r'(\$?[0-9,]+)', message_text)
            if amount_match:
                try:
                    amount = float(amount_match.group(1).replace('$', '').replace(',', ''))
                except ValueError:
                    pass
            
            ai_response = await ai_advisor.generate_investment_strategy(
                investment_amount=amount,
                risk_profile=risk_profile,
                investment_horizon=investment_horizon,
                pool_data=pools
            )
            
        elif classification == "risk_assessment":
            # Question about risk assessment
            logger.info("Generating risk assessment")
            # Find the pool with highest APR for risk assessment example
            highest_apr_pool = {}
            if pools and len(pools) > 0:
                highest_apr_pool = {
                    'token_a_symbol': pools[0].token_a_symbol,
                    'token_b_symbol': pools[0].token_b_symbol,
                    'apr_24h': pools[0].apr_24h,
                    'apr_7d': pools[0].apr_7d,
                    'apr_30d': pools[0].apr_30d,
                    'tvl': pools[0].tvl,
                    'fee': pools[0].fee,
                    'volume_24h': pools[0].volume_24h
                }
            
            risk_result = await ai_advisor.assess_investment_risk(highest_apr_pool)
            
            # Format risk assessment response
            risk_level = risk_result.get('risk_level', 'medium')
            explanation = risk_result.get('explanation', 'No detailed explanation available.')
            
            if risk_level.lower() == 'high' or risk_level.lower() == 'very high':
                risk_emoji = "🔴"
            elif risk_level.lower() == 'medium':
                risk_emoji = "🟠"
            else:
                risk_emoji = "🟢"
                
            ai_response = (
                f"*Risk Assessment: {risk_level.upper()}* {risk_emoji}\n\n"
                f"{explanation}\n\n"
                f"*Key Considerations:*\n• {risk_result.get('key_factors', 'N/A')}\n\n"
                f"*Impermanent Loss Risk:*\n• {risk_result.get('impermanent_loss', 'N/A')}\n\n"
                f"*Volatility:*\n• {risk_result.get('volatility', 'N/A')}\n\n"
                f"*Liquidity:*\n• {risk_result.get('liquidity', 'N/A')}\n\n"
                "Remember that all cryptocurrency investments carry inherent risks."
            )
            
        elif classification == "defi_explanation":
            # Question about DeFi concepts - extract the concept
            logger.info("Generating DeFi concept explanation")
            concept_match = re.search(r'(what is|explain|how does|tell me about) ([\w\s]+)', message_text.lower())
            concept = concept_match.group(2).strip() if concept_match else message_text
            
            ai_response = await ai_advisor.explain_financial_concept(concept)
            
        # Check if this is just a simple button press with no specific function match
        elif message_text in ["Invest", "Explore", "Account"] or message_text in ["💰", "🔍", "👤"]:
            # Provide a more helpful response rather than going to AI
            logger.info(f"Handling simple button text: {message_text}")
            
            # Map the button text to the appropriate response
            if "Invest" in message_text or "💰" in message_text:
                await start_invest_flow(update, context)
                return
            elif "Explore" in message_text or "🔍" in message_text:
                context.args = []
                await explore_command(update, context)
                return
            elif "Account" in message_text or "👤" in message_text:
                context.args = []
                await account_command(update, context)
                return
        
        else:
            # General financial advice
            logger.info("Generating general financial advice")
            ai_response = await ai_advisor.get_financial_advice(
                message_text, 
                pool_data=pools,
                risk_profile=risk_profile,
                investment_horizon=investment_horizon
            )
        
        # Send the AI response with the persistent keyboard
        await update.message.reply_markdown(
            ai_response,
            reply_markup=MAIN_KEYBOARD  # Add the persistent keyboard to all responses
        )
        
        # Update the database with our query and response
        with app.app_context():
            # Update the query with the response
            if query:
                query.response_text = ai_response if isinstance(ai_response, str) else str(ai_response)
                query.processing_time = (datetime.datetime.now() - query.timestamp).total_seconds() * 1000
                # Save to db in a non-blocking way
                asyncio.create_task(update_query_response(query.id, query.response_text, query.processing_time))
                
            # Log that we've responded with an AI-generated answer
            db_utils.log_user_activity(user.id, "ai_response", details=f"Classification: {classification}")
            
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        logger.error(traceback.format_exc())
        from keyboard_utils import MAIN_KEYBOARD
        
        # Special handling for large investment amounts
        if "500000" in message_text or "50000" in message_text:
            await update.message.reply_markdown(
                "⚠️ *Investment Amount Too Large*\n\n"
                "For security reasons, we limit individual investment amounts. "
                "Please try a smaller amount (under $10,000) or contact support for assistance with larger investments.",
                reply_markup=MAIN_KEYBOARD
            )
        else:
            await update.message.reply_text(
                "Sorry, I encountered an error while processing your request. Please try again later.",
                reply_markup=MAIN_KEYBOARD
            )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in updates."""
    try:
        error = context.error
        trace = "".join(traceback.format_exception(None, error, error.__traceback__))
        
        # Log error with more details
        logger.error(f"Exception while handling an update: {error}\n{trace}")
        logger.error(f"Update that caused error: {update}")
        logger.error(f"Context info: {context}")
        
        # Store error in database
        error_type = type(error).__name__
        error_message = str(error)
        
        # Try to get user ID if available
        user_id = None
        if update and isinstance(update, Update) and update.effective_user:
            user_id = update.effective_user.id
            logger.info(f"Error occurred for user {user_id}")
            
        try:
            # Only log to database if error is not related to database
            if "SQLAlchemy" not in error_type and "no application context" not in error_message:
                db_utils.log_error(
                    error_type=error_type,
                    error_message=error_message,
                    traceback=trace,
                    module="bot",
                    user_id=user_id
                )
                logger.info(f"Error logged to database: {error_type}")
            else:
                logger.warning(f"Skipping database logging for SQLAlchemy error: {error_message}")
        except Exception as db_error:
            logger.error(f"Failed to log error to database: {db_error}")
        
        # Inform user with persistent keyboard
        if update and isinstance(update, Update) and update.effective_message:
            try:
                from keyboard_utils import MAIN_KEYBOARD
                logger.info("Attempting to send error message to user with persistent keyboard")
                await update.effective_message.reply_text(
                    "Sorry, an error occurred while processing your request. Please try again later.",
                    reply_markup=MAIN_KEYBOARD
                )
                logger.info("Error message sent to user successfully")
            except Exception as reply_error:
                logger.error(f"Failed to send error message to user: {reply_error}")
    except Exception as e:
        logger.error(f"Error in error handler: {e}")
        logger.error(traceback.format_exc())

async def send_daily_updates() -> None:
    """Send daily updates to subscribed users."""
    try:
        # Get subscribed users
        subscribed_users = db_utils.get_subscribed_users()
        
        if not subscribed_users:
            logger.info("No subscribed users found for daily updates")
            return
            
        # Get pool data
        pools = await get_pool_data()
        
        if not pools:
            logger.error("Failed to get pool data for daily updates")
            return
            
        # Format daily update message
        update_message = format_daily_update(pools)
        
        # TODO: Send message to all subscribed users
        # This would be implemented when you have the application running 24/7
        logger.info(f"Would send daily updates to {len(subscribed_users)} users")
    except Exception as e:
        logger.error(f"Error sending daily updates: {e}")

# Callback Query Handler (for inline buttons)
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from inline keyboards."""
    try:
        # Import app at function level to avoid circular imports
        from app import app
        import hashlib
        
        # Use aggressive anti-loop protection first
        from anti_loop import is_looping, lock_chat
        
        query = update.callback_query
        user = query.from_user
        chat_id = query.message.chat_id
        callback_data = query.data
        
        # Check if this is a potential message loop with our less aggressive protection
        if is_looping(chat_id, callback_data, query.id):
            logger.warning(f"Anti-loop system prevented processing callback: {callback_data[:30]}...")
            # For button callbacks, we use a much shorter lock to improve responsiveness
            if any(callback_data.startswith(prefix) for prefix in [
                'menu_', 'account_', 'explore_', 'profile_', 'wallet_', 'invest_', 'amount_', 'simulate_'
            ]):
                # Very short lock for UI buttons - 0.5 seconds
                lock_chat(chat_id, 0.5)
            else:
                # Shorter lock than before for other callbacks - 2 seconds
                lock_chat(chat_id, 2.0)
            return
            
        # Create unique tracking IDs for this callback to prevent duplicates
        callback_id = f"cb_{query.id}"
        content_id = f"cb_data_{user.id}_{hashlib.md5(callback_data.encode()).hexdigest()[:8]}"
        
        # Store callback tracking IDs for additional protection
        if not hasattr(context, 'user_data'):
            context.user_data = {}
        
        # Less aggressive duplicate detection for UI buttons
        is_ui_button = any(callback_data.startswith(prefix) for prefix in [
            'menu_', 'account_', 'explore_', 'profile_', 'invest_'
        ])
        
        # For UI navigation buttons, we'll be much less strict about duplicate detection
        if is_ui_button:
            # Clear any previous callback_handled flag to ensure UI buttons always work
            if "callback_handled" in context.user_data:
                del context.user_data["callback_handled"]
                
            # For UI navigation, allow processing the same button more frequently
            # Only check exact duplicate callback IDs (not content)
            if context.user_data.get(callback_id, False):
                logger.info(f"UI Button pressed again: {callback_data[:30]} - allowing through")
                # Still allow it to go through, just logging
            
            # We don't use content_id check for UI buttons to make them more responsive
        else:
            # For non-UI buttons, maintain stricter duplicate detection
            if context.user_data.get("callback_handled", False):
                logger.info("Skipping already handled callback query (user_data flag)")
                return
                
            if context.user_data.get(callback_id, False) or context.user_data.get(content_id, False):
                logger.info(f"Skipping duplicate callback: {callback_data[:30]}...")
                return
        
        # Mark as being handled using multiple methods
        context.user_data["callback_handled"] = True
        context.user_data["message_response_sent"] = False
        context.user_data[callback_id] = True
        
        # Only store content ID for non-UI buttons
        if not is_ui_button:
            context.user_data[content_id] = True
        
        # Log user activity within app context
        with app.app_context():
            db_utils.log_user_activity(user.id, f"callback_{callback_data}")
        
        # Acknowledge the callback query
        await query.answer()
        
        # One-command UX specific callbacks
        if callback_data == "start_invest":
            # Start the investment flow
            logger.info(f"User {user.id} clicked inline Invest button")
            await start_invest_flow(update, context)
            return
            
        elif callback_data == "invest_back_to_profile":
            # Go back to profile selection in investment flow
            logger.info(f"User {user.id} went back to profile selection")
            if 'invest_amount' in context.user_data:
                amount = context.user_data['invest_amount']
                await query.message.reply_text(
                    f"You want to invest ${amount:.2f}.\n\n"
                    "What risk profile would you prefer?",
                    reply_markup=RISK_PROFILE_KEYBOARD
                )
                context.user_data["state"] = STATE_AWAITING_PROFILE
            else:
                # If no amount stored, restart the flow
                await start_invest_flow(update, context)
            return
            
        elif callback_data.startswith("confirm_invest_"):
            # User confirmed an investment in a specific pool
            pool_id = callback_data.replace("confirm_invest_", "")
            logger.info(f"User {user.id} confirmed investment in pool {pool_id}")
            await confirm_investment(update, context, pool_id)
            return
        
        if callback_data == "walletconnect":
            # Create a new context.args with empty list for the walletconnect command
            context.args = []
            await walletconnect_command(update, context)
            
        # Handle menu navigation
        elif callback_data == "menu_invest":
            # Show invest menu - Import at use to avoid circular imports
            from menus import get_invest_menu
            
            # Updated to match menu_explore approach and display full message rather than just edit buttons
            # This provides better context to the user and is more reliable
            await query.message.edit_text(
                "💰 *Invest in DeFi Pools* 💰\n\n"
                "How much would you like to invest?\n"
                "Select an amount below or choose 'Custom Amount' to enter a specific value:",
                reply_markup=get_invest_menu(),
                parse_mode="Markdown"
            )
            return
            
        elif callback_data == "menu_explore":
            # Show explore menu - Import at use to avoid circular imports
            from menus import get_explore_menu
            
            # Updated to match main.py behavior and display full message rather than just edit buttons
            await query.message.edit_text(
                "📊 *Explore DeFi Opportunities* 📊\n\n"
                "Select what you'd like to explore:",
                reply_markup=get_explore_menu(),
                parse_mode="Markdown"
            )
            return
            
        # NEW DIRECT COMMAND APPROACH - Explicitly handle the specialized direct command buttons
        elif callback_data == "direct_command_faq":
            logger.info(f"Handling DIRECT FAQ command button from user {user.id}")
            
            # Create a simplified context for running the faq_command
            simplified_context = ContextTypes.DEFAULT_TYPE()
            simplified_context.args = []
            
            # Directly run the faq_command with the current update
            await faq_command(update, simplified_context)
            return
            
        elif callback_data == "direct_command_social":
            logger.info(f"Handling DIRECT COMMUNITY command button from user {user.id}")
            
            # Create a simplified context for running the social_command
            simplified_context = ContextTypes.DEFAULT_TYPE()
            simplified_context.args = []
            
            # Directly run the social_command with the current update  
            await social_command(update, simplified_context)
            return
            
        elif callback_data == "menu_account":
            # Show account menu - Import at use to avoid circular imports
            from menus import get_account_menu
            
            # Updated to match main.py behavior and display full message
            await query.message.edit_text(
                "👤 *Your Account* 👤\n\n"
                "Manage your personal settings and wallet connections:",
                reply_markup=get_account_menu(),
                parse_mode="Markdown"
            )
            return
        
        # Handle account menu options with standardized approach
        elif callback_data.startswith("account_"):
            # Extract the account action for standardized handling
            account_action = callback_data.replace("account_", "")
            logger.info(f"Processing account action: {account_action}")
            
            # Handle different account actions
            if account_action == "wallet":
                # Redirect to walletconnect handler
                logger.info("Redirecting account_wallet to walletconnect handler")
                # Create a new context.args with empty list for the walletconnect command
                context.args = []
                await walletconnect_command(update, context)
            
            elif account_action == "subscribe":
                # Process subscribe through a callback-friendly approach
                logger.info("Processing account_subscribe button")
                try:
                    # Import app at function level to avoid circular imports
                    from app import app
                    
                    # Get user info
                    user = update.callback_query.from_user
                    
                    # Use app context for all database operations
                    success = False
                    with app.app_context():
                        # Subscribe user in database
                        success = db_utils.subscribe_user(user.id)
                        
                        if success:
                            db_utils.log_user_activity(user.id, "subscribe")
                    
                    # Send response using callback query's message
                    if success:
                        await query.message.reply_markdown(
                            "✅ You've successfully subscribed to daily updates!\n\n"
                            "You'll receive daily insights about the best-performing liquidity pools "
                            "and investment opportunities.\n\n"
                            "Use /unsubscribe to stop receiving updates at any time."
                        )
                    else:
                        await query.message.reply_markdown(
                            "You're already subscribed to daily updates.\n\n"
                            "Use /unsubscribe if you wish to stop receiving updates."
                        )
                except Exception as e:
                    logger.error(f"Error in subscribe button handler: {e}", exc_info=True)
                    await query.message.reply_text(
                        "Sorry, an error occurred while processing your request. Please try again later."
                    )
                
            elif account_action == "unsubscribe":
                # Process unsubscribe through a callback-friendly approach
                logger.info("Processing account_unsubscribe button")
                try:
                    # Import app at function level to avoid circular imports
                    from app import app
                    
                    # Get user info
                    user = update.callback_query.from_user
                    
                    # Use app context for all database operations
                    success = False
                    with app.app_context():
                        # Unsubscribe user in database
                        success = db_utils.unsubscribe_user(user.id)
                        
                        if success:
                            db_utils.log_user_activity(user.id, "unsubscribe")
                    
                    # Send response using callback query's message
                    if success:
                        await query.message.reply_markdown(
                            "✅ You've successfully unsubscribed from daily updates.\n\n"
                            "You'll no longer receive daily pool insights.\n\n"
                            "Use /subscribe if you'd like to receive updates again in the future."
                        )
                    else:
                        await query.message.reply_markdown(
                            "You're not currently subscribed to daily updates.\n\n"
                            "Use /subscribe if you'd like to receive daily insights."
                        )
                except Exception as e:
                    logger.error(f"Error in unsubscribe button handler: {e}", exc_info=True)
                    await query.message.reply_text(
                        "Sorry, an error occurred while processing your request. Please try again later."
                    )
                
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
                
            elif account_action == "status":
                # Process status through a callback-friendly approach
                logger.info("Processing account_status button")
                try:
                    # Import the app at function level to avoid circular imports
                    from app import app
                    
                    # Get user info
                    user = update.callback_query.from_user
                    
                    # Use app context for all database operations
                    with app.app_context():
                        # Log the activity inside app context
                        db_utils.log_user_activity(user.id, "status_command")
                        
                        # Get user status inside app context
                        db_user = db_utils.get_or_create_user(user.id)
                        
                        # Format the status text with user data
                        status_text = (
                            "🤖 *FiLot Bot Status*\n\n"
                            "✅ Bot is operational and ready to assist you!\n\n"
                            "*Your Account Status:*\n"
                            f"• User ID: {db_user.telegram_id}\n"
                            f"• Subscription: {'Active ✅' if db_user.is_subscribed else 'Inactive ❌'}\n"
                            f"• Verification: {'Verified ✅' if db_user.is_verified else 'Unverified ❌'}\n"
                            f"• Account Created: {db_user.created_at.strftime('%Y-%m-%d')}\n\n"
                            "Use /help to see available commands."
                        )
                    
                    # Send response using callback query's message
                    await query.message.reply_markdown(status_text)
                    
                except Exception as e:
                    logger.error(f"Error in status button handler: {e}", exc_info=True)
                    await query.message.reply_text(
                        "Sorry, an error occurred while checking status. Please try again later."
                    )
                
            elif account_action == "profile":
                # Show profile options
                logger.info("Showing profile options from account_profile")
                await query.message.reply_markdown(
                    "👤 *Risk Profile Settings* 👤\n\n"
                    "Select your investment risk profile:\n\n"
                    "🔴 *High Risk*: More volatile pools with higher potential returns\n\n"
                    "🟢 *Stable*: Lower volatility pools with more consistent returns\n\n"
                    "Your profile determines which pools are recommended to you.",
                    reply_markup=RISK_PROFILE_KEYBOARD
                )
                
            else:
                # We already handled the common account actions (subscribe, unsubscribe, help, status)
                # at the top of this section, so if we get here, it's an unknown action
                logger.warning(f"Unknown account action: {account_action}")
                from keyboard_utils import MAIN_KEYBOARD
                await query.message.reply_text(
                    f"Sorry, the action '{account_action}' is not recognized. Please use /help to see available commands.",
                    reply_markup=MAIN_KEYBOARD
                )
                
            return
        elif callback_data == "menu_main":
            # Show main menu - Import at use to avoid circular imports
            from menus import get_main_menu
            await query.message.edit_reply_markup(reply_markup=get_main_menu())
            return
            
        # Handle invest menu options
        elif callback_data.startswith("invest_"):
            # Parse the investment option
            parts = callback_data.split("_")
            if len(parts) >= 3:
                profile = parts[1]
                amount = float(parts[2])
                
                # Store in user data
                context.user_data["invest_profile"] = profile
                context.user_data["invest_amount"] = amount
                
                # Get pool data and show options
                pools = await get_top_pools_for_profile(profile, amount)
                
                # Show confirmation options
                if len(pools) >= 2:
                    await query.message.reply_markdown(
                        f"*Investment Options for ${amount}*\n\n"
                        f"Please choose a pool to invest in:",
                        reply_markup=get_invest_confirmation_keyboard(pools[0], pools[1])
                    )
                    context.user_data["state"] = STATE_AWAITING_CONFIRMATION
                else:
                    # Not enough pools, show a message
                    await query.message.reply_text(
                        "Sorry, not enough investment options available at the moment. Please try again later.",
                        reply_markup=MAIN_KEYBOARD
                    )
            return
                
        elif callback_data.startswith("check_wc_"):
            try:
                # Check WalletConnect session status
                session_id = callback_data.replace("check_wc_", "")
                logger.info(f"Checking WalletConnect session status for session: {session_id}")
                
                # Get the session info from the database
                session_info = await check_walletconnect_session(session_id)
                
                if not session_info["success"]:
                    error_msg = session_info.get('error', 'Session not found')
                    logger.warning(f"Session check failed: {error_msg}")
                    await query.message.reply_markdown(
                        f"❌ *Connection Error*\n\n"
                        f"{error_msg}\n\n"
                        "Please try creating a new wallet connection with /walletconnect."
                    )
                    return
                
                # Since this is a mock implementation, we'll simulate a successful connection
                # In a real implementation, we'd check if the wallet has connected
                status = "connected"  # For demo, assume connected after checking
                logger.info(f"Session status: {status}")
                
                # Update the session status in the database
                if status != session_info["status"]:
                    # Use app context for database operations
                    with app.app_context():
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE wallet_sessions SET status = %s WHERE session_id = %s",
                            (status, session_id)
                        )
                        cursor.close()
                        conn.close()
                
                if status == "connected":
                    try:
                        # Get mock wallet data for display
                        wallet_data = await get_wallet_balances(user.id)
                        token_list = ", ".join([f"{token} ({balance})" for token, balance in wallet_data.get("balances", {}).items()])
                        
                        await query.message.reply_markdown(
                            "✅ *Wallet Connected Successfully!*\n\n"
                            f"Your wallet is now connected in read-only mode.\n\n"
                            f"*Detected tokens:*\n{token_list}\n\n"
                            "You can now get personalized pool recommendations based on your holdings.\n\n"
                            "Use /info to see available pools or /simulate to calculate potential earnings."
                        )
                    except Exception as e:
                        logger.error(f"Error handling connected wallet: {e}")
                        await query.message.reply_markdown(
                            "✅ *Wallet Connected!*\n\n"
                            "Your wallet is now connected in read-only mode.\n\n"
                            "Use /info to see available pools or /simulate to calculate potential earnings."
                        )
                else:
                    try:
                        # For buttons in the message
                        # Get connection URIs from session data
                        session_data = session_info.get("session_data", {})
                        uri = session_data.get("uri", "")  # HTTPS URI for Telegram buttons
                        raw_wc_uri = session_data.get("raw_wc_uri", "")  # Raw WC URI for display
                        
                        # Create updated keyboard with check status button
                        keyboard = [
                            [InlineKeyboardButton("Check Connection Status", callback_data=f"check_wc_{session_id}")],
                            [InlineKeyboardButton("Cancel Connection", callback_data=f"cancel_wc_{session_id}")]
                        ]
                        
                        # Add wallet app button only if we have a valid URI
                        if uri and uri.startswith("https://"):
                            keyboard.insert(0, [InlineKeyboardButton("Open in Wallet App", url=uri)])
                        
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        # Only update the reply markup if there's a change
                        try:
                            await query.message.edit_reply_markup(reply_markup=reply_markup)
                        except Exception as edit_error:
                            logger.warning(f"Could not update message markup: {edit_error}")
                        
                        response_text = (
                            "⏳ *Waiting for Connection*\n\n"
                            "The wallet connection is still pending. Please open your wallet app and approve the connection.\n\n"
                        )
                        
                        # Include the raw WC URI and QR code if available
                        if raw_wc_uri:
                            try:
                                # Generate QR code for the URI using simple API
                                qr_img = qrcode.make(raw_wc_uri)
                                
                                # Create and send the QR code image
                                buffer = io.BytesIO()
                                qr_img.save(buffer)
                                buffer.seek(0)
                                
                                await query.message.reply_photo(
                                    photo=buffer,
                                    caption="📱 Scan this QR code with your wallet app to connect"
                                )
                                
                                # Also send the text version for manual copying
                                await query.message.reply_text(f"Alternatively, you can manually copy this WalletConnect URI:\n\n{raw_wc_uri}")
                            except Exception as qr_error:
                                logger.error(f"Error generating QR code in callback: {qr_error}")
                                # Fallback to text only if QR fails
                                await query.message.reply_text(f"Connect with this WalletConnect URI:\n\n{raw_wc_uri}")
                            # Don't include it in the main message
                            
                        response_text += "Click 'Check Connection Status' after approving in your wallet."
                        
                        await query.message.reply_markdown(response_text)
                    except Exception as e:
                        logger.error(f"Error processing pending connection: {e}")
                        await query.message.reply_markdown(
                            "⏳ *Waiting for Connection*\n\n"
                            "Please open your wallet app and approve the connection, then click 'Check Connection Status'."
                        )
            except Exception as e:
                logger.error(f"Error checking WalletConnect session: {e}")
                await query.message.reply_text(
                    "Sorry, an error occurred while checking the connection status. Please try again later."
                )
                
        elif callback_data.startswith("cancel_wc_"):
            # Cancel WalletConnect session
            session_id = callback_data.replace("cancel_wc_", "")
            result = await kill_walletconnect_session(session_id)
            
            if result["success"]:
                await query.message.reply_markdown(
                    "✅ *Connection Cancelled*\n\n"
                    "The wallet connection request has been cancelled.\n\n"
                    "Use /wallet to start a new connection when you're ready."
                )
            else:
                await query.message.reply_markdown(
                    f"❌ Error: {result.get('error', 'Unknown error')}\n\n"
                    "Please try again later."
                )
                
        elif callback_data == "enter_address":
            await query.message.reply_markdown(
                "💼 *Enter Wallet Address*\n\n"
                "Please provide your Solana wallet address using the command:\n"
                "/wallet [your_address]\n\n"
                "Example: `/wallet 5YourWalletAddressHere12345`"
            )
            
        # Handle explore menu options with standardized approach
        elif callback_data == "view_pools" or callback_data.startswith("explore_"):
            # Extract the explore action for standardized handling
            explore_action = ""
            
            if callback_data.startswith("explore_"):
                explore_action = callback_data.replace("explore_", "")
            elif callback_data == "view_pools":
                explore_action = "pools"
                
            logger.info(f"Processing explore action: {explore_action}")
                
            # Handle different explore actions
            if explore_action == "simulate":
                # Show investment simulation options
                # Import at function level to avoid circular imports
                from menus import get_simulate_menu
                
                # Updated to use the simulation menu not the investment menu
                await query.message.reply_markdown(
                    "💰 *Investment Return Simulator* 💰\n\n"
                    "Choose an investment amount to simulate potential returns "
                    "based on current APRs and liquidity pool data:\n\n"
                    "_This is a simulation only and not financial advice._",
                    reply_markup=get_simulate_menu()
                )
                
            elif explore_action == "pools":
                # Send a confirmation message that we're fetching pool information
                loading_message = await query.message.reply_markdown(
                    "🔍 *Fetching Pool Opportunities*\n\n"
                    "Please wait while I gather the latest data on available liquidity pools..."
                )
                
                try:
                    # Import at function level to avoid circular imports
                    from response_data import get_pool_data as get_predefined_pool_data
                    
                    # Get predefined pool data directly as dictionaries
                    predefined_data = get_predefined_pool_data()
                    
                    # Process top APR pools from the predefined data
                    pool_list = predefined_data.get('topAPR', [])
                    
                    if not pool_list:
                        await loading_message.reply_text(
                            "Sorry, I couldn't retrieve pool data at the moment. Please try again later."
                        )
                        return
                        
                    formatted_info = format_pool_info(pool_list)
                    # Use regular reply_text to avoid markdown formatting issues
                    await loading_message.reply_text(formatted_info)
                    logger.info(f"Sent pool info response for {callback_data} callback")
                except Exception as e:
                    logger.error(f"Error fetching pool data via callback: {e}")
                    await loading_message.reply_text(
                        "Sorry, an error occurred while retrieving pool data. Please try again later."
                    )
                
            elif explore_action == "faq":
                # Show FAQ information with updated text from main.py
                faq_text = (
                    "❓ *Frequently Asked Questions* ❓\n\n"
                    "*What is FiLot?*\n"
                    "FiLot is your AI-powered crypto investment advisor. It helps you discover and "
                    "invest in the best liquidity pools with real-time data.\n\n"
                    "*How does pool investment work?*\n"
                    "You provide liquidity to a pool (e.g., SOL/USDC) and earn fees from trades.\n\n"
                    "*How do I start investing?*\n"
                    "1. Connect your wallet using /account\n"
                    "2. Choose an investment amount with /invest\n"
                    "3. Select a pool and confirm your investment\n\n"
                    "*What are the risks?*\n"
                    "Liquidity pools can have impermanent loss if token prices change significantly.\n\n"
                    "Our system monitors market conditions and can suggest optimal entry and exit points to maximize returns."
                )
                await query.message.reply_markdown(faq_text)
                
            # Handler for "simulate" was moved up to avoid duplicate handlers
                
            elif explore_action == "social":
                # Show social media information with updated text from main.py
                community_text = (
                    "🌐 *Join Our Community* 🌐\n\n"
                    "Connect with fellow investors and get the latest updates:\n\n"
                    "• Telegram Group: @FilotCommunity\n"
                    "• Discord: discord.gg/filot\n"
                    "• Twitter: @FilotFinance\n\n"
                    "Share your experiences and learn from others!\n\n"
                    "⚡️ For technical support, email: support@filot.finance"
                )
                
                # Create social media buttons
                keyboard = [
                    [
                        InlineKeyboardButton("🌐 Website", url="https://filot.finance"),
                        InlineKeyboardButton("𝕏 Twitter", url="https://twitter.com/filotfinance")
                    ],
                    [
                        InlineKeyboardButton("💬 Telegram", url="https://t.me/filotcommunity"),
                        InlineKeyboardButton("📱 Discord", url="https://discord.gg/filot")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.reply_markdown(community_text, reply_markup=reply_markup)
                
            else:
                # Handle unknown explore action
                logger.warning(f"Unknown explore action: {explore_action}")
                from keyboard_utils import MAIN_KEYBOARD
                await query.message.reply_text(
                    "Sorry, that option is not available yet. Please try another option from the Explore menu.",
                    reply_markup=MAIN_KEYBOARD
                )
            
        # Handle simulation requests when simulate_100, simulate_500, etc. is clicked
        elif callback_data.startswith("simulate_"):
            try:
                # Extract the simulation amount
                amount_str = callback_data.replace("simulate_", "")
                
                # Check for custom simulation request
                if amount_str == "custom":
                    await query.message.reply_markdown(
                        "✏️ *Custom Simulation Amount* ✏️\n\n"
                        "Please enter the amount you want to simulate in USD.\n"
                        "For example: `$500` or `1000`",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("⬅️ Back to Simulate", callback_data="explore_simulate")]
                        ])
                    )
                    return
                
                # Handle numeric amounts
                amount = float(amount_str)
                logger.info(f"Processing simulation request for ${amount:.2f}")
                
                # Instead of calling simulate_command directly, let's implement the simulation here
                await query.message.reply_text("Please wait while I run the investment simulation...")
                
                try:
                    # Import at function level to avoid circular imports
                    from response_data import get_pool_data as get_predefined_pool_data
                    
                    # Get predefined pool data directly as dictionaries
                    predefined_data = get_predefined_pool_data()
                    
                    # Process top APR pools from the predefined data (bestPerformance = topAPR)
                    # These should be the 2 highest-performing pools
                    pool_list = predefined_data.get('bestPerformance', [])
                    
                    if not pool_list:
                        await query.message.reply_text(
                            "Sorry, I couldn't retrieve pool data at the moment. Please try again later."
                        )
                        return
                    
                    # For simulation, we use the top performing pools (2 pools)
                    from utils import format_simulation_results
                    
                    formatted_simulation = format_simulation_results(pool_list, amount)
                    
                    # Add wallet connection options - both direct and WalletConnect
                    keyboard = [
                        [
                            InlineKeyboardButton("Connect Wallet (Address)", callback_data="wallet_connect_address"),
                            InlineKeyboardButton("Connect Wallet (QR Code)", callback_data="wallet_connect_qr")
                        ],
                        [InlineKeyboardButton("⬅️ Back to Explore", callback_data="back_to_explore")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    # Send the simulation results
                    await query.message.reply_text(formatted_simulation, reply_markup=reply_markup)
                    logger.info(f"Sent simulation response for amount ${amount:.2f}")
                except Exception as e:
                    logger.error(f"Error processing simulation: {e}", exc_info=True)
                    await query.message.reply_text(
                        "Sorry, there was an error running the simulation. Please try again later."
                    )
                return
                
            except (ValueError, TypeError) as e:
                logger.error(f"Error processing simulation callback: {e}")
                await query.message.reply_text(
                    "Sorry, there was an error processing your simulation request. "
                    "Please try again or use /simulate command directly."
                )
                return
                
        # Handle back to explore menu button
        elif callback_data == "back_to_explore":
            # Go back to explore menu
            from menus import get_explore_menu
            
            explore_text = (
                "🔍 *Explore FiLot Features* 🔍\n\n"
                "Discover investment opportunities, simulate returns, and learn about cryptocurrency pools."
            )
            
            # Use edit_text instead of reply_markdown to update the existing message
            await query.message.edit_text(
                explore_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_explore_menu()
            )
            return
        
        # Handle wallet connection options from simulation results
        elif callback_data == "wallet_connect_address":
            await query.message.reply_markdown(
                "🔗 *Connect Wallet by Address* 🔗\n\n"
                "Please enter your Solana wallet address to connect.\n"
                "Example: `8xrt7LnhU4VrVNmhfjVsHLa2rMxXUyGemwveRFchvQxr`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back to Simulation", callback_data="back_to_explore")]
                ])
            )
            return
        
        elif callback_data == "wallet_connect_qr":
            await query.message.reply_markdown(
                "📱 *WalletConnect QR Code* 📱\n\n"
                "Scan this QR code with your Solana wallet app to connect.\n"
                "(QR code generation in progress...)",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back to Simulation", callback_data="back_to_explore")]
                ])
            )
            # In a real implementation, we would generate a WalletConnect session and QR code here
            return
            
        # Handle investment-related actions with standardized approach
        elif callback_data.startswith("invest_") or callback_data.startswith("amount_") or callback_data.startswith("wallet_connect_"):
            # Determine the investment action type
            invest_action = ""
            
            # Handle numeric wallet_connect callbacks specially
            if callback_data.startswith("wallet_connect_") and any(c.isdigit() for c in callback_data):
                # This is a wallet connect for a specific amount from simulation
                try:
                    amount = float(callback_data.replace("wallet_connect_", ""))
                    logger.info(f"Processing wallet connect for investment amount: ${amount:.2f}")
                    
                    # Show wallet connect options
                    await query.message.reply_markdown(
                        f"🔗 *Connect Wallet for ${amount:.2f} Investment* 🔗\n\n"
                        "Choose how you'd like to connect your wallet:",
                        reply_markup=InlineKeyboardMarkup([
                            [
                                InlineKeyboardButton("Enter Address", callback_data="wallet_connect_address"),
                                InlineKeyboardButton("Scan QR Code", callback_data="wallet_connect_qr")
                            ],
                            [InlineKeyboardButton("⬅️ Back", callback_data="back_to_explore")]
                        ])
                    )
                    return
                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing wallet connect amount: {e}")
                    
            # Normal invest action handling        
            if callback_data.startswith("invest_"):
                invest_action = callback_data.replace("invest_", "")
                logger.info(f"Processing invest action: {invest_action}")
            elif callback_data.startswith("amount_"):
                invest_action = "amount"
                logger.info(f"Processing investment amount selection: {callback_data}")
            elif callback_data.startswith("wallet_connect_"):
                invest_action = "wallet_connect"
                logger.info(f"Processing wallet connect for investment: {callback_data}")
            
            # Handle different investment actions
            if invest_action == "wallet_connect" and not callback_data.startswith("wallet_connect_address") and not callback_data.startswith("wallet_connect_qr"):
                # For generic wallet connect without amount specified
                await query.message.reply_markdown(
                    "🔗 *Connect Wallet* 🔗\n\n"
                    "Choose how you'd like to connect your wallet:",
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("Enter Address", callback_data="wallet_connect_address"),
                            InlineKeyboardButton("Scan QR Code", callback_data="wallet_connect_qr")
                        ],
                        [InlineKeyboardButton("⬅️ Back", callback_data="back_to_main")]
                    ])
                )
            
            elif invest_action == "amount" or callback_data.startswith("amount_"):
                # Import the proper handler from investment_flow
                from investment_flow import process_invest_amount_callback
                from keyboard_utils import MAIN_KEYBOARD

                try:
                    # Special handling for amount buttons to make them more reliable
                    if callback_data == "amount_custom":
                        # For custom amount entry, let the user enter their own amount
                        await query.message.reply_markdown(
                            "💰 *Enter Your Investment Amount*\n\n"
                            "Please enter how much you would like to invest. Just type a number (e.g. 100).\n\n"
                            "💡 *Example:* 500 (represents $500 USD)",
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("⬅️ Back to Invest Menu", callback_data="menu_invest")]
                            ])
                        )
                        
                        # Set state to await amount if context available
                        if hasattr(context, 'user_data'):
                            context.user_data["state"] = "awaiting_amount"
                    else:
                        # Process a specific amount that was chosen via button
                        try:
                            amount = float(callback_data.replace("amount_", ""))
                            logger.info(f"Processing investment amount: ${amount:.2f}")
                            
                            # Show investment options for this amount
                            from pool_formatter import get_top_pools, format_pool_details
                            top_pools = await get_top_pools(3, profile=None, min_tvl=10000)
                            
                            response = (
                                f"💰 *Investment Options for ${amount:.2f}*\n\n"
                                f"Here are the top pools for your investment:\n\n"
                            )
                            
                            # Format pools with investment-specific details
                            for i, pool in enumerate(top_pools, 1):
                                response += format_pool_details(pool, i, amount)
                            
                            # Create buttons for pools
                            keyboard = []
                            for i, pool in enumerate(top_pools):
                                pool_id = pool.get('id', f'pool_{i}')
                                token_pair = f"{pool.get('token_a_symbol', 'Token A')}/{pool.get('token_b_symbol', 'Token B')}"
                                keyboard.append([
                                    InlineKeyboardButton(f"Invest in {token_pair}", callback_data=f"confirm_invest_{pool_id}")
                                ])
                            
                            # Add navigation buttons
                            keyboard.append([
                                InlineKeyboardButton("⬅️ Back to Amounts", callback_data="menu_invest"),
                                InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_main")
                            ])
                            
                            # Send response
                            await query.message.reply_markdown(
                                response,
                                reply_markup=InlineKeyboardMarkup(keyboard)
                            )
                            
                        except ValueError:
                            # Fallback to the investment flow handler
                            await process_invest_amount_callback(update, context, callback_data)
                except Exception as e:
                    logger.error(f"Error processing amount callback: {e}", exc_info=True)
                    await query.message.reply_text(
                        "Sorry, I couldn't process that investment amount. Please try again or select another option.",
                        reply_markup=MAIN_KEYBOARD
                    )
                
            # Add other investment action handlers as needed
            else:
                # Handle unknown investment action
                logger.warning(f"Unknown investment action: {invest_action}")
                from keyboard_utils import MAIN_KEYBOARD
                await query.message.reply_text(
                    "Sorry, that investment option is not available yet. Please try another option.",
                    reply_markup=MAIN_KEYBOARD
                )
        
        else:
            # Fallback for unrecognized callbacks
            logger.warning(f"Unrecognized callback data: {callback_data}")
            await query.message.reply_text(
                "Sorry, I couldn't process that action. Please try again."
            )
    except Exception as e:
        logger.error(f"Error handling callback query: {e}")
        if update and update.callback_query:
            await update.callback_query.message.reply_text(
                "Sorry, an error occurred while processing your request. Please try again later."
            )

def create_application():
    """Register all necessary handlers to the application and return the Application instance."""
    # Check for Telegram bot token (first look for the secret, then fallback to env var for backward compatibility)
    token = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("Telegram bot token not found. Please set the TELEGRAM_TOKEN secret.")
        raise ValueError("Telegram bot token not found")
    
    # Create the Application
    application = Application.builder().token(token).build()
    
    # Register core command handlers (simplified UX with 3 main commands)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Register the three main commands
    application.add_handler(CommandHandler("invest", invest_command))
    application.add_handler(CommandHandler("explore", explore_command))
    application.add_handler(CommandHandler("account", account_command))
    
    # Register legacy/auxiliary commands (still accessible but de-emphasized in help)
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(CommandHandler("simulate", simulate_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("verify", verify_command))
    application.add_handler(CommandHandler("wallet", wallet_command))
    application.add_handler(CommandHandler("walletconnect", walletconnect_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("faq", faq_command))
    application.add_handler(CommandHandler("social", social_command))
    
    # Register direct profile commands that don't rely on buttons
    try:
        from direct_profile_commands import set_risk_profile_command
        application.add_handler(CommandHandler("high_risk", 
            lambda update, context: set_risk_profile_command(update, context, "high-risk")))
        application.add_handler(CommandHandler("stable", 
            lambda update, context: set_risk_profile_command(update, context, "stable")))
        application.add_handler(CommandHandler("set_profile", 
            lambda update, context: set_risk_profile_command(update, context, None)))
        logger.info("✅ Registered direct profile commands: /high_risk, /stable, and /set_profile")
    except Exception as e:
        logger.error(f"❌ Failed to register direct profile commands: {e}")
    
    # Register our dedicated command button handlers from the new module as a fallback
    try:
        from command_buttons import register_handlers
        register_handlers(application)
        logger.info("Registered dedicated command button handlers for FAQ and Community")
    except Exception as e:
        logger.error(f"Failed to register command button handlers: {e}")
    
    # Register agentic command handlers
    application.add_handler(CommandHandler("recommend", recommend_command))
    application.add_handler(CommandHandler("execute", execute_command))
    application.add_handler(CommandHandler("positions", positions_command))
    application.add_handler(CommandHandler("exit", exit_command))
    
    # Register AI-powered investment commands
    try:
        from commands.smart_invest import smart_invest_command, handle_smart_invest_callback
        application.add_handler(CommandHandler("smart_invest", smart_invest_command))
        application.add_handler(CallbackQueryHandler(handle_smart_invest_callback, pattern="^(smart_invest_|smart_amount_|smart_confirm_|refresh_smart_invest)"))
        logger.info("Registered AI-powered smart investment commands")
    except Exception as e:
        logger.error(f"Failed to register smart investment handlers: {e}")
    
    # Register callback query handlers
    # We use separate handlers for standard and agentic callbacks to avoid conflicts
    application.add_handler(CallbackQueryHandler(handle_agentic_callback_query, pattern="^(execute_|exit_|confirm_|ignore_)"))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Register message handler for non-command messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Initialize scheduler and register alert callback
    scheduler = init_scheduler()
    scheduler.register_alert_callback(handle_position_alert)
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    logger.info("Application created with all handlers registered")
    
    return application