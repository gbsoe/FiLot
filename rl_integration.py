#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Reinforcement Learning Integration Module for FiLot Bot
This module integrates the trained RL agent into the FiLot bot for making liquidity pool investment decisions.
"""

import os
import logging
import numpy as np
import torch
from typing import Dict, List, Tuple, Any, Optional

# Import RL modules
from rl_agent import DQNAgent, ActorCriticAgent
from rl_environment import RLPoolEnv

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

class RLInvestmentAdvisor:
    """
    RL-based investment advisor that replaces rule-based investment logic.
    This class serves as an interface between the Telegram bot and the trained RL agent.
    """
    
    def __init__(self, 
                model_path: str = './rl_models/final_model',
                agent_type: str = 'dqn',
                use_rl: bool = True,
                device: str = None):
        """
        Initialize the RL investment advisor.
        
        Args:
            model_path: Path to the trained model
            agent_type: Type of agent ('dqn' or 'actor_critic')
            use_rl: Whether to use RL or fall back to rule-based logic
            device: Device to run the model on ('cpu' or 'cuda')
        """
        self.model_path = model_path
        self.agent_type = agent_type
        self.use_rl = use_rl
        
        # Set device
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        
        # Initialize environment (needed for state representation)
        self.env = RLPoolEnv()
        
        # Get state and action dimensions
        self.state_dim = self.env.observation_space.shape[0]
        self.action_dim = self.env.action_space.n
        
        # Initialize agent if using RL
        self.agent = None
        if self.use_rl:
            self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize and load the RL agent."""
        try:
            # Create agent based on type
            if self.agent_type == 'dqn':
                self.agent = DQNAgent(self.state_dim, self.action_dim, device=self.device)
                logger.info(f"Created DQN agent with state_dim={self.state_dim}, action_dim={self.action_dim}")
            else:
                self.agent = ActorCriticAgent(self.state_dim, self.action_dim, device=self.device)
                logger.info(f"Created Actor-Critic agent with state_dim={self.state_dim}, action_dim={self.action_dim}")
            
            # Load trained model
            if os.path.exists(self.model_path):
                success = self.agent.load(self.model_path)
                if success:
                    logger.info(f"Successfully loaded RL agent from {self.model_path}")
                else:
                    logger.warning(f"Failed to load RL agent from {self.model_path}, using untrained agent")
            else:
                logger.warning(f"Model path {self.model_path} not found, using untrained agent")
                
        except Exception as e:
            logger.error(f"Error initializing RL agent: {e}")
            self.use_rl = False
            logger.warning("Falling back to rule-based logic")
    
    def get_state_from_pool_data(self, 
                               pool_data: List[Dict[str, Any]], 
                               user_balance: float, 
                               user_positions: Dict[str, float]) -> np.ndarray:
        """
        Convert pool data and user state to a state vector for the RL agent.
        
        Args:
            pool_data: List of pool data dictionaries
            user_balance: User's current USDC balance
            user_positions: User's current positions (pool_id -> amount)
            
        Returns:
            State vector for the RL agent
        """
        # Reset environment to get a clean state
        self.env.reset()
        
        # Set environment state to match user state
        self.env.balance = user_balance
        self.env.positions = user_positions.copy()
        
        # Update pool data in environment
        # This is a simplification - in a production system, you would
        # properly sync all environment state with actual data
        self.env.historical_data = pool_data
        
        # Get observation from environment
        state = self.env._get_observation()
        
        return state
    
    def get_pool_recommendations(self, 
                               pool_data: List[Dict[str, Any]], 
                               user_data: Dict[str, Any], 
                               risk_profile: str = 'moderate',
                               top_n: int = 3) -> List[Dict[str, Any]]:
        """
        Get pool recommendations based on RL agent or rule-based logic.
        
        Args:
            pool_data: List of pool data dictionaries
            user_data: User data including balance and positions
            risk_profile: User's risk profile ('conservative', 'moderate', 'aggressive')
            top_n: Number of recommendations to return
            
        Returns:
            List of recommended pools with additional metadata
        """
        # Extract user balance and positions
        user_balance = user_data.get('balance', 0)
        user_positions = user_data.get('positions', {})
        
        # If not using RL, fall back to rule-based recommendations
        if not self.use_rl or self.agent is None:
            return self._get_rule_based_recommendations(pool_data, user_data, risk_profile, top_n)
        
        try:
            # Get state representation
            state = self.get_state_from_pool_data(pool_data, user_balance, user_positions)
            
            # Get action from RL agent
            action = self.agent.select_action(state, evaluation=True)
            
            # Parse the action
            pool_idx, action_type = self._parse_action(action)
            
            # If action is "do nothing" or not buy, fall back to rule-based
            if pool_idx is None or action_type != 'buy':
                return self._get_rule_based_recommendations(pool_data, user_data, risk_profile, top_n)
            
            # Get the recommended pool
            pool_id = self.env.pool_ids[pool_idx] if pool_idx < len(self.env.pool_ids) else None
            if pool_id is None:
                return self._get_rule_based_recommendations(pool_data, user_data, risk_profile, top_n)
            
            # Find the pool data for the recommended pool
            recommended_pool = None
            for pool in pool_data:
                if pool.get('id') == pool_id:
                    recommended_pool = pool
                    break
            
            if recommended_pool is None:
                return self._get_rule_based_recommendations(pool_data, user_data, risk_profile, top_n)
            
            # Get additional recommendations
            other_recommendations = self._get_rule_based_recommendations(pool_data, user_data, risk_profile, top_n - 1)
            
            # Add RL recommendation at the top with a tag
            recommended_pool['rl_recommended'] = True
            recommended_pool['confidence'] = 0.95  # High confidence for RL recommendation
            
            # Combine recommendations
            recommendations = [recommended_pool] + other_recommendations
            
            return recommendations[:top_n]
            
        except Exception as e:
            logger.error(f"Error getting RL recommendations: {e}")
            return self._get_rule_based_recommendations(pool_data, user_data, risk_profile, top_n)
    
    def get_exit_recommendations(self, 
                               pool_data: List[Dict[str, Any]], 
                               user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get recommendations for which positions to exit based on RL agent or rule-based logic.
        
        Args:
            pool_data: List of pool data dictionaries
            user_data: User data including balance and positions
            
        Returns:
            List of pools recommended for exit with reasons
        """
        # Extract user positions
        user_positions = user_data.get('positions', {})
        user_balance = user_data.get('balance', 0)
        
        # If no positions or not using RL, fall back to rule-based recommendations
        if not user_positions or not self.use_rl or self.agent is None:
            return self._get_rule_based_exit_recommendations(pool_data, user_data)
        
        try:
            # Get state representation
            state = self.get_state_from_pool_data(pool_data, user_balance, user_positions)
            
            # Get action from RL agent
            action = self.agent.select_action(state, evaluation=True)
            
            # Parse the action
            pool_idx, action_type = self._parse_action(action)
            
            # If action is not sell, fall back to rule-based
            if pool_idx is None or action_type != 'sell':
                return self._get_rule_based_exit_recommendations(pool_data, user_data)
            
            # Get the recommended pool to exit
            pool_id = self.env.pool_ids[pool_idx] if pool_idx < len(self.env.pool_ids) else None
            if pool_id is None or pool_id not in user_positions:
                return self._get_rule_based_exit_recommendations(pool_data, user_data)
            
            # Find the pool data for the recommended exit
            exit_pool = None
            for pool in pool_data:
                if pool.get('id') == pool_id:
                    exit_pool = pool
                    break
            
            if exit_pool is None:
                return self._get_rule_based_exit_recommendations(pool_data, user_data)
            
            # Calculate impermanent loss
            price0_change = exit_pool.get('price0_change', 0)
            price1_change = exit_pool.get('price1_change', 0)
            il_percent = self._calculate_impermanent_loss(price0_change, price1_change)
            
            # Add exit recommendation data
            exit_pool['position_value'] = user_positions.get(pool_id, 0)
            exit_pool['exit_reason'] = "RL model predicts optimal exit point"
            exit_pool['impermanent_loss'] = il_percent
            exit_pool['rl_recommended'] = True
            
            return [exit_pool]
            
        except Exception as e:
            logger.error(f"Error getting RL exit recommendations: {e}")
            return self._get_rule_based_exit_recommendations(pool_data, user_data)
    
    def get_rebalance_recommendations(self, 
                                   pool_data: List[Dict[str, Any]], 
                                   user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get recommendations for portfolio rebalancing based on RL agent.
        
        Args:
            pool_data: List of pool data dictionaries
            user_data: User data including balance and positions
            
        Returns:
            Dictionary with rebalance recommendations
        """
        # If not using RL, fall back to rule-based recommendations
        if not self.use_rl or self.agent is None:
            return self._get_rule_based_rebalance_recommendations(pool_data, user_data)
        
        # Get positions and balance
        positions = user_data.get('positions', {})
        balance = user_data.get('balance', 0)
        
        # Initialize recommendations
        rebalance_plan = {
            'increase': [],
            'decrease': [],
            'enter': [],
            'exit': [],
            'summary': "Rebalance strategy based on RL model optimal portfolio allocation"
        }
        
        try:
            # Simulate a sequence of actions to generate a rebalance plan
            # This requires multiple steps of the RL agent to build a complete plan
            
            # Get initial state
            state = self.get_state_from_pool_data(pool_data, balance, positions)
            
            # Maximum number of actions to consider
            max_actions = 5
            
            # Track pools to avoid repeating
            processed_pools = set()
            
            for _ in range(max_actions):
                # Get action from RL agent
                action = self.agent.select_action(state, evaluation=True)
                
                # Parse the action
                pool_idx, action_type = self._parse_action(action)
                
                # Skip if no meaningful action
                if pool_idx is None or pool_idx >= len(self.env.pool_ids):
                    continue
                
                # Get pool ID
                pool_id = self.env.pool_ids[pool_idx]
                
                # Skip if already processed this pool
                if pool_id in processed_pools:
                    continue
                
                processed_pools.add(pool_id)
                
                # Find pool data
                pool = None
                for p in pool_data:
                    if p.get('id') == pool_id:
                        pool = p
                        break
                
                if pool is None:
                    continue
                
                # Determine recommendation based on action type
                if action_type == 'buy':
                    if pool_id in positions:
                        # Increase existing position
                        rebalance_plan['increase'].append({
                            'pool': pool,
                            'current_amount': positions.get(pool_id, 0),
                            'target_amount': positions.get(pool_id, 0) * 1.5,  # Increase by 50%
                            'reason': "RL model predicts increased returns"
                        })
                    else:
                        # Enter new position
                        rebalance_plan['enter'].append({
                            'pool': pool,
                            'suggested_amount': balance * 0.2,  # 20% of available balance
                            'reason': "RL model predicts strong returns"
                        })
                
                elif action_type == 'sell':
                    if pool_id in positions:
                        # Exit position
                        rebalance_plan['exit'].append({
                            'pool': pool,
                            'current_amount': positions.get(pool_id, 0),
                            'reason': "RL model predicts declining returns"
                        })
                    
                # Simulate the action and update state
                next_state, _, _, _ = self.env.step(action)
                state = next_state
            
            # If no specific recommendations, add a general one
            if not any([rebalance_plan['increase'], rebalance_plan['decrease'], 
                      rebalance_plan['enter'], rebalance_plan['exit']]):
                rebalance_plan['summary'] = "RL model suggests maintaining current allocation"
            
            return rebalance_plan
            
        except Exception as e:
            logger.error(f"Error getting RL rebalance recommendations: {e}")
            return self._get_rule_based_rebalance_recommendations(pool_data, user_data)
    
    def _parse_action(self, action: int) -> Tuple[Optional[int], Optional[str]]:
        """
        Parse an action integer into pool index and action type.
        
        Args:
            action: Integer action from the agent
            
        Returns:
            Tuple of (pool_idx, action_type)
            action_type is one of 'buy', 'sell', 'hold', or None if invalid
        """
        # Action 0 is "do nothing"
        if action == 0:
            return None, None
        
        # Otherwise, action is encoded as:
        # 1 to num_pools: Buy for pool_idx
        # num_pools+1 to 2*num_pools: Sell for pool_idx
        # 2*num_pools+1 to 3*num_pools: Hold for pool_idx
        action = action - 1  # Adjust for the "do nothing" action
        
        num_pools = self.env.num_pools
        pool_idx = action % num_pools
        
        if action < num_pools:
            return pool_idx, 'buy'
        elif action < 2 * num_pools:
            return pool_idx, 'sell'
        else:
            return pool_idx, 'hold'
    
    def _calculate_impermanent_loss(self, price0_change: float, price1_change: float) -> float:
        """
        Calculate impermanent loss based on price changes of the two tokens.
        
        Args:
            price0_change: Relative price change of token0 (decimal)
            price1_change: Relative price change of token1 (decimal)
            
        Returns:
            Impermanent loss as a decimal (0.01 = 1%)
        """
        # Convert price changes to actual price ratios
        p0_ratio = 1 + price0_change
        p1_ratio = 1 + price1_change
        
        # Simple IL formula: IL = 2√(p0_ratio * p1_ratio)/(p0_ratio + p1_ratio) - 1
        if p0_ratio <= 0 or p1_ratio <= 0:
            return 0.0  # Avoid invalid calculations
        
        geometric_mean = np.sqrt(p0_ratio * p1_ratio)
        arithmetic_mean = (p0_ratio + p1_ratio) / 2
        
        if arithmetic_mean == 0:
            return 0.0
        
        il = 2 * geometric_mean / (p0_ratio + p1_ratio) - 1
        
        # IL is negative (it's a loss), but we return the positive value
        # for easier integration with the reward function
        return -min(il, 0.0)
    
    def _get_rule_based_recommendations(self, 
                                     pool_data: List[Dict[str, Any]], 
                                     user_data: Dict[str, Any],
                                     risk_profile: str,
                                     top_n: int) -> List[Dict[str, Any]]:
        """
        Get pool recommendations based on rule-based logic (fallback).
        
        Args:
            pool_data: List of pool data dictionaries
            user_data: User data including balance and positions
            risk_profile: User's risk profile ('conservative', 'moderate', 'aggressive')
            top_n: Number of recommendations to return
            
        Returns:
            List of recommended pools
        """
        # Copy pool data to avoid modifying the original
        pools = pool_data.copy()
        
        # Apply filters based on risk profile
        if risk_profile == 'conservative':
            # Conservative: Focus on established, stable pools with lower APR
            pools = [p for p in pools if p.get('age_days', 0) > 30 and p.get('tvl', 0) > 500000]
            pools.sort(key=lambda p: (p.get('tvl', 0), p.get('apr', 0)), reverse=True)
        elif risk_profile == 'aggressive':
            # Aggressive: Focus on high APR pools
            pools = [p for p in pools if p.get('apr', 0) > 20]
            pools.sort(key=lambda p: p.get('apr', 0), reverse=True)
        else:
            # Moderate (default): Balance APR and TVL
            pools = [p for p in pools if p.get('age_days', 0) > 14 and p.get('tvl', 0) > 100000]
            pools.sort(key=lambda p: (p.get('apr', 0) * 0.7 + np.log1p(p.get('tvl', 0)) * 0.3), reverse=True)
        
        # Take top N pools
        recommended_pools = pools[:top_n]
        
        # Add rule-based tag
        for pool in recommended_pools:
            pool['rl_recommended'] = False
            pool['confidence'] = 0.85  # Lower confidence for rule-based
        
        return recommended_pools
    
    def _get_rule_based_exit_recommendations(self, 
                                         pool_data: List[Dict[str, Any]], 
                                         user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get rule-based exit recommendations (fallback).
        
        Args:
            pool_data: List of pool data dictionaries
            user_data: User data including balance and positions
            
        Returns:
            List of pools recommended for exit
        """
        positions = user_data.get('positions', {})
        if not positions:
            return []
        
        exit_recommendations = []
        
        # Check positions against current pool data
        for pool_id, amount in positions.items():
            # Find pool data
            pool = None
            for p in pool_data:
                if p.get('id') == pool_id:
                    pool = p
                    break
            
            if pool is None:
                continue
            
            # Check APR drop (exit if APR dropped by 30% or more)
            original_apr = pool.get('original_apr', pool.get('apr', 0))
            current_apr = pool.get('apr', 0)
            
            apr_drop = (original_apr - current_apr) / original_apr if original_apr > 0 else 0
            
            # Check impermanent loss
            price0_change = pool.get('price0_change', 0)
            price1_change = pool.get('price1_change', 0)
            il_percent = self._calculate_impermanent_loss(price0_change, price1_change)
            
            # Exit if APR dropped significantly or impermanent loss is high
            if apr_drop > 0.3 or il_percent > 0.05:
                reason = []
                if apr_drop > 0.3:
                    reason.append(f"APR dropped by {apr_drop:.1%}")
                if il_percent > 0.05:
                    reason.append(f"Impermanent loss reached {il_percent:.1%}")
                
                # Add to exit recommendations
                pool['position_value'] = amount
                pool['exit_reason'] = " and ".join(reason)
                pool['impermanent_loss'] = il_percent
                pool['rl_recommended'] = False
                
                exit_recommendations.append(pool)
        
        return exit_recommendations
    
    def _get_rule_based_rebalance_recommendations(self, 
                                             pool_data: List[Dict[str, Any]], 
                                             user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get rule-based portfolio rebalance recommendations (fallback).
        
        Args:
            pool_data: List of pool data dictionaries
            user_data: User data including balance and positions
            
        Returns:
            Dictionary with rebalance recommendations
        """
        positions = user_data.get('positions', {})
        balance = user_data.get('balance', 0)
        
        rebalance_plan = {
            'increase': [],
            'decrease': [],
            'enter': [],
            'exit': [],
            'summary': "Rule-based rebalance strategy based on APR, TVL and risk"
        }
        
        # Sort pools by APR (for potential new positions)
        sorted_pools = sorted(pool_data, key=lambda p: p.get('apr', 0), reverse=True)
        
        # Check current positions
        position_pools = []
        for pool_id, amount in positions.items():
            # Find pool data
            pool = None
            for p in pool_data:
                if p.get('id') == pool_id:
                    pool = p
                    position_pools.append(pool)
                    break
            
            if pool is None:
                continue
            
            # Check for exit or decrease
            apr = pool.get('apr', 0)
            
            if apr < 10:  # Very low APR
                rebalance_plan['exit'].append({
                    'pool': pool,
                    'current_amount': amount,
                    'reason': f"Low APR of {apr:.1f}%"
                })
            elif apr < 15:  # Moderately low APR
                rebalance_plan['decrease'].append({
                    'pool': pool,
                    'current_amount': amount,
                    'target_amount': amount * 0.5,  # Reduce by 50%
                    'reason': f"Declining APR of {apr:.1f}%"
                })
        
        # Find new pools to enter (if we have balance)
        if balance > 0:
            # Filter out pools we already have positions in
            new_pools = [p for p in sorted_pools if p.get('id') not in positions]
            
            # Take top 2 new pools by APR
            for pool in new_pools[:2]:
                apr = pool.get('apr', 0)
                if apr > 20:  # Only suggest high APR pools
                    rebalance_plan['enter'].append({
                        'pool': pool,
                        'suggested_amount': balance * 0.4,  # 40% of available balance
                        'reason': f"High APR of {apr:.1f}%"
                    })
        
        # Find positions to increase
        position_pools.sort(key=lambda p: p.get('apr', 0), reverse=True)
        for pool in position_pools[:1]:  # Top position by APR
            pool_id = pool.get('id')
            amount = positions.get(pool_id, 0)
            apr = pool.get('apr', 0)
            
            if apr > 25 and balance > 0:  # Very high APR and we have balance
                rebalance_plan['increase'].append({
                    'pool': pool,
                    'current_amount': amount,
                    'target_amount': amount + (balance * 0.6),  # Add 60% of available balance
                    'reason': f"Exceptional APR of {apr:.1f}%"
                })
        
        return rebalance_plan

# For testing
if __name__ == "__main__":
    # Create RL advisor
    advisor = RLInvestmentAdvisor(use_rl=False)  # Use rule-based logic for testing
    
    # Create test pool data
    pool_data = [
        {
            'id': 'pool_1',
            'token0': 'SOL',
            'token1': 'USDC',
            'apr': 35.5,
            'tvl': 2500000,
            'price0_change': 0.02,
            'price1_change': 0.001,
            'age_days': 120,
            'volume7d': 500000
        },
        {
            'id': 'pool_2',
            'token0': 'BTC',
            'token1': 'USDC',
            'apr': 18.2,
            'tvl': 5000000,
            'price0_change': 0.03,
            'price1_change': 0.001,
            'age_days': 90,
            'volume7d': 1200000
        },
        {
            'id': 'pool_3',
            'token0': 'ETH',
            'token1': 'USDC',
            'apr': 12.5,
            'tvl': 3800000,
            'price0_change': -0.01,
            'price1_change': 0.001,
            'age_days': 150,
            'volume7d': 800000
        }
    ]
    
    # Create test user data
    user_data = {
        'balance': 1000,
        'positions': {
            'pool_2': 500,
            'pool_3': 200
        }
    }
    
    # Get recommendations
    recommendations = advisor.get_pool_recommendations(pool_data, user_data, 'moderate', 2)
    print("Pool Recommendations:")
    for i, rec in enumerate(recommendations):
        print(f"{i+1}. {rec['token0']}-{rec['token1']}: APR {rec['apr']}%, TVL ${rec['tvl']}")
    
    # Get exit recommendations
    exit_recs = advisor.get_exit_recommendations(pool_data, user_data)
    print("\nExit Recommendations:")
    for i, rec in enumerate(exit_recs):
        print(f"{i+1}. {rec['token0']}-{rec['token1']}: {rec.get('exit_reason', 'No reason')}")
    
    # Get rebalance recommendations
    rebalance = advisor.get_rebalance_recommendations(pool_data, user_data)
    print("\nRebalance Recommendations:")
    print(f"Summary: {rebalance['summary']}")
    if rebalance['increase']:
        print("Increase:")
        for rec in rebalance['increase']:
            print(f"  {rec['pool']['token0']}-{rec['pool']['token1']}: {rec['current_amount']} → {rec['target_amount']}")
    if rebalance['enter']:
        print("Enter:")
        for rec in rebalance['enter']:
            print(f"  {rec['pool']['token0']}-{rec['pool']['token1']}: Invest {rec['suggested_amount']}")