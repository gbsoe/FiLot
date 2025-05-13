"""
Dedicated handler for FAQ and Community buttons to ensure they work properly
and avoid conflicts between main.py and bot.py
"""

import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def handle_faq_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Explicit handler for the FAQ button to ensure it works correctly"""
    query = update.callback_query
    logger.info(f"FAQ button clicked by user {query.from_user.id}")
    
    # Show FAQ information with back button
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
    
    # Create back button keyboard
    keyboard = [
        [
            InlineKeyboardButton("⬅️ Back to Explore Menu", callback_data="menu_explore")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Answer callback query to stop the loading animation
    await query.answer()
    
    # Send the FAQ message with back button
    await query.message.reply_markdown(faq_text, reply_markup=reply_markup)
    logger.info("Sent FAQ response via dedicated handler")

async def handle_community_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Explicit handler for the Community button to ensure it works correctly"""
    query = update.callback_query
    logger.info(f"Community button clicked by user {query.from_user.id}")
    
    # Show social media information
    community_text = (
        "🌐 *Join Our Community* 🌐\n\n"
        "Connect with fellow investors and get the latest updates:\n\n"
        "• Telegram Group: @FilotCommunity\n"
        "• Discord: discord.gg/filot\n"
        "• Twitter: @FilotFinance\n\n"
        "Share your experiences and learn from others!\n\n"
        "⚡️ For technical support, email: support@filot.finance"
    )
    
    # Create social media buttons with back button
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
            InlineKeyboardButton("⬅️ Back to Explore Menu", callback_data="menu_explore")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Answer callback query to stop the loading animation
    await query.answer()
    
    # Send the community message with social buttons
    await query.message.reply_markdown(community_text, reply_markup=reply_markup)
    logger.info("Sent community links via dedicated handler")

# This function will be imported by main.py to set up the handlers
def register_handlers(application):
    """Register the FAQ and Community button handlers with the application"""
    from telegram.ext import CallbackQueryHandler
    
    # Register show_faq handler
    application.add_handler(CallbackQueryHandler(
        handle_faq_button, 
        pattern="^show_faq$"
    ))
    
    # Register show_community handler
    application.add_handler(CallbackQueryHandler(
        handle_community_button, 
        pattern="^show_community$"
    ))
    
    logger.info("Registered dedicated FAQ and Community button handlers")