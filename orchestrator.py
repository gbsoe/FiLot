#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Orchestrator for the Telegram cryptocurrency pool bot agentic features
Coordinates between agents and provides a unified interface for bot commands
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Union
import json

# Import local modules
from models import User, Pool, Position, CompositeSignal, PositionStatus, db
from recommendation_agent import RecommendationAgent
from execution_agent import ExecutionAgent
from monitoring_agent import MonitoringAgent
from walletconnect_utils import create_walletconnect_session, check_walletconnect_session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Central orchestrator that coordinates the different agents and provides
    a unified interface for bot commands.
    """
    
    def __init__(self):
        """Initialize the orchestrator with all agents"""
        self.recommendation_agent = RecommendationAgent()
        self.execution_agent = ExecutionAgent()
        self.monitoring_agent = MonitoringAgent()
        
        # Session storage for user recommendations
        self.user_sessions = {}
        
    async def recommend(self, user_id: int, profile: str = "high-risk") -> Dict[str, Any]:
        """
        Generate personalized pool recommendations based on user's risk profile
        
        Args:
            user_id: Telegram user ID
            profile: User's risk profile, either "high-risk" or "stable"
            
        Returns:
            Dictionary with recommendation results
        """
        logger.info(f"Generating recommendations for user {user_id} with profile {profile}")
        
        try:
            # Validate profile
            if profile not in ["high-risk", "stable"]:
                return {
                    "success": False,
                    "error": "Invalid profile. Choose 'high-risk' or 'stable'."
                }
                
            # Import Flask app
            from app import app
            
            # Get user from database within application context
            with app.app_context():
                user = db.session.query(User).filter(User.id == user_id).first()
                
                if not user:
                    logger.warning(f"User {user_id} not found in database")
                    # Create user if not exists
                    from db_utils import get_or_create_user
                    user = get_or_create_user(user_id)
                
                # Get recommendations from agent
                recommendations = await self.recommendation_agent.compute_recommendations(profile)
                
                # Store in session
                self.user_sessions[user_id] = {
                    "last_recommendation": recommendations,
                    "timestamp": datetime.now().isoformat(),
                    "profile": profile
                }
                
                # Update user profile if different
                if user.risk_profile != profile:
                    user.risk_profile = profile
                    user.updated_at = datetime.now()
                    db.session.commit()
                    logger.info(f"Updated user {user_id} risk profile to {profile}")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return {
                "success": False,
                "error": f"Error generating recommendations: {e}"
            }
            
    async def execute(self, user_id: int, usd_amount: float) -> Dict[str, Any]:
        """
        Execute investment into the most recently recommended pool
        
        Args:
            user_id: Telegram user ID
            usd_amount: Amount in USD to invest
            
        Returns:
            Dictionary with execution results
        """
        logger.info(f"Executing investment for user {user_id} with amount ${usd_amount}")
        
        try:
            # Check if user has a recent recommendation
            if user_id not in self.user_sessions or "last_recommendation" not in self.user_sessions[user_id]:
                return {
                    "success": False,
                    "error": "No recent recommendation found. Please use /recommend first."
                }
                
            # Get the last recommendation
            recommendation = self.user_sessions[user_id]["last_recommendation"]
            
            # Check if recommendation was successful
            if not recommendation.get("success", False):
                return {
                    "success": False,
                    "error": "Last recommendation was not successful. Please try /recommend again."
                }
                
            # Get the higher return pool (default to execute)
            selected_pool = recommendation.get("higher_return", None)
            
            if not selected_pool:
                return {
                    "success": False,
                    "error": "No suitable pool found in last recommendation. Please try /recommend again."
                }
                
            # Check if user has a connected wallet
            wallet_address = await self.execution_agent.get_wallet_address(user_id)
            
            if not wallet_address:
                return {
                    "success": False,
                    "error": "No wallet connected. Please connect a wallet using /walletconnect first."
                }
                
            # Check minimum investment amount
            if usd_amount < 10:
                return {
                    "success": False,
                    "error": "Minimum investment amount is $10 USD."
                }
                
            # Execute investment using placeholder data
            result = await self.execution_agent.execute_investment(
                user_id,
                selected_pool,
                usd_amount
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing investment: {e}")
            return {
                "success": False,
                "error": f"Error executing investment: {e}"
            }
            
    async def exit(self, user_id: int, position_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Exit a specific position or the most recent active position
        
        Args:
            user_id: Telegram user ID
            position_id: Optional position ID to exit (if None, exits most recent)
            
        Returns:
            Dictionary with exit results
        """
        logger.info(f"Exiting position for user {user_id}, position_id={position_id}")
        
        try:
            # If position_id not provided, get user positions from monitoring agent
            if position_id is None:
                positions = await self.monitoring_agent.get_user_positions(user_id)
                
                if not positions:
                    return {
                        "success": False,
                        "error": "No active positions found."
                    }
                
                # Use the first position as default
                position_id = positions[0]["id"]
            
            # Exit position using our new function
            result = await self.execution_agent.exit_position(
                user_id,
                position_id
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error exiting position: {e}")
            return {
                "success": False,
                "error": f"Error exiting position: {e}"
            }
            
    async def get_positions(self, user_id: int) -> Dict[str, Any]:
        """
        Get all positions for a user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dictionary with positions list
        """
        logger.info(f"Getting positions for user {user_id}")
        
        try:
            # Import Flask app and run within application context
            from app import app
            with app.app_context():
                # Get positions using the monitoring agent
                positions = await self.monitoring_agent.get_user_positions(user_id)
                
                if not positions:
                    return {
                        "success": True,
                        "positions": [],
                        "message": "No positions found."
                    }
                    
                return {
                    "success": True,
                    "positions": positions
                }
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return {
                "success": False,
                "error": f"Error getting positions: {e}"
            }
            
    async def submit_signed_transaction(
        self, 
        user_id: int,
        transaction_signature: str,
        position_id: Optional[int] = None,
        is_exit: bool = False
    ) -> Dict[str, Any]:
        """
        Submit a signed transaction to the network
        
        Args:
            user_id: Telegram user ID
            transaction_signature: Signed transaction data
            position_id: Optional position ID for this transaction
            is_exit: Whether this is an exit transaction
            
        Returns:
            Dictionary with submission results
        """
        logger.info(f"Submitting transaction for user {user_id}")
        
        try:
            result = await self.execution_agent.submit_transaction(
                user_id,
                transaction_signature,
                position_id,
                is_exit
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error submitting transaction: {e}")
            return {
                "success": False,
                "error": f"Error submitting transaction: {e}"
            }
            
    async def monitor_positions(self) -> List[Dict[str, Any]]:
        """
        Monitor all active positions for exit conditions
        
        Returns:
            List of positions that need exit transactions with alerts
        """
        logger.info("Monitoring positions for exit conditions")
        
        try:
            # Evaluate all positions
            positions_to_exit = await self.monitoring_agent.evaluate_positions()
            
            if not positions_to_exit:
                logger.info("No positions need to be exited")
                return []
                
            logger.info(f"Found {len(positions_to_exit)} positions that meet exit conditions")
            
            # Build exit transactions
            exit_transactions = await self.monitoring_agent.build_exit_transactions(positions_to_exit)
            
            # Filter positions where we should send alerts
            alerts = []
            for exit_data in exit_transactions:
                position_id = exit_data["position_id"]
                user_id = exit_data["user_id"]
                
                if self.monitoring_agent.should_send_alert(user_id, position_id):
                    alerts.append(exit_data)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
            return []
            
    async def get_wallet_info(self, user_id: int) -> Dict[str, Any]:
        """
        Get wallet information for a user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dictionary with wallet information
        """
        logger.info(f"Getting wallet info for user {user_id}")
        
        try:
            return await self.execution_agent.check_token_balances(user_id)
            
        except Exception as e:
            logger.error(f"Error getting wallet info: {e}")
            return {
                "success": False,
                "error": f"Error getting wallet info: {e}"
            }
            
    def clear_session(self, user_id: int) -> None:
        """
        Clear a user's session data
        
        Args:
            user_id: Telegram user ID
        """
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
            
    def get_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a user's session data
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Session data or None if not found
        """
        return self.user_sessions.get(user_id)

# Singleton instance
_instance = None

def get_orchestrator() -> Orchestrator:
    """Get the singleton Orchestrator instance."""
    global _instance
    if _instance is None:
        _instance = Orchestrator()
    return _instance