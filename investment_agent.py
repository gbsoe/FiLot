#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Investment Agent for FiLot Bot
This module provides an intelligent agent for making investment decisions
using reinforcement learning and market analysis.
"""

import os
import logging
import time
import random
from typing import Dict, List, Tuple, Any, Optional
import json
import numpy as np

# Import our RL integration
from rl_integration import RLInvestmentAdvisor

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

class PoolRankingModel:
    """Model for ranking liquidity pools based on performance metrics."""
    
    def __init__(self, use_rl: bool = True):
        """
        Initialize the pool ranking model.
        
        Args:
            use_rl: Whether to use reinforcement learning for rankings
        """
        self.use_rl = use_rl
        
        # Initialize RL advisor if using RL
        self.rl_advisor = RLInvestmentAdvisor(use_rl=use_rl) if use_rl else None
    
    async def rank_pools(self, 
                       pools: List[Dict[str, Any]], 
                       risk_profile: str = 'moderate',
                       investment_horizon: str = 'medium',
                       portfolio: Dict[str, Any] = None,
                       token_preference: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Rank pools according to user profile and preferences.
        
        Args:
            pools: List of pool data dictionaries
            risk_profile: User's risk profile ('conservative', 'moderate', 'aggressive')
            investment_horizon: User's investment timeframe ('short', 'medium', 'long')
            portfolio: User's current portfolio information
            token_preference: Optional list of preferred tokens
            
        Returns:
            Sorted list of pools with ranking metadata
        """
        # Use RL advisor if available and configured
        if self.use_rl and self.rl_advisor:
            user_data = {
                'balance': portfolio.get('balance', 1000) if portfolio else 1000,
                'positions': portfolio.get('positions', {}) if portfolio else {}
            }
            
            # Map risk profiles
            rl_risk_profile = {
                'conservative': 'conservative',
                'moderate': 'moderate',
                'aggressive': 'aggressive'
            }.get(risk_profile, 'moderate')
            
            # Get recommendations from RL advisor
            top_n = min(5, len(pools))
            recommended_pools = self.rl_advisor.get_pool_recommendations(
                pools, user_data, rl_risk_profile, top_n
            )
            
            # Add ranking information
            for i, pool in enumerate(recommended_pools):
                pool['rank'] = i + 1
                pool['score'] = 1.0 - (i * 0.1)  # Simple scoring 1.0, 0.9, 0.8, etc.
                pool['match'] = 'high' if i < 2 else 'medium'
                
                # Add RL confidence
                if 'confidence' not in pool:
                    pool['confidence'] = 0.9 - (i * 0.05)
                
                # Add explanation based on RL or traditional metrics
                if pool.get('rl_recommended', False):
                    pool['explanation'] = "AI model predicts optimal risk-reward balance"
                else:
                    if risk_profile == 'conservative':
                        pool['explanation'] = f"Stable pool with {pool.get('apr', 0):.1f}% APR and ${pool.get('tvl', 0):,.0f} TVL"
                    elif risk_profile == 'aggressive':
                        pool['explanation'] = f"High return potential with {pool.get('apr', 0):.1f}% APR"
                    else:
                        pool['explanation'] = f"Balanced opportunity with {pool.get('apr', 0):.1f}% APR and good liquidity"
            
            return recommended_pools
        
        # Fallback to traditional ranking logic
        return self._traditional_ranking(pools, risk_profile, investment_horizon, portfolio, token_preference)
    
    def _traditional_ranking(self, 
                          pools: List[Dict[str, Any]], 
                          risk_profile: str,
                          investment_horizon: str,
                          portfolio: Dict[str, Any] = None,
                          token_preference: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Traditional rule-based pool ranking logic.
        
        Args:
            pools: List of pool data dictionaries
            risk_profile: User's risk profile
            investment_horizon: User's investment timeframe
            portfolio: User's current portfolio information
            token_preference: Optional list of preferred tokens
            
        Returns:
            Sorted list of pools with ranking metadata
        """
        # Copy pools to avoid modifying the original
        ranked_pools = pools.copy()
        
        # Filter by token preference if provided
        if token_preference and len(token_preference) > 0:
            ranked_pools = [p for p in ranked_pools if 
                          p.get('token0', '').upper() in token_preference or 
                          p.get('token1', '').upper() in token_preference]
        
        # Apply risk profile-based scoring
        for pool in ranked_pools:
            # Base score starts at 1.0
            base_score = 1.0
            
            # APR contributes 30-70% of score based on risk profile
            apr = pool.get('apr', 0)
            apr_weight = {
                'conservative': 0.3,
                'moderate': 0.5,
                'aggressive': 0.7
            }.get(risk_profile, 0.5)
            
            # APR score (normalized to 0-1 range, assuming max APR of 100%)
            apr_score = min(apr / 100.0, 1.0) 
            
            # TVL contributes 20-60% of score based on risk profile (inverse of APR weight)
            tvl = pool.get('tvl', 0)
            tvl_weight = {
                'conservative': 0.6,
                'moderate': 0.4,
                'aggressive': 0.2
            }.get(risk_profile, 0.4)
            
            # TVL score (log scale and normalized)
            tvl_score = min(np.log1p(tvl) / 15.0, 1.0)
            
            # Age of pool contributes 10% of score
            age = pool.get('age_days', 0)
            age_score = min(age / 180.0, 1.0)  # Normalize to 0-1 range (6 months max)
            age_weight = 0.1
            
            # Combine scores with weights
            pool['score'] = (apr_score * apr_weight) + (tvl_score * tvl_weight) + (age_score * age_weight)
            
            # Add explanations
            if risk_profile == 'conservative':
                pool['explanation'] = f"Stable pool with {apr:.1f}% APR and ${tvl:,.0f} TVL"
            elif risk_profile == 'aggressive':
                pool['explanation'] = f"High return potential with {apr:.1f}% APR"
            else:
                pool['explanation'] = f"Balanced opportunity with {apr:.1f}% APR and good liquidity"
            
            # Add confidence score
            pool['confidence'] = 0.85  # Standard confidence for traditional model
        
        # Sort by score
        ranked_pools.sort(key=lambda p: p['score'], reverse=True)
        
        # Add rank
        for i, pool in enumerate(ranked_pools):
            pool['rank'] = i + 1
            pool['match'] = 'high' if i < 3 else ('medium' if i < 6 else 'low')
        
        return ranked_pools

class InvestmentTimingModel:
    """Model for determining optimal timing for investments."""
    
    def __init__(self, use_rl: bool = True):
        """
        Initialize the investment timing model.
        
        Args:
            use_rl: Whether to use reinforcement learning for timing decisions
        """
        self.use_rl = use_rl
        self.rl_advisor = RLInvestmentAdvisor(use_rl=use_rl) if use_rl else None
    
    async def should_enter_position(self, 
                                 pool_data: Dict[str, Any], 
                                 user_data: Dict[str, Any],
                                 risk_profile: str = 'moderate') -> Dict[str, Any]:
        """
        Determine if now is a good time to enter a position.
        
        Args:
            pool_data: Data about the pool to assess
            user_data: User data including balance and positions
            risk_profile: User's risk profile
            
        Returns:
            Dict with recommendation and explanation
        """
        if self.use_rl and self.rl_advisor:
            # Wrap pool in a list as the advisor expects a list
            pools = [pool_data]
            
            # Get recommendations
            recommendations = self.rl_advisor.get_pool_recommendations(
                pools, user_data, risk_profile, 1
            )
            
            if recommendations and recommendations[0].get('rl_recommended', False):
                return {
                    'should_enter': True,
                    'confidence': recommendations[0].get('confidence', 0.8),
                    'explanation': "RL model indicates favorable entry conditions",
                    'timing_score': 0.9
                }
        
        # Fallback to traditional logic
        return self._traditional_timing_assessment(pool_data, risk_profile)
    
    async def should_exit_position(self, 
                                pool_data: Dict[str, Any], 
                                position_data: Dict[str, Any],
                                user_data: Dict[str, Any],
                                risk_profile: str = 'moderate') -> Dict[str, Any]:
        """
        Determine if now is a good time to exit a position.
        
        Args:
            pool_data: Data about the pool
            position_data: Data about the user's position
            user_data: Additional user data
            risk_profile: User's risk profile
            
        Returns:
            Dict with recommendation and explanation
        """
        if self.use_rl and self.rl_advisor:
            # Wrap pool in a list as the advisor expects a list
            pools = [pool_data]
            
            # Add position to user data
            if 'positions' not in user_data:
                user_data['positions'] = {}
            
            user_data['positions'][pool_data.get('id', 'unknown')] = position_data.get('amount', 0)
            
            # Get exit recommendations
            exit_recs = self.rl_advisor.get_exit_recommendations(pools, user_data)
            
            if exit_recs:
                return {
                    'should_exit': True,
                    'confidence': exit_recs[0].get('confidence', 0.8),
                    'explanation': exit_recs[0].get('exit_reason', "RL model suggests exit"),
                    'timing_score': 0.8
                }
            
            return {
                'should_exit': False,
                'confidence': 0.7,
                'explanation': "RL model suggests holding position",
                'timing_score': 0.3
            }
        
        # Fallback to traditional logic
        return self._traditional_exit_assessment(pool_data, position_data, risk_profile)
    
    def _traditional_timing_assessment(self, 
                                    pool_data: Dict[str, Any], 
                                    risk_profile: str) -> Dict[str, Any]:
        """
        Traditional rule-based timing assessment.
        
        Args:
            pool_data: Data about the pool to assess
            risk_profile: User's risk profile
            
        Returns:
            Dict with recommendation and explanation
        """
        # Extract metrics
        apr = pool_data.get('apr', 0)
        tvl = pool_data.get('tvl', 0)
        price0_change = pool_data.get('price0_change', 0)
        price1_change = pool_data.get('price1_change', 0)
        
        # Default to not enter
        result = {
            'should_enter': False,
            'confidence': 0.6,
            'explanation': "Market conditions are not optimal for entry",
            'timing_score': 0.4
        }
        
        # Simple timing rules
        if risk_profile == 'conservative':
            # Conservative investors prefer stable conditions
            if apr > 15 and tvl > 500000 and abs(price0_change) < 0.05 and abs(price1_change) < 0.05:
                result = {
                    'should_enter': True,
                    'confidence': 0.8,
                    'explanation': "Stable market conditions with good APR and liquidity",
                    'timing_score': 0.75
                }
        elif risk_profile == 'aggressive':
            # Aggressive investors may enter during volatility for better entry prices
            if apr > 30 or (apr > 20 and (price0_change < -0.05 or price1_change < -0.05)):
                result = {
                    'should_enter': True,
                    'confidence': 0.7,
                    'explanation': "High APR opportunity with potential price upside",
                    'timing_score': 0.85
                }
        else:  # moderate
            # Moderate investors balance stability and opportunity
            if apr > 20 and tvl > 200000 and max(abs(price0_change), abs(price1_change)) < 0.1:
                result = {
                    'should_enter': True,
                    'confidence': 0.75,
                    'explanation': "Good balance of APR and market stability",
                    'timing_score': 0.8
                }
        
        return result
    
    def _traditional_exit_assessment(self, 
                                  pool_data: Dict[str, Any], 
                                  position_data: Dict[str, Any],
                                  risk_profile: str) -> Dict[str, Any]:
        """
        Traditional rule-based exit timing assessment.
        
        Args:
            pool_data: Data about the pool
            position_data: Data about the user's position
            risk_profile: User's risk profile
            
        Returns:
            Dict with recommendation and explanation
        """
        # Extract metrics
        apr = pool_data.get('apr', 0)
        original_apr = position_data.get('entry_apr', apr)
        apr_change = (apr - original_apr) / original_apr if original_apr > 0 else 0
        
        price0_change = pool_data.get('price0_change', 0)
        price1_change = pool_data.get('price1_change', 0)
        
        # Calculate impermanent loss
        p0_ratio = 1 + price0_change
        p1_ratio = 1 + price1_change
        
        if p0_ratio <= 0 or p1_ratio <= 0:
            il_percent = 0
        else:
            geometric_mean = np.sqrt(p0_ratio * p1_ratio)
            il_percent = 2 * geometric_mean / (p0_ratio + p1_ratio) - 1
            il_percent = -min(il_percent, 0.0)  # Convert to positive value
        
        # Default to not exit
        result = {
            'should_exit': False,
            'confidence': 0.6,
            'explanation': "Current position remains favorable",
            'timing_score': 0.3
        }
        
        # Combine factors based on risk profile
        if risk_profile == 'conservative':
            # Conservative investors exit quickly on adverse conditions
            if apr_change < -0.2 or il_percent > 0.03:
                reason = []
                if apr_change < -0.2:
                    reason.append(f"APR dropped by {-apr_change:.1%}")
                if il_percent > 0.03:
                    reason.append(f"impermanent loss of {il_percent:.1%}")
                
                result = {
                    'should_exit': True,
                    'confidence': 0.8,
                    'explanation': "Exit recommended due to " + " and ".join(reason),
                    'timing_score': 0.8,
                    'impermanent_loss': il_percent
                }
        elif risk_profile == 'aggressive':
            # Aggressive investors tolerate more risk
            if apr_change < -0.4 or il_percent > 0.08:
                reason = []
                if apr_change < -0.4:
                    reason.append(f"significant APR drop of {-apr_change:.1%}")
                if il_percent > 0.08:
                    reason.append(f"high impermanent loss of {il_percent:.1%}")
                
                result = {
                    'should_exit': True,
                    'confidence': 0.75,
                    'explanation': "Exit recommended due to " + " and ".join(reason),
                    'timing_score': 0.7,
                    'impermanent_loss': il_percent
                }
        else:  # moderate
            # Moderate investors balance risk and opportunity
            if apr_change < -0.3 or il_percent > 0.05:
                reason = []
                if apr_change < -0.3:
                    reason.append(f"APR decline of {-apr_change:.1%}")
                if il_percent > 0.05:
                    reason.append(f"impermanent loss of {il_percent:.1%}")
                
                result = {
                    'should_exit': True,
                    'confidence': 0.7,
                    'explanation': "Exit recommended due to " + " and ".join(reason),
                    'timing_score': 0.75,
                    'impermanent_loss': il_percent
                }
        
        return result

class PositionSizingModel:
    """Model for determining optimal position sizes."""
    
    def __init__(self, use_rl: bool = True):
        """
        Initialize the position sizing model.
        
        Args:
            use_rl: Whether to use reinforcement learning for position sizing
        """
        self.use_rl = use_rl
        self.rl_advisor = RLInvestmentAdvisor(use_rl=use_rl) if use_rl else None
    
    async def calculate_position_sizes(self, 
                                    available_balance: float,
                                    ranked_pools: List[Dict[str, Any]],
                                    user_data: Dict[str, Any],
                                    risk_profile: str = 'moderate',
                                    max_positions: int = 5) -> List[Dict[str, Any]]:
        """
        Calculate optimal position sizes for a portfolio.
        
        Args:
            available_balance: Available balance to allocate
            ranked_pools: List of ranked pool opportunities
            user_data: User data including existing positions
            risk_profile: User's risk profile
            max_positions: Maximum number of positions to hold
            
        Returns:
            List of pools with position size recommendations
        """
        if self.use_rl and self.rl_advisor:
            # Get rebalance recommendations
            user_data['balance'] = available_balance
            rebalance = self.rl_advisor.get_rebalance_recommendations(ranked_pools, user_data)
            
            # Process recommendations
            recommendations = []
            
            # Process new entries
            for entry in rebalance.get('enter', []):
                pool = entry.get('pool', {})
                amount = entry.get('suggested_amount', available_balance * 0.2)
                
                recommendations.append({
                    'pool': pool,
                    'size': amount,
                    'percentage': amount / available_balance * 100 if available_balance > 0 else 0,
                    'reason': entry.get('reason', "RL model allocation"),
                    'confidence': 0.9
                })
            
            # Process increases
            for increase in rebalance.get('increase', []):
                pool = increase.get('pool', {})
                current = increase.get('current_amount', 0)
                target = increase.get('target_amount', current * 1.5)
                amount = target - current
                
                if amount > 0:
                    recommendations.append({
                        'pool': pool,
                        'size': amount,
                        'percentage': amount / available_balance * 100 if available_balance > 0 else 0,
                        'reason': increase.get('reason', "RL model increase"),
                        'confidence': 0.85
                    })
            
            # If we have recommendations, return them
            if recommendations:
                # Sort by confidence/size
                recommendations.sort(key=lambda r: r.get('confidence', 0) * r.get('size', 0), reverse=True)
                return recommendations[:max_positions]
        
        # Fallback to traditional logic
        return self._traditional_position_sizing(available_balance, ranked_pools, risk_profile, max_positions)
    
    def _traditional_position_sizing(self, 
                                  available_balance: float,
                                  ranked_pools: List[Dict[str, Any]],
                                  risk_profile: str = 'moderate',
                                  max_positions: int = 5) -> List[Dict[str, Any]]:
        """
        Traditional rule-based position sizing.
        
        Args:
            available_balance: Available balance to allocate
            ranked_pools: List of ranked pool opportunities
            risk_profile: User's risk profile
            max_positions: Maximum number of positions to hold
            
        Returns:
            List of pools with position size recommendations
        """
        # Risk profile determines concentration
        if risk_profile == 'conservative':
            # Conservative: More diversification
            #  - Top pool: 30% of balance
            #  - 2nd pool: 25% of balance
            #  - 3rd pool: 20% of balance
            #  - 4th pool: 15% of balance
            #  - 5th pool: 10% of balance
            allocation_percentages = [30, 25, 20, 15, 10]
        elif risk_profile == 'aggressive':
            # Aggressive: More concentration
            #  - Top pool: 50% of balance
            #  - 2nd pool: 30% of balance
            #  - 3rd pool: 20% of balance
            allocation_percentages = [50, 30, 20, 0, 0]
        else:
            # Moderate: Balanced allocation
            #  - Top pool: 40% of balance
            #  - 2nd pool: 25% of balance
            #  - 3rd pool: 20% of balance
            #  - 4th pool: 15% of balance
            allocation_percentages = [40, 25, 20, 15, 0]
        
        # Limit to max_positions
        allocation_percentages = allocation_percentages[:max_positions]
        
        # Adjust if not 100%
        total_percentage = sum(allocation_percentages)
        if total_percentage != 100 and total_percentage > 0:
            allocation_percentages = [p * 100 / total_percentage for p in allocation_percentages]
        
        # Calculate position sizes
        recommendations = []
        
        # Only process as many pools as we have in ranked_pools
        pools_to_process = min(len(ranked_pools), len(allocation_percentages))
        
        for i in range(pools_to_process):
            pool = ranked_pools[i]
            percentage = allocation_percentages[i]
            size = available_balance * percentage / 100
            
            if size > 0:
                recommendations.append({
                    'pool': pool,
                    'size': size,
                    'percentage': percentage,
                    'reason': f"{percentage:.0f}% allocation based on risk profile",
                    'confidence': 0.8 - (i * 0.05)  # Confidence decreases slightly for lower-ranked pools
                })
        
        return recommendations

class InvestmentAgent:
    """Main agent responsible for autonomous investment decisions."""
    
    def __init__(self, 
                 user_id: int, 
                 risk_profile: str = 'moderate', 
                 investment_horizon: str = 'medium', 
                 automation_level: str = 'semi',
                 use_rl: bool = True):
        """
        Initialize the investment agent.
        
        Args:
            user_id: Telegram user ID
            risk_profile: User's risk profile
            investment_horizon: User's investment timeframe
            automation_level: Level of automation ('manual', 'semi', 'full')
            use_rl: Whether to use reinforcement learning
        """
        self.user_id = user_id
        self.risk_profile = risk_profile
        self.investment_horizon = investment_horizon
        self.automation_level = automation_level
        self.use_rl = use_rl
        self.models = self._initialize_models()
        
        # Initialize RL advisor for direct access if needed
        self.rl_advisor = RLInvestmentAdvisor(use_rl=use_rl) if use_rl else None
    
    def _initialize_models(self) -> Dict[str, Any]:
        """Initialize the AI models needed for decision making."""
        return {
            'pool_ranking': PoolRankingModel(use_rl=self.use_rl),
            'timing': InvestmentTimingModel(use_rl=self.use_rl),
            'position_sizing': PositionSizingModel(use_rl=self.use_rl)
        }
    
    async def get_recommendations(self, 
                               amount: Optional[float] = None,
                               token_preference: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Generate investment recommendations based on user profile.
        
        Args:
            amount: Optional investment amount
            token_preference: Optional list of preferred tokens
            
        Returns:
            Dictionary of recommendations
        """
        try:
            # Fetch latest pool data
            pools = await self._get_pool_data()
            
            # Get user's portfolio for context
            portfolio = await self._get_user_portfolio()
            
            # Check if we should use direct RL interface for enhanced recommendations
            if self.use_rl and self.rl_advisor:
                try:
                    logger.info(f"Using RL-based recommendations for user {self.user_id}")
                    
                    # Get user data in the format expected by the RL advisor
                    user_data = {
                        'balance': amount or portfolio.get('available_balance', 1000),
                        'positions': portfolio.get('positions', {}),
                        'risk_profile': self.risk_profile
                    }
                    
                    # Get RL-powered recommendations
                    rl_ranked_pools = await self.rl_advisor.get_investment_recommendations(
                        pools=pools,
                        amount=float(amount) if amount is not None else 1000.0
                    )
                    
                    # Get market timing from RL advisor
                    market_timing = await self.rl_advisor.get_market_timing()
                    
                    # If RL recommendations are available, use them directly
                    if rl_ranked_pools:
                        # Still get position sizing from the traditional model
                        balance_to_allocate = amount if amount is not None else portfolio.get('available_balance', 1000)
                        position_recommendations = await self.models['position_sizing'].calculate_position_sizes(
                            available_balance=balance_to_allocate,
                            ranked_pools=rl_ranked_pools,
                            user_data=portfolio,
                            risk_profile=self.risk_profile
                        )
                        
                        # Return early with RL-based recommendations
                        return {
                            'ranked_pools': rl_ranked_pools,
                            'timing': market_timing,
                            'position_sizing': position_recommendations,
                            'portfolio': portfolio,
                            'method': 'reinforcement_learning'
                        }
                except Exception as e:
                    logger.error(f"Error getting RL recommendations: {e}")
                    logger.info("Falling back to traditional recommendation method")
                    # Fall through to traditional method
            
            # Traditional recommendation method (fallback if RL fails or not enabled)
            # Rank pools according to user profile
            ranked_pools = await self.models['pool_ranking'].rank_pools(
                pools=pools,
                risk_profile=self.risk_profile,
                investment_horizon=self.investment_horizon,
                portfolio=portfolio,
                token_preference=token_preference
            )
            
            # Determine timing
            timing_assessment = {}
            if ranked_pools:
                timing_assessment = await self.models['timing'].should_enter_position(
                    ranked_pools[0],
                    {'balance': amount or 1000, 'positions': portfolio.get('positions', {})},
                    self.risk_profile
                )
            
            # Determine optimal position sizes
            balance_to_allocate = amount if amount is not None else portfolio.get('available_balance', 1000)
            position_recommendations = await self.models['position_sizing'].calculate_position_sizes(
                available_balance=balance_to_allocate,
                ranked_pools=ranked_pools,
                user_data=portfolio,
                risk_profile=self.risk_profile
            )
            
            # Compile recommendations
            recommendations = {
                'timestamp': time.time(),
                'risk_profile': self.risk_profile,
                'investment_horizon': self.investment_horizon,
                'amount': amount,
                'token_preference': token_preference,
                'ranked_pools': ranked_pools,
                'timing': timing_assessment,
                'position_recommendations': position_recommendations,
                'model_type': 'reinforcement_learning' if self.use_rl else 'rule_based'
            }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return {
                'error': str(e),
                'timestamp': time.time(),
                'risk_profile': self.risk_profile
            }
    
    async def should_exit_position(self, position_id: str) -> Dict[str, Any]:
        """
        Determine if a position should be exited.
        
        Args:
            position_id: ID of the position to evaluate
            
        Returns:
            Exit recommendation
        """
        try:
            # Get position data
            position = await self._get_position_data(position_id)
            if not position:
                return {
                    'error': 'Position not found',
                    'should_exit': False,
                    'confidence': 0
                }
            
            # Get pool data
            pool_data = position.get('pool_data', {})
            
            # Get user portfolio for context
            portfolio = await self._get_user_portfolio()
            
            # Determine if position should be exited
            exit_recommendation = await self.models['timing'].should_exit_position(
                pool_data,
                position,
                portfolio,
                self.risk_profile
            )
            
            return exit_recommendation
            
        except Exception as e:
            logger.error(f"Error evaluating exit for position {position_id}: {e}")
            return {
                'error': str(e),
                'should_exit': False,
                'confidence': 0
            }
    
    async def get_portfolio_rebalance(self) -> Dict[str, Any]:
        """
        Generate portfolio rebalancing recommendations.
        
        Returns:
            Rebalancing plan
        """
        try:
            # Get latest pool data
            pools = await self._get_pool_data()
            
            # Get user portfolio
            portfolio = await self._get_user_portfolio()
            
            # Get rebalance recommendations from RL advisor
            if self.use_rl and self.rl_advisor:
                rebalance = self.rl_advisor.get_rebalance_recommendations(pools, portfolio)
                
                # Add metadata
                rebalance['timestamp'] = time.time()
                rebalance['risk_profile'] = self.risk_profile
                rebalance['model_type'] = 'reinforcement_learning'
                
                return rebalance
            
            # Fallback to traditional rebalancing
            return self._traditional_rebalance(pools, portfolio)
            
        except Exception as e:
            logger.error(f"Error generating rebalance plan: {e}")
            return {
                'error': str(e),
                'timestamp': time.time()
            }
    
    async def _get_pool_data(self) -> List[Dict[str, Any]]:
        """
        Get the latest pool data.
        
        Returns:
            List of pool data dictionaries
        """
        try:
            # Import our pool data providers
            from api_mock_data import get_mock_pools
            from raydium_client import get_pools
            
            # Try to get data from real API first
            try:
                pools = get_pools()
                if pools and len(pools) > 0:
                    return pools
            except Exception as api_error:
                logger.warning(f"Error getting real pool data: {api_error}")
            
            # Fallback to mock data
            return get_mock_pools()
            
        except Exception as e:
            logger.error(f"Error getting pool data: {e}")
            return []
    
    async def _get_user_portfolio(self) -> Dict[str, Any]:
        """
        Get the user's current portfolio.
        
        Returns:
            Dictionary with portfolio data
        """
        try:
            # Check if we have a database connection
            try:
                from db_utils import get_user_positions
                positions = get_user_positions(self.user_id)
                
                if positions:
                    return {
                        'user_id': self.user_id,
                        'positions': positions,
                        'available_balance': 1000,  # Placeholder - should be fetched from wallet
                        'total_value': sum(positions.values()) + 1000,
                        'source': 'database'
                    }
            except Exception as db_error:
                logger.warning(f"Error getting user positions from database: {db_error}")
            
            # Fallback to empty portfolio
            return {
                'user_id': self.user_id,
                'positions': {},
                'available_balance': 1000,  # Default test balance
                'total_value': 1000,
                'source': 'default'
            }
            
        except Exception as e:
            logger.error(f"Error getting user portfolio: {e}")
            return {
                'user_id': self.user_id,
                'positions': {},
                'available_balance': 1000,
                'error': str(e)
            }
    
    async def _get_position_data(self, position_id: str) -> Dict[str, Any]:
        """
        Get data for a specific position.
        
        Args:
            position_id: ID of the position
            
        Returns:
            Position data dictionary
        """
        try:
            # Try to get real position data
            # This would be implemented for production use
            
            # Fallback to mock position
            pool_id = position_id.split(':')[0] if ':' in position_id else position_id
            
            # Get pool data for this position
            pools = await self._get_pool_data()
            pool_data = next((p for p in pools if p.get('id') == pool_id), None)
            
            if not pool_data:
                return None
            
            # Mock position data
            return {
                'id': position_id,
                'pool_id': pool_id,
                'amount': 100,
                'entry_time': time.time() - 86400,  # 1 day ago
                'entry_price0': pool_data.get('price0', 1.0) * 0.95,  # Slightly lower than current
                'entry_price1': pool_data.get('price1', 1.0) * 0.97,
                'entry_apr': pool_data.get('apr', 10) * 1.2,  # Slightly higher than current
                'pool_data': pool_data
            }
            
        except Exception as e:
            logger.error(f"Error getting position data for {position_id}: {e}")
            return None
    
    def _traditional_rebalance(self, 
                           pools: List[Dict[str, Any]], 
                           portfolio: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a traditional rule-based portfolio rebalance plan.
        
        Args:
            pools: List of pool data
            portfolio: User's portfolio data
            
        Returns:
            Rebalance plan
        """
        positions = portfolio.get('positions', {})
        balance = portfolio.get('available_balance', 0)
        
        rebalance_plan = {
            'increase': [],
            'decrease': [],
            'enter': [],
            'exit': [],
            'summary': "Traditional rebalancing based on APR changes and risk profile",
            'timestamp': time.time(),
            'risk_profile': self.risk_profile,
            'model_type': 'rule_based'
        }
        
        # Sort pools by APR
        sorted_pools = sorted(pools, key=lambda p: p.get('apr', 0), reverse=True)
        
        # Identify pools to exit (bottom 25% by APR)
        exit_threshold = sorted_pools[int(len(sorted_pools) * 0.75)]['apr'] if len(sorted_pools) > 4 else 10
        
        # Check current positions
        for pool_id, amount in positions.items():
            # Find pool data
            pool = next((p for p in pools if p.get('id') == pool_id), None)
            if not pool:
                continue
            
            apr = pool.get('apr', 0)
            
            if apr < exit_threshold:
                # Exit low-performing positions
                rebalance_plan['exit'].append({
                    'pool': pool,
                    'current_amount': amount,
                    'reason': f"Low APR of {apr:.1f}% compared to other opportunities"
                })
            elif apr > sorted_pools[int(len(sorted_pools) * 0.25)]['apr'] if len(sorted_pools) > 4 else 30:
                # Increase high-performing existing positions
                rebalance_plan['increase'].append({
                    'pool': pool,
                    'current_amount': amount,
                    'target_amount': amount * 1.5,  # Increase by 50%
                    'reason': f"High-performing position with {apr:.1f}% APR"
                })
        
        # Find new opportunities (top 10% by APR)
        top_pools = sorted_pools[:max(1, int(len(sorted_pools) * 0.1))]
        
        # Filter out pools we already have positions in
        new_opportunities = [p for p in top_pools if p.get('id') not in positions]
        
        # Suggest entering top new pools
        for pool in new_opportunities[:2]:  # Limit to 2 new positions
            apr = pool.get('apr', 0)
            if apr > 20:  # Only suggest high APR pools
                entry_amount = min(balance * 0.4, 400)  # 40% of balance or $400, whichever is lower
                
                if entry_amount > 50:  # Minimum investment threshold
                    rebalance_plan['enter'].append({
                        'pool': pool,
                        'suggested_amount': entry_amount,
                        'reason': f"High APR opportunity at {apr:.1f}%"
                    })
        
        return rebalance_plan

# For testing
if __name__ == "__main__":
    import asyncio
    
    async def test_agent():
        # Create agent
        agent = InvestmentAgent(user_id=12345, risk_profile='moderate', use_rl=True)
        
        # Get recommendations
        recommendations = await agent.get_recommendations(amount=1000)
        
        print("\n===== INVESTMENT RECOMMENDATIONS =====")
        print(f"Model type: {recommendations.get('model_type', 'unknown')}")
        print(f"Risk profile: {recommendations.get('risk_profile', 'unknown')}")
        
        # Print timing assessment
        timing = recommendations.get('timing', {})
        print("\n-- Timing Assessment --")
        print(f"Should enter: {timing.get('should_enter', False)}")
        print(f"Confidence: {timing.get('confidence', 0):.2f}")
        print(f"Explanation: {timing.get('explanation', 'None')}")
        
        # Print top pools
        print("\n-- Top Ranked Pools --")
        for i, pool in enumerate(recommendations.get('ranked_pools', [])[:3]):
            print(f"{i+1}. {pool.get('token0', '')}-{pool.get('token1', '')}: {pool.get('apr', 0):.1f}% APR")
            print(f"   Explanation: {pool.get('explanation', 'None')}")
        
        # Print position recommendations
        print("\n-- Position Recommendations --")
        for i, rec in enumerate(recommendations.get('position_recommendations', [])):
            pool = rec.get('pool', {})
            print(f"{i+1}. {pool.get('token0', '')}-{pool.get('token1', '')}: ${rec.get('size', 0):.2f} ({rec.get('percentage', 0):.1f}%)")
            print(f"   Reason: {rec.get('reason', 'None')}")
        
        # Get rebalance recommendations
        rebalance = await agent.get_portfolio_rebalance()
        
        print("\n===== PORTFOLIO REBALANCE =====")
        print(f"Model type: {rebalance.get('model_type', 'unknown')}")
        print(f"Summary: {rebalance.get('summary', 'None')}")
        
        # Print enter recommendations
        if rebalance.get('enter'):
            print("\n-- Enter New Positions --")
            for i, entry in enumerate(rebalance.get('enter', [])):
                pool = entry.get('pool', {})
                print(f"{i+1}. {pool.get('token0', '')}-{pool.get('token1', '')}: ${entry.get('suggested_amount', 0):.2f}")
                print(f"   Reason: {entry.get('reason', 'None')}")
        
        # Print exit recommendations
        if rebalance.get('exit'):
            print("\n-- Exit Positions --")
            for i, exit_rec in enumerate(rebalance.get('exit', [])):
                pool = exit_rec.get('pool', {})
                print(f"{i+1}. {pool.get('token0', '')}-{pool.get('token1', '')}: ${exit_rec.get('current_amount', 0):.2f}")
                print(f"   Reason: {exit_rec.get('reason', 'None')}")
    
    # Run the test
    asyncio.run(test_agent())