#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Reinforcement Learning Environment for Liquidity Pool Investments
This module provides a Gym-compatible environment for training RL agents to make optimal
liquidity pool investment decisions.
"""

import numpy as np
import pandas as pd
import gym
from gym import spaces
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Any, Optional
import logging
import os
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

class RLPoolEnv(gym.Env):
    """
    A Gym environment for liquidity pool investment simulation.
    
    This environment simulates DeFi liquidity pool investments based on historical data,
    allowing an RL agent to learn optimal investment strategies considering APR,
    impermanent loss, and other factors.
    """
    
    def __init__(self, 
                historical_data: Optional[pd.DataFrame] = None,
                data_source: str = 'raydium',
                initial_balance: float = 1000.0,
                episode_length: int = 30,
                transaction_fee: float = 0.003,
                max_pools: int = 5,
                reward_scaling: float = 0.01,
                il_penalty_factor: float = 1.5):
        """
        Initialize the RL environment for liquidity pool investments.
        
        Args:
            historical_data: DataFrame containing historical pool data, if None will be loaded
            data_source: Source of data ('raydium', 'file', etc.)
            initial_balance: Starting USDC balance for the agent
            episode_length: Number of days per training episode
            transaction_fee: Fee per transaction as a decimal (0.003 = 0.3%)
            max_pools: Maximum number of pools the agent can invest in simultaneously
            reward_scaling: Factor to scale rewards for better learning dynamics
            il_penalty_factor: Weight for impermanent loss penalty in the reward function
        """
        super().__init__()
        
        # Environment parameters
        self.initial_balance = initial_balance
        self.episode_length = episode_length
        self.transaction_fee = transaction_fee
        self.max_pools = max_pools
        self.reward_scaling = reward_scaling
        self.il_penalty_factor = il_penalty_factor
        self.data_source = data_source
        
        # Load historical data if not provided
        self.historical_data = historical_data if historical_data is not None else self._load_historical_data()
        
        # Get the unique pool IDs
        self.pool_ids = self.historical_data['pool_id'].unique().tolist()
        self.num_pools = len(self.pool_ids)
        
        # Action space: For each pool, agent can decide to:
        # - Buy (add liquidity)
        # - Sell (remove liquidity)
        # - Hold (do nothing)
        # Total actions = (num_pools * 3) + 1 (do nothing for all pools)
        self.action_space = spaces.Discrete((self.num_pools * 3) + 1)
        
        # State space includes:
        # - Current balance
        # - Current position in each pool (0 to 1 representing % of funds)
        # - Pool features (APR, TVL, price changes, etc.) for each pool
        # - Time remaining in episode
        
        # For each pool, we track: 
        # - Current invested amount
        # - APR
        # - TVL
        # - 24h change in token0 price
        # - 24h change in token1 price
        # - 7d volume
        # - Pool age (days)
        # - Impermanent loss estimate
        pool_features = 8
        
        # Define the observation space
        self.observation_space = spaces.Box(
            low=-np.inf,  # Lower bound
            high=np.inf,  # Upper bound
            shape=(1 + self.max_pools + (self.num_pools * pool_features) + 1,),  # +1 for time
            dtype=np.float32
        )
        
        # Reset the environment
        self.reset()
        
    def _load_historical_data(self) -> pd.DataFrame:
        """
        Load historical data for training the RL agent.
        
        Returns:
            DataFrame containing historical pool data
        """
        logger.info(f"Loading historical pool data from {self.data_source}")
        
        # If using Raydium data, try to load from cache first
        try:
            # Load data from our existing API
            from raydium_client import get_pools, get_pool_history
            from api_mock_data import get_mock_pools
            
            # Get pool data
            logger.info("Fetching pool data from Raydium API")
            pools = get_mock_pools(min_apr=10.0, min_tvl=100000.0)
            
            if not pools or len(pools) == 0:
                logger.warning("No pools returned from API, using default mock data")
                pools = get_mock_pools()
            
            # Convert to dataframe and add timestamps for historical simulation
            df_pools = pd.DataFrame(pools)
            
            # Generate historical data for each pool
            historical_data = []
            
            # Create 90 days of historical data
            base_date = datetime.now() - timedelta(days=90)
            
            for pool in pools:
                pool_id = pool.get('id', '')
                
                # Simulate some reasonable variation in metrics over time
                for day in range(90):
                    date = base_date + timedelta(days=day)
                    
                    # Add some random walk to the APR and TVL
                    apr_factor = 1 + np.random.normal(0, 0.03)  # 3% daily std dev
                    tvl_factor = 1 + np.random.normal(0, 0.02)  # 2% daily std dev
                    
                    # Ensure values stay reasonable
                    apr = max(1.0, min(200.0, pool.get('apr', 20) * apr_factor))
                    tvl = max(10000, min(10000000, pool.get('tvl', 100000) * tvl_factor))
                    
                    # Add price changes
                    price0_change = np.random.normal(0, 0.03)  # 3% daily std dev
                    price1_change = np.random.normal(0, 0.03)  # 3% daily std dev
                    
                    # Create daily record
                    daily_data = {
                        'date': date,
                        'pool_id': pool_id,
                        'token0': pool.get('token0', 'Unknown'),
                        'token1': pool.get('token1', 'Unknown'),
                        'apr': apr,
                        'tvl': tvl,
                        'price0_change': price0_change,
                        'price1_change': price1_change,
                        'volume_7d': pool.get('volume7d', 50000) * (1 + np.random.normal(0, 0.05)),
                        'age_days': pool.get('age_days', 30) + day
                    }
                    
                    historical_data.append(daily_data)
            
            return pd.DataFrame(historical_data)
            
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
            # Fallback to synthetic data for testing
            logger.info("Generating synthetic data for testing")
            
            # Create synthetic data with reasonable properties
            synthetic_data = []
            base_date = datetime.now() - timedelta(days=90)
            
            # Create 10 sample pools
            for pool_id in range(10):
                # Base APR and TVL with some randomness
                base_apr = np.random.uniform(5, 50)  # Between 5% and 50%
                base_tvl = np.random.uniform(50000, 5000000)  # $50K to $5M
                
                # Generate 90 days of history
                for day in range(90):
                    date = base_date + timedelta(days=day)
                    
                    # Add random walk to metrics
                    apr_walk = np.random.normal(0, base_apr * 0.03)  # 3% of base APR
                    tvl_walk = np.random.normal(0, base_tvl * 0.02)  # 2% of base TVL
                    
                    apr = max(1.0, base_apr + apr_walk)
                    tvl = max(10000, base_tvl + tvl_walk)
                    
                    # Add price changes
                    price0_change = np.random.normal(0, 0.03)  # 3% daily std dev
                    price1_change = np.random.normal(0, 0.03)  # 3% daily std dev
                    
                    # Create daily record
                    daily_data = {
                        'date': date,
                        'pool_id': f"pool_{pool_id}",
                        'token0': f"token0_{pool_id}",
                        'token1': f"token1_{pool_id}",
                        'apr': apr,
                        'tvl': tvl,
                        'price0_change': price0_change,
                        'price1_change': price1_change,
                        'volume_7d': 50000 * (1 + np.random.normal(0, 0.05)),
                        'age_days': 30 + day
                    }
                    
                    synthetic_data.append(daily_data)
            
            return pd.DataFrame(synthetic_data)
    
    def reset(self, seed=None, options=None) -> tuple:
        """
        Reset the environment to start a new episode.
        
        Args:
            seed: Optional random seed for reproducibility
            options: Optional configuration options
            
        Returns:
            Tuple of (observation, info)
        """
        # Set random seed if provided
        if seed is not None:
            np.random.seed(seed)
            
        # Reset balances and positions
        self.balance = self.initial_balance
        self.positions = {pool_id: 0.0 for pool_id in self.pool_ids[:self.max_pools]}
        
        # Reset episode tracking
        self.current_step = 0
        self.total_returns = 0.0
        self.episode_rewards = []
        self.portfolio_history = []
        self.action_history = []
        
        # Sample a random starting point in the historical data
        # (leaving enough days for a full episode)
        max_start_idx = len(self.historical_data['date'].unique()) - self.episode_length
        if max_start_idx > 0:
            self.start_date_idx = np.random.randint(0, max_start_idx)
        else:
            self.start_date_idx = 0
            logger.warning("Not enough historical data for full episode, starting from beginning")
        
        # Get the starting date
        all_dates = sorted(self.historical_data['date'].unique())
        self.current_date = all_dates[self.start_date_idx]
        
        # Get the initial observation
        observation = self._get_observation()
        
        # Return observation and empty info dict to match Gym API
        return observation, {}
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Take a step in the environment by executing an action.
        
        Args:
            action: The action to execute (integer index)
            
        Returns:
            Tuple containing:
            - Next observation
            - Reward
            - Whether episode is terminated
            - Whether episode is truncated
            - Info dict with additional information
        """
        # Parse the action
        pool_idx, action_type = self._parse_action(action)
        
        # Execute the action if it's valid
        reward = 0.0
        info = {"action_taken": "none", "pool_id": None}
        
        if pool_idx is not None and action_type is not None:
            # Get the pool ID
            if pool_idx < len(self.pool_ids):
                pool_id = self.pool_ids[pool_idx]
                info["pool_id"] = pool_id
                
                # Get current pool data
                pool_data = self._get_pool_data(pool_id)
                
                if action_type == 'buy' and self.balance > 0:
                    # Add liquidity (invest 10% of current balance)
                    investment_amount = self.balance * 0.1
                    
                    # Apply transaction fee
                    fee = investment_amount * self.transaction_fee
                    actual_investment = investment_amount - fee
                    
                    # Update balance and position
                    self.balance -= investment_amount
                    self.positions[pool_id] = self.positions.get(pool_id, 0.0) + actual_investment
                    
                    info["action_taken"] = "buy"
                    info["amount"] = actual_investment
                    
                elif action_type == 'sell' and self.positions.get(pool_id, 0.0) > 0:
                    # Remove liquidity (remove all invested in this pool)
                    removal_amount = self.positions[pool_id]
                    
                    # Calculate returns based on time held and APR
                    # Simplified model assumes compounding daily returns based on APR
                    apr_decimal = pool_data.get('apr', 0.0) / 100.0
                    days_held = 1  # Assuming at least one day
                    
                    # Calculate impermanent loss
                    il_percent = self._calculate_impermanent_loss(
                        pool_data.get('price0_change', 0.0),
                        pool_data.get('price1_change', 0.0)
                    )
                    
                    # Apply APR, impermanent loss, and fees
                    daily_return = (1 + (apr_decimal / 365)) ** days_held
                    il_factor = 1 - il_percent
                    
                    # Final amount received
                    amount_received = removal_amount * daily_return * il_factor
                    fee = amount_received * self.transaction_fee
                    final_amount = amount_received - fee
                    
                    # Update balance and position
                    self.balance += final_amount
                    self.positions[pool_id] = 0.0
                    
                    # Record profit or loss
                    profit = final_amount - removal_amount
                    
                    info["action_taken"] = "sell"
                    info["amount"] = final_amount
                    info["profit"] = profit
                    info["il_percent"] = il_percent
                
                elif action_type == 'hold':
                    # Do nothing
                    info["action_taken"] = "hold"
        
        # Update all positions based on APR and price changes
        self._update_positions()
        
        # Calculate portfolio value
        portfolio_value = self.balance + sum(self.positions.values())
        
        # Calculate reward based on change in portfolio value and impermanent loss
        prev_portfolio_value = self.initial_balance if len(self.portfolio_history) == 0 else self.portfolio_history[-1]
        portfolio_change = portfolio_value - prev_portfolio_value
        
        # Impermanent loss penalty component
        il_penalty = self._calculate_total_impermanent_loss() * self.il_penalty_factor
        
        # Total reward is change in portfolio minus IL penalty
        reward = (portfolio_change - il_penalty) * self.reward_scaling
        
        # Store history
        self.portfolio_history.append(portfolio_value)
        self.episode_rewards.append(reward)
        self.action_history.append(info)
        
        # Advance to the next day
        self.current_step += 1
        all_dates = sorted(self.historical_data['date'].unique())
        if self.start_date_idx + self.current_step < len(all_dates):
            self.current_date = all_dates[self.start_date_idx + self.current_step]
        
        # Check if episode is done
        terminated = self.current_step >= self.episode_length
        truncated = False  # We don't truncate episodes early in this environment
        
        # Get the new observation
        observation = self._get_observation()
        
        # Add additional info
        info["portfolio_value"] = portfolio_value
        info["balance"] = self.balance
        info["step"] = self.current_step
        info["positions"] = self.positions.copy()
        
        return observation, reward, terminated, truncated, info
    
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
        
        pool_idx = action % self.num_pools
        
        if action < self.num_pools:
            return pool_idx, 'buy'
        elif action < 2 * self.num_pools:
            return pool_idx, 'sell'
        else:
            return pool_idx, 'hold'
    
    def _get_pool_data(self, pool_id: str) -> Dict[str, Any]:
        """
        Get the current data for a specific pool.
        
        Args:
            pool_id: The ID of the pool
            
        Returns:
            Dictionary of pool data
        """
        # Filter data for the current date and pool
        pool_data = self.historical_data[
            (self.historical_data['date'] == self.current_date) & 
            (self.historical_data['pool_id'] == pool_id)
        ]
        
        if pool_data.empty:
            # Return empty data if not found
            return {}
        
        # Convert to dictionary
        return pool_data.iloc[0].to_dict()
    
    def _get_observation(self) -> np.ndarray:
        """
        Get the current observation from the environment.
        
        Returns:
            Numpy array representing the current state
        """
        # Start with balance
        obs = [self.balance / self.initial_balance]  # Normalize
        
        # Add current positions (normalized)
        position_values = []
        for pool_id in self.pool_ids[:self.max_pools]:
            position_norm = self.positions.get(pool_id, 0.0) / self.initial_balance
            position_values.append(position_norm)
        
        # Pad if needed
        position_values = position_values + [0.0] * (self.max_pools - len(position_values))
        obs.extend(position_values)
        
        # Add pool features
        for pool_id in self.pool_ids:
            pool_data = self._get_pool_data(pool_id)
            
            # Extract and normalize features
            apr = pool_data.get('apr', 0.0) / 100.0  # Normalize APR to 0-1 range
            tvl = np.log1p(pool_data.get('tvl', 0.0)) / 20.0  # Log scale and normalize
            price0_change = pool_data.get('price0_change', 0.0)
            price1_change = pool_data.get('price1_change', 0.0)
            volume_7d = np.log1p(pool_data.get('volume_7d', 0.0)) / 15.0
            age_days = min(pool_data.get('age_days', 0.0) / 365.0, 1.0)  # Cap at 1 year
            
            # Calculate impermanent loss
            il = self._calculate_impermanent_loss(price0_change, price1_change)
            
            # Get current position
            position = self.positions.get(pool_id, 0.0) / self.initial_balance
            
            # Add all features
            obs.extend([apr, tvl, price0_change, price1_change, volume_7d, age_days, il, position])
        
        # Add time remaining in episode (normalized)
        obs.append((self.episode_length - self.current_step) / self.episode_length)
        
        return np.array(obs, dtype=np.float32)
    
    def _update_positions(self) -> None:
        """
        Update all positions based on APR and price changes.
        This simulates the daily returns and impermanent loss for all held positions.
        """
        for pool_id, amount in self.positions.items():
            if amount > 0:
                # Get current pool data
                pool_data = self._get_pool_data(pool_id)
                
                # Skip if no data available
                if not pool_data:
                    continue
                
                # Calculate daily return based on APR
                apr_decimal = pool_data.get('apr', 0.0) / 100.0
                daily_return = 1 + (apr_decimal / 365)
                
                # Calculate impermanent loss
                il_percent = self._calculate_impermanent_loss(
                    pool_data.get('price0_change', 0.0),
                    pool_data.get('price1_change', 0.0)
                )
                il_factor = 1 - il_percent
                
                # Update position value
                self.positions[pool_id] = amount * daily_return * il_factor
    
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
    
    def _calculate_total_impermanent_loss(self) -> float:
        """
        Calculate the total impermanent loss across all positions.
        
        Returns:
            Total impermanent loss weighted by position size
        """
        total_il = 0.0
        total_position_value = sum(self.positions.values())
        
        if total_position_value == 0:
            return 0.0
        
        for pool_id, amount in self.positions.items():
            if amount > 0:
                pool_data = self._get_pool_data(pool_id)
                
                if not pool_data:
                    continue
                
                il_percent = self._calculate_impermanent_loss(
                    pool_data.get('price0_change', 0.0),
                    pool_data.get('price1_change', 0.0)
                )
                
                # Weight IL by position size
                weight = amount / total_position_value
                total_il += il_percent * weight
        
        return total_il
    
    def render(self, mode: str = 'human') -> Optional[np.ndarray]:
        """
        Render the environment visualization.
        
        Args:
            mode: Rendering mode ('human' or 'rgb_array')
            
        Returns:
            RGB array if mode is 'rgb_array', otherwise None
        """
        if mode == 'human':
            # Create a visualization of the portfolio
            plt.figure(figsize=(12, 8))
            
            # Plot 1: Portfolio value over time
            plt.subplot(2, 2, 1)
            plt.plot(self.portfolio_history)
            plt.title('Portfolio Value')
            plt.xlabel('Day')
            plt.ylabel('Value ($)')
            
            # Plot 2: Rewards over time
            plt.subplot(2, 2, 2)
            plt.plot(self.episode_rewards)
            plt.title('Rewards')
            plt.xlabel('Day')
            plt.ylabel('Reward')
            
            # Plot 3: Current Positions
            plt.subplot(2, 2, 3)
            positions = {k: v for k, v in self.positions.items() if v > 0}
            if positions:
                plt.bar(positions.keys(), positions.values())
                plt.title('Current Positions')
                plt.xlabel('Pool')
                plt.ylabel('Amount ($)')
                plt.xticks(rotation=45)
            else:
                plt.text(0.5, 0.5, 'No active positions', 
                         horizontalalignment='center', verticalalignment='center')
                plt.title('Current Positions')
            
            # Plot 4: Action History
            plt.subplot(2, 2, 4)
            actions = [info['action_taken'] for info in self.action_history]
            action_counts = {
                'buy': actions.count('buy'),
                'sell': actions.count('sell'),
                'hold': actions.count('hold'),
                'none': actions.count('none')
            }
            plt.bar(action_counts.keys(), action_counts.values())
            plt.title('Action Counts')
            plt.xlabel('Action')
            plt.ylabel('Count')
            
            plt.tight_layout()
            plt.show()
            
            return None
        elif mode == 'rgb_array':
            # For producing videos, return RGB array
            # This would need to be implemented if video recording is needed
            return np.zeros((300, 400, 3), dtype=np.uint8)

# For testing
if __name__ == "__main__":
    # Create environment
    env = RLPoolEnv()
    
    # Test reset and step
    obs = env.reset()
    print(f"Observation shape: {obs.shape}")
    
    # Take some random actions
    for i in range(10):
        action = env.action_space.sample()
        obs, reward, done, info = env.step(action)
        print(f"Step {i}: Action {action}, Reward {reward:.4f}, Done {done}")
        print(f"Action taken: {info['action_taken']}")
        
    # Render
    env.render()