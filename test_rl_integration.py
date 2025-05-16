#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for the FiLot reinforcement learning integration.
This script demonstrates how to use the trained RL agent for investment decisions.
"""

import os
import logging
import json
import numpy as np
import torch
import asyncio
from typing import Dict, List, Any
import matplotlib.pyplot as plt
import argparse

# Import our RL modules
from rl_integration import RLInvestmentAdvisor
from investment_agent import InvestmentAgent

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

async def test_rl_advisor():
    """Test the RLInvestmentAdvisor directly with sample data."""
    
    # Create advisor (without loading trained models for testing)
    advisor = RLInvestmentAdvisor(use_rl=True)
    
    # Sample pool data
    pools = [
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
    
    # Sample user data
    user_data = {
        'balance': 1000,
        'positions': {
            'pool_2': 500,
            'pool_3': 200
        }
    }
    
    # Test pool recommendations
    print("\n===== POOL RECOMMENDATIONS =====")
    recommendations = advisor.get_pool_recommendations(pools, user_data, 'moderate', 2)
    for i, rec in enumerate(recommendations):
        print(f"{i+1}. {rec['token0']}-{rec['token1']}: APR {rec['apr']}%, TVL ${rec['tvl']}")
        print(f"   RL recommended: {rec.get('rl_recommended', False)}")
        print(f"   Confidence: {rec.get('confidence', 0):.2f}")
        if 'explanation' in rec:
            print(f"   Explanation: {rec['explanation']}")
    
    # Test exit recommendations
    print("\n===== EXIT RECOMMENDATIONS =====")
    exit_recs = advisor.get_exit_recommendations(pools, user_data)
    for i, rec in enumerate(exit_recs):
        print(f"{i+1}. {rec['token0']}-{rec['token1']}: {rec.get('exit_reason', 'No reason')}")
        print(f"   Impermanent loss: {rec.get('impermanent_loss', 0):.2%}")
        print(f"   RL recommended: {rec.get('rl_recommended', False)}")
    
    # Test rebalance recommendations
    print("\n===== REBALANCE RECOMMENDATIONS =====")
    rebalance = advisor.get_rebalance_recommendations(pools, user_data)
    
    print(f"Summary: {rebalance['summary']}")
    
    if rebalance['increase']:
        print("\n-- Increase positions --")
        for rec in rebalance['increase']:
            pool = rec['pool']
            print(f"• {pool['token0']}-{pool['token1']}: {rec['current_amount']} → {rec['target_amount']}")
            print(f"  Reason: {rec['reason']}")
    
    if rebalance['enter']:
        print("\n-- Enter new positions --")
        for rec in rebalance['enter']:
            pool = rec['pool']
            print(f"• {pool['token0']}-{pool['token1']}: ${rec['suggested_amount']:.2f}")
            print(f"  Reason: {rec['reason']}")
    
    if rebalance['exit']:
        print("\n-- Exit positions --")
        for rec in rebalance['exit']:
            pool = rec['pool']
            print(f"• {pool['token0']}-{pool['token1']}: ${rec['current_amount']:.2f}")
            print(f"  Reason: {rec['reason']}")
    
    return recommendations, exit_recs, rebalance

async def test_investment_agent():
    """Test the InvestmentAgent with the integrated RL advisor."""
    
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
        print(f"   RL recommended: {pool.get('rl_recommended', False)}")
    
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
    
    return recommendations, rebalance

async def compare_agent_performance():
    """Compare RL-based vs rule-based agent performance."""
    
    print("\n===== COMPARING AGENT PERFORMANCE =====")
    
    # Create agents with different approaches
    rl_agent = InvestmentAgent(user_id=1, risk_profile='moderate', use_rl=True)
    rule_agent = InvestmentAgent(user_id=2, risk_profile='moderate', use_rl=False)
    
    # Get recommendations from both
    rl_recs = await rl_agent.get_recommendations(amount=1000)
    rule_recs = await rule_agent.get_recommendations(amount=1000)
    
    # Compare top ranked pools
    rl_pools = rl_recs.get('ranked_pools', [])[:3]
    rule_pools = rule_recs.get('ranked_pools', [])[:3]
    
    print("\nTop Pool Rankings:")
    print(f"{'Rank':<5}{'RL Agent':<30}{'Rule Agent':<30}")
    print("-" * 65)
    
    for i in range(3):
        rl_pool = rl_pools[i] if i < len(rl_pools) else None
        rule_pool = rule_pools[i] if i < len(rule_pools) else None
        
        rl_name = f"{rl_pool.get('token0', '')}-{rl_pool.get('token1', '')}" if rl_pool else "N/A"
        rule_name = f"{rule_pool.get('token0', '')}-{rule_pool.get('token1', '')}" if rule_pool else "N/A"
        
        print(f"{i+1:<5}{rl_name:<30}{rule_name:<30}")
    
    # Compare position sizing
    rl_positions = rl_recs.get('position_recommendations', [])
    rule_positions = rule_recs.get('position_recommendations', [])
    
    print("\nPosition Sizing:")
    print(f"{'Pool':<20}{'RL Agent':<15}{'Rule Agent':<15}")
    print("-" * 50)
    
    # Combine all position pools
    all_pools = set()
    for pos in rl_positions:
        pool = pos.get('pool', {})
        all_pools.add(f"{pool.get('token0', '')}-{pool.get('token1', '')}")
    
    for pos in rule_positions:
        pool = pos.get('pool', {})
        all_pools.add(f"{pool.get('token0', '')}-{pool.get('token1', '')}")
    
    # Create lookup dictionaries
    rl_pos_dict = {}
    for pos in rl_positions:
        pool = pos.get('pool', {})
        pool_name = f"{pool.get('token0', '')}-{pool.get('token1', '')}"
        rl_pos_dict[pool_name] = pos.get('size', 0)
    
    rule_pos_dict = {}
    for pos in rule_positions:
        pool = pos.get('pool', {})
        pool_name = f"{pool.get('token0', '')}-{pool.get('token1', '')}"
        rule_pos_dict[pool_name] = pos.get('size', 0)
    
    # Display comparison
    for pool in sorted(all_pools):
        rl_size = rl_pos_dict.get(pool, 0)
        rule_size = rule_pos_dict.get(pool, 0)
        print(f"{pool:<20}${rl_size:<14.2f}${rule_size:<14.2f}")
    
    # Compare timing assessments
    rl_timing = rl_recs.get('timing', {})
    rule_timing = rule_recs.get('timing', {})
    
    print("\nTiming Assessment:")
    print(f"RL Agent: {rl_timing.get('should_enter', False)}, confidence: {rl_timing.get('confidence', 0):.2f}")
    print(f"Rule Agent: {rule_timing.get('should_enter', False)}, confidence: {rule_timing.get('confidence', 0):.2f}")
    
    return rl_recs, rule_recs

async def generate_performance_charts(num_days=30):
    """Generate simulated performance charts for RL vs rule-based agents."""
    
    print("\n===== GENERATING PERFORMANCE SIMULATION =====")
    
    # Initial portfolio values
    initial_value = 1000
    rl_portfolio = [initial_value]
    rule_portfolio = [initial_value]
    
    # Simulated daily returns (slightly better for RL over time)
    np.random.seed(42)  # For reproducibility
    
    # Mean returns slightly favor RL
    rl_mean_return = 0.005
    rule_mean_return = 0.003
    
    # Standard deviation (volatility) is the same
    return_std = 0.02
    
    # Generate random returns
    for day in range(num_days):
        # RL has slightly better returns
        rl_return = np.random.normal(rl_mean_return, return_std)
        rl_value = rl_portfolio[-1] * (1 + rl_return)
        rl_portfolio.append(rl_value)
        
        # Traditional strategy
        rule_return = np.random.normal(rule_mean_return, return_std)
        rule_value = rule_portfolio[-1] * (1 + rule_return)
        rule_portfolio.append(rule_value)
    
    # Calculate performance metrics
    rl_total_return = (rl_portfolio[-1] / initial_value) - 1
    rule_total_return = (rule_portfolio[-1] / initial_value) - 1
    
    rl_sharpe = np.mean(np.diff(rl_portfolio) / rl_portfolio[:-1]) / np.std(np.diff(rl_portfolio) / rl_portfolio[:-1]) * np.sqrt(252)
    rule_sharpe = np.mean(np.diff(rule_portfolio) / rule_portfolio[:-1]) / np.std(np.diff(rule_portfolio) / rule_portfolio[:-1]) * np.sqrt(252)
    
    # Plot results
    plt.figure(figsize=(10, 6))
    plt.plot(range(num_days + 1), rl_portfolio, label=f'RL Agent (Return: {rl_total_return:.2%})')
    plt.plot(range(num_days + 1), rule_portfolio, label=f'Rule-Based (Return: {rule_total_return:.2%})')
    plt.title('Simulated Performance: RL vs Rule-Based Investment Strategy')
    plt.xlabel('Days')
    plt.ylabel('Portfolio Value ($)')
    plt.legend()
    plt.grid(True)
    
    # Save figure
    os.makedirs('performance_charts', exist_ok=True)
    plt.savefig('performance_charts/performance_comparison.png')
    plt.close()
    
    print(f"RL Agent Total Return: {rl_total_return:.2%}, Sharpe Ratio: {rl_sharpe:.2f}")
    print(f"Rule-Based Agent Total Return: {rule_total_return:.2%}, Sharpe Ratio: {rule_sharpe:.2f}")
    print(f"Performance chart saved to performance_charts/performance_comparison.png")
    
    return rl_portfolio, rule_portfolio

def main():
    parser = argparse.ArgumentParser(description="Test reinforcement learning integration")
    parser.add_argument("--test-type", type=str, choices=["advisor", "agent", "compare", "charts", "all"], default="all",
                       help="Which tests to run")
    args = parser.parse_args()
    
    # Run the appropriate tests
    loop = asyncio.get_event_loop()
    
    if args.test_type == "advisor" or args.test_type == "all":
        loop.run_until_complete(test_rl_advisor())
    
    if args.test_type == "agent" or args.test_type == "all":
        loop.run_until_complete(test_investment_agent())
    
    if args.test_type == "compare" or args.test_type == "all":
        loop.run_until_complete(compare_agent_performance())
    
    if args.test_type == "charts" or args.test_type == "all":
        loop.run_until_complete(generate_performance_charts())

if __name__ == "__main__":
    main()