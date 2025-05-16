"""
Integration module connecting the RL investment system with the bot
"""

import logging
import os
import numpy as np
from typing import Dict, List, Any, Optional
import asyncio
import random
import torch

# Configure logging
logger = logging.getLogger(__name__)

# Ensure RL model directory exists
os.makedirs('models', exist_ok=True)
MODEL_PATH = 'models/investment_rl_model.pth'

class RLInvestmentAdvisor:
    """
    Reinforcement Learning-based investment advisor that provides optimized
    liquidity pool investment recommendations.
    """
    
    def __init__(self, risk_profile: str = 'moderate'):
        """
        Initialize the RL investment advisor.
        
        Args:
            risk_profile: User's risk profile ('conservative', 'moderate', 'aggressive')
        """
        self.risk_profile = risk_profile
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Risk profile mapping to RL reward weights
        self.risk_weights = {
            'conservative': {'return': 0.5, 'risk': 0.9, 'volatility': 0.8},
            'moderate': {'return': 0.7, 'risk': 0.6, 'volatility': 0.6},
            'aggressive': {'return': 0.9, 'risk': 0.3, 'volatility': 0.4}
        }
        
        # Initialize a simulated model (we'll skip loading since we don't have a trained model yet)
        self._initialize_simulated_model()
    
    def load_model(self) -> bool:
        """
        Load the pre-trained RL model.
        
        Returns:
            bool: True if loading was successful, False otherwise
        """
        try:
            if os.path.exists(MODEL_PATH):
                # Load the model architecture
                from rl_agent import DQNAgent
                
                # For demonstration, we'll create a simplified model
                # In production, we would load weights from a file
                input_dim = 8  # Features like APR, TVL, volume, etc.
                output_dim = 1  # Investment score
                
                self.model = DQNAgent(input_dim, output_dim)
                self.model.to(self.device)
                
                # Load model weights if they exist
                try:
                    self.model.load_state_dict(torch.load(MODEL_PATH, map_location=self.device))
                    self.model.eval()  # Set to evaluation mode
                    logger.info(f"Successfully loaded RL model from {MODEL_PATH}")
                    return True
                except Exception as e:
                    logger.warning(f"Could not load model weights: {e}")
                    # Continue with initialized model
            
            # If no model exists, we'll use a simulated one
            logger.info("No pre-trained model found, using simulated RL model")
            self._initialize_simulated_model()
            return False
            
        except Exception as e:
            logger.error(f"Error loading RL model: {e}")
            self._initialize_simulated_model()
            return False
    
    def _initialize_simulated_model(self):
        """
        Initialize a simulated model for demonstration purposes.
        This is used when a trained model is not available.
        """
        class SimulatedRLModel:
            def __init__(self, risk_weights):
                self.risk_weights = risk_weights
            
            def predict(self, features):
                # Simulate RL-based scoring with weighted random values
                # that are biased by the risk profile
                apr_weight = 0.4
                tvl_weight = 0.3
                volume_weight = 0.2
                impermanent_loss_weight = 0.1
                
                # Apply risk profile adjustments
                apr_weight *= self.risk_weights.get('return', 0.7)
                tvl_weight *= self.risk_weights.get('risk', 0.6)
                volume_weight *= self.risk_weights.get('volatility', 0.6)
                
                # Extract features
                apr = features.get('apr', 0)
                tvl = features.get('tvl', 0)
                volume = features.get('volume', 0)
                impermanent_loss_risk = features.get('impermanent_loss_risk', 0)
                
                # Normalize values
                normalized_apr = min(apr / 100, 1.0)  # Cap at 100% APR
                normalized_tvl = min(tvl / 1000000, 1.0)  # Cap at $1M TVL
                normalized_volume = min(volume / 1000000, 1.0)  # Cap at $1M volume
                
                # Compute score
                score = (
                    apr_weight * normalized_apr +
                    tvl_weight * normalized_tvl +
                    volume_weight * normalized_volume -
                    impermanent_loss_weight * impermanent_loss_risk
                )
                
                # Add some randomness for diversity in recommendations
                randomness = random.uniform(0.8, 1.2)
                score *= randomness
                
                return max(0, min(1, score))  # Clamp between 0 and 1
                
        # Create the simulated model
        self.model = SimulatedRLModel(self.risk_weights.get(self.risk_profile, 
                                                          self.risk_weights['moderate']))
    
    async def get_investment_recommendations(self, pools: List[Dict[str, Any]], 
                                           amount: float = 1000.0) -> List[Dict[str, Any]]:
        """
        Generate RL-based investment recommendations from available pools.
        
        Args:
            pools: List of pool data dictionaries
            amount: Investment amount
            
        Returns:
            Ranked list of pool recommendations with explanations
        """
        if not pools:
            logger.warning("No pools provided for RL recommendations")
            return []
        
        # Prepare results list
        results = []
        
        try:
            for pool in pools:
                # Extract core features
                features = {
                    'apr': pool.get('apr', 0),
                    'tvl': pool.get('tvl', 0),
                    'volume': pool.get('volume', 0),
                    'impermanent_loss_risk': self._calculate_impermanent_loss_risk(pool),
                    'price_correlation': pool.get('price_correlation', 0.5),
                    'liquidity_depth': pool.get('liquidity_depth', 0.5),
                    'token0_volatility': pool.get('token0_volatility', 0.5),
                    'token1_volatility': pool.get('token1_volatility', 0.5)
                }
                
                # Get RL-based investment score
                if hasattr(self.model, 'predict'):
                    # Use simulated model
                    confidence = self.model.predict(features)
                else:
                    # Use PyTorch model
                    feature_tensor = self._prepare_features_tensor(features)
                    with torch.no_grad():
                        output = self.model(feature_tensor)
                        confidence = torch.sigmoid(output).item()
                
                # Add score and explanation to pool data
                recommendation = pool.copy()
                recommendation['confidence'] = float(confidence)
                recommendation['explanation'] = self._generate_explanation(
                    features, confidence, self.risk_profile
                )
                
                # Add to results
                results.append(recommendation)
            
            # Sort by confidence (descending)
            results.sort(key=lambda x: x.get('confidence', 0), reverse=True)
            
            return results
            
        except Exception as e:
            logger.error(f"Error generating RL recommendations: {e}")
            return []
    
    def _calculate_impermanent_loss_risk(self, pool: Dict[str, Any]) -> float:
        """
        Calculate impermanent loss risk based on historical price data.
        
        Args:
            pool: Pool data dictionary
            
        Returns:
            Risk score between 0 and 1
        """
        # In a real implementation, this would use historical price data and volatility
        # For demonstration, we'll use a simplified approach
        
        # If the pool has volatility data, use it
        if 'token0_volatility' in pool and 'token1_volatility' in pool:
            token0_volatility = pool['token0_volatility']
            token1_volatility = pool['token1_volatility']
            correlation = pool.get('price_correlation', 0.5)
            
            # Higher volatility and lower correlation = higher IL risk
            # IL risk formula: sqrt(token0_vol^2 + token1_vol^2 - 2*corr*token0_vol*token1_vol)
            il_risk = (token0_volatility**2 + token1_volatility**2 - 
                      2 * correlation * token0_volatility * token1_volatility)**0.5
            
            # Normalize to 0-1 range
            return min(1.0, max(0.0, il_risk / 2.0))
        
        # Fallback: estimate based on token symbols
        token0 = pool.get('token0', '').upper()
        token1 = pool.get('token1', '').upper()
        
        # Stablecoin pairs have lower IL risk
        stablecoins = ['USDC', 'USDT', 'DAI', 'BUSD', 'UST']
        
        if token0 in stablecoins and token1 in stablecoins:
            return 0.1  # Very low IL risk for stablecoin pairs
        elif token0 in stablecoins or token1 in stablecoins:
            return 0.4  # Moderate IL risk for one stablecoin
        else:
            return 0.7  # Higher IL risk for non-stablecoin pairs
    
    def _prepare_features_tensor(self, features: Dict[str, Any]) -> torch.Tensor:
        """
        Convert features dictionary to tensor for model input.
        
        Args:
            features: Pool features dictionary
            
        Returns:
            PyTorch tensor
        """
        # Extract features in a consistent order
        feature_list = [
            features.get('apr', 0) / 100,  # Normalize APR
            features.get('tvl', 0) / 1000000,  # Normalize TVL
            features.get('volume', 0) / 1000000,  # Normalize volume
            features.get('impermanent_loss_risk', 0),
            features.get('price_correlation', 0.5),
            features.get('liquidity_depth', 0.5),
            features.get('token0_volatility', 0.5),
            features.get('token1_volatility', 0.5)
        ]
        
        # Convert to tensor
        tensor = torch.tensor(feature_list, dtype=torch.float32).to(self.device)
        return tensor.unsqueeze(0)  # Add batch dimension
    
    def _generate_explanation(self, features: Dict[str, Any], confidence: float, 
                             risk_profile: str) -> str:
        """
        Generate a human-readable explanation for the recommendation.
        
        Args:
            features: Pool features
            confidence: Model confidence score
            risk_profile: User's risk profile
            
        Returns:
            Explanation string
        """
        # Base explanation on the most prominent factors
        apr = features.get('apr', 0)
        tvl = features.get('tvl', 0)
        il_risk = features.get('impermanent_loss_risk', 0)
        
        # Different explanations based on confidence level
        if confidence > 0.8:
            if risk_profile == 'aggressive':
                return f"Optimal high-return opportunity with balanced risk"
            elif risk_profile == 'conservative':
                return f"Strong stability metrics with reasonable returns"
            else:
                return f"Excellent balance of yield and security factors"
        elif confidence > 0.6:
            if apr > 30:
                return f"Good yield metrics with acceptable risk profile"
            elif tvl > 500000:
                return f"Solid liquidity with reliable performance history"
            else:
                return f"Favorable risk-adjusted return potential"
        elif confidence > 0.4:
            return f"Moderate opportunity with reasonable risk-reward"
        else:
            return f"Basic option that meets minimum criteria"

    async def get_market_timing(self) -> Dict[str, Any]:
        """
        Provide recommendations on market timing based on current conditions.
        
        Returns:
            Dictionary with market timing advice
        """
        # In a real implementation, this would analyze market conditions
        # For demonstration, we'll simulate timing recommendations
        
        # Simulate market conditions assessment
        try:
            # Generate random values for simulation
            # In production, these would come from actual market indicators
            market_indicators = {
                'trend': random.uniform(-1.0, 1.0),  # -1 to 1 (bearish to bullish)
                'volatility': random.uniform(0.1, 0.9),  # 0 to 1 (low to high)
                'sentiment': random.uniform(-0.8, 0.8),  # -1 to 1 (negative to positive)
                'liquidity': random.uniform(0.3, 0.9)  # 0 to 1 (tight to abundant)
            }
            
            # Apply risk profile adjustments
            risk_weights = self.risk_weights.get(self.risk_profile, self.risk_weights['moderate'])
            
            # Conservative investors need more positive signals to enter
            # Aggressive investors are willing to enter with less positive signals
            entry_threshold = 0.6 - ((risk_weights.get('return', 0.7) - 0.5) * 0.5)
            
            # Calculate entry score
            entry_score = (
                market_indicators['trend'] * 0.4 +
                market_indicators['sentiment'] * 0.3 +
                market_indicators['liquidity'] * 0.3 -
                market_indicators['volatility'] * (1.0 - risk_weights.get('volatility', 0.6))
            )
            
            # Normalize to 0-1 range
            entry_score = (entry_score + 1) / 2
            
            # Determine if entry is favorable
            should_enter = entry_score > entry_threshold
            
            # Calculate confidence level (how strong the signal is)
            confidence = abs(entry_score - 0.5) * 2  # 0 to 1 scale
            
            return {
                'should_enter': should_enter,
                'confidence': confidence,
                'market_conditions': {
                    'trend': 'bullish' if market_indicators['trend'] > 0 else 'bearish',
                    'volatility': 'high' if market_indicators['volatility'] > 0.6 else 'moderate',
                    'liquidity': 'good' if market_indicators['liquidity'] > 0.6 else 'moderate'
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating market timing advice: {e}")
            return {
                'should_enter': True,  # Default to positive
                'confidence': 0.5,
                'market_conditions': {
                    'trend': 'neutral',
                    'volatility': 'moderate',
                    'liquidity': 'moderate'
                }
            }

# Helper function to get the singleton instance
_rl_advisor_instance = None

def get_rl_advisor(risk_profile: str = 'moderate') -> RLInvestmentAdvisor:
    """
    Get or create the RL advisor instance.
    
    Args:
        risk_profile: User's risk profile
        
    Returns:
        RLInvestmentAdvisor instance
    """
    global _rl_advisor_instance
    
    if _rl_advisor_instance is None:
        _rl_advisor_instance = RLInvestmentAdvisor(risk_profile)
    elif _rl_advisor_instance.risk_profile != risk_profile:
        # Update risk profile if changed
        _rl_advisor_instance.risk_profile = risk_profile
        _rl_advisor_instance.model.risk_weights = _rl_advisor_instance.risk_weights.get(
            risk_profile, _rl_advisor_instance.risk_weights['moderate']
        )
    
    return _rl_advisor_instance