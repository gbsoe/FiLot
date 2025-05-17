#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Enhanced navigation test for the FiLot Telegram bot.
Tests the improved navigation system with focus on preventing duplicate responses.
"""

import logging
import time
import random
from typing import List, Dict, Any, Set, Tuple, Optional
import json
import sqlite3

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(name)s: %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Import necessary modules
import main
from callback_handler import route_callback, CallbackRegistry
from navigation_context import record_navigation, get_navigation_history, detect_pattern
from anti_loop import reset_all_locks

class ImprovedNavigationTester:
    """Tests the improved navigation system with our enhanced button handling."""
    
    def __init__(self):
        """Initialize the tester with test scenarios."""
        self.results = {}
        
        # Test context for simulating updates
        self.test_context = {
            "chat_id": random.randint(10000, 99999),  # Random chat ID for isolation
            "user_id": random.randint(10000, 99999),
            "message_id": 100000,
            "callback_id": "test_callback_id",
            "test_mode": True
        }
        
        # Define our test scenarios
        self.test_scenarios = [
            {
                "name": "Rapid Button Press Test",
                "description": "Tests that rapid presses of the same button don't cause duplicate responses",
                "actions": [
                    {"callback": "menu_invest", "delay": 0.1},
                    {"callback": "menu_invest", "delay": 0.1},
                    {"callback": "menu_invest", "delay": 0.1}
                ],
                "expected_responses": 1  # Only the first press should generate a response
            },
            {
                "name": "Menu Navigation Test",
                "description": "Tests that proper menu navigation works correctly",
                "actions": [
                    {"callback": "menu_invest", "delay": 0.5},
                    {"callback": "menu_explore", "delay": 0.5},
                    {"callback": "menu_account", "delay": 0.5},
                    {"callback": "back_to_main", "delay": 0.5}
                ],
                "expected_responses": 4  # All should generate responses
            },
            {
                "name": "Back-Forth Navigation Test",
                "description": "Tests navigation back and forth between menus",
                "actions": [
                    {"callback": "menu_invest", "delay": 0.5},
                    {"callback": "back_to_main", "delay": 0.5},
                    {"callback": "menu_invest", "delay": 0.5},
                    {"callback": "back_to_main", "delay": 0.5}
                ],
                "expected_responses": 4  # All should generate responses with our improvements
            },
            {
                "name": "Complex Navigation Pattern Test",
                "description": "Tests a complex navigation pattern with multiple screens",
                "actions": [
                    {"callback": "menu_invest", "delay": 0.5},
                    {"callback": "amount_100", "delay": 0.5},
                    {"callback": "back_to_main", "delay": 0.5},
                    {"callback": "menu_explore", "delay": 0.5},
                    {"callback": "explore_pools", "delay": 0.5},
                    {"callback": "back_to_main", "delay": 0.5}
                ],
                "expected_responses": 6  # All should generate responses
            },
            {
                "name": "Identical Sequence Test",
                "description": "Tests repeating the exact same navigation sequence twice",
                "actions": [
                    # First sequence
                    {"callback": "menu_invest", "delay": 0.5},
                    {"callback": "amount_100", "delay": 0.5},
                    {"callback": "back_to_main", "delay": 0.5},
                    # Second identical sequence
                    {"callback": "menu_invest", "delay": 0.5}, 
                    {"callback": "amount_100", "delay": 0.5},
                    {"callback": "back_to_main", "delay": 0.5}
                ],
                "expected_responses": 6  # All should generate responses with our improvements
            }
        ]
    
    def run_test_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test scenario and return the results."""
        logger.info(f"Running scenario: {scenario['name']}")
        logger.info(f"Description: {scenario['description']}")
        
        # Clear any previous state
        reset_all_locks()
        CallbackRegistry.prune_old_data()
        
        # Use a fresh chat ID for this test to ensure isolation
        chat_id = random.randint(100000, 999999)
        self.test_context["chat_id"] = chat_id
        
        responses = []
        
        # Execute each action in the scenario
        for idx, action in enumerate(scenario["actions"]):
            # Update the callback ID to create a unique update object
            callback_id = f"test_{scenario['name']}_{idx}_{time.time()}"
            self.test_context["callback_id"] = callback_id
            
            # Get the callback data and delay
            callback_data = action["callback"]
            delay = action.get("delay", 0.1)
            
            # Log the action
            logger.info(f"Action {idx+1}/{len(scenario['actions'])}: {callback_data}")
            
            try:
                # Route the callback
                response = route_callback(callback_data, self.test_context.copy())
                responses.append(response)
                
                # Log the response
                if response:
                    logger.info(f"  Response: {response.get('action', 'unknown')}")
                else:
                    logger.info(f"  Response: None (no action taken)")
                
                # Check the navigation history after the action
                nav_history = get_navigation_history(chat_id, 1)
                if nav_history:
                    pattern = detect_pattern(chat_id)
                    if pattern:
                        logger.info(f"  Detected pattern: {pattern}")
                
                # Wait for the specified delay
                time.sleep(delay)
            except Exception as e:
                logger.error(f"Error in scenario {scenario['name']}, action {idx+1}: {e}")
        
        # Count the actual responses (non-None values)
        actual_responses = sum(1 for r in responses if r is not None)
        
        # Calculate success based on expected vs actual responses
        success = actual_responses == scenario["expected_responses"]
        
        # Create the result
        result = {
            "scenario": scenario["name"],
            "description": scenario["description"],
            "actions": [a["callback"] for a in scenario["actions"]],
            "expected_responses": scenario["expected_responses"],
            "actual_responses": actual_responses,
            "responses": [r.get("action", str(r)) if r else None for r in responses],
            "success": success
        }
        
        # Log the result
        if success:
            logger.info(f"✅ Scenario PASSED: {scenario['name']} ({actual_responses}/{scenario['expected_responses']} responses)")
        else:
            logger.error(f"❌ Scenario FAILED: {scenario['name']} ({actual_responses}/{scenario['expected_responses']} responses)")
        
        return result
    
    def run_all_scenarios(self) -> Dict[str, Any]:
        """Run all test scenarios and return the results."""
        all_results = {}
        
        for scenario in self.test_scenarios:
            result = self.run_test_scenario(scenario)
            all_results[scenario["name"]] = result
        
        return all_results
    
    def calculate_summary(self) -> Dict[str, Any]:
        """Calculate a summary of all test results."""
        total_scenarios = len(self.results)
        successful_scenarios = sum(1 for r in self.results.values() if r["success"])
        
        total_actions = sum(len(r["actions"]) for r in self.results.values())
        expected_responses = sum(r["expected_responses"] for r in self.results.values())
        actual_responses = sum(r["actual_responses"] for r in self.results.values())
        
        return {
            "total_scenarios": total_scenarios,
            "successful_scenarios": successful_scenarios,
            "success_rate": (successful_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0,
            "total_actions": total_actions,
            "expected_responses": expected_responses,
            "actual_responses": actual_responses,
            "response_accuracy": (actual_responses / expected_responses * 100) if expected_responses > 0 else 0
        }
    
    def run_tests_and_generate_report(self) -> None:
        """Run all tests and generate a comprehensive report."""
        start_time = time.time()
        
        # Run all test scenarios
        self.results = self.run_all_scenarios()
        
        # Calculate summary
        summary = self.calculate_summary()
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Print the report
        print("\n===== IMPROVED NAVIGATION SYSTEM TEST RESULTS =====\n")
        
        print(f"Total Scenarios: {summary['total_scenarios']}")
        print(f"Successful Scenarios: {summary['successful_scenarios']} ({summary['success_rate']:.1f}%)")
        print(f"Total Button Actions: {summary['total_actions']}")
        print(f"Response Accuracy: {summary['actual_responses']}/{summary['expected_responses']} ({summary['response_accuracy']:.1f}%)")
        print(f"Execution Time: {execution_time:.2f} seconds\n")
        
        # Print scenario details
        print("--- Scenario Results ---\n")
        
        for name, result in self.results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"{status} - {name}")
            print(f"  Description: {result['description']}")
            print(f"  Actions: {' → '.join(result['actions'])}")
            print(f"  Expected: {result['expected_responses']} responses")
            print(f"  Actual: {result['actual_responses']} responses")
            
            if not result["success"]:
                print("  Response Details:")
                for i, (action, response) in enumerate(zip(result["actions"], result["responses"])):
                    print(f"    {i+1}. {action} → {response}")
            
            print()
        
        # Overall assessment
        print("--- Overall Assessment ---\n")
        
        if summary["success_rate"] == 100:
            print("✅ EXCELLENT: The improved navigation system is working perfectly.")
            print("• All scenarios passed without any issues.")
            print("• Button responses are correctly processed without duplication.")
            print("• Complex navigation patterns are handled properly.")
        elif summary["success_rate"] >= 80:
            print("⚠️ GOOD: The improved navigation system is working well.")
            print("• Most scenarios passed successfully.")
            print("• Some minor issues remain to be addressed.")
        else:
            print("❌ NEEDS IMPROVEMENT: The navigation system still has significant issues.")
            print("• Multiple scenarios failed to perform as expected.")
            print("• Review the failed scenarios for specific issues.")
        
        print("\n===========================================")
        
        # Save the detailed results to a file
        with open("improved_navigation_test_results.json", "w") as f:
            json.dump({
                "summary": summary,
                "results": self.results,
                "timestamp": time.time(),
                "execution_time": execution_time
            }, f, indent=2)
        
        # Save an HTML report
        self._save_html_report(summary)
        
        logger.info(f"Test results saved to improved_navigation_test_results.json")
    
    def _save_html_report(self, summary: Dict[str, Any]) -> None:
        """Save an HTML report of the test results."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>FiLot Navigation System Test Results</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2, h3 {{ color: #2754EB; }}
                .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .scenario {{ margin-bottom: 20px; border: 1px solid #ddd; padding: 15px; border-radius: 5px; }}
                .pass {{ background-color: #e8f5e9; }}
                .fail {{ background-color: #ffebee; }}
                .actions {{ font-family: monospace; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .success-rate {{ font-size: 24px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>FiLot Navigation System Test Results</h1>
            
            <div class="summary">
                <h2>Summary</h2>
                <p class="success-rate">{summary['success_rate']:.1f}% Success Rate</p>
                <p>Total Scenarios: {summary['total_scenarios']}</p>
                <p>Successful Scenarios: {summary['successful_scenarios']}</p>
                <p>Total Button Actions: {summary['total_actions']}</p>
                <p>Response Accuracy: {summary['actual_responses']}/{summary['expected_responses']} ({summary['response_accuracy']:.1f}%)</p>
            </div>
            
            <h2>Scenario Results</h2>
        """
        
        # Add each scenario result
        for name, result in self.results.items():
            status_class = "pass" if result["success"] else "fail"
            status_text = "PASS" if result["success"] else "FAIL"
            
            html_content += f"""
            <div class="scenario {status_class}">
                <h3>{name} - {status_text}</h3>
                <p>{result['description']}</p>
                <p class="actions">Actions: {' → '.join(result['actions'])}</p>
                <p>Expected Responses: {result['expected_responses']}</p>
                <p>Actual Responses: {result['actual_responses']}</p>
            """
            
            if not result["success"]:
                html_content += f"""
                <h4>Response Details</h4>
                <table>
                    <tr>
                        <th>#</th>
                        <th>Action</th>
                        <th>Response</th>
                    </tr>
                """
                
                for i, (action, response) in enumerate(zip(result["actions"], result["responses"])):
                    html_content += f"""
                    <tr>
                        <td>{i+1}</td>
                        <td>{action}</td>
                        <td>{response}</td>
                    </tr>
                    """
                
                html_content += "</table>"
            
            html_content += "</div>"
        
        # Add overall assessment
        html_content += """
            <h2>Overall Assessment</h2>
        """
        
        if summary["success_rate"] == 100:
            html_content += """
            <p>✅ <strong>EXCELLENT:</strong> The improved navigation system is working perfectly.</p>
            <ul>
                <li>All scenarios passed without any issues.</li>
                <li>Button responses are correctly processed without duplication.</li>
                <li>Complex navigation patterns are handled properly.</li>
            </ul>
            """
        elif summary["success_rate"] >= 80:
            html_content += """
            <p>⚠️ <strong>GOOD:</strong> The improved navigation system is working well.</p>
            <ul>
                <li>Most scenarios passed successfully.</li>
                <li>Some minor issues remain to be addressed.</li>
            </ul>
            """
        else:
            html_content += """
            <p>❌ <strong>NEEDS IMPROVEMENT:</strong> The navigation system still has significant issues.</p>
            <ul>
                <li>Multiple scenarios failed to perform as expected.</li>
                <li>Review the failed scenarios for specific issues.</li>
            </ul>
            """
        
        # Close the HTML
        html_content += """
        </body>
        </html>
        """
        
        # Save the HTML report
        with open("improved_navigation_test_report.html", "w") as f:
            f.write(html_content)
        
        logger.info("HTML test report saved to improved_navigation_test_report.html")

# Run the tests
if __name__ == "__main__":
    try:
        # Initialize the navigation database table if needed
        conn = sqlite3.connect("filot_bot.db")
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS navigation_context (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            callback_data TEXT NOT NULL,
            context TEXT,
            timestamp REAL NOT NULL,
            navigation_step INTEGER,
            session_id TEXT
        )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Error initializing navigation database: {e}")
    
    tester = ImprovedNavigationTester()
    tester.run_tests_and_generate_report()