"""
Direct menu fix that completely bypasses the problematic code.
This is a simplified implementation for the Account button menu.
"""

# Create a function that returns a static menu
def get_account_menu():
    """
    Returns a static account menu with all the buttons from the screenshot.
    """
    return {
        "inline_keyboard": [
            [{"text": "💼 Connect Wallet", "callback_data": "account_wallet"}],
            [
                {"text": "🔴 High-Risk Profile", "callback_data": "account_profile_high-risk"},
                {"text": "🟢 Stable Profile", "callback_data": "account_profile_stable"}
            ],
            [
                {"text": "🔔 Subscribe", "callback_data": "account_subscribe"},
                {"text": "🔕 Unsubscribe", "callback_data": "account_unsubscribe"}
            ],
            [
                {"text": "❓ Help", "callback_data": "show_help"},
                {"text": "📊 Status", "callback_data": "account_status"}
            ],
            [{"text": "🏠 Back to Main Menu", "callback_data": "back_to_main"}]
        ]
    }

def get_account_message():
    """
    Returns a static account message.
    """
    return (
        "👤 *Your Account* 👤\n\n"
        "Wallet: ❌ Not Connected\n"
        "Risk Profile: Moderate\n"
        "Daily Updates: ❌ Not Subscribed\n\n"
        "Select an option below to manage your account:"
    )