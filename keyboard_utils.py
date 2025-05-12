"""
Persistent keyboard utilities for simplified bot interaction
"""

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup

# Main persistent reply keyboard
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [["💰 Invest"], ["🔍 Explore", "👤 Account"]],
    resize_keyboard=True,
    one_time_keyboard=False
)

# Risk profile selection keyboard
RISK_PROFILE_KEYBOARD = ReplyKeyboardMarkup(
    [["High-risk", "Stable"], ["⬅️ Back to Main Menu"]],
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