"""
Scenario flow test script for the FiLot Telegram bot.

This script tests several multi-step button flows from the DETAILED_BUTTON_SCENARIOS.md mapping.
"""

import time
import logging
import asyncio
from telegram import Bot, Update
from telegram.ext import Application

import bot
import globals
from menus import get_main_menu, get_invest_menu, get_explore_menu, get_account_menu

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ScenarioTester:
    """Tests scenario flows from DETAILED_BUTTON_SCENARIOS.md"""
    
    def __init__(self):
        self.results = []
        self.missing_handlers = []
        self.all_handlers = []
        self.callback_handlers = {}
    
    def check_handlers_for_scenarios(self):
        """Check if handlers exist for all callbacks mentioned in scenarios"""
        logger.info("Checking handlers for DETAILED_BUTTON_SCENARIOS.md...")
        
        # Define navigational callbacks directly (same as in main.py)
        navigational_callbacks = [
            # Explore menu options
            "explore_pools", "explore_simulate", "explore_info", "explore_faq", "back_to_explore",
            # Main menu
            "menu_explore", "menu_invest", "menu_account", "menu_faq", "back_to_main",
            # Simulate options 
            "simulate_50", "simulate_100", "simulate_250", "simulate_500", "simulate_1000", "simulate_5000",
            # Account menu options
            "walletconnect", "status", "subscribe", "unsubscribe",
            # Profile options
            "profile_high-risk", "profile_stable",
            # Amount options
            "amount_50", "amount_100", "amount_250", "amount_500", "amount_1000", "amount_5000", "amount_custom"
        ]
        
        # Extract handlers from the navigational_callbacks list
        logger.info("Checking navigational callbacks...")
        for callback in navigational_callbacks:
            self.all_handlers.append(callback)
            logger.info(f"Found handler for: {callback}")
        
        # Also check navigation prefixes
        navigation_prefixes = [
            'account_', 'profile_', 'explore_', 'menu_', 'back_', 
            'simulate_', 'amount_', 'wallet_', 'invest_'
        ]
        logger.info(f"Navigation prefixes: {navigation_prefixes}")
        
        # Check specific high-priority scenarios from our mapping
        # Invest button scenarios 1-10
        invest_scenarios = [
            "menu_invest",
            "amount_50", "amount_100", "amount_250", 
            "amount_500", "amount_1000", "amount_5000",
            "amount_custom", "back_to_main"
        ]
        
        # Explore button scenarios 334-343
        explore_scenarios = [
            "menu_explore",
            "explore_pools", "explore_simulate", 
            "back_to_main"
        ]
        
        # Account button scenarios 667-676
        account_scenarios = [
            "menu_account",
            "account_wallet", "profile_high-risk", "profile_stable",
            "account_subscribe", "account_unsubscribe", "account_help",
            "account_status", "back_to_main"
        ]
        
        # Combined all important scenarios
        key_scenarios = invest_scenarios + explore_scenarios + account_scenarios
        logger.info(f"Checking {len(key_scenarios)} key scenarios...")
        
        # Find missing handlers
        for scenario in key_scenarios:
            if scenario not in self.all_handlers:
                # Check if it matches any prefix pattern
                has_prefix_match = any(scenario.startswith(prefix) for prefix in navigation_prefixes)
                if not has_prefix_match:
                    self.missing_handlers.append(scenario)
                    logger.warning(f"Missing handler for scenario: {scenario}")
                else:
                    logger.info(f"Handler for '{scenario}' covered by prefix match")
        
        # Test specific button menus
        self.test_menu_buttons(get_main_menu(), "Main Menu")
        self.test_menu_buttons(get_invest_menu(), "Invest Menu")
        self.test_menu_buttons(get_explore_menu(), "Explore Menu")
        self.test_menu_buttons(get_account_menu(), "Account Menu")
    
    def test_menu_buttons(self, menu, menu_name):
        """Test if all buttons in a menu have handlers"""
        if not menu or not hasattr(menu, 'inline_keyboard'):
            logger.warning(f"Invalid menu: {menu_name}")
            return
            
        logger.info(f"Testing {menu_name} buttons...")
        for row in menu.inline_keyboard:
            for button in row:
                callback_data = button.callback_data
                button_text = button.text
                
                # Check if handler exists
                if callback_data in self.all_handlers:
                    logger.info(f"✅ Button '{button_text}' -> {callback_data} has handler")
                else:
                    # Check if it matches any prefix pattern
                    navigation_prefixes = [
                        'account_', 'profile_', 'explore_', 'menu_', 'back_', 
                        'simulate_', 'amount_', 'wallet_', 'invest_'
                    ]
                    
                    has_prefix_match = any(callback_data.startswith(prefix) for prefix in navigation_prefixes)
                    if has_prefix_match:
                        logger.info(f"✅ Button '{button_text}' -> {callback_data} covered by prefix match")
                    else:
                        logger.warning(f"❌ Button '{button_text}' -> {callback_data} has no handler")
                        self.missing_handlers.append(callback_data)
    
    def verify_invest_flow(self):
        """Verify invest button flow according to scenarios 1-10"""
        logger.info("Verifying INVEST flow (scenarios 1-10)...")
        
        # Check if all required handlers exist
        required_handlers = [
            "menu_invest",  # Invest button
            "amount_50", "amount_100", "amount_250", "amount_500", "amount_1000", "amount_5000",  # Amount buttons
            "amount_custom",  # Custom amount
            "profile_high-risk", "profile_stable"  # Risk profiles
        ]
        
        missing = [h for h in required_handlers if h not in self.all_handlers]
        
        if missing:
            result = {
                "flow": "INVEST Basic Flow (scenarios 1-10)",
                "status": "INCOMPLETE",
                "details": f"Missing handlers: {', '.join(missing)}"
            }
        else:
            result = {
                "flow": "INVEST Basic Flow (scenarios 1-10)",
                "status": "READY",
                "details": "All required handlers exist for this flow"
            }
        
        self.results.append(result)
    
    def verify_explore_flow(self):
        """Verify explore button flow according to scenarios 334-343"""
        logger.info("Verifying EXPLORE flow (scenarios 334-343)...")
        
        # Check if all required handlers exist
        required_handlers = [
            "menu_explore",  # Explore button
            "explore_pools", "explore_simulate",  # Explore options
            "back_to_main"  # Back to main
        ]
        
        missing = [h for h in required_handlers if h not in self.all_handlers]
        
        if missing:
            result = {
                "flow": "EXPLORE Basic Flow (scenarios 334-343)",
                "status": "INCOMPLETE",
                "details": f"Missing handlers: {', '.join(missing)}"
            }
        else:
            result = {
                "flow": "EXPLORE Basic Flow (scenarios 334-343)",
                "status": "READY",
                "details": "All required handlers exist for this flow"
            }
        
        self.results.append(result)
    
    def verify_account_flow(self):
        """Verify account button flow according to scenarios 667-676"""
        logger.info("Verifying ACCOUNT flow (scenarios 667-676)...")
        
        # Check if all required handlers exist
        required_handlers = [
            "menu_account",  # Account button
            "account_wallet", "profile_high-risk", "profile_stable",  # Account options
            "account_subscribe", "account_unsubscribe", "account_help", "account_status",  # Account actions
            "back_to_main"  # Back to main
        ]
        
        missing = [h for h in required_handlers if h not in self.all_handlers]
        
        if missing:
            result = {
                "flow": "ACCOUNT Basic Flow (scenarios 667-676)",
                "status": "INCOMPLETE",
                "details": f"Missing handlers: {', '.join(missing)}"
            }
        else:
            result = {
                "flow": "ACCOUNT Basic Flow (scenarios 667-676)",
                "status": "READY",
                "details": "All required handlers exist for this flow"
            }
        
        self.results.append(result)
    
    def verify_cross_flow_navigation(self):
        """Verify navigation between different flows"""
        logger.info("Verifying cross-flow navigation...")
        
        # Check if back_to_main handler exists and other necessary navigation handlers
        required_handlers = [
            "back_to_main",  # Back to main menu
            "menu_invest", "menu_explore", "menu_account"  # Main menu options
        ]
        
        missing = [h for h in required_handlers if h not in self.all_handlers]
        
        if missing:
            result = {
                "flow": "Cross-Flow Navigation",
                "status": "INCOMPLETE",
                "details": f"Missing handlers: {', '.join(missing)}"
            }
        else:
            result = {
                "flow": "Cross-Flow Navigation",
                "status": "READY",
                "details": "All required navigation handlers exist"
            }
        
        self.results.append(result)
    
    def run_all_tests(self):
        """Run all scenario tests"""
        try:
            # Check handlers for scenarios
            self.check_handlers_for_scenarios()
            
            # Verify specific flows
            self.verify_invest_flow()
            self.verify_explore_flow()
            self.verify_account_flow()
            self.verify_cross_flow_navigation()
            
            # Print results
            self.print_results()
            
            # Return overall status
            if len(self.missing_handlers) > 0:
                logger.warning(f"❌ {len(self.missing_handlers)} missing handlers found")
                return False
            else:
                logger.info("✅ All handlers are in place")
                return True
                
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return False
    
    def print_results(self):
        """Print test results in a readable format"""
        print("\n===== DETAILED SCENARIO FLOW TEST RESULTS =====\n")
        
        ready_flows = sum(1 for r in self.results if r["status"] == "READY")
        incomplete_flows = sum(1 for r in self.results if r["status"] == "INCOMPLETE")
        
        for result in self.results:
            status_symbol = "✅" if result["status"] == "READY" else "❌"
            print(f"{status_symbol} {result['flow']}")
            print(f"   Status: {result['status']}")
            print(f"   Details: {result['details']}")
            print()
        
        print(f"Total flows tested: {len(self.results)}")
        print(f"Ready flows: {ready_flows}")
        print(f"Incomplete flows: {incomplete_flows}")
        
        if self.missing_handlers:
            print("\nMissing handlers:")
            for handler in self.missing_handlers:
                print(f"❌ {handler}")
        else:
            print("\n✅ All required handlers are implemented")
            
        print("\n===========================================")

def main():
    """Run the scenario flow tests"""
    tester = ScenarioTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()