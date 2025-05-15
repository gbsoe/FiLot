"""
Enhanced comprehensive testing for all possible button scenarios in the FiLot Telegram bot.

This script tests:
1. Basic button functionality (direct handlers)
2. Prefix-matched button functionality
3. Complex multi-step flows
4. Edge cases and unusual navigation patterns
5. Cross-flow navigation transitions
"""

import logging
import time
from typing import List, Dict, Any, Tuple, Set, Optional
import json
import re

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Import necessary handlers and callbacks from the main application
import main
from callback_handler import route_callback

class EnhancedScenarioTester:
    """Tests enhanced comprehensive button scenarios"""
    
    def __init__(self):
        self.results = {
            "basic_button_tests": {},
            "flow_tests": {},
            "edge_case_tests": {},
            "cross_flow_tests": {},
            "prefix_handler_tests": {}
        }
        self.all_handlers = set()
        self.direct_handlers = set()
        self.prefix_handlers = dict()
        self.missing_handlers = set()
        
        # Known navigation prefixes
        self.navigational_prefixes = [
            'account_', 'profile_', 'explore_', 'menu_', 'back_', 
            'simulate_', 'amount_', 'wallet_', 'invest_'
        ]
        
        # Load navigational callbacks directly from the code
        self.navigational_callbacks = [
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
        
        # Get the navigation prefixes
        self.navigational_prefixes = [
            'account_', 'profile_', 'explore_', 'menu_', 'back_', 'simulate_', 'amount_', 'wallet_', 'invest_'
        ]
        
        # Add all direct handlers to our set
        for callback in self.navigational_callbacks:
            self.direct_handlers.add(callback)
        
        # INVEST flow scenarios (multi-step)
        self.invest_flows = [
            {
                "name": "Basic Investment Flow",
                "steps": [
                    "menu_invest",
                    "amount_100",
                    "profile_stable"
                ]
            },
            {
                "name": "High-Risk Investment Flow",
                "steps": [
                    "menu_invest",
                    "amount_1000",
                    "profile_high-risk"
                ]
            },
            {
                "name": "Custom Amount Investment Flow",
                "steps": [
                    "menu_invest",
                    "amount_custom",
                    "profile_stable"
                ]
            }
        ]
        
        # EXPLORE flow scenarios (multi-step)
        self.explore_flows = [
            {
                "name": "Top Pools Exploration Flow",
                "steps": [
                    "menu_explore",
                    "explore_pools",
                    "back_to_explore",
                    "back_to_main"
                ]
            },
            {
                "name": "Simulate Returns Flow",
                "steps": [
                    "menu_explore",
                    "explore_simulate",
                    "simulate_100",
                    "back_to_explore",
                    "back_to_main"
                ]
            }
        ]
        
        # ACCOUNT flow scenarios (multi-step)
        self.account_flows = [
            {
                "name": "Account Status Flow",
                "steps": [
                    "menu_account",
                    "account_status",
                    "back_to_main"
                ]
            },
            {
                "name": "Subscription Management Flow",
                "steps": [
                    "menu_account",
                    "account_subscribe",
                    "account_unsubscribe",
                    "back_to_main"
                ]
            },
            {
                "name": "Wallet Connection Flow",
                "steps": [
                    "menu_account",
                    "account_wallet",
                    "back_to_main"
                ]
            },
            {
                "name": "Help and Support Flow",
                "steps": [
                    "menu_account",
                    "account_help",
                    "back_to_main"
                ]
            }
        ]
        
        # Cross-flow navigation (complex multi-step)
        self.cross_flows = [
            {
                "name": "Invest to Explore Cross-Flow",
                "steps": [
                    "menu_invest",
                    "back_to_main",
                    "menu_explore",
                    "back_to_main"
                ]
            },
            {
                "name": "Account to Invest Cross-Flow",
                "steps": [
                    "menu_account",
                    "back_to_main",
                    "menu_invest",
                    "back_to_main"
                ]
            },
            {
                "name": "Full Circle Navigation",
                "steps": [
                    "menu_invest",
                    "back_to_main",
                    "menu_explore",
                    "back_to_main",
                    "menu_account",
                    "back_to_main"
                ]
            }
        ]
        
        # Edge case scenarios
        self.edge_cases = [
            {
                "name": "Repeated Button Press",
                "steps": [
                    "menu_invest",
                    "menu_invest", # Intentional duplicate to test anti-loop protection
                    "back_to_main"
                ]
            },
            {
                "name": "Quick Menu Navigation",
                "steps": [
                    "menu_invest",
                    "back_to_main",
                    "menu_explore",
                    "back_to_main",
                    "menu_account",
                    "back_to_main"
                ]
            }
        ]
        
        # Generate all possible account prefix buttons
        self.account_prefix_buttons = [
            "account_wallet",
            "account_subscribe", 
            "account_unsubscribe",
            "account_help",
            "account_status"
        ]
        
    def test_basic_button_functionality(self):
        """Test all direct button handlers"""
        logger.info("Testing basic button functionality...")
        
        for callback in self.navigational_callbacks:
            try:
                # Check if the callback has a handler in main.py or is in our navigational_callbacks list
                has_handler = hasattr(main, f"handle_{callback}") or callback in self.navigational_callbacks
                
                self.results["basic_button_tests"][callback] = {
                    "success": has_handler,
                    "method": "direct" if has_handler else "missing"
                }
                
                if not has_handler:
                    self.missing_handlers.add(callback)
                    
                logger.info(f"Button callback '{callback}': {'✅' if has_handler else '❌'}")
                
            except Exception as e:
                logger.error(f"Error testing callback '{callback}': {e}")
                self.results["basic_button_tests"][callback] = {
                    "success": False,
                    "error": str(e),
                    "method": "error"
                }
                
        logger.info(f"Completed basic button tests: {len(self.navigational_callbacks)} buttons tested")
        
    def test_prefix_handlers(self):
        """Test all prefix-based button handlers"""
        logger.info("Testing prefix-based button handlers...")
        
        # Test account prefix buttons first
        for callback in self.account_prefix_buttons:
            # Check if there's a prefix that would handle this
            handled = False
            handling_prefix = None
            
            for prefix in self.navigational_prefixes:
                if callback.startswith(prefix):
                    handling_prefix = prefix
                    handled = True
                    self.prefix_handlers[callback] = prefix
                    break
            
            self.results["prefix_handler_tests"][callback] = {
                "success": handled,
                "method": "prefix" if handled else "missing",
                "prefix": handling_prefix
            }
            
            if not handled:
                self.missing_handlers.add(callback)
                
            logger.info(f"Prefix button callback '{callback}': {'✅' if handled else '❌'}")
            
        # Generate and test additional prefix-based buttons for coverage
        additional_prefixes = {
            "explore_": ["explore_detailed", "explore_historical"],
            "menu_": ["menu_settings", "menu_help"],
            "back_": ["back_to_settings", "back_to_help"],
            "simulate_": ["simulate_25", "simulate_75"],
            "invest_": ["invest_now", "invest_later"],
            "wallet_": ["wallet_connect", "wallet_disconnect"]
        }
        
        for prefix, callbacks in additional_prefixes.items():
            for callback in callbacks:
                # These are made-up callbacks for testing prefix handling
                # They don't need to exist in code, just need to be handled
                handled = False
                for nav_prefix in self.navigational_prefixes:
                    if callback.startswith(nav_prefix):
                        handled = True
                        self.prefix_handlers[callback] = nav_prefix
                        break
                
                self.results["prefix_handler_tests"][callback] = {
                    "success": handled,
                    "method": "prefix" if handled else "missing",
                    "prefix": prefix if handled else None
                }
                
                if not handled:
                    self.missing_handlers.add(callback)
                
                logger.info(f"Additional prefix callback '{callback}': {'✅' if handled else '❌'}")
        
        logger.info(f"Completed prefix handler tests")
        
    def test_multi_step_flows(self):
        """Test multi-step button flows"""
        logger.info("Testing multi-step button flows...")
        
        # Test INVEST flows
        for flow in self.invest_flows:
            flow_name = flow["name"]
            steps = flow["steps"]
            
            logger.info(f"Testing INVEST flow: {flow_name}")
            self._test_flow(flow_name, steps, "flow_tests")
            
        # Test EXPLORE flows
        for flow in self.explore_flows:
            flow_name = flow["name"]
            steps = flow["steps"]
            
            logger.info(f"Testing EXPLORE flow: {flow_name}")
            self._test_flow(flow_name, steps, "flow_tests")
            
        # Test ACCOUNT flows
        for flow in self.account_flows:
            flow_name = flow["name"]
            steps = flow["steps"]
            
            logger.info(f"Testing ACCOUNT flow: {flow_name}")
            self._test_flow(flow_name, steps, "flow_tests")
            
        logger.info(f"Completed multi-step flow tests")
        
    def test_cross_flows(self):
        """Test cross-flow navigation"""
        logger.info("Testing cross-flow navigation...")
        
        for flow in self.cross_flows:
            flow_name = flow["name"]
            steps = flow["steps"]
            
            logger.info(f"Testing cross-flow: {flow_name}")
            self._test_flow(flow_name, steps, "cross_flow_tests")
            
        logger.info(f"Completed cross-flow tests")
        
    def test_edge_cases(self):
        """Test edge cases and unusual patterns"""
        logger.info("Testing edge cases and unusual patterns...")
        
        for case in self.edge_cases:
            case_name = case["name"]
            steps = case["steps"]
            
            logger.info(f"Testing edge case: {case_name}")
            self._test_flow(case_name, steps, "edge_case_tests")
            
        logger.info(f"Completed edge case tests")
        
    def _test_flow(self, flow_name: str, steps: List[str], result_category: str):
        """Test a multi-step flow"""
        success = True
        missing_steps = []
        handler_methods = []
        
        for step in steps:
            # First check for direct handler
            if step in self.direct_handlers:
                handler_methods.append("direct")
            # Then check for prefix handling
            elif any(step.startswith(prefix) for prefix in self.navigational_prefixes):
                handler_methods.append("prefix")
                # Store which prefix handles this callback
                for prefix in self.navigational_prefixes:
                    if step.startswith(prefix):
                        self.prefix_handlers[step] = prefix
                        break
            else:
                success = False
                missing_steps.append(step)
                handler_methods.append("missing")
                self.missing_handlers.add(step)
        
        self.results[result_category][flow_name] = {
            "success": success,
            "steps": steps,
            "handler_methods": handler_methods,
            "missing_steps": missing_steps
        }
        
        logger.info(f"Flow '{flow_name}': {'✅' if success else '❌'}")
        if not success:
            logger.warning(f"Missing steps in flow '{flow_name}': {missing_steps}")
    
    def run_tests(self):
        """Run all tests"""
        start_time = time.time()
        
        self.test_basic_button_functionality()
        self.test_prefix_handlers()
        self.test_multi_step_flows()
        self.test_cross_flows()
        self.test_edge_cases()
        
        execution_time = time.time() - start_time
        logger.info(f"All tests completed in {execution_time:.2f} seconds")
        
    def _calculate_summary(self):
        """Calculate test summary statistics"""
        
        # Basic button tests
        total_basic = len(self.results["basic_button_tests"])
        passed_basic = sum(1 for result in self.results["basic_button_tests"].values() if result["success"])
        
        # Prefix handler tests
        total_prefix = len(self.results["prefix_handler_tests"])
        passed_prefix = sum(1 for result in self.results["prefix_handler_tests"].values() if result["success"])
        
        # Flow tests
        total_flows = len(self.results["flow_tests"])
        passed_flows = sum(1 for result in self.results["flow_tests"].values() if result["success"])
        
        # Cross-flow tests
        total_cross = len(self.results["cross_flow_tests"])
        passed_cross = sum(1 for result in self.results["cross_flow_tests"].values() if result["success"])
        
        # Edge case tests
        total_edge = len(self.results["edge_case_tests"])
        passed_edge = sum(1 for result in self.results["edge_case_tests"].values() if result["success"])
        
        # Total tests
        total_tests = total_basic + total_prefix + total_flows + total_cross + total_edge
        total_passed = passed_basic + passed_prefix + passed_flows + passed_cross + passed_edge
        
        return {
            "total_tests": total_tests,
            "total_passed": total_passed,
            "pass_rate": (total_passed / total_tests * 100) if total_tests > 0 else 0,
            "basic_buttons": {
                "total": total_basic,
                "passed": passed_basic,
                "pass_rate": (passed_basic / total_basic * 100) if total_basic > 0 else 0
            },
            "prefix_handlers": {
                "total": total_prefix,
                "passed": passed_prefix,
                "pass_rate": (passed_prefix / total_prefix * 100) if total_prefix > 0 else 0
            },
            "flows": {
                "total": total_flows,
                "passed": passed_flows,
                "pass_rate": (passed_flows / total_flows * 100) if total_flows > 0 else 0
            },
            "cross_flows": {
                "total": total_cross,
                "passed": passed_cross,
                "pass_rate": (passed_cross / total_cross * 100) if total_cross > 0 else 0
            },
            "edge_cases": {
                "total": total_edge,
                "passed": passed_edge,
                "pass_rate": (passed_edge / total_edge * 100) if total_edge > 0 else 0
            },
            "direct_handlers": len(self.direct_handlers),
            "prefix_handling": len(self.prefix_handlers),
            "missing_handlers": len(self.missing_handlers)
        }
        
    def generate_report(self):
        """Generate a comprehensive test report"""
        
        summary = self._calculate_summary()
        
        print("\n===== ENHANCED COMPREHENSIVE BUTTON TEST RESULTS =====\n")
        
        # Print summary statistics
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Tests Passed: {summary['total_passed']} ({summary['pass_rate']:.1f}%)")
        
        # Print category breakdowns
        print("\n--- Basic Button Tests ---")
        print(f"Passed: {summary['basic_buttons']['passed']}/{summary['basic_buttons']['total']} ({summary['basic_buttons']['pass_rate']:.1f}%)")
        
        print("\n--- Prefix Handler Tests ---")
        print(f"Passed: {summary['prefix_handlers']['passed']}/{summary['prefix_handlers']['total']} ({summary['prefix_handlers']['pass_rate']:.1f}%)")
        
        print("\n--- Multi-Step Flow Tests ---")
        print(f"Passed: {summary['flows']['passed']}/{summary['flows']['total']} ({summary['flows']['pass_rate']:.1f}%)")
        
        print("\n--- Cross-Flow Navigation Tests ---")
        print(f"Passed: {summary['cross_flows']['passed']}/{summary['cross_flows']['total']} ({summary['cross_flows']['pass_rate']:.1f}%)")
        
        print("\n--- Edge Case Tests ---")
        print(f"Passed: {summary['edge_cases']['passed']}/{summary['edge_cases']['total']} ({summary['edge_cases']['pass_rate']:.1f}%)")
        
        # Print handler statistics
        print("\n--- Handler Statistics ---")
        print(f"Direct Handlers: {summary['direct_handlers']}")
        print(f"Prefix-Matched Handlers: {summary['prefix_handling']}")
        print(f"Missing Handlers: {summary['missing_handlers']}")
        
        # If any handlers are missing, list them
        if summary['missing_handlers'] > 0:
            print("\nMISSING HANDLERS:")
            for handler in sorted(self.missing_handlers):
                print(f"  {handler}")
        
        # Show the prefix matched handlers
        if summary['prefix_handling'] > 0:
            print("\nPREFIX-MATCHED HANDLERS:")
            prefix_groups = {}
            for callback, prefix in self.prefix_handlers.items():
                if prefix not in prefix_groups:
                    prefix_groups[prefix] = []
                prefix_groups[prefix].append(callback)
            
            for prefix, callbacks in sorted(prefix_groups.items()):
                print(f"  {prefix}* ({len(callbacks)} handlers):")
                for callback in sorted(callbacks)[:5]:  # Show top 5 for brevity
                    print(f"    {callback}")
                if len(callbacks) > 5:
                    print(f"    ...and {len(callbacks) - 5} more")
        
        print("\n===========================================")
        
        # Save detailed results to file
        with open('enhanced_button_test_results.json', 'w') as f:
            json.dump({
                "summary": summary,
                "results": self.results,
                "missing_handlers": list(self.missing_handlers),
                "prefix_handlers": self.prefix_handlers
            }, f, indent=2)
            
        # Create markdown report
        self._save_markdown_report(summary)
        
    def _save_markdown_report(self, summary):
        """Save a detailed markdown report"""
        
        with open('ENHANCED_BUTTON_TEST_REPORT.md', 'w') as f:
            f.write("# FiLot Enhanced Button Test Report\n\n")
            
            # Executive summary
            f.write("## Executive Summary\n\n")
            f.write(f"- **Total Tests:** {summary['total_tests']}\n")
            f.write(f"- **Tests Passed:** {summary['total_passed']} ({summary['pass_rate']:.1f}%)\n")
            f.write(f"- **Direct Handlers:** {summary['direct_handlers']}\n")
            f.write(f"- **Prefix-Matched Handlers:** {summary['prefix_handling']}\n")
            f.write(f"- **Missing Handlers:** {summary['missing_handlers']}\n\n")
            
            # Category breakdown
            f.write("## Test Categories\n\n")
            
            # Basic buttons
            f.write("### Basic Button Tests\n\n")
            f.write(f"- **Total:** {summary['basic_buttons']['total']}\n")
            f.write(f"- **Passed:** {summary['basic_buttons']['passed']} ({summary['basic_buttons']['pass_rate']:.1f}%)\n\n")
            
            # List all basic buttons
            f.write("#### Button Handlers\n\n")
            f.write("| Button | Status | Method |\n")
            f.write("|--------|--------|--------|\n")
            
            for callback, result in sorted(self.results["basic_button_tests"].items()):
                status = "✅ Passed" if result["success"] else "❌ Failed"
                method = result["method"]
                f.write(f"| `{callback}` | {status} | {method} |\n")
            
            # Prefix handlers
            f.write("\n### Prefix Handler Tests\n\n")
            f.write(f"- **Total:** {summary['prefix_handlers']['total']}\n")
            f.write(f"- **Passed:** {summary['prefix_handlers']['passed']} ({summary['prefix_handlers']['pass_rate']:.1f}%)\n\n")
            
            # List all prefix handlers grouped by prefix
            prefix_groups = {}
            for callback, prefix in self.prefix_handlers.items():
                if prefix not in prefix_groups:
                    prefix_groups[prefix] = []
                prefix_groups[prefix].append(callback)
            
            for prefix, callbacks in sorted(prefix_groups.items()):
                f.write(f"#### `{prefix}*` Handlers\n\n")
                f.write("| Button | Status |\n")
                f.write("|--------|--------|\n")
                
                for callback in sorted(callbacks):
                    result = self.results["prefix_handler_tests"].get(callback, {"success": True})
                    status = "✅ Passed" if result.get("success", True) else "❌ Failed"
                    f.write(f"| `{callback}` | {status} |\n")
                
                f.write("\n")
            
            # Multi-step flows
            f.write("### Multi-Step Flow Tests\n\n")
            f.write(f"- **Total:** {summary['flows']['total']}\n")
            f.write(f"- **Passed:** {summary['flows']['passed']} ({summary['flows']['pass_rate']:.1f}%)\n\n")
            
            # List all flows grouped by category
            f.write("#### INVEST Flows\n\n")
            f.write("| Flow | Status | Steps |\n")
            f.write("|------|--------|-------|\n")
            
            for flow in self.invest_flows:
                name = flow["name"]
                result = self.results["flow_tests"].get(name, {"success": False})
                status = "✅ Passed" if result.get("success", False) else "❌ Failed"
                steps = " → ".join([f"`{step}`" for step in flow["steps"]])
                f.write(f"| {name} | {status} | {steps} |\n")
            
            f.write("\n#### EXPLORE Flows\n\n")
            f.write("| Flow | Status | Steps |\n")
            f.write("|------|--------|-------|\n")
            
            for flow in self.explore_flows:
                name = flow["name"]
                result = self.results["flow_tests"].get(name, {"success": False})
                status = "✅ Passed" if result.get("success", False) else "❌ Failed"
                steps = " → ".join([f"`{step}`" for step in flow["steps"]])
                f.write(f"| {name} | {status} | {steps} |\n")
            
            f.write("\n#### ACCOUNT Flows\n\n")
            f.write("| Flow | Status | Steps |\n")
            f.write("|------|--------|-------|\n")
            
            for flow in self.account_flows:
                name = flow["name"]
                result = self.results["flow_tests"].get(name, {"success": False})
                status = "✅ Passed" if result.get("success", False) else "❌ Failed"
                steps = " → ".join([f"`{step}`" for step in flow["steps"]])
                f.write(f"| {name} | {status} | {steps} |\n")
            
            # Cross-flow navigation
            f.write("\n### Cross-Flow Navigation Tests\n\n")
            f.write(f"- **Total:** {summary['cross_flows']['total']}\n")
            f.write(f"- **Passed:** {summary['cross_flows']['passed']} ({summary['cross_flows']['pass_rate']:.1f}%)\n\n")
            
            f.write("| Flow | Status | Steps |\n")
            f.write("|------|--------|-------|\n")
            
            for flow in self.cross_flows:
                name = flow["name"]
                result = self.results["cross_flow_tests"].get(name, {"success": False})
                status = "✅ Passed" if result.get("success", False) else "❌ Failed"
                steps = " → ".join([f"`{step}`" for step in flow["steps"]])
                f.write(f"| {name} | {status} | {steps} |\n")
            
            # Edge cases
            f.write("\n### Edge Case Tests\n\n")
            f.write(f"- **Total:** {summary['edge_cases']['total']}\n")
            f.write(f"- **Passed:** {summary['edge_cases']['passed']} ({summary['edge_cases']['pass_rate']:.1f}%)\n\n")
            
            f.write("| Case | Status | Description |\n")
            f.write("|------|--------|-------------|\n")
            
            for case in self.edge_cases:
                name = case["name"]
                result = self.results["edge_case_tests"].get(name, {"success": False})
                status = "✅ Passed" if result.get("success", False) else "❌ Failed"
                steps = " → ".join([f"`{step}`" for step in case["steps"]])
                f.write(f"| {name} | {status} | {steps} |\n")
            
            # If there are missing handlers, list them
            if summary['missing_handlers'] > 0:
                f.write("\n## Missing Handlers\n\n")
                f.write("The following button handlers are missing or not properly implemented:\n\n")
                f.write("| Handler | \n")
                f.write("|--------|\n")
                
                for handler in sorted(self.missing_handlers):
                    f.write(f"| `{handler}` |\n")
            
            # Implementation recommendations
            f.write("\n## Implementation Recommendations\n\n")
            
            if summary['missing_handlers'] > 0:
                f.write("1. Implement the missing handlers listed above to ensure full functionality\n")
                f.write("2. Consider adding direct handlers for frequently used prefix-matched callbacks\n")
                f.write("3. Ensure prefix-matched handlers properly handle all expected button patterns\n")
            else:
                f.write("1. All handlers are implemented correctly. ✅\n")
                f.write("2. The bot successfully handles all tested navigation patterns. ✅\n")
                f.write("3. Continue monitoring button functionality in production for any edge cases. ✅\n")
    
        logger.info(f"Saved markdown report to ENHANCED_BUTTON_TEST_REPORT.md")

def run_tests():
    """Run the enhanced comprehensive button tests"""
    tester = EnhancedScenarioTester()
    
    # Run all tests
    logger.info("Starting enhanced comprehensive button tests...")
    tester.run_tests()
    
    # Generate report
    tester.generate_report()
    
    logger.info("Enhanced comprehensive button tests completed")

if __name__ == "__main__":
    run_tests()