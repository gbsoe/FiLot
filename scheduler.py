#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Scheduler for the Telegram cryptocurrency pool bot
Periodically runs monitoring tasks and other scheduled jobs
"""

import os
import logging
import asyncio
import time
from datetime import datetime, timedelta
import threading
from typing import Dict, Any, Optional, List, Callable, Awaitable

# Import local modules
from orchestrator import get_orchestrator
from models import Position, PositionStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class Scheduler:
    """Scheduler for running periodic tasks"""
    
    def __init__(self):
        """Initialize the scheduler"""
        self.running = False
        self.tasks = {}
        self.alert_callbacks = []
        
    def add_task(self, name: str, func: Callable[[], Awaitable[Any]], interval_seconds: int) -> None:
        """
        Add a task to the scheduler
        
        Args:
            name: Name of the task
            func: Async function to call
            interval_seconds: How often to run the task in seconds
        """
        self.tasks[name] = {
            "func": func,
            "interval": interval_seconds,
            "last_run": 0  # Never run
        }
        logger.info(f"Added task {name} with interval {interval_seconds}s")
        
    def register_alert_callback(self, callback: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """
        Register a callback function for position exit alerts
        
        Args:
            callback: Async function to call with alert data
        """
        self.alert_callbacks.append(callback)
        logger.info(f"Registered alert callback {callback.__name__}")
        
    async def _run_task(self, name: str, task: Dict[str, Any]) -> None:
        """
        Run a task and handle errors
        
        Args:
            name: Name of the task
            task: Task configuration
        """
        try:
            logger.info(f"Running task {name}")
            result = await task["func"]()
            task["last_run"] = time.time()
            task["last_result"] = result
            logger.info(f"Task {name} completed successfully")
            
            # If this is the monitoring task and we have alerts, call callbacks
            if name == "monitor_positions" and result and len(result) > 0:
                logger.info(f"Monitoring task found {len(result)} alerts")
                for alert in result:
                    for callback in self.alert_callbacks:
                        try:
                            await callback(alert)
                        except Exception as e:
                            logger.error(f"Error in alert callback: {e}")
                
        except Exception as e:
            logger.error(f"Error running task {name}: {e}")
            
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop that runs tasks at their intervals"""
        while self.running:
            current_time = time.time()
            
            for name, task in self.tasks.items():
                # Check if it's time to run this task
                if current_time - task["last_run"] >= task["interval"]:
                    # Run the task
                    await self._run_task(name, task)
            
            # Sleep for a short time to avoid CPU hogging
            await asyncio.sleep(1)
            
    def start(self) -> None:
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
            
        self.running = True
        
        # Start scheduler in a separate thread
        threading.Thread(target=self._start_async_loop, daemon=True).start()
        logger.info("Scheduler started")
        
    def _start_async_loop(self) -> None:
        """Start the async event loop for the scheduler thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self._scheduler_loop())
        finally:
            loop.close()
            
    def stop(self) -> None:
        """Stop the scheduler"""
        self.running = False
        logger.info("Scheduler stopped")

# Initialize scheduler
def init_scheduler() -> Scheduler:
    """
    Initialize the scheduler with default tasks
    
    Returns:
        Initialized scheduler
    """
    scheduler = Scheduler()
    
    # Add monitoring task (every 15 minutes)
    orchestrator = get_orchestrator()
    scheduler.add_task("monitor_positions", orchestrator.monitor_positions, 15 * 60)
    
    # Start the scheduler
    scheduler.start()
    
    return scheduler