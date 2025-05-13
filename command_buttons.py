"""
Direct command buttons that bypass the callback system entirely
This is a workaround for callback buttons that aren't working properly
"""

import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CommandHandler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def faq_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle direct /faq command instead of relying on callbacks"""
    logger.info(f"Handling /faq command from user {update.effective_user.id}")
    
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
            InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="menu_main")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send the FAQ message with back button
    await update.message.reply_markdown(faq_text, reply_markup=reply_markup)
    logger.info("Sent FAQ response via direct command handler")

async def community_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle direct /community command instead of relying on callbacks"""
    logger.info(f"Handling /community command from user {update.effective_user.id}")
    
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
            InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="menu_main")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send the community message with social buttons
    await update.message.reply_markdown(community_text, reply_markup=reply_markup)
    logger.info("Sent community links via direct command handler")

def register_handlers(application):
    """Register the direct command handlers with the application"""
    application.add_handler(CommandHandler("faq", faq_command))
    application.add_handler(CommandHandler("community", community_command))
    logger.info("Registered direct command handlers for FAQ and Community")