"""
Test script for button navigation flows in the FiLot bot.

This script simulates different button navigation patterns to ensure buttons work correctly
in all scenarios, especially the main navigation buttons (Invest, Explore, Account).
"""

import os
import time
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Global tracking for test results
TEST_RESULTS = {}

class ButtonFlowTester:
    """
    Tester class for button navigation flows.
    """
    
    def __init__(self, bot_instance=None):
        """Initialize the tester."""
        self.bot = bot_instance
        self.test_user_id = 12345678  # Simulated test user
        self.test_chat_id = 12345678  # Simulated test chat
        
    async def simulate_button_press(self, callback_data: str) -> Dict[str, Any]:
        """
        Simulate a button press by calling the appropriate handlers.
        
        Args:
            callback_data: Callback data string for the button
            
        Returns:
            Handler result dictionary
        """
        try:
            # Import required modules
            import callback_handler
            
            # Create handler context
            handler_context = {
                "callback_data": callback_data,
                "user_id": self.test_user_id,
                "chat_id": self.test_chat_id,
                "timestamp": time.time()
            }
            
            # Call the handler
            start_time = time.time()
            result = callback_handler.route_callback(handler_context)
            end_time = time.time()
            
            # Add timing information
            result["processing_time"] = end_time - start_time
            
            logger.info(f"Button press simulated: {callback_data}, Result: {result.get('action', 'unknown')}")
            return result
            
        except Exception as e:
            logger.error(f"Error in button simulation: {e}")
            return {"error": str(e)}
            
    async def test_navigation_flow(self, flow_steps: List[str], name: str) -> Dict[str, Any]:
        """
        Test a specific navigation flow by simulating button presses in sequence.
        
        Args:
            flow_steps: List of callback data strings to simulate in order
            name: Name of the test flow
            
        Returns:
            Test results dictionary
        """
        logger.info(f"Testing navigation flow: {name}")
        logger.info(f"Steps: {' -> '.join(flow_steps)}")
        
        results = []
        errors = []
        
        for i, callback_data in enumerate(flow_steps):
            try:
                # Simulate the button press
                result = await self.simulate_button_press(callback_data)
                results.append(result)
                
                # Check for errors
                if "error" in result:
                    errors.append(f"Step {i+1}: {result['error']}")
                    logger.error(f"Error in step {i+1}: {result['error']}")
                
                # Small delay to simulate real user interaction
                await asyncio.sleep(0.1)
                
            except Exception as e:
                errors.append(f"Step {i+1}: {str(e)}")
                logger.error(f"Error in step {i+1}: {e}")
        
        # Compile test results
        test_result = {
            "name": name,
            "steps": flow_steps,
            "results": results,
            "errors": errors,
            "success": len(errors) == 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # Print test summary
        if test_result["success"]:
            logger.info(f"✅ Flow test passed: {name}")
        else:
            logger.error(f"❌ Flow test failed: {name}")
            for error in errors:
                logger.error(f"  - {error}")
                
        # Save result
        TEST_RESULTS[name] = test_result
        return test_result

    async def test_all_button_flows(self) -> None:
        """Test all important button navigation flows."""
        # Define the test flows
        test_flows = [
            {
                "name": "Invest to Explore",
                "steps": ["menu_invest", "menu_explore"]
            },
            {
                "name": "Explore to Invest",
                "steps": ["menu_explore", "menu_invest"]
            },
            {
                "name": "Invest to Account",
                "steps": ["menu_invest", "menu_account"]
            },
            {
                "name": "Account to Invest",
                "steps": ["menu_account", "menu_invest"]
            },
            {
                "name": "Explore to Account",
                "steps": ["menu_explore", "menu_account"]
            },
            {
                "name": "Account to Explore",
                "steps": ["menu_account", "menu_explore"]
            },
            {
                "name": "Main Menu Circle",
                "steps": ["menu_invest", "menu_explore", "menu_account", "back_to_main"]
            },
            {
                "name": "Repeated Button Press",
                "steps": ["menu_invest", "menu_invest", "menu_invest"]
            },
            {
                "name": "Fast Navigation",
                "steps": ["menu_invest", "menu_explore", "menu_account", "menu_invest"]
            },
            {
                "name": "Ping-Pong Pattern",
                "steps": ["menu_invest", "menu_explore", "menu_invest", "menu_explore"]
            }
        ]
        
        # Run all tests
        for flow in test_flows:
            await self.test_navigation_flow(flow["steps"], flow["name"])
            
        # Generate test summary
        self._generate_test_summary()
            
    def _generate_test_summary(self) -> None:
        """Generate and print a summary of all test results."""
        passed = [name for name, result in TEST_RESULTS.items() if result["success"]]
        failed = [name for name, result in TEST_RESULTS.items() if not result["success"]]
        
        logger.info("\n==== BUTTON NAVIGATION TEST SUMMARY ====")
        logger.info(f"Total Tests: {len(TEST_RESULTS)}")
        logger.info(f"Passed: {len(passed)} ✅")
        logger.info(f"Failed: {len(failed)} ❌")
        
        if failed:
            logger.info("\nFailed Tests:")
            for name in failed:
                logger.info(f"  - {name}")
                for error in TEST_RESULTS[name]["errors"]:
                    logger.info(f"    * {error}")
        
        logger.info("=======================================")
        

# Run tests when executed directly
if __name__ == "__main__":
    async def run_tests():
        tester = ButtonFlowTester()
        await tester.test_all_button_flows()
        
    # Run the tests asynchronously
    asyncio.run(run_tests())