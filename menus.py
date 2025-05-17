"""
Menu handling utilities for the simplified bot command structure
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

def get_invest_menu() -> InlineKeyboardMarkup:
    """
    Creates the One-Touch inline keyboard for invest command options with improved visuals
    """
    keyboard = [
        [
            InlineKeyboardButton("$50 💰", callback_data="amount_50"),
            InlineKeyboardButton("$100 💰", callback_data="amount_100"),
            InlineKeyboardButton("$250 💰", callback_data="amount_250")
        ],
        [
            InlineKeyboardButton("$500 💰", callback_data="amount_500"),
            InlineKeyboardButton("$1,000 💰", callback_data="amount_1000"),
            InlineKeyboardButton("$5,000 💰", callback_data="amount_5000")
        ],
        [
            InlineKeyboardButton("👁️ View My Positions", callback_data="menu_positions"),
            InlineKeyboardButton("✏️ Custom Amount", callback_data="amount_custom")
        ],
        [
            InlineKeyboardButton("🏠 Back to Main Menu", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_explore_menu() -> InlineKeyboardMarkup:
    """
    Creates the One-Touch inline keyboard for explore command options with improved visuals
    
    Note: Removed FAQ and Community buttons as they were causing issues.
    Only keeping the top row of buttons that are working properly.
    """
    # Using more specific button types to ensure proper callback handling
    keyboard = [
        [
            InlineKeyboardButton("🏆 Top Pools", callback_data="explore_pools"),
            InlineKeyboardButton("📊 Simulate Returns", callback_data="explore_simulate")
        ],
        [
            InlineKeyboardButton("🏠 Back to Main Menu", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_account_menu() -> InlineKeyboardMarkup:
    """
    Creates the One-Touch inline keyboard for account command options with improved visuals
    """
    keyboard = [
        [
            InlineKeyboardButton("💼 Connect Wallet", callback_data="account_wallet")
        ],
        [
            InlineKeyboardButton("🔴 High-Risk Profile", callback_data="account_profile_high-risk"),
            InlineKeyboardButton("🟢 Stable Profile", callback_data="account_profile_stable")
        ],
        [
            InlineKeyboardButton("🔔 Subscribe", callback_data="account_subscribe"),
            InlineKeyboardButton("🔕 Unsubscribe", callback_data="account_unsubscribe")
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data="account_help"),
            InlineKeyboardButton("📊 Status", callback_data="account_status")
        ],
        [
            InlineKeyboardButton("🏠 Back to Main Menu", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_custom_amount_menu() -> InlineKeyboardMarkup:
    """
    Creates the One-Touch inline keyboard for custom investment amount options
    """
    keyboard = [
        [
            InlineKeyboardButton("✏️ Enter Custom", callback_data="amount_enter_custom")
        ],
        [
            InlineKeyboardButton("$200 💰", callback_data="amount_200"),
            InlineKeyboardButton("$300 💰", callback_data="amount_300"),
            InlineKeyboardButton("$750 💰", callback_data="amount_750")
        ],
        [
            InlineKeyboardButton("$2,000 💰", callback_data="amount_2000"),
            InlineKeyboardButton("$10,000 💰", callback_data="amount_10000")
        ],
        [
            InlineKeyboardButton("⬅️ Back to Invest Menu", callback_data="menu_invest")
        ],
        [
            InlineKeyboardButton("🏠 Back to Main Menu", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_exit_position_menu(positions) -> InlineKeyboardMarkup:
    """
    Creates the One-Touch inline keyboard for exiting positions with visual improvements
    """
    keyboard = []
    
    # Add a button for each position
    for position in positions[:5]:  # Limit to 5 positions to avoid too many buttons
        pos_id = position['id']
        token_pair = f"{position.get('token_a', 'Token A')}/{position.get('token_b', 'Token B')}"
        # Add visual indicators for exit positions
        keyboard.append([
            InlineKeyboardButton(f"🚪 Exit {token_pair}", callback_data=f"exit_{pos_id}")
        ])
    
    # Add a back button
    keyboard.append([
        InlineKeyboardButton("⬅️ Back to Invest Menu", callback_data="menu_invest")
    ])
    
    # Add main menu button
    keyboard.append([
        InlineKeyboardButton("🏠 Back to Main Menu", callback_data="back_to_main")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def get_main_menu() -> InlineKeyboardMarkup:
    """
    Creates the One-Touch main menu inline keyboard with clear visual emphasis
    """
    keyboard = [
        [
            InlineKeyboardButton("💰 INVEST NOW", callback_data="menu_invest")
        ],
        [
            InlineKeyboardButton("🔍 Explore Options", callback_data="menu_explore"),
            InlineKeyboardButton("👤 My Account", callback_data="menu_account")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_simulate_menu() -> InlineKeyboardMarkup:
    """
    Creates the One-Touch inline keyboard for simulation amount options with visual improvements
    Matches the exact format seen in the user's screenshot
    """
    keyboard = [
        [
            InlineKeyboardButton("$50 💰", callback_data="simulate_50"),
            InlineKeyboardButton("$100 💰", callback_data="simulate_100"),
            InlineKeyboardButton("$250 💰", callback_data="simulate_250")
        ],
        [
            InlineKeyboardButton("$500 💰", callback_data="simulate_500"),
            InlineKeyboardButton("$1,000 💰", callback_data="simulate_1000"),
            InlineKeyboardButton("$5,000 💰", callback_data="simulate_5000")
        ],
        [
            InlineKeyboardButton("👁️ View My Positions", callback_data="menu_positions"),
            InlineKeyboardButton("✏️ Custom Amount", callback_data="simulate_custom")
        ],
        [
            InlineKeyboardButton("⬅️ Back to Explore", callback_data="back_to_explore")
        ],
        [
            InlineKeyboardButton("🏠 Back to Main Menu", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def is_investment_intent(text: str) -> bool:
    """
    Check if the message text indicates investment intent.
    This enables button-like behavior even when users type similar text instead.
    Part of the One-Touch navigation system for improved UX.
    """
    # Button-text matches - handle cases where users type the button text
    button_texts = [
        "invest", "💰 invest", "invest now", "💰 invest now",
        "$50", "$100", "$250", "$500", "$1,000", "$5,000", 
        "high-risk", "stable", "high risk", "custom amount", "custom investment"
    ]
    
    # Intent keywords - identify investment intent in natural language
    intent_keywords = [
        "buy", "purchase", "put money", "allocate funds", 
        "deploy capital", "deposit", "money in", "want to invest",
        "looking to invest", "interested in investing", "invest in", 
        "start investing", "place order", "make investment",
        "fund", "invest my", "put in", "get started"
    ]
    
    text_lower = text.lower()
    return (any(keyword in text_lower for keyword in button_texts) or 
            any(keyword in text_lower for keyword in intent_keywords))

def is_position_inquiry(text: str) -> bool:
    """
    Check if the message text is asking about positions.
    Part of the intelligent recognition system for the One-Touch navigation.
    """
    # Button-text matches
    button_texts = [
        "view my positions", "view positions", "positions", "my positions", 
        "👁️ view my positions", "portfolio"
    ]
    
    # Intent keywords - natural language variations
    intent_keywords = [
        "my investment", "holdings", "my stake", "balance", "my pools", 
        "my liquidity", "what am i holding", "where is my money",
        "show me my investments", "what do i own", "my funds", 
        "what have i invested in", "show investments", 
        "my portfolio", "check positions", "check my positions"
    ]
    
    text_lower = text.lower()
    return (any(keyword in text_lower for keyword in button_texts) or 
            any(keyword in text_lower for keyword in intent_keywords))

def is_pool_inquiry(text: str) -> bool:
    """
    Check if the message text is asking about pools.
    Part of the One-Touch navigation system's intelligent text recognition.
    """
    # Button-text matches
    button_texts = [
        "explore", "🔍 explore", "explore options", "top pools", "🏆 top pools",
        "pools", "show pools", "list pools"
    ]
    
    # Intent keywords - natural language variations
    intent_keywords = [
        "liquidity pool", "best pools", "pool options", "market", 
        "opportunities", "pairs", "apr", "yield", "returns", 
        "what pools", "show me pools", "available pools", "highest apr",
        "profitable pools", "good investments", "promising pools",
        "which pools", "recommend pools", "pool list", "pool data",
        "highest yield", "current pools", "best options", "top performing",
        "best rates", "high yield", "earning"
    ]
    
    text_lower = text.lower()
    return (any(keyword in text_lower for keyword in button_texts) or 
            any(keyword in text_lower for keyword in intent_keywords))

def is_wallet_inquiry(text: str) -> bool:
    """
    Check if the message text is asking about wallet connections.
    This assists the One-Touch navigation by recognizing wallet-related requests.
    """
    # Button-text matches
    button_texts = [
        "account", "👤 account", "my account", "👤 my account",
        "connect wallet", "💼 connect wallet", "wallet"
    ]
    
    # Intent keywords - natural language variations
    intent_keywords = [
        "walletconnect", "my wallet", "link wallet", "crypto wallet",  
        "connect my wallet", "setup wallet", "pair wallet", "wallet setup",
        "add wallet", "register wallet", "use my wallet", "scan qr code",
        "wallet address", "wallet integration", "solana wallet"
    ]
    
    text_lower = text.lower()
    return (any(keyword in text_lower for keyword in button_texts) or 
            any(keyword in text_lower for keyword in intent_keywords))

def extract_amount(text: str) -> float:
    """
    Extract an investment amount from text with enhanced pattern matching.
    Part of the One-Touch navigation system to detect investment amounts
    in natural language.
    
    Returns:
        float: The detected amount, or 0 if no amount found
    """
    import re
    
    # Clean text for better pattern matching
    text = text.lower().strip()
    
    # First check for One-Touch button text with amounts
    amount_buttons = {
        "$50": 50.0, "$100": 100.0, "$200": 200.0, "$250": 250.0, 
        "$300": 300.0, "$500": 500.0, "$750": 750.0, 
        "$1,000": 1000.0, "$2,000": 2000.0, "$5,000": 5000.0, "$10,000": 10000.0
    }
    
    # Check if any button amount text appears in the message
    for button_text, amount in amount_buttons.items():
        # Remove dollar sign and emoji from comparison
        clean_button = button_text.replace("$", "").replace(",", "").replace("💰", "").strip()
        if clean_button in text.replace(",", ""):
            return amount
            
    # More comprehensive pattern matching
    # Match patterns like "$100", "100 dollars", "100USD", "100.50", "1,000", "1k", "5k"
    amount_patterns = [
        # Standard currency format with or without $ and decimal
        r'\$?(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:dollars|usd)?',
        
        # Handle "k" notation (e.g., "5k" = 5000)
        r'(\d+(?:\.\d+)?)\s*k\b'
    ]
    
    for pattern in amount_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1)
            
            # Handle "k" notation
            if pattern.endswith(r'k\b'):
                return float(amount_str) * 1000
            
            # Handle regular numbers with commas
            return float(amount_str.replace(",", ""))
    
    return 0.0