"""
Extended button flow test script for the FiLot Telegram bot.

This script tests deep button flows based on the DETAILED_BUTTON_SCENARIOS.md mapping.
It simulates multi-step interactions to ensure the entire user journey works correctly.
"""

import asyncio
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

import bot
import main
import menus
import globals
import keyboard_utils
import investment_flow
from callback_handler import handle_callback_query
from bot import start_command, help_command

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class MockUpdate:
    """Mock Update class for testing bot interactions"""
    def __init__(self, chat_id=123456789, user_id=123456789, message_text=None, callback_data=None):
        self.effective_chat = type('obj', (object,), {'id': chat_id})
        self.effective_user = type('obj', (object,), {
            'id': user_id, 
            'first_name': 'Test',
            'last_name': 'User',
            'username': 'testuser'
        })
        
        if message_text:
            self.effective_message = type('obj', (object,), {
                'text': message_text,
                'chat': self.effective_chat,
                'reply_text': self._mock_reply_text,
                'reply_markdown': self._mock_reply_markdown,
                'reply_html': self._mock_reply_html,
                'reply_markup': None
            })
            self.message = self.effective_message
            self.callback_query = None
        elif callback_data:
            self.callback_query = type('obj', (object,), {
                'data': callback_data,
                'id': 'test_callback_id',
                'from_user': self.effective_user,
                'message': type('obj', (object,), {
                    'chat': self.effective_chat,
                    'reply_text': self._mock_reply_text,
                    'reply_markdown': self._mock_reply_markdown,
                    'reply_html': self._mock_reply_html,
                    'reply_markup': None
                }),
                'answer': self._mock_answer
            })
            self.effective_message = self.callback_query.message
            self.message = None
    
    def _mock_reply_text(self, text, **kwargs):
        logger.info(f"Mock reply text: {text}")
        if 'reply_markup' in kwargs:
            self._log_keyboard(kwargs['reply_markup'])
        return type('obj', (object,), {'message_id': 12345})
    
    def _mock_reply_markdown(self, text, **kwargs):
        logger.info(f"Mock reply markdown: {text}")
        if 'reply_markup' in kwargs:
            self._log_keyboard(kwargs['reply_markup'])
        return type('obj', (object,), {'message_id': 12345})
    
    def _mock_reply_html(self, text, **kwargs):
        logger.info(f"Mock reply HTML: {text}")
        if 'reply_markup' in kwargs:
            self._log_keyboard(kwargs['reply_markup'])
        return type('obj', (object,), {'message_id': 12345})
    
    def _mock_answer(self, text=None, **kwargs):
        if text:
            logger.info(f"Mock callback answer: {text}")
        return True
    
    def _log_keyboard(self, reply_markup):
        if isinstance(reply_markup, InlineKeyboardMarkup):
            logger.info("Keyboard buttons:")
            for row in reply_markup.inline_keyboard:
                button_info = []
                for button in row:
                    button_info.append(f"{button.text} -> {button.callback_data}")
                logger.info(", ".join(button_info))

class MockContext:
    """Mock Context class for testing bot interactions"""
    def __init__(self):
        self.user_data = {}
        self.bot = type('obj', (object,), {
            'send_message': self._mock_send_message,
        })
    
    def _mock_send_message(self, chat_id, text, **kwargs):
        logger.info(f"Mock send message to {chat_id}: {text}")
        if 'reply_markup' in kwargs:
            self._log_keyboard(kwargs['reply_markup'])
        return type('obj', (object,), {'message_id': 12345})
    
    def _log_keyboard(self, reply_markup):
        if isinstance(reply_markup, InlineKeyboardMarkup):
            logger.info("Keyboard buttons:")
            for row in reply_markup.inline_keyboard:
                button_info = []
                for button in row:
                    button_info.append(f"{button.text} -> {button.callback_data}")
                logger.info(", ".join(button_info))

class ButtonFlowTester:
    """Tests complex button flows based on scenarios in DETAILED_BUTTON_SCENARIOS.md"""
    
    def __init__(self):
        self.results = []
        self.app = None
    
    async def setup(self):
        """Set up the testing environment"""
        self.context = MockContext()
        logger.info("Setting up button flow tests...")
    
    async def test_invest_flow_basic(self):
        """Test basic invest flow: INVEST -> $50 -> High-Risk -> Pool Selection"""
        logger.info("Testing basic invest flow...")
        
        # Step 1: INVEST NOW button
        update = MockUpdate(callback_data="menu_invest")
        await handle_callback_query(update, self.context)
        
        # Step 2: $50 amount button
        update = MockUpdate(callback_data="amount_50")
        await handle_callback_query(update, self.context)
        
        # Step 3: High-Risk profile button
        update = MockUpdate(callback_data="profile_high-risk")
        await handle_callback_query(update, self.context)
        
        # Check if flow worked correctly
        pool_selection_reached = "invest_profile" in self.context.user_data and self.context.user_data["invest_profile"] == "high-risk"
        amount_stored = "invest_amount" in self.context.user_data and self.context.user_data["invest_amount"] == 50
        
        self.results.append({
            "test": "Basic Invest Flow",
            "status": "PASS" if pool_selection_reached and amount_stored else "FAIL",
            "details": f"Profile: {self.context.user_data.get('invest_profile')}, Amount: {self.context.user_data.get('invest_amount')}"
        })
    
    async def test_explore_flow_basic(self):
        """Test basic explore flow: EXPLORE -> Top Pools"""
        logger.info("Testing basic explore flow...")
        
        # Step 1: EXPLORE button
        update = MockUpdate(callback_data="menu_explore")
        await handle_callback_query(update, self.context)
        
        # Step 2: Top Pools button
        update = MockUpdate(callback_data="explore_pools")
        await handle_callback_query(update, self.context)
        
        # No specific state to check for this flow, just ensure no errors
        self.results.append({
            "test": "Basic Explore Flow",
            "status": "PASS",
            "details": "Navigation completed without errors"
        })
    
    async def test_account_flow_basic(self):
        """Test basic account flow: ACCOUNT -> Risk Profile selection"""
        logger.info("Testing basic account flow...")
        
        # Step 1: ACCOUNT button
        update = MockUpdate(callback_data="menu_account")
        await handle_callback_query(update, self.context)
        
        # Step 2: High-Risk Profile button
        update = MockUpdate(callback_data="profile_high-risk")
        await handle_callback_query(update, self.context)
        
        # Check if profile was set
        from app import app
        with app.app_context():
            import db_utils
            db_user = db_utils.get_or_create_user(123456789)
            profile_set = hasattr(db_user, 'risk_profile') and db_user.risk_profile == 'high-risk'
        
        self.results.append({
            "test": "Basic Account Flow",
            "status": "PASS" if profile_set else "FAIL",
            "details": f"Profile set correctly in database: {profile_set}"
        })
    
    async def test_navigation_between_menus(self):
        """Test navigation between main, invest, explore, and account menus"""
        logger.info("Testing navigation between menus...")
        
        # Start at main menu
        update = MockUpdate(message_text="/start")
        await start_command(update, self.context)
        
        # Navigate to invest menu
        update = MockUpdate(callback_data="menu_invest")
        await handle_callback_query(update, self.context)
        
        # Back to main menu
        update = MockUpdate(callback_data="back_to_main")
        await handle_callback_query(update, self.context)
        
        # Navigate to explore menu
        update = MockUpdate(callback_data="menu_explore")
        await handle_callback_query(update, self.context)
        
        # Back to main menu
        update = MockUpdate(callback_data="back_to_main")
        await handle_callback_query(update, self.context)
        
        # Navigate to account menu
        update = MockUpdate(callback_data="menu_account")
        await handle_callback_query(update, self.context)
        
        # Back to main menu
        update = MockUpdate(callback_data="back_to_main")
        await handle_callback_query(update, self.context)
        
        # No specific state to check, just ensure no errors
        self.results.append({
            "test": "Navigation Between Menus",
            "status": "PASS",
            "details": "Successfully navigated between all main menus"
        })
    
    async def test_repeated_button_presses(self):
        """Test handling of repeated button presses"""
        logger.info("Testing repeated button presses...")
        
        # Press INVEST button multiple times
        for _ in range(3):
            update = MockUpdate(callback_data="menu_invest")
            await handle_callback_query(update, self.context)
        
        # Press $50 button multiple times
        for _ in range(3):
            update = MockUpdate(callback_data="amount_50")
            await handle_callback_query(update, self.context)
        
        # Press high-risk profile button multiple times
        for _ in range(3):
            update = MockUpdate(callback_data="profile_high-risk")
            await handle_callback_query(update, self.context)
        
        # No specific state to check, just ensure no errors
        self.results.append({
            "test": "Repeated Button Presses",
            "status": "PASS",
            "details": "Repeatedly pressed same buttons without errors"
        })
    
    async def run_all_tests(self):
        """Run all button flow tests"""
        await self.setup()
        
        tests = [
            self.test_invest_flow_basic,
            self.test_explore_flow_basic,
            self.test_account_flow_basic,
            self.test_navigation_between_menus,
            self.test_repeated_button_presses
        ]
        
        for test in tests:
            try:
                await test()
            except Exception as e:
                logger.error(f"Error in {test.__name__}: {e}")
                self.results.append({
                    "test": test.__name__,
                    "status": "ERROR",
                    "details": str(e)
                })
        
        self.print_results()
    
    def print_results(self):
        """Print test results in a readable format"""
        print("\n===== BUTTON FLOW TEST RESULTS =====\n")
        
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        errors = sum(1 for r in self.results if r["status"] == "ERROR")
        
        for result in self.results:
            status_symbol = "✅" if result["status"] == "PASS" else "❌"
            print(f"{status_symbol} {result['test']}")
            print(f"   Status: {result['status']}")
            print(f"   Details: {result['details']}")
            print()
        
        print(f"Total tests: {len(self.results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Errors: {errors}")
        print("\n===========================================")

async def main():
    """Run the button flow tests"""
    tester = ButtonFlowTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())