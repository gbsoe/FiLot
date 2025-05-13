"""
Global variables for the Telegram bot.
This module provides access to shared resources between modules.
"""

# Global bot instance
bot = None

# Function to set the bot instance
def set_bot(bot_instance):
    """
    Set the global bot instance.
    
    Args:
        bot_instance: The Telegram bot instance
    """
    global bot
    bot = bot_instance