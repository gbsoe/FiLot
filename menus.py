"""
Menu handling utilities for the simplified bot command structure
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

def get_invest_menu() -> InlineKeyboardMarkup:
    """
    Creates the inline keyboard for invest command options
    """
    keyboard = [
        [
            InlineKeyboardButton("High-Risk $50", callback_data="invest_high-risk_50"),
            InlineKeyboardButton("High-Risk $100", callback_data="invest_high-risk_100")
        ],
        [
            InlineKeyboardButton("Stable $50", callback_data="invest_stable_50"),
            InlineKeyboardButton("Stable $100", callback_data="invest_stable_100")
        ],
        [
            InlineKeyboardButton("View Positions", callback_data="menu_positions"),
            InlineKeyboardButton("Custom Investment", callback_data="menu_custom_invest")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_explore_menu() -> InlineKeyboardMarkup:
    """
    Creates the inline keyboard for explore command options
    """
    keyboard = [
        [
            InlineKeyboardButton("Top Pools", callback_data="explore_pools"),
            InlineKeyboardButton("Simulate", callback_data="explore_simulate")
        ],
        [
            InlineKeyboardButton("FAQ", callback_data="explore_faq"),
            InlineKeyboardButton("Social Media", callback_data="explore_social")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_account_menu() -> InlineKeyboardMarkup:
    """
    Creates the inline keyboard for account command options
    """
    keyboard = [
        [
            InlineKeyboardButton("Connect Wallet", callback_data="account_wallet"),
            InlineKeyboardButton("Profile Settings", callback_data="account_profile")
        ],
        [
            InlineKeyboardButton("Subscribe", callback_data="account_subscribe"),
            InlineKeyboardButton("Unsubscribe", callback_data="account_unsubscribe")
        ],
        [
            InlineKeyboardButton("Help", callback_data="account_help"),
            InlineKeyboardButton("Status", callback_data="account_status")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_custom_amount_menu() -> InlineKeyboardMarkup:
    """
    Creates the inline keyboard for custom investment amount options
    """
    keyboard = [
        [
            InlineKeyboardButton("$200", callback_data="invest_high-risk_200"),
            InlineKeyboardButton("$500", callback_data="invest_high-risk_500"),
            InlineKeyboardButton("$1000", callback_data="invest_high-risk_1000")
        ],
        [
            InlineKeyboardButton("Back to Invest Menu", callback_data="menu_invest")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_exit_position_menu(positions) -> InlineKeyboardMarkup:
    """
    Creates the inline keyboard for exiting positions
    """
    keyboard = []
    
    # Add a button for each position
    for position in positions[:5]:  # Limit to 5 positions to avoid too many buttons
        pos_id = position['id']
        token_pair = f"{position.get('token_a', 'Token A')}/{position.get('token_b', 'Token B')}"
        keyboard.append([
            InlineKeyboardButton(f"Exit {token_pair}", callback_data=f"exit_{pos_id}")
        ])
    
    # Add a back button
    keyboard.append([
        InlineKeyboardButton("Back to Invest Menu", callback_data="menu_invest")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def get_main_menu() -> InlineKeyboardMarkup:
    """
    Creates the main menu inline keyboard
    """
    keyboard = [
        [
            InlineKeyboardButton("📈 Invest", callback_data="menu_invest"),
            InlineKeyboardButton("🔍 Explore", callback_data="menu_explore")
        ],
        [
            InlineKeyboardButton("👤 Account", callback_data="menu_account")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_simulate_menu() -> InlineKeyboardMarkup:
    """
    Creates the inline keyboard for simulation amount options
    """
    keyboard = [
        [
            InlineKeyboardButton("$100", callback_data="simulate_100"),
            InlineKeyboardButton("$500", callback_data="simulate_500"),
            InlineKeyboardButton("$1000", callback_data="simulate_1000")
        ],
        [
            InlineKeyboardButton("Back to Explore Menu", callback_data="menu_explore")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def is_investment_intent(text: str) -> bool:
    """
    Check if the message text indicates investment intent
    """
    investment_keywords = [
        "invest", "buy", "purchase", "put money", "allocate funds", 
        "deploy capital", "deposit", "money in", "want to invest",
        "looking to invest", "interested in investing"
    ]
    
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in investment_keywords)

def is_position_inquiry(text: str) -> bool:
    """
    Check if the message text is asking about positions
    """
    position_keywords = [
        "my position", "my investment", "portfolio", "holdings", 
        "my stake", "balance", "my pools", "my liquidity", 
        "what am i holding", "where is my money"
    ]
    
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in position_keywords)

def is_pool_inquiry(text: str) -> bool:
    """
    Check if the message text is asking about pools
    """
    pool_keywords = [
        "pool", "pools", "liquidity", "market", "opportunities", 
        "best rates", "top pools", "high yield", "apr", 
        "returns", "earning"
    ]
    
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in pool_keywords)

def is_wallet_inquiry(text: str) -> bool:
    """
    Check if the message text is asking about wallet
    """
    wallet_keywords = [
        "wallet", "connect", "walletconnect", "my wallet", 
        "link wallet", "crypto wallet", "connect wallet"
    ]
    
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in wallet_keywords)

def extract_amount(text: str) -> float:
    """
    Extract an investment amount from text
    Returns 0 if no amount found
    """
    import re
    
    # Match patterns like "$100", "100 dollars", "100USD", "100.50"
    amount_pattern = r'\$?(\d+(?:\.\d+)?)\s*(?:dollars|usd)?'
    match = re.search(amount_pattern, text, re.IGNORECASE)
    
    if match:
        return float(match.group(1))
    return 0