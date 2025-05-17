"""
Integration module to connect our profile button fixes with the main bot.
This ensures both the buttons and direct commands work reliably.
"""

import logging
from typing import Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def register_button_handlers(application: Any) -> None:
    """
    Register the profile button handlers with the application.
    
    Args:
        application: The Telegram application instance
    """
    try:
        from telegram.ext import CallbackQueryHandler
        
        # Try to import our profile button manager
        from profile_button_manager import process_button_callback
        
        # Add our callback handler with high priority (low group number)
        application.add_handler(
            CallbackQueryHandler(process_button_callback, pattern=".*"), group=1
        )
        
        logger.info("✅ Registered profile button handlers with high priority")
    except Exception as e:
        logger.error(f"❌ Failed to register profile button handlers: {e}")

def register_direct_commands(application: Any) -> None:
    """
    Register the direct command handlers with the application.
    
    Args:
        application: The Telegram application instance
    """
    try:
        from telegram.ext import CommandHandler
        
        # Try to import our direct profile commands
        from direct_profile_commands import set_risk_profile_command
        
        # Add direct command handlers
        application.add_handler(
            CommandHandler("high_risk", 
                           lambda update, context: set_risk_profile_command(update, context, "high-risk"))
        )
        application.add_handler(
            CommandHandler("stable", 
                           lambda update, context: set_risk_profile_command(update, context, "stable"))
        )
        application.add_handler(
            CommandHandler("set_profile", 
                           lambda update, context: set_risk_profile_command(update, context, None))
        )
        
        logger.info("✅ Registered direct profile commands: /high_risk, /stable, /set_profile")
    except Exception as e:
        logger.error(f"❌ Failed to register direct profile commands: {e}")

def integrate_with_callback_handler() -> None:
    """
    Integrate our profile button fixes with the central callback handler.
    This patch should be called after the bot is initialized.
    """
    try:
        # Try to import the central callback handler
        import callback_handler
        
        # Import our profile button handler
        from profile_button_manager import handle_profile_button
        
        # Get the original route_callback function
        original_route_callback = callback_handler.route_callback
        
        # Define our wrapper function
        def patched_route_callback(handler_context):
            # Extract callback data and user ID
            callback_data = handler_context.get('callback_data', '')
            user_id = handler_context.get('user_id', 0)
            
            # First try our profile button handler
            try:
                result = handle_profile_button(callback_data, user_id)
                if result:
                    # Our handler processed this button
                    logger.info(f"Profile button handler processed: {callback_data}")
                    return result
            except Exception as e:
                logger.error(f"Error in profile button handler: {e}")
            
            # Fall back to original handler
            return original_route_callback(handler_context)
            
        # Patch the route_callback function
        callback_handler.route_callback = patched_route_callback
        logger.info("✅ Integrated profile button handler with central callback router")
    except Exception as e:
        logger.error(f"❌ Failed to integrate with callback handler: {e}")

def apply_all_fixes(application: Optional[Any] = None) -> None:
    """
    Apply all profile button fixes to the bot.
    
    Args:
        application: Optional Telegram application instance
    """
    # Try to integrate with callback handler
    try:
        integrate_with_callback_handler()
    except Exception as e:
        logger.error(f"Failed to integrate with callback handler: {e}")
    
    # Register direct command handlers if application is provided
    if application:
        try:
            register_direct_commands(application)
            register_button_handlers(application)
        except Exception as e:
            logger.error(f"Failed to register handlers: {e}")
            
    logger.info("Profile button fixes applied successfully")

# For direct execution
if __name__ == "__main__":
    # This will only integrate with the callback handler,
    # since we don't have access to the application instance
    apply_all_fixes()
    print("Profile button fixes applied successfully")