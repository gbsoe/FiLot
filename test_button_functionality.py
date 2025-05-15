"""
Button functionality test script for the FiLot Telegram bot.

This script tests all the major button navigation paths defined in BUTTON_NAVIGATION_MAP.md
to ensure they are working correctly.
"""

import logging
import asyncio
import time
from typing import List, Dict, Any, Optional

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Import necessary components for testing
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes

# Import bot module components
import bot
from bot import create_application
from menus import get_account_menu, get_explore_menu, get_invest_menu, get_main_menu
from keyboard_utils import MAIN_KEYBOARD

# Import test utilities
from telegram.ext import ExtBot

class ButtonTester:
    """Tests button functionality against the documented navigation map."""
    
    def __init__(self):
        self.test_results = []
        self.failures = []
        self.bot_app = None
        
    async def setup(self):
        """Initialize the bot application for testing."""
        try:
            # Create the application but don't start polling
            self.bot_app = create_application()
            logger.info("Bot application created for testing")
            return True
        except Exception as e:
            logger.error(f"Error setting up bot for testing: {e}")
            return False
            
    async def test_button_exists(self, menu_function, button_text: str, 
                                 expected_callback: str) -> bool:
        """
        Test if a button with specific text and callback exists in a menu.
        
        Args:
            menu_function: Function that returns an InlineKeyboardMarkup
            button_text: Text to look for on the button
            expected_callback: Expected callback_data value
            
        Returns:
            True if button exists with correct callback, False otherwise
        """
        try:
            # Get the menu
            menu = menu_function()
            
            # Verify it's a keyboard markup
            if not isinstance(menu, InlineKeyboardMarkup):
                self.failures.append(f"Menu is not an InlineKeyboardMarkup: {type(menu)}")
                return False
                
            # Search all buttons in the keyboard
            for row in menu.inline_keyboard:
                for button in row:
                    if button.text == button_text:
                        if button.callback_data == expected_callback:
                            return True
                        else:
                            self.failures.append(
                                f"Button '{button_text}' has incorrect callback: "
                                f"expected '{expected_callback}', got '{button.callback_data}'"
                            )
                            return False
            
            # Button not found
            self.failures.append(f"Button with text '{button_text}' not found in menu")
            return False
            
        except Exception as e:
            self.failures.append(f"Error testing button existence: {e}")
            return False

    async def verify_callback_handler_exists(self, callback_data: str) -> bool:
        """
        Test if a callback handler exists for a specific callback_data.
        
        This checks if either main.py or bot.py has a handler for this callback.
        
        Args:
            callback_data: The callback_data to check for
            
        Returns:
            True if handler exists, False otherwise
        """
        # This is a simplified check that examines our handled callbacks
        handled_callbacks = [
            # Main navigation
            "back_to_main",
            
            # Account section
            "account_wallet", "account_subscribe", "account_unsubscribe", 
            "account_help", "account_status",
            
            # Invest section
            "menu_invest", "menu_positions",
            "amount_100", "amount_250", "amount_500", "amount_1000", "amount_5000", 
            "amount_custom",
            
            # Explore section
            "menu_explore", "explore_pools", "explore_simulate",
            "simulate_100", "simulate_500", "simulate_1000", "simulate_5000", 
            "simulate_custom",
            
            # Profile section
            "profile_high-risk", "profile_stable"
        ]
        
        # Check for prefix matches (for dynamic callbacks like pool_detail_X)
        callback_prefixes = [
            "pool_detail_", "pool_recommendation_", "position_detail_",
            "exit_position_", "confirm_exit_", "invest_in_pool_", "simulation_detail_"
        ]
        
        # Check exact matches
        if callback_data in handled_callbacks:
            return True
            
        # Check prefix matches
        for prefix in callback_prefixes:
            if callback_data.startswith(prefix):
                return True
                
        self.failures.append(f"No handler found for callback: {callback_data}")
        return False

    async def test_account_buttons(self):
        """Test all Account section buttons."""
        logger.info("Testing Account menu buttons...")
        
        # Get the account menu
        account_menu = get_account_menu()
        
        # Expected buttons in the account menu
        expected_buttons = [
            ("💼 Connect Wallet", "account_wallet"),
            ("🔴 High-Risk Profile", "profile_high-risk"),
            ("🟢 Stable Profile", "profile_stable"),
            ("🔔 Subscribe", "account_subscribe"),
            ("🔕 Unsubscribe", "account_unsubscribe"),
            ("❓ Help", "account_help"),
            ("📊 Status", "account_status"),
            ("🏠 Back to Main Menu", "back_to_main")
        ]
        
        # Test each button
        for button_text, callback_data in expected_buttons:
            exists = await self.test_button_exists(get_account_menu, button_text, callback_data)
            handler_exists = await self.verify_callback_handler_exists(callback_data)
            
            self.test_results.append({
                "section": "Account",
                "button": button_text,
                "callback": callback_data,
                "button_exists": exists,
                "handler_exists": handler_exists,
                "status": "PASS" if exists and handler_exists else "FAIL"
            })
            
        logger.info(f"Account menu button tests completed: {len(self.test_results)} tests")

    async def test_invest_buttons(self):
        """Test all Invest section buttons."""
        logger.info("Testing Invest menu buttons...")
        
        # Get the investment menu
        invest_menu = get_investment_menu()
        
        # Expected buttons in the investment menu
        expected_buttons = [
            ("$100 💸", "amount_100"),
            ("$250 💸", "amount_250"),
            ("$500 💸", "amount_500"),
            ("$1,000 💰", "amount_1000"),
            ("$5,000 💰", "amount_5000"),
            ("👁️ View My Positions", "menu_positions"),
            ("✏️ Custom Amount", "amount_custom"),
            ("🏠 Back to Main Menu", "back_to_main")
        ]
        
        # Test each button
        for button_text, callback_data in expected_buttons:
            exists = await self.test_button_exists(get_investment_menu, button_text, callback_data)
            handler_exists = await self.verify_callback_handler_exists(callback_data)
            
            self.test_results.append({
                "section": "Invest",
                "button": button_text,
                "callback": callback_data,
                "button_exists": exists,
                "handler_exists": handler_exists,
                "status": "PASS" if exists and handler_exists else "FAIL"
            })
            
        logger.info(f"Invest menu button tests completed: {len(self.test_results) - 8} tests")

    async def test_explore_buttons(self):
        """Test all Explore section buttons."""
        logger.info("Testing Explore menu buttons...")
        
        # Get the explore menu
        explore_menu = get_explore_menu()
        
        # Expected buttons in the explore menu
        expected_buttons = [
            ("🏆 Top Pools", "explore_pools"),
            ("📊 Simulate Returns", "explore_simulate"),
            ("🏠 Back to Main Menu", "back_to_main")
        ]
        
        # Test each button
        for button_text, callback_data in expected_buttons:
            exists = await self.test_button_exists(get_explore_menu, button_text, callback_data)
            handler_exists = await self.verify_callback_handler_exists(callback_data)
            
            self.test_results.append({
                "section": "Explore",
                "button": button_text,
                "callback": callback_data,
                "button_exists": exists,
                "handler_exists": handler_exists,
                "status": "PASS" if exists and handler_exists else "FAIL"
            })
            
        logger.info(f"Explore menu button tests completed: {len(self.test_results) - 16} tests")

    async def test_main_menu_buttons(self):
        """Test all main menu buttons."""
        logger.info("Testing Main menu buttons...")
        
        # Get the main menu
        main_menu = get_main_menu()
        
        # Expected buttons in the main menu
        expected_buttons = [
            ("💰 Invest", "menu_invest"),
            ("🔍 Explore", "menu_explore"),
            ("👤 Account", "menu_account"),
        ]
        
        # Test each button
        for button_text, callback_data in expected_buttons:
            exists = await self.test_button_exists(get_main_menu, button_text, callback_data)
            handler_exists = await self.verify_callback_handler_exists(callback_data)
            
            self.test_results.append({
                "section": "Main Menu",
                "button": button_text,
                "callback": callback_data,
                "button_exists": exists,
                "handler_exists": handler_exists,
                "status": "PASS" if exists and handler_exists else "FAIL"
            })
            
        logger.info(f"Main menu button tests completed: {len(self.test_results) - 19} tests")

    async def run_all_tests(self):
        """Run all button functionality tests."""
        logger.info("Starting button functionality tests...")
        
        # Setup the testing environment
        setup_success = await self.setup()
        if not setup_success:
            logger.error("Failed to set up testing environment. Aborting tests.")
            return False
            
        # Run tests for each section
        await self.test_main_menu_buttons()
        await self.test_account_buttons()
        await self.test_invest_buttons()
        await self.test_explore_buttons()
        
        # Print test results
        passed = sum(1 for result in self.test_results if result["status"] == "PASS")
        failed = sum(1 for result in self.test_results if result["status"] == "FAIL")
        
        logger.info("Button functionality tests completed.")
        logger.info(f"Total tests: {len(self.test_results)}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        
        return True

    def print_results(self):
        """Print detailed test results."""
        print("\n===== BUTTON FUNCTIONALITY TEST RESULTS =====")
        
        current_section = None
        for result in self.test_results:
            # Print section header when section changes
            if result["section"] != current_section:
                current_section = result["section"]
                print(f"\n--- {current_section} Section ---")
                
            # Print test result
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            print(f"{status_icon} Button: {result['button']} -> {result['callback']}")
            
            # Print failure details if any
            if result["status"] == "FAIL":
                if not result["button_exists"]:
                    print(f"   ↳ Button doesn't exist in menu")
                if not result["handler_exists"]:
                    print(f"   ↳ No handler found for callback data")
        
        print("\n--- Failure Details ---")
        if self.failures:
            for i, failure in enumerate(self.failures, 1):
                print(f"{i}. {failure}")
        else:
            print("No failures detected!")
            
        print("\n===========================================")
        
        # Create a summary of fixes needed if any tests failed
        if any(result["status"] == "FAIL" for result in self.test_results):
            print("\n--- Required Fixes ---")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"• Fix {result['section']} button '{result['button']}' with callback '{result['callback']}'")
            print()


async def main():
    """Run the button tests and print results."""
    tester = ButtonTester()
    await tester.run_all_tests()
    tester.print_results()


if __name__ == "__main__":
    asyncio.run(main())