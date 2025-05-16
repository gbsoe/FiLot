#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Training script for Reinforcement Learning agents on liquidity pool investments.
This module trains DQN or Actor-Critic agents using the RLPoolEnv environment.
"""

import os
import numpy as np
import torch
import matplotlib.pyplot as plt
from tqdm import tqdm
import logging
import argparse
import json
from typing import Dict, List, Tuple, Any, Optional
import time

# Import our custom RL modules
from rl_environment import RLPoolEnv
from rl_agent import DQNAgent, ActorCriticAgent

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

def train_dqn_agent(env: RLPoolEnv, 
                    agent: DQNAgent, 
                    num_episodes: int, 
                    save_dir: str,
                    eval_freq: int = 10,
                    render_freq: int = 100) -> Dict[str, List[float]]:
    """
    Train a DQN agent on the given environment.
    
    Args:
        env: The RL environment
        agent: The DQN agent to train
        num_episodes: Number of episodes to train for
        save_dir: Directory to save agent and results
        eval_freq: Frequency to evaluate the agent (in episodes)
        render_freq: Frequency to render the environment (in episodes)
        
    Returns:
        Dictionary of training metrics
    """
    # Create save directory if it doesn't exist
    os.makedirs(save_dir, exist_ok=True)
    
    # Training metrics
    metrics = {
        'episode_rewards': [],
        'episode_lengths': [],
        'portfolio_values': [],
        'losses': [],
        'eval_returns': []
    }
    
    # Training loop
    for episode in tqdm(range(num_episodes), desc="Training"):
        # Reset environment
        state = env.reset()
        episode_reward = 0
        episode_losses = []
        done = False
        step = 0
        
        # Episode loop
        while not done:
            # Select action
            action = agent.select_action(state)
            
            # Execute action in environment
            next_state, reward, done, info = env.step(action)
            
            # Store experience in replay buffer
            agent.replay_buffer.add(state, action, reward, next_state, done)
            
            # Update agent
            if len(agent.replay_buffer) > agent.batch_size:
                loss = agent.update()
                if loss is not None:
                    episode_losses.append(loss)
            
            # Update state and metrics
            state = next_state
            episode_reward += reward
            step += 1
            
            # Render occasionally
            if episode % render_freq == 0 and done:
                env.render()
        
        # End of episode updates
        agent.episode_completed()
        
        # Record metrics
        metrics['episode_rewards'].append(episode_reward)
        metrics['episode_lengths'].append(step)
        metrics['portfolio_values'].append(env.portfolio_history[-1] if env.portfolio_history else env.initial_balance)
        metrics['losses'].append(np.mean(episode_losses) if episode_losses else 0)
        
        # Log progress
        logger.info(f"Episode {episode+1}: Reward = {episode_reward:.2f}, "
                   f"Portfolio Value = {env.portfolio_history[-1] if env.portfolio_history else env.initial_balance:.2f}, "
                   f"Epsilon = {agent.epsilon:.4f}")
        
        # Evaluate occasionally
        if (episode + 1) % eval_freq == 0:
            eval_return = evaluate_agent(env, agent)
            metrics['eval_returns'].append(eval_return)
            
            # Save agent
            agent.save(os.path.join(save_dir, f"checkpoint_ep{episode+1}"))
            
            # Save metrics
            with open(os.path.join(save_dir, 'metrics.json'), 'w') as f:
                json.dump(metrics, f)
    
    # Save final agent
    agent.save(os.path.join(save_dir, "final_model"))
    
    # Plot and save training curves
    plot_training_curves(metrics, save_dir)
    
    return metrics

def train_actor_critic_agent(env: RLPoolEnv, 
                            agent: ActorCriticAgent, 
                            num_episodes: int, 
                            save_dir: str,
                            eval_freq: int = 10,
                            render_freq: int = 100) -> Dict[str, List[float]]:
    """
    Train an Actor-Critic agent on the given environment.
    
    Args:
        env: The RL environment
        agent: The Actor-Critic agent to train
        num_episodes: Number of episodes to train for
        save_dir: Directory to save agent and results
        eval_freq: Frequency to evaluate the agent (in episodes)
        render_freq: Frequency to render the environment (in episodes)
        
    Returns:
        Dictionary of training metrics
    """
    # Create save directory if it doesn't exist
    os.makedirs(save_dir, exist_ok=True)
    
    # Training metrics
    metrics = {
        'episode_rewards': [],
        'episode_lengths': [],
        'portfolio_values': [],
        'actor_losses': [],
        'critic_losses': [],
        'eval_returns': []
    }
    
    # Training loop
    for episode in tqdm(range(num_episodes), desc="Training"):
        # Reset environment
        state = env.reset()
        episode_reward = 0
        episode_actor_losses = []
        episode_critic_losses = []
        done = False
        step = 0
        
        # Episode loop
        while not done:
            # Select action
            action = agent.select_action(state)
            
            # Execute action in environment
            next_state, reward, done, info = env.step(action)
            
            # Store experience in replay buffer
            agent.replay_buffer.add(state, action, reward, next_state, done)
            
            # Update agent
            if len(agent.replay_buffer) > agent.batch_size:
                update_result = agent.update()
                if update_result is not None:
                    actor_loss, critic_loss = update_result
                    episode_actor_losses.append(actor_loss)
                    episode_critic_losses.append(critic_loss)
            
            # Update state and metrics
            state = next_state
            episode_reward += reward
            step += 1
            
            # Render occasionally
            if episode % render_freq == 0 and done:
                env.render()
        
        # End of episode updates
        agent.episode_completed()
        
        # Record metrics
        metrics['episode_rewards'].append(episode_reward)
        metrics['episode_lengths'].append(step)
        metrics['portfolio_values'].append(env.portfolio_history[-1] if env.portfolio_history else env.initial_balance)
        metrics['actor_losses'].append(np.mean(episode_actor_losses) if episode_actor_losses else 0)
        metrics['critic_losses'].append(np.mean(episode_critic_losses) if episode_critic_losses else 0)
        
        # Log progress
        logger.info(f"Episode {episode+1}: Reward = {episode_reward:.2f}, "
                   f"Portfolio Value = {env.portfolio_history[-1] if env.portfolio_history else env.initial_balance:.2f}")
        
        # Evaluate occasionally
        if (episode + 1) % eval_freq == 0:
            eval_return = evaluate_agent(env, agent)
            metrics['eval_returns'].append(eval_return)
            
            # Save agent
            agent.save(os.path.join(save_dir, f"checkpoint_ep{episode+1}"))
            
            # Save metrics
            with open(os.path.join(save_dir, 'metrics.json'), 'w') as f:
                json.dump(metrics, f)
    
    # Save final agent
    agent.save(os.path.join(save_dir, "final_model"))
    
    # Plot and save training curves
    plot_training_curves(metrics, save_dir, agent_type='actor_critic')
    
    return metrics

def evaluate_agent(env: RLPoolEnv, agent: Any, num_episodes: int = 5) -> float:
    """
    Evaluate an agent on the environment without training.
    
    Args:
        env: The RL environment
        agent: The agent to evaluate
        num_episodes: Number of episodes to evaluate for
        
    Returns:
        Average episode return
    """
    returns = []
    
    for _ in range(num_episodes):
        state = env.reset()
        episode_reward = 0
        done = False
        
        while not done:
            # Select action (no exploration)
            action = agent.select_action(state, evaluation=True)
            
            # Execute action in environment
            next_state, reward, done, _ = env.step(action)
            
            # Update state and reward
            state = next_state
            episode_reward += reward
        
        returns.append(episode_reward)
    
    # Return average episode reward
    return np.mean(returns)

def backtest_agent(env: RLPoolEnv, agent: Any, rule_based: bool = False) -> Dict[str, Any]:
    """
    Backtest an agent on historical data and calculate performance metrics.
    
    Args:
        env: The RL environment
        agent: The agent to backtest
        rule_based: Whether to use rule-based strategy instead of RL
        
    Returns:
        Dictionary of performance metrics
    """
    # Reset environment
    state = env.reset()
    done = False
    
    # Tracking variables
    portfolio_values = [env.initial_balance]
    returns = []
    prev_value = env.initial_balance
    actions_taken = []
    
    # Episode loop
    while not done:
        if rule_based:
            # Rule-based strategy (buy high APR pools, sell low APR ones)
            action = _rule_based_action(state, env)
        else:
            # RL agent action
            action = agent.select_action(state, evaluation=True)
        
        # Execute action in environment
        next_state, reward, done, info = env.step(action)
        
        # Update state
        state = next_state
        
        # Record portfolio value
        portfolio_value = env.balance + sum(env.positions.values())
        portfolio_values.append(portfolio_value)
        
        # Calculate daily return
        daily_return = (portfolio_value / prev_value) - 1 if prev_value > 0 else 0
        returns.append(daily_return)
        prev_value = portfolio_value
        
        # Record action
        actions_taken.append(info['action_taken'])
    
    # Calculate performance metrics
    total_return = (portfolio_values[-1] / env.initial_balance) - 1
    
    # Calculate Sharpe ratio (assuming risk-free rate = 0)
    daily_returns = np.array(returns)
    sharpe_ratio = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252) if np.std(daily_returns) > 0 else 0
    
    # Calculate maximum drawdown
    max_drawdown = _calculate_max_drawdown(portfolio_values)
    
    # Calculate win rate (percentage of positive daily returns)
    win_rate = np.sum(daily_returns > 0) / len(daily_returns) if len(daily_returns) > 0 else 0
    
    # Results dictionary
    results = {
        'portfolio_values': portfolio_values,
        'daily_returns': returns,
        'total_return': total_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'actions': actions_taken
    }
    
    return results

def _rule_based_action(state: np.ndarray, env: RLPoolEnv) -> int:
    """
    Generate a rule-based action for comparison.
    This simple strategy buys pools with high APR and sells those with low APR.
    
    Args:
        state: Current state vector
        env: Environment for context
        
    Returns:
        Action index
    """
    # Get current pool data
    pool_data = {}
    for i, pool_id in enumerate(env.pool_ids):
        current_data = env._get_pool_data(pool_id)
        if current_data:
            pool_data[pool_id] = current_data
    
    # Determine best action
    if not pool_data:
        return 0  # Do nothing if no data
    
    # Sort pools by APR
    sorted_pools = sorted(pool_data.items(), key=lambda x: x[1].get('apr', 0), reverse=True)
    
    # Get positions
    positions = env.positions
    
    # Find highest APR pool with no position
    for pool_id, data in sorted_pools:
        if positions.get(pool_id, 0) == 0 and env.balance > 0 and data.get('apr', 0) > 20:
            # Buy this pool
            pool_idx = env.pool_ids.index(pool_id)
            action = pool_idx + 1  # +1 because action 0 is "do nothing"
            return action
    
    # Find lowest APR pool with a position
    for pool_id, data in reversed(sorted_pools):
        if positions.get(pool_id, 0) > 0 and data.get('apr', 0) < 10:
            # Sell this pool
            pool_idx = env.pool_ids.index(pool_id)
            action = pool_idx + env.num_pools + 1  # Offset for sell actions
            return action
    
    # Default: do nothing
    return 0

def _calculate_max_drawdown(portfolio_values: List[float]) -> float:
    """
    Calculate the maximum drawdown from a list of portfolio values.
    
    Args:
        portfolio_values: List of portfolio values over time
        
    Returns:
        Maximum drawdown as a percentage (0 to 1)
    """
    # Convert to numpy array
    values = np.array(portfolio_values)
    
    # Calculate running maximum
    running_max = np.maximum.accumulate(values)
    
    # Calculate drawdowns
    drawdowns = (running_max - values) / running_max
    
    # Return maximum drawdown
    return np.max(drawdowns) if len(drawdowns) > 0 else 0

def plot_training_curves(metrics: Dict[str, List[float]], save_dir: str, agent_type: str = 'dqn'):
    """
    Plot and save training curves.
    
    Args:
        metrics: Dictionary of training metrics
        save_dir: Directory to save plots
        agent_type: Type of agent ('dqn' or 'actor_critic')
    """
    # Create figure
    plt.figure(figsize=(15, 12))
    
    # Plot episode rewards
    plt.subplot(2, 2, 1)
    plt.plot(metrics['episode_rewards'])
    plt.title('Episode Rewards')
    plt.xlabel('Episode')
    plt.ylabel('Total Reward')
    plt.grid(True)
    
    # Plot portfolio values
    plt.subplot(2, 2, 2)
    plt.plot(metrics['portfolio_values'])
    plt.title('Final Portfolio Value')
    plt.xlabel('Episode')
    plt.ylabel('Value ($)')
    plt.grid(True)
    
    # Plot losses
    plt.subplot(2, 2, 3)
    if agent_type == 'dqn':
        plt.plot(metrics['losses'])
        plt.title('Training Loss')
        plt.xlabel('Episode')
        plt.ylabel('Loss')
    else:
        plt.plot(metrics['actor_losses'], label='Actor')
        plt.plot(metrics['critic_losses'], label='Critic')
        plt.title('Training Losses')
        plt.xlabel('Episode')
        plt.ylabel('Loss')
        plt.legend()
    plt.grid(True)
    
    # Plot evaluation returns
    plt.subplot(2, 2, 4)
    plt.plot(range(0, len(metrics['eval_returns']) * 10, 10), metrics['eval_returns'])
    plt.title('Evaluation Returns')
    plt.xlabel('Episode')
    plt.ylabel('Average Return')
    plt.grid(True)
    
    # Save figure
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, 'training_curves.png'))
    plt.close()

def compare_models(env: RLPoolEnv, rl_agent: Any, save_dir: str):
    """
    Compare RL agent performance against rule-based baseline.
    
    Args:
        env: The RL environment
        rl_agent: The trained RL agent
        save_dir: Directory to save results
    """
    # Run backtest with RL agent
    logger.info("Backtesting RL agent...")
    rl_results = backtest_agent(env, rl_agent)
    
    # Run backtest with rule-based strategy
    logger.info("Backtesting rule-based strategy...")
    rule_results = backtest_agent(env, None, rule_based=True)
    
    # Plot comparison
    plt.figure(figsize=(15, 12))
    
    # Plot portfolio values
    plt.subplot(2, 2, 1)
    plt.plot(rl_results['portfolio_values'], label='RL Agent')
    plt.plot(rule_results['portfolio_values'], label='Rule-Based')
    plt.title('Portfolio Value Comparison')
    plt.xlabel('Day')
    plt.ylabel('Value ($)')
    plt.legend()
    plt.grid(True)
    
    # Plot cumulative returns
    plt.subplot(2, 2, 2)
    rl_cum_returns = np.cumprod(np.array(rl_results['daily_returns']) + 1) - 1
    rule_cum_returns = np.cumprod(np.array(rule_results['daily_returns']) + 1) - 1
    plt.plot(rl_cum_returns, label='RL Agent')
    plt.plot(rule_cum_returns, label='Rule-Based')
    plt.title('Cumulative Returns')
    plt.xlabel('Day')
    plt.ylabel('Return (%)')
    plt.legend()
    plt.grid(True)
    
    # Plot action distribution
    plt.subplot(2, 2, 3)
    rl_actions = rl_results['actions']
    rule_actions = rule_results['actions']
    
    rl_action_counts = {
        'buy': rl_actions.count('buy'),
        'sell': rl_actions.count('sell'),
        'hold': rl_actions.count('hold'),
        'none': rl_actions.count('none')
    }
    rule_action_counts = {
        'buy': rule_actions.count('buy'),
        'sell': rule_actions.count('sell'),
        'hold': rule_actions.count('hold'),
        'none': rule_actions.count('none')
    }
    
    # Bar positions
    x = np.arange(4)
    width = 0.35
    
    plt.bar(x - width/2, rl_action_counts.values(), width, label='RL Agent')
    plt.bar(x + width/2, rule_action_counts.values(), width, label='Rule-Based')
    plt.title('Action Distribution')
    plt.xticks(x, rl_action_counts.keys())
    plt.ylabel('Count')
    plt.legend()
    
    # Plot performance metrics
    plt.subplot(2, 2, 4)
    metrics = ['total_return', 'sharpe_ratio', 'max_drawdown', 'win_rate']
    rl_metrics = [rl_results[m] for m in metrics]
    rule_metrics = [rule_results[m] for m in metrics]
    
    x = np.arange(len(metrics))
    plt.bar(x - width/2, rl_metrics, width, label='RL Agent')
    plt.bar(x + width/2, rule_metrics, width, label='Rule-Based')
    plt.title('Performance Metrics')
    plt.xticks(x, metrics, rotation=45)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, 'comparison.png'))
    plt.close()
    
    # Save results as JSON
    comparison = {
        'rl_agent': rl_results,
        'rule_based': rule_results
    }
    
    with open(os.path.join(save_dir, 'comparison_results.json'), 'w') as f:
        # Convert numpy arrays to lists for JSON serialization
        comparison_serializable = {
            'rl_agent': {k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in rl_results.items()},
            'rule_based': {k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in rule_results.items()}
        }
        json.dump(comparison_serializable, f)
    
    # Log comparison
    logger.info("\n----- Performance Comparison -----")
    logger.info(f"Total Return: RL = {rl_results['total_return']:.2%}, Rule = {rule_results['total_return']:.2%}")
    logger.info(f"Sharpe Ratio: RL = {rl_results['sharpe_ratio']:.2f}, Rule = {rule_results['sharpe_ratio']:.2f}")
    logger.info(f"Max Drawdown: RL = {rl_results['max_drawdown']:.2%}, Rule = {rule_results['max_drawdown']:.2%}")
    logger.info(f"Win Rate: RL = {rl_results['win_rate']:.2%}, Rule = {rule_results['win_rate']:.2%}")

def main():
    """Main function to set up and train the RL agents."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Train RL agents for liquidity pool investments")
    parser.add_argument("--agent", type=str, choices=["dqn", "actor_critic"], default="dqn",
                       help="Type of agent to train")
    parser.add_argument("--episodes", type=int, default=500,
                       help="Number of episodes to train for")
    parser.add_argument("--save_dir", type=str, default="./rl_models",
                       help="Directory to save models and results")
    parser.add_argument("--eval_freq", type=int, default=10,
                       help="Frequency to evaluate the agent (in episodes)")
    parser.add_argument("--render_freq", type=int, default=100,
                       help="Frequency to render the environment (in episodes)")
    parser.add_argument("--seed", type=int, default=42,
                       help="Random seed for reproducibility")
    args = parser.parse_args()
    
    # Set random seeds
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    random.seed(args.seed)
    
    # Create save directory
    os.makedirs(args.save_dir, exist_ok=True)
    
    # Save arguments
    with open(os.path.join(args.save_dir, 'args.json'), 'w') as f:
        json.dump(vars(args), f)
    
    # Create environment
    env = RLPoolEnv()
    
    # Get state and action dimensions
    state_dim = env.observation_space.shape[0]
    action_dim = env.action_space.n
    
    # Create agent
    if args.agent == "dqn":
        agent = DQNAgent(state_dim, action_dim)
        logger.info(f"Created DQN agent with state_dim={state_dim}, action_dim={action_dim}")
        
        # Train agent
        logger.info(f"Training DQN agent for {args.episodes} episodes...")
        metrics = train_dqn_agent(env, agent, args.episodes, args.save_dir, args.eval_freq, args.render_freq)
    else:
        agent = ActorCriticAgent(state_dim, action_dim)
        logger.info(f"Created Actor-Critic agent with state_dim={state_dim}, action_dim={action_dim}")
        
        # Train agent
        logger.info(f"Training Actor-Critic agent for {args.episodes} episodes...")
        metrics = train_actor_critic_agent(env, agent, args.episodes, args.save_dir, args.eval_freq, args.render_freq)
    
    # Compare against rule-based baseline
    logger.info("Comparing RL agent against rule-based baseline...")
    compare_models(env, agent, args.save_dir)
    
    logger.info(f"Training and evaluation completed. Results saved to {args.save_dir}")

if __name__ == "__main__":
    main()