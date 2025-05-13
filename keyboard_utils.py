"""
Persistent keyboard utilities for simplified bot interaction
Provides a consistent One-Command UX with persistent menu buttons
"""

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup

# Main persistent reply keyboard
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [["💰 Invest"], ["🔍 Explore", "👤 Account"]],
    resize_keyboard=True,
    one_time_keyboard=False
)

# JSON-serializable dictionary version of MAIN_KEYBOARD for use with the Telegram API
MAIN_KEYBOARD_DICT = {
    "keyboard": [["💰 Invest"], ["🔍 Explore", "👤 Account"]],
    "resize_keyboard": True,
    "one_time_keyboard": False
}

# Inline version of the main keyboard for embedding in messages
def get_main_menu_inline() -> InlineKeyboardMarkup:
    """
    Creates an inline keyboard with the main menu options
    
    Returns:
        InlineKeyboardMarkup with Invest, Explore and Account buttons
    """
    keyboard = [
        [
            InlineKeyboardButton("💰 Invest", callback_data="menu_invest")
        ],
        [
            InlineKeyboardButton("🔍 Explore", callback_data="menu_explore"),
            InlineKeyboardButton("👤 Account", callback_data="menu_account")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# Risk profile selection keyboard with clear visual indicators
RISK_PROFILE_KEYBOARD = ReplyKeyboardMarkup(
    [["🔴 High-risk", "🟢 Stable"], ["⬅️ Back to Main Menu"]],
    resize_keyboard=True,
    one_time_keyboard=False
)

# Back to main menu keyboard
BACK_KEYBOARD = ReplyKeyboardMarkup(
    [["⬅️ Back to Main Menu"]],
    resize_keyboard=True,
    one_time_keyboard=False
)

# Invest inline quick access button
INVEST_INLINE = InlineKeyboardMarkup(
    [[InlineKeyboardButton("💰 Invest", callback_data="start_invest")]]
)

def get_invest_confirmation_keyboard(pool_a, pool_b) -> InlineKeyboardMarkup:
    """
    Creates an inline keyboard for confirming pool investment choices
    
    Args:
        pool_a: First pool recommendation
        pool_b: Second pool recommendation
        
    Returns:
        InlineKeyboardMarkup with pool selection buttons
    """
    keyboard = [
        [
            InlineKeyboardButton(f"Pool {pool_a['token_a']}/{pool_a['token_b']}", 
                                callback_data=f"confirm_invest_{pool_a['id']}")
        ],
        [
            InlineKeyboardButton(f"Pool {pool_b['token_a']}/{pool_b['token_b']}", 
                                callback_data=f"confirm_invest_{pool_b['id']}")
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="invest_back_to_profile")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)