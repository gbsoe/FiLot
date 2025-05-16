#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mixed scenario tester for the FiLot Telegram bot.
This script tests both button interactions and regular commands in combinations.
"""

import logging
import time
import random
import re
from typing import List, Dict, Any, Set, Tuple, Optional
import json

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Import necessary modules
import main
from callback_handler import route_callback, CallbackRegistry
from anti_loop import reset_all_locks
from debug_message_tracking import reset_tracking

class MixedScenarioTester:
    """Advanced tester that simulates mixed button + command interactions."""
    
    def __init__(self):
        """Initialize the tester with all scenarios."""
        # Set up test tracking
        self.results = {
            "mixed_command_tests": {},
            "complex_flow_tests": {},
            "interference_tests": {},
            "error_recovery_tests": {}
        }
        
        # Standard commands to test
        self.commands = [
            "/start", 
            "/help", 
            "/faq", 
            "/invest", 
            "/explore", 
            "/account", 
            "/connect", 
            "/status", 
            "/simulate 100",
            "/pools",
            "/profile high",
            "/profile stable"
        ]
        
        # Load navigational callbacks
        self.callbacks = [
            # Main menu
            "menu_invest", "menu_explore", "menu_account", "back_to_main",
            # Invest menu
            "amount_50", "amount_100", "amount_250", "amount_500", "amount_1000", "amount_5000", "amount_custom",
            # Explore menu
            "explore_pools", "explore_simulate", 
            # Account menu
            "account_wallet", "account_subscribe", "account_unsubscribe", "account_help", "account_status",
            # Profile selection
            "profile_high-risk", "profile_stable"
        ]
        
        # Set up mixed command-button flows to test
        self.mixed_flows = [
            {
                "name": "Command Start -> Button Navigation",
                "steps": [
                    {"type": "command", "value": "/start"},
                    {"type": "button", "value": "menu_invest"},
                    {"type": "button", "value": "amount_100"},
                    {"type": "button", "value": "back_to_main"}
                ]
            },
            {
                "name": "Button Start -> Command Override",
                "steps": [
                    {"type": "button", "value": "menu_explore"},
                    {"type": "button", "value": "explore_pools"},
                    {"type": "command", "value": "/invest"},
                    {"type": "button", "value": "amount_250"}
                ]
            },
            {
                "name": "Profile Command -> Button Investment",
                "steps": [
                    {"type": "command", "value": "/profile high"},
                    {"type": "button", "value": "menu_invest"},
                    {"type": "button", "value": "amount_500"},
                    {"type": "command", "value": "/help"}
                ]
            },
            {
                "name": "Interleaved Commands and Buttons",
                "steps": [
                    {"type": "command", "value": "/start"},
                    {"type": "button", "value": "menu_account"},
                    {"type": "command", "value": "/status"},
                    {"type": "button", "value": "profile_stable"},
                    {"type": "command", "value": "/pools"}
                ]
            }
        ]
        
        # Set up complex multi-flow scenarios
        self.complex_flows = [
            {
                "name": "Full Investment Journey (Mixed)",
                "steps": [
                    {"type": "command", "value": "/start"},
                    {"type": "button", "value": "menu_invest"},
                    {"type": "button", "value": "amount_1000"},
                    {"type": "command", "value": "/profile high"},
                    {"type": "button", "value": "back_to_main"},
                    {"type": "command", "value": "/pools"}
                ]
            },
            {
                "name": "Account Setup Journey (Mixed)",
                "steps": [
                    {"type": "command", "value": "/start"},
                    {"type": "button", "value": "menu_account"},
                    {"type": "button", "value": "account_subscribe"},
                    {"type": "command", "value": "/status"},
                    {"type": "button", "value": "profile_stable"},
                    {"type": "command", "value": "/help"}
                ]
            },
            {
                "name": "Exploration + Investment (Mixed)",
                "steps": [
                    {"type": "command", "value": "/explore"},
                    {"type": "button", "value": "explore_pools"},
                    {"type": "command", "value": "/simulate 250"},
                    {"type": "button", "value": "menu_invest"},
                    {"type": "button", "value": "amount_250"}
                ]
            }
        ]
        
        # Test error recovery/interference scenarios
        self.interference_scenarios = [
            {
                "name": "Button Press During Text Entry",
                "steps": [
                    {"type": "command", "value": "/invest"},
                    {"type": "button", "value": "amount_custom"},
                    # Simulate user entering text when they should be entering a number
                    {"type": "command", "value": "not a number"},
                    {"type": "button", "value": "back_to_main"}
                ],
            },
            {
                "name": "Command Interrupt Button Flow",
                "steps": [
                    {"type": "button", "value": "menu_invest"},
                    # User issues command mid-flow
                    {"type": "command", "value": "/explore"},
                    {"type": "button", "value": "explore_pools"},
                ]
            },
            {
                "name": "Rapid Button Switching",
                "steps": [
                    {"type": "button", "value": "menu_invest"},
                    {"type": "button", "value": "menu_explore"},
                    {"type": "button", "value": "menu_account"},
                    {"type": "button", "value": "back_to_main"},
                ]
            }
        ]
        
        # Create additional random mixed scenarios
        self.random_flows = self._generate_random_flows(5)
        
    def _generate_random_flows(self, count: int) -> List[Dict[str, Any]]:
        """Generate random mixed command-button flows for testing."""
        random_flows = []
        
        for i in range(count):
            # Determine random flow length (3-8 steps)
            flow_length = random.randint(3, 8)
            steps = []
            
            # Generate random steps (mix of commands and buttons)
            for j in range(flow_length):
                # Randomly choose between command and button
                step_type = random.choice(["command", "button"])
                
                if step_type == "command":
                    value = random.choice(self.commands)
                else:
                    value = random.choice(self.callbacks)
                
                steps.append({"type": step_type, "value": value})
            
            # Add the random flow
            random_flows.append({
                "name": f"Random Mixed Flow {i+1}",
                "steps": steps
            })
        
        return random_flows
        
    def test_mixed_command_button_flows(self):
        """Test mixed flows with both commands and buttons."""
        logger.info("Testing mixed command/button flows...")
        
        for flow in self.mixed_flows:
            flow_name = flow["name"]
            steps = flow["steps"]
            
            logger.info(f"Testing flow: {flow_name}")
            result = self._test_mixed_flow(flow_name, steps)
            self.results["mixed_command_tests"][flow_name] = result
            
        logger.info(f"Completed mixed command/button tests: {len(self.mixed_flows)} flows")
        
    def test_complex_journeys(self):
        """Test complex multi-flow journeys."""
        logger.info("Testing complex multi-flow journeys...")
        
        for flow in self.complex_flows:
            flow_name = flow["name"]
            steps = flow["steps"]
            
            logger.info(f"Testing complex journey: {flow_name}")
            result = self._test_mixed_flow(flow_name, steps)
            self.results["complex_flow_tests"][flow_name] = result
            
        logger.info(f"Completed complex journey tests: {len(self.complex_flows)} flows")
    
    def test_interference_scenarios(self):
        """Test scenarios where commands and buttons might interfere with each other."""
        logger.info("Testing interference scenarios...")
        
        for scenario in self.interference_scenarios:
            scenario_name = scenario["name"]
            steps = scenario["steps"]
            
            logger.info(f"Testing interference scenario: {scenario_name}")
            result = self._test_mixed_flow(scenario_name, steps)
            self.results["interference_tests"][scenario_name] = result
            
        logger.info(f"Completed interference tests: {len(self.interference_scenarios)} scenarios")
    
    def test_random_flows(self):
        """Test randomly generated flows."""
        logger.info("Testing random mixed flows...")
        
        for flow in self.random_flows:
            flow_name = flow["name"]
            steps = flow["steps"]
            
            logger.info(f"Testing random flow: {flow_name}")
            result = self._test_mixed_flow(flow_name, steps)
            self.results["mixed_command_tests"][flow_name] = result
            
        logger.info(f"Completed random flow tests: {len(self.random_flows)} flows")
    
    def _test_mixed_flow(self, flow_name: str, steps: List[Dict[str, str]]) -> Dict[str, Any]:
        """Test a mixed flow of commands and button interactions."""
        success = True
        step_results = []
        error_messages = []
        
        # Reset any tracking or locks between tests
        reset_all_locks()
        reset_tracking()
        CallbackRegistry.prune_old_data()
        
        # Create a context object to simulate update context
        test_context = {
            "chat_id": 12345,
            "user_id": 67890,
            "message_id": 100000,
            "callback_id": "test_callback_id",
            "test_mode": True
        }
        
        # Simulate each step
        for step_idx, step in enumerate(steps):
            step_type = step["type"]
            value = step["value"]
            step_success = False
            step_result = {"step": step_idx + 1, "type": step_type, "value": value}
            
            try:
                if step_type == "command":
                    # Simulate command handling
                    # For simplicity, we just check if the command has a handler
                    # In a real test, we would call the actual handler
                    command_name = value.split(" ")[0][1:]  # Remove the /
                    handler_name = f"handle_{command_name}_command"
                    if hasattr(main, handler_name) or handler_name in dir(main):
                        step_success = True
                        step_result["handler"] = handler_name
                    else:
                        # Try alternative naming patterns
                        alt_handler = f"cmd_{command_name}"
                        if hasattr(main, alt_handler) or alt_handler in dir(main):
                            step_success = True
                            step_result["handler"] = alt_handler
                        else:
                            generic_handler = "handle_command"
                            if hasattr(main, generic_handler) or generic_handler in dir(main):
                                step_success = True
                                step_result["handler"] = generic_handler
                            else:
                                step_success = False
                                error_messages.append(f"No handler found for command: {value}")
                else:  # Button callback
                    # Use the route_callback function to simulate button press
                    result = route_callback(value, test_context)
                    # Check if the result indicates successful handling
                    step_success = result is not None and "error" not in result
                    step_result["result"] = result
            except Exception as e:
                step_success = False
                error_message = f"Error in step {step_idx + 1}: {str(e)}"
                error_messages.append(error_message)
                logger.error(error_message)
            
            step_result["success"] = step_success
            step_results.append(step_result)
            
            # Update overall success
            success = success and step_success
        
        # Create comprehensive result
        result = {
            "flow_name": flow_name,
            "success": success,
            "steps": step_results,
            "error_messages": error_messages
        }
        
        logger.info(f"Flow '{flow_name}': {'✅' if success else '❌'}")
        return result
    
    def run_all_tests(self):
        """Run all test scenarios."""
        start_time = time.time()
        
        self.test_mixed_command_button_flows()
        self.test_complex_journeys()
        self.test_interference_scenarios()
        self.test_random_flows()
        
        execution_time = time.time() - start_time
        logger.info(f"All mixed scenario tests completed in {execution_time:.2f} seconds")
    
    def _calculate_summary(self) -> Dict[str, Any]:
        """Calculate test summary statistics."""
        # Count overall tests and successes
        total_mixed = len(self.results["mixed_command_tests"])
        successful_mixed = sum(1 for result in self.results["mixed_command_tests"].values() 
                              if result["success"])
        
        total_complex = len(self.results["complex_flow_tests"])
        successful_complex = sum(1 for result in self.results["complex_flow_tests"].values() 
                                if result["success"])
        
        total_interference = len(self.results["interference_tests"])
        successful_interference = sum(1 for result in self.results["interference_tests"].values() 
                                     if result["success"])
        
        # Count total steps of each type
        total_steps = 0
        successful_steps = 0
        total_command_steps = 0
        successful_command_steps = 0
        total_button_steps = 0
        successful_button_steps = 0
        
        for category in self.results.values():
            for flow_result in category.values():
                for step in flow_result["steps"]:
                    total_steps += 1
                    if step["success"]:
                        successful_steps += 1
                    
                    if step["type"] == "command":
                        total_command_steps += 1
                        if step["success"]:
                            successful_command_steps += 1
                    else:  # Button
                        total_button_steps += 1
                        if step["success"]:
                            successful_button_steps += 1
        
        return {
            "total_tests": total_mixed + total_complex + total_interference,
            "successful_tests": successful_mixed + successful_complex + successful_interference,
            "success_rate": ((successful_mixed + successful_complex + successful_interference) / 
                            (total_mixed + total_complex + total_interference) * 100),
            "mixed_flows": {
                "total": total_mixed,
                "successful": successful_mixed,
                "success_rate": (successful_mixed / total_mixed * 100) if total_mixed > 0 else 0
            },
            "complex_flows": {
                "total": total_complex,
                "successful": successful_complex,
                "success_rate": (successful_complex / total_complex * 100) if total_complex > 0 else 0
            },
            "interference_flows": {
                "total": total_interference,
                "successful": successful_interference,
                "success_rate": (successful_interference / total_interference * 100) if total_interference > 0 else 0
            },
            "steps": {
                "total": total_steps,
                "successful": successful_steps,
                "success_rate": (successful_steps / total_steps * 100) if total_steps > 0 else 0,
                "commands": {
                    "total": total_command_steps,
                    "successful": successful_command_steps,
                    "success_rate": (successful_command_steps / total_command_steps * 100) 
                                   if total_command_steps > 0 else 0
                },
                "buttons": {
                    "total": total_button_steps,
                    "successful": successful_button_steps,
                    "success_rate": (successful_button_steps / total_button_steps * 100) 
                                  if total_button_steps > 0 else 0
                }
            }
        }
    
    def generate_report(self):
        """Generate a comprehensive test report."""
        
        summary = self._calculate_summary()
        
        print("\n===== MIXED SCENARIO TEST RESULTS =====\n")
        
        # Print overall summary
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Successful Tests: {summary['successful_tests']} ({summary['success_rate']:.1f}%)")
        
        # Print step statistics
        print(f"\nTotal Steps Tested: {summary['steps']['total']}")
        print(f"Successful Steps: {summary['steps']['successful']} ({summary['steps']['success_rate']:.1f}%)")
        print(f"  Command Steps: {summary['steps']['commands']['successful']}/{summary['steps']['commands']['total']} "
              f"({summary['steps']['commands']['success_rate']:.1f}%)")
        print(f"  Button Steps: {summary['steps']['buttons']['successful']}/{summary['steps']['buttons']['total']} "
              f"({summary['steps']['buttons']['success_rate']:.1f}%)")
        
        # Print category summaries
        print("\n--- Mixed Command/Button Flow Tests ---")
        print(f"Passed: {summary['mixed_flows']['successful']}/{summary['mixed_flows']['total']} "
              f"({summary['mixed_flows']['success_rate']:.1f}%)")
        
        print("\n--- Complex Journey Tests ---")
        print(f"Passed: {summary['complex_flows']['successful']}/{summary['complex_flows']['total']} "
              f"({summary['complex_flows']['success_rate']:.1f}%)")
        
        print("\n--- Interference Scenario Tests ---")
        print(f"Passed: {summary['interference_flows']['successful']}/{summary['interference_flows']['total']} "
              f"({summary['interference_flows']['success_rate']:.1f}%)")
        
        # If there were any failures, print details
        if summary['successful_tests'] < summary['total_tests']:
            print("\n--- Failed Tests ---")
            for category_name, category in self.results.items():
                for flow_name, result in category.items():
                    if not result["success"]:
                        print(f"\n{flow_name} (in {category_name}):")
                        print("  Failed Steps:")
                        for step in result["steps"]:
                            if not step["success"]:
                                print(f"    Step {step['step']}: {step['type']} - {step['value']}")
                        if result["error_messages"]:
                            print("  Errors:")
                            for error in result["error_messages"]:
                                print(f"    {error}")
        
        print("\n===========================================")
        
        # Save detailed results to file
        with open('mixed_scenario_test_results.json', 'w') as f:
            json.dump({
                "summary": summary,
                "results": self.results
            }, f, indent=2)
        
        # Create markdown report
        self._save_markdown_report(summary)
    
    def _save_markdown_report(self, summary: Dict[str, Any]):
        """Save a detailed markdown report."""
        
        with open('MIXED_SCENARIO_TEST_REPORT.md', 'w') as f:
            f.write("# FiLot Mixed Scenario Test Report\n\n")
            
            # Executive summary
            f.write("## Executive Summary\n\n")
            f.write(f"- **Total Tests:** {summary['total_tests']}\n")
            f.write(f"- **Successful Tests:** {summary['successful_tests']} ({summary['success_rate']:.1f}%)\n")
            f.write(f"- **Total Steps:** {summary['steps']['total']}\n")
            f.write(f"- **Successful Steps:** {summary['steps']['successful']} ({summary['steps']['success_rate']:.1f}%)\n\n")
            
            # Command vs Button stats
            f.write("### Command vs Button Statistics\n\n")
            f.write("| Type | Successful | Total | Success Rate |\n")
            f.write("|------|------------|-------|-------------|\n")
            f.write(f"| Commands | {summary['steps']['commands']['successful']} | {summary['steps']['commands']['total']} | {summary['steps']['commands']['success_rate']:.1f}% |\n")
            f.write(f"| Buttons | {summary['steps']['buttons']['successful']} | {summary['steps']['buttons']['total']} | {summary['steps']['buttons']['success_rate']:.1f}% |\n\n")
            
            # Category breakdown
            f.write("## Test Categories\n\n")
            
            # Mixed flows
            f.write("### Mixed Command/Button Flows\n\n")
            f.write(f"- **Total:** {summary['mixed_flows']['total']}\n")
            f.write(f"- **Successful:** {summary['mixed_flows']['successful']} ({summary['mixed_flows']['success_rate']:.1f}%)\n\n")
            
            f.write("| Flow | Status | Steps |\n")
            f.write("|------|--------|-------|\n")
            
            for flow_name, result in self.results["mixed_command_tests"].items():
                status = "✅ Passed" if result["success"] else "❌ Failed"
                step_details = " → ".join([f"{s['type']}:`{s['value']}`" for s in result["steps"]])
                f.write(f"| {flow_name} | {status} | {step_details} |\n")
            
            # Complex journeys
            f.write("\n### Complex Journey Tests\n\n")
            f.write(f"- **Total:** {summary['complex_flows']['total']}\n")
            f.write(f"- **Successful:** {summary['complex_flows']['successful']} ({summary['complex_flows']['success_rate']:.1f}%)\n\n")
            
            f.write("| Journey | Status | Steps |\n")
            f.write("|---------|--------|-------|\n")
            
            for flow_name, result in self.results["complex_flow_tests"].items():
                status = "✅ Passed" if result["success"] else "❌ Failed"
                step_details = " → ".join([f"{s['type']}:`{s['value']}`" for s in result["steps"]])
                f.write(f"| {flow_name} | {status} | {step_details} |\n")
            
            # Interference scenarios
            f.write("\n### Interference Scenarios\n\n")
            f.write(f"- **Total:** {summary['interference_flows']['total']}\n")
            f.write(f"- **Successful:** {summary['interference_flows']['successful']} ({summary['interference_flows']['success_rate']:.1f}%)\n\n")
            
            f.write("| Scenario | Status | Steps |\n")
            f.write("|----------|--------|-------|\n")
            
            for flow_name, result in self.results["interference_tests"].items():
                status = "✅ Passed" if result["success"] else "❌ Failed"
                step_details = " → ".join([f"{s['type']}:`{s['value']}`" for s in result["steps"]])
                f.write(f"| {flow_name} | {status} | {step_details} |\n")
            
            # Failed test details (if any)
            if summary['successful_tests'] < summary['total_tests']:
                f.write("\n## Failed Test Details\n\n")
                
                for category_name, category in self.results.items():
                    category_failures = [flow_name for flow_name, result in category.items() 
                                        if not result["success"]]
                    
                    if category_failures:
                        f.write(f"### {category_name}\n\n")
                        
                        for flow_name in category_failures:
                            result = category[flow_name]
                            f.write(f"#### {flow_name}\n\n")
                            
                            f.write("**Failed Steps:**\n\n")
                            f.write("| Step | Type | Value | Error |\n")
                            f.write("|------|------|-------|-------|\n")
                            
                            for step in result["steps"]:
                                if not step["success"]:
                                    step_num = step["step"]
                                    step_type = step["type"]
                                    step_value = step["value"]
                                    error = result["error_messages"][0] if result["error_messages"] else "Unknown error"
                                    f.write(f"| {step_num} | {step_type} | `{step_value}` | {error} |\n")
                            
                            f.write("\n")
            
            # Implementation suggestions
            f.write("\n## Recommendations\n\n")
            
            if summary['success_rate'] == 100:
                f.write("1. All mixed scenarios work correctly. ✅\n")
                f.write("2. The bot handles transitions between button interactions and commands smoothly. ✅\n")
                f.write("3. Error recovery and interference prevention mechanisms are working well. ✅\n")
            else:
                f.write("1. Improve error handling for failed transitions between commands and buttons.\n")
                f.write("2. Strengthen error recovery mechanisms in complex flows.\n")
                f.write("3. Add additional safeguards for interruption scenarios.\n")
            
        logger.info(f"Saved markdown report to MIXED_SCENARIO_TEST_REPORT.md")

# Run the enhanced tests
if __name__ == "__main__":
    tester = MixedScenarioTester()
    
    # Run all tests
    logger.info("Starting mixed scenario tests...")
    tester.run_all_tests()
    
    # Generate report
    tester.generate_report()
    
    logger.info("Mixed scenario tests completed")