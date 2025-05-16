#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script to verify the FiLot Telegram bot does not produce duplicate responses.
This test specifically targets rapid button presses and edge cases.
"""

import logging
import time
import random
from typing import List, Dict, Any, Set, Tuple
import json

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(name)s: %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Import necessary modules
import main
from callback_handler import route_callback, CallbackRegistry
from anti_loop import reset_all_locks
from debug_message_tracking import cleanup_tracking

class DuplicateResponseTester:
    """Tests scenarios where duplicate responses might occur."""
    
    def __init__(self):
        """Initialize the tester with relevant test scenarios."""
        self.results = {
            "rapid_press_tests": {},
            "menu_loop_tests": {},
            "back_forth_tests": {},
            "identical_sequence_tests": {}
        }
        
        # Test context for simulating updates
        self.test_context = {
            "chat_id": 12345,
            "user_id": 67890,
            "message_id": 100000,
            "callback_id": "test_callback_id",
            "test_mode": True
        }
        
        # Menu navigation buttons
        self.menu_buttons = [
            "menu_invest", "menu_explore", "menu_account", "back_to_main"
        ]
        
        # INVEST flow buttons
        self.invest_buttons = [
            "amount_50", "amount_100", "amount_250", "amount_500", 
            "amount_1000", "amount_5000", "profile_high-risk", "profile_stable"
        ]
        
        # EXPLORE flow buttons
        self.explore_buttons = [
            "explore_pools", "explore_simulate", "simulate_50", "simulate_100", 
            "simulate_250", "simulate_500", "simulate_1000", "simulate_5000"
        ]
        
        # ACCOUNT flow buttons
        self.account_buttons = [
            "account_wallet", "account_subscribe", "account_unsubscribe", 
            "account_help", "account_status"
        ]
        
        # Set up rapid press test cases (same button pressed multiple times in succession)
        self.rapid_press_cases = []
        for button in self.menu_buttons:
            self.rapid_press_cases.append({
                "name": f"Rapid press - {button}",
                "button": button,
                "presses": 5,  # Press the same button 5 times in quick succession
                "delay": 0.05  # 50ms between presses (simulating rapid clicks)
            })
        
        # Set up menu loop test cases (navigate around different menus)
        self.menu_loop_tests = [
            {
                "name": "Menu Loop - Main → Invest → Main → Explore → Main → Account",
                "buttons": ["menu_invest", "back_to_main", "menu_explore", "back_to_main", "menu_account", "back_to_main"]
            },
            {
                "name": "Menu Loop - Complex Pattern",
                "buttons": ["menu_invest", "menu_explore", "menu_account", "menu_invest", "back_to_main"]
            }
        ]
        
        # Set up back and forth tests (rapidly navigate between two menus)
        self.back_forth_tests = [
            {
                "name": "Back-Forth - Invest ↔ Main",
                "buttons": ["menu_invest", "back_to_main"] * 3
            },
            {
                "name": "Back-Forth - Explore ↔ Main",
                "buttons": ["menu_explore", "back_to_main"] * 3
            },
            {
                "name": "Back-Forth - Account ↔ Main",
                "buttons": ["menu_account", "back_to_main"] * 3
            }
        ]
        
        # Set up identical sequence tests (repeat the exact same navigation sequence)
        self.identical_sequence_tests = [
            {
                "name": "Identical Sequence - Invest Flow",
                "sequence": ["menu_invest", "amount_100", "profile_high-risk", "back_to_main"],
                "repetitions": 2
            },
            {
                "name": "Identical Sequence - Explore Flow",
                "sequence": ["menu_explore", "explore_pools", "back_to_main"],
                "repetitions": 2
            },
            {
                "name": "Identical Sequence - Account Flow",
                "sequence": ["menu_account", "account_status", "back_to_main"],
                "repetitions": 2
            }
        ]
    
    def test_rapid_button_presses(self):
        """Test rapid presses of the same button."""
        logger.info("Testing rapid button presses...")
        
        for case in self.rapid_press_cases:
            case_name = case["name"]
            button = case["button"]
            presses = case["presses"]
            delay = case["delay"]
            
            logger.info(f"Testing rapid press case: {case_name}")
            
            # Reset tracking between tests
            reset_all_locks()
            cleanup_tracking()
            CallbackRegistry.prune_old_data()
            
            responses = []
            
            # Simulate rapid button presses
            for i in range(presses):
                # Update the callback_id to simulate different update objects
                context = self.test_context.copy()
                context["callback_id"] = f"test_callback_id_{i}"
                
                try:
                    response = route_callback(button, context)
                    responses.append(response)
                    
                    # Small delay to simulate multiple rapid clicks
                    time.sleep(delay)
                except Exception as e:
                    logger.error(f"Error in rapid press test: {str(e)}")
            
            # Analyze responses for duplicates
            duplicate_count = 0
            response_actions = [r.get("action") if r else None for r in responses]
            for i in range(1, len(response_actions)):
                if response_actions[i] is not None and response_actions[i] == response_actions[i-1]:
                    duplicate_count += 1
            
            # Store results
            self.results["rapid_press_tests"][case_name] = {
                "button": button,
                "presses": presses,
                "responses": len([r for r in responses if r is not None]),
                "duplicate_responses": duplicate_count,
                "success": duplicate_count == 0,
                "response_actions": response_actions
            }
            
            logger.info(f"Rapid press test '{case_name}': " + 
                       f"{'✅' if duplicate_count == 0 else '❌'} " +
                       f"({len([r for r in responses if r is not None])}/{presses} responses, {duplicate_count} duplicates)")
    
    def test_menu_loops(self):
        """Test navigation around different menus in loops."""
        logger.info("Testing menu loop navigation...")
        
        for test in self.menu_loop_tests:
            test_name = test["name"]
            buttons = test["buttons"]
            
            logger.info(f"Testing menu loop: {test_name}")
            
            # Reset tracking between tests
            reset_all_locks()
            cleanup_tracking()
            CallbackRegistry.prune_old_data()
            
            responses = []
            
            # Simulate button presses in sequence
            for i, button in enumerate(buttons):
                # Update the callback_id to simulate different update objects
                context = self.test_context.copy()
                context["callback_id"] = f"test_callback_id_{i}"
                
                try:
                    response = route_callback(button, context)
                    responses.append(response)
                    
                    # Small delay to simulate user interaction
                    time.sleep(0.05)
                except Exception as e:
                    logger.error(f"Error in menu loop test: {str(e)}")
            
            # Analyze responses
            null_responses = sum(1 for r in responses if r is None)
            
            # Store results
            self.results["menu_loop_tests"][test_name] = {
                "buttons": buttons,
                "expected_responses": len(buttons),
                "actual_responses": len(buttons) - null_responses,
                "null_responses": null_responses,
                "success": null_responses == 0,
                "responses": [r.get("action") if r else None for r in responses]
            }
            
            logger.info(f"Menu loop test '{test_name}': " + 
                       f"{'✅' if null_responses == 0 else '❌'} " +
                       f"({len(buttons) - null_responses}/{len(buttons)} responses)")
    
    def test_back_forth_navigation(self):
        """Test rapid back and forth navigation between menus."""
        logger.info("Testing back and forth navigation...")
        
        for test in self.back_forth_tests:
            test_name = test["name"]
            buttons = test["buttons"]
            
            logger.info(f"Testing back-forth navigation: {test_name}")
            
            # Reset tracking between tests
            reset_all_locks()
            cleanup_tracking()
            CallbackRegistry.prune_old_data()
            
            responses = []
            
            # Simulate button presses in sequence
            for i, button in enumerate(buttons):
                # Update the callback_id to simulate different update objects
                context = self.test_context.copy()
                context["callback_id"] = f"test_callback_id_{i}"
                
                try:
                    response = route_callback(button, context)
                    responses.append(response)
                    
                    # Small delay to simulate user interaction
                    time.sleep(0.05)
                except Exception as e:
                    logger.error(f"Error in back-forth test: {str(e)}")
            
            # Analyze responses
            null_responses = sum(1 for r in responses if r is None)
            
            # Store results
            self.results["back_forth_tests"][test_name] = {
                "buttons": buttons,
                "expected_responses": len(buttons),
                "actual_responses": len(buttons) - null_responses,
                "null_responses": null_responses,
                "success": null_responses == 0,
                "responses": [r.get("action") if r else None for r in responses]
            }
            
            logger.info(f"Back-forth test '{test_name}': " + 
                       f"{'✅' if null_responses == 0 else '❌'} " +
                       f"({len(buttons) - null_responses}/{len(buttons)} responses)")
    
    def test_identical_sequences(self):
        """Test repeated identical navigation sequences."""
        logger.info("Testing identical navigation sequences...")
        
        for test in self.identical_sequence_tests:
            test_name = test["name"]
            sequence = test["sequence"]
            repetitions = test["repetitions"]
            
            logger.info(f"Testing identical sequence: {test_name}")
            
            # Reset tracking between tests
            reset_all_locks()
            cleanup_tracking()
            CallbackRegistry.prune_old_data()
            
            all_responses = []
            
            # Repeat the sequence multiple times
            for rep in range(repetitions):
                logger.info(f"  Repetition {rep+1}/{repetitions}")
                
                rep_responses = []
                # Simulate button presses in sequence
                for i, button in enumerate(sequence):
                    # Update the callback_id to simulate different update objects
                    context = self.test_context.copy()
                    context["callback_id"] = f"test_callback_id_rep{rep}_btn{i}"
                    
                    try:
                        response = route_callback(button, context)
                        rep_responses.append(response)
                        
                        # Small delay to simulate user interaction
                        time.sleep(0.1)
                    except Exception as e:
                        logger.error(f"Error in identical sequence test: {str(e)}")
                
                all_responses.append(rep_responses)
            
            # Analyze responses across repetitions
            sequence_failures = 0
            
            # Compare responses across repetitions
            for button_idx in range(len(sequence)):
                responses_for_button = [rep[button_idx] for rep in all_responses]
                
                # Check if any repetition of the same button had a null response when others didn't
                non_null_responses = [r is not None for r in responses_for_button]
                if any(non_null_responses) and not all(non_null_responses):
                    sequence_failures += 1
            
            # Store results
            self.results["identical_sequence_tests"][test_name] = {
                "sequence": sequence,
                "repetitions": repetitions,
                "sequence_failures": sequence_failures,
                "success": sequence_failures == 0,
                "responses": [[r.get("action") if r else None for r in rep] for rep in all_responses]
            }
            
            logger.info(f"Identical sequence test '{test_name}': " + 
                       f"{'✅' if sequence_failures == 0 else '❌'} " +
                       f"({sequence_failures} sequence failures)")
    
    def run_all_tests(self):
        """Run all duplicate response tests."""
        start_time = time.time()
        
        self.test_rapid_button_presses()
        self.test_menu_loops()
        self.test_back_forth_navigation()
        self.test_identical_sequences()
        
        execution_time = time.time() - start_time
        logger.info(f"All duplicate response tests completed in {execution_time:.2f} seconds")
    
    def _calculate_summary(self):
        """Calculate test summary statistics."""
        # Count overall tests and successes
        total_rapid = len(self.results["rapid_press_tests"])
        successful_rapid = sum(1 for result in self.results["rapid_press_tests"].values() 
                              if result["success"])
        
        total_menu_loops = len(self.results["menu_loop_tests"])
        successful_menu_loops = sum(1 for result in self.results["menu_loop_tests"].values() 
                                   if result["success"])
        
        total_back_forth = len(self.results["back_forth_tests"])
        successful_back_forth = sum(1 for result in self.results["back_forth_tests"].values() 
                                   if result["success"])
        
        total_sequences = len(self.results["identical_sequence_tests"])
        successful_sequences = sum(1 for result in self.results["identical_sequence_tests"].values() 
                                  if result["success"])
        
        total_tests = total_rapid + total_menu_loops + total_back_forth + total_sequences
        successful_tests = successful_rapid + successful_menu_loops + successful_back_forth + successful_sequences
        
        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
            "rapid_press": {
                "total": total_rapid,
                "successful": successful_rapid,
                "success_rate": (successful_rapid / total_rapid * 100) if total_rapid > 0 else 0
            },
            "menu_loops": {
                "total": total_menu_loops,
                "successful": successful_menu_loops,
                "success_rate": (successful_menu_loops / total_menu_loops * 100) if total_menu_loops > 0 else 0
            },
            "back_forth": {
                "total": total_back_forth,
                "successful": successful_back_forth,
                "success_rate": (successful_back_forth / total_back_forth * 100) if total_back_forth > 0 else 0
            },
            "identical_sequences": {
                "total": total_sequences,
                "successful": successful_sequences,
                "success_rate": (successful_sequences / total_sequences * 100) if total_sequences > 0 else 0
            }
        }
    
    def generate_report(self):
        """Generate a comprehensive test report."""
        
        summary = self._calculate_summary()
        
        print("\n===== DUPLICATE RESPONSE PREVENTION TEST RESULTS =====\n")
        
        # Print overall summary
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Successful Tests: {summary['successful_tests']} ({summary['success_rate']:.1f}%)")
        
        # Print category summaries
        print("\n--- Rapid Button Press Tests ---")
        print(f"Passed: {summary['rapid_press']['successful']}/{summary['rapid_press']['total']} "
              f"({summary['rapid_press']['success_rate']:.1f}%)")
        
        print("\n--- Menu Loop Tests ---")
        print(f"Passed: {summary['menu_loops']['successful']}/{summary['menu_loops']['total']} "
              f"({summary['menu_loops']['success_rate']:.1f}%)")
        
        print("\n--- Back-Forth Navigation Tests ---")
        print(f"Passed: {summary['back_forth']['successful']}/{summary['back_forth']['total']} "
              f"({summary['back_forth']['success_rate']:.1f}%)")
        
        print("\n--- Identical Sequence Tests ---")
        print(f"Passed: {summary['identical_sequences']['successful']}/{summary['identical_sequences']['total']} "
              f"({summary['identical_sequences']['success_rate']:.1f}%)")
        
        # Print detailed results for any failures
        if summary['successful_tests'] < summary['total_tests']:
            print("\n--- FAILED TESTS ---")
            
            for category_name, category in self.results.items():
                for test_name, result in category.items():
                    if not result["success"]:
                        print(f"\n{test_name} ({category_name}):")
                        if category_name == "rapid_press_tests":
                            print(f"  Button: {result['button']}")
                            print(f"  Presses: {result['presses']}")
                            print(f"  Responses: {result['responses']}")
                            print(f"  Duplicate responses: {result['duplicate_responses']}")
                            print(f"  Response actions: {result['response_actions']}")
                        elif category_name == "menu_loop_tests" or category_name == "back_forth_tests":
                            print(f"  Buttons: {result['buttons']}")
                            print(f"  Expected responses: {result['expected_responses']}")
                            print(f"  Actual responses: {result['actual_responses']}")
                            print(f"  Null responses: {result['null_responses']}")
                            print(f"  Responses: {result['responses']}")
                        elif category_name == "identical_sequence_tests":
                            print(f"  Sequence: {result['sequence']}")
                            print(f"  Repetitions: {result['repetitions']}")
                            print(f"  Sequence failures: {result['sequence_failures']}")
                            print(f"  Responses: {result['responses']}")
        
        print("\n===== ANTI-LOOP PROTECTION ASSESSMENT =====\n")
        
        if summary['success_rate'] == 100:
            print("✅ EXCELLENT: Anti-loop protection is working perfectly.")
            print("• No duplicate responses detected in any test case.")
            print("• All navigation patterns handled correctly.")
            print("• Button presses are properly tracked and deduplicated.")
        elif summary['success_rate'] >= 80:
            print("⚠️ GOOD: Anti-loop protection is working well but has minor issues.")
            print("• Most test cases passed successfully.")
            print("• Some edge cases could potentially generate duplicate responses.")
            print("• Consider reviewing the failed test cases above.")
        else:
            print("❌ NEEDS IMPROVEMENT: Anti-loop protection has significant issues.")
            print("• Multiple test cases failed to prevent duplicate responses.")
            print("• Users may experience UI confusion due to duplicate messages.")
            print("• Review the tracking and deduplication mechanisms in the code.")
        
        print("\n===========================================")
        
        # Save detailed results to file
        with open('duplicate_response_test_results.json', 'w') as f:
            json.dump({
                "summary": summary,
                "results": self.results
            }, f, indent=2)
        
        # Create markdown report
        self._save_markdown_report(summary)
    
    def _save_markdown_report(self, summary):
        """Save a detailed markdown report."""
        
        with open('DUPLICATE_RESPONSE_TEST_REPORT.md', 'w') as f:
            f.write("# FiLot Anti-Loop and Duplicate Response Test Report\n\n")
            
            # Executive summary
            f.write("## Executive Summary\n\n")
            f.write(f"- **Total Tests:** {summary['total_tests']}\n")
            f.write(f"- **Successful Tests:** {summary['successful_tests']} ({summary['success_rate']:.1f}%)\n\n")
            
            if summary['success_rate'] == 100:
                f.write("✅ **EXCELLENT**: Anti-loop protection is working perfectly\n\n")
            elif summary['success_rate'] >= 80:
                f.write("⚠️ **GOOD**: Anti-loop protection is working well but has minor issues\n\n")
            else:
                f.write("❌ **NEEDS IMPROVEMENT**: Anti-loop protection has significant issues\n\n")
            
            # Test categories
            f.write("## Test Categories\n\n")
            
            # Rapid press tests
            f.write("### Rapid Button Press Tests\n\n")
            f.write(f"- **Total:** {summary['rapid_press']['total']}\n")
            f.write(f"- **Successful:** {summary['rapid_press']['successful']} ({summary['rapid_press']['success_rate']:.1f}%)\n\n")
            
            f.write("| Test | Button | Presses | Responses | Duplicates | Status |\n")
            f.write("|------|--------|---------|-----------|------------|--------|\n")
            
            for test_name, result in self.results["rapid_press_tests"].items():
                status = "✅ Passed" if result["success"] else "❌ Failed"
                f.write(f"| {test_name} | `{result['button']}` | {result['presses']} | {result['responses']} | {result['duplicate_responses']} | {status} |\n")
            
            # Menu loop tests
            f.write("\n### Menu Loop Tests\n\n")
            f.write(f"- **Total:** {summary['menu_loops']['total']}\n")
            f.write(f"- **Successful:** {summary['menu_loops']['successful']} ({summary['menu_loops']['success_rate']:.1f}%)\n\n")
            
            f.write("| Test | Buttons | Expected | Actual | Null | Status |\n")
            f.write("|------|---------|----------|--------|------|--------|\n")
            
            for test_name, result in self.results["menu_loop_tests"].items():
                status = "✅ Passed" if result["success"] else "❌ Failed"
                buttons = " → ".join([f"`{b}`" for b in result["buttons"]])
                f.write(f"| {test_name} | {buttons} | {result['expected_responses']} | {result['actual_responses']} | {result['null_responses']} | {status} |\n")
            
            # Back-forth tests
            f.write("\n### Back-Forth Navigation Tests\n\n")
            f.write(f"- **Total:** {summary['back_forth']['total']}\n")
            f.write(f"- **Successful:** {summary['back_forth']['successful']} ({summary['back_forth']['success_rate']:.1f}%)\n\n")
            
            f.write("| Test | Pattern | Expected | Actual | Null | Status |\n")
            f.write("|------|---------|----------|--------|------|--------|\n")
            
            for test_name, result in self.results["back_forth_tests"].items():
                status = "✅ Passed" if result["success"] else "❌ Failed"
                pattern = " ↔ ".join([b.replace("menu_", "").replace("back_to_", "") for b in result["buttons"][:2]])
                f.write(f"| {test_name} | {pattern} x{len(result['buttons'])//2} | {result['expected_responses']} | {result['actual_responses']} | {result['null_responses']} | {status} |\n")
            
            # Identical sequence tests
            f.write("\n### Identical Sequence Tests\n\n")
            f.write(f"- **Total:** {summary['identical_sequences']['total']}\n")
            f.write(f"- **Successful:** {summary['identical_sequences']['successful']} ({summary['identical_sequences']['success_rate']:.1f}%)\n\n")
            
            f.write("| Test | Sequence | Repetitions | Failures | Status |\n")
            f.write("|------|----------|-------------|----------|--------|\n")
            
            for test_name, result in self.results["identical_sequence_tests"].items():
                status = "✅ Passed" if result["success"] else "❌ Failed"
                sequence = " → ".join([f"`{s}`" for s in result["sequence"]])
                f.write(f"| {test_name} | {sequence} | {result['repetitions']} | {result['sequence_failures']} | {status} |\n")
            
            # Conclusion and recommendations
            f.write("\n## Conclusion and Recommendations\n\n")
            
            if summary['success_rate'] == 100:
                f.write("### Excellent Anti-Loop Protection\n\n")
                f.write("The FiLot Telegram bot's anti-loop protection system is working perfectly. All tests passed successfully, demonstrating that:\n\n")
                f.write("1. **Rapid Button Presses**: Multiple presses of the same button are correctly handled without duplicating responses\n")
                f.write("2. **Menu Navigation**: Complex navigation patterns work correctly without generating errors\n")
                f.write("3. **Repeated Sequences**: Identical navigation sequences are properly processed\n\n")
                f.write("**Recommendation**: Continue monitoring in production to ensure the system maintains this level of performance under real-world conditions.\n")
            elif summary['success_rate'] >= 80:
                f.write("### Good Anti-Loop Protection with Minor Issues\n\n")
                f.write("The FiLot Telegram bot's anti-loop protection system is working well with some minor issues:\n\n")
                
                # List which categories had issues
                if summary['rapid_press']['success_rate'] < 100:
                    f.write("- **Rapid Button Presses**: Some duplicate responses detected in rapid press scenarios\n")
                if summary['menu_loops']['success_rate'] < 100:
                    f.write("- **Menu Navigation**: Some complex navigation patterns generated errors\n")
                if summary['back_forth']['success_rate'] < 100:
                    f.write("- **Back-Forth Navigation**: Issues detected in rapid menu switching\n")
                if summary['identical_sequences']['success_rate'] < 100:
                    f.write("- **Repeated Sequences**: Some identical sequences were not handled correctly\n")
                
                f.write("\n**Recommendations**:\n")
                f.write("1. Review the callback deduplication mechanism in `callback_handler.py`\n")
                f.write("2. Enhance the time window for deduplication in busy navigation sequences\n")
                f.write("3. Consider adding additional safety checks for frequently used buttons\n")
            else:
                f.write("### Anti-Loop Protection Needs Significant Improvement\n\n")
                f.write("The FiLot Telegram bot's anti-loop protection system has significant issues that need addressing:\n\n")
                
                # List major categories with issues
                if summary['rapid_press']['success_rate'] < 70:
                    f.write("- **Rapid Button Presses**: Multiple duplicate responses detected in rapid press scenarios\n")
                if summary['menu_loops']['success_rate'] < 70:
                    f.write("- **Menu Navigation**: Many complex navigation patterns generated errors\n")
                if summary['back_forth']['success_rate'] < 70:
                    f.write("- **Back-Forth Navigation**: Significant issues detected in rapid menu switching\n")
                if summary['identical_sequences']['success_rate'] < 70:
                    f.write("- **Repeated Sequences**: Identical sequences were frequently mishandled\n")
                
                f.write("\n**Critical Recommendations**:\n")
                f.write("1. Implement a more robust callback deduplication system\n")
                f.write("2. Add persistent tracking of recent button presses in the database\n")
                f.write("3. Consider adding a cooldown period for certain navigation buttons\n")
                f.write("4. Implement additional logging and monitoring in production\n")
            
        logger.info(f"Saved markdown report to DUPLICATE_RESPONSE_TEST_REPORT.md")

# Run the tests
if __name__ == "__main__":
    tester = DuplicateResponseTester()
    
    # Run all tests
    logger.info("Starting duplicate response prevention tests...")
    tester.run_all_tests()
    
    # Generate report
    tester.generate_report()
    
    logger.info("Duplicate response prevention tests completed")