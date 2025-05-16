#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Reinforcement Learning Agent for Liquidity Pool Investments
Implements DQN and Actor-Critic agents using PyTorch to optimize investment decisions.
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
from collections import deque, namedtuple
import random
import logging
from typing import List, Tuple, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

# Create a named tuple for storing experiences
Experience = namedtuple('Experience', ['state', 'action', 'reward', 'next_state', 'done'])

class ReplayBuffer:
    """
    Experience replay buffer to store and sample agent interactions with the environment.
    """
    
    def __init__(self, capacity: int = 10000):
        """
        Initialize a replay buffer with fixed capacity.
        
        Args:
            capacity: Maximum number of experiences to store
        """
        self.buffer = deque(maxlen=capacity)
    
    def add(self, state, action, reward, next_state, done):
        """
        Add a new experience to the buffer.
        
        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state
            done: Whether the episode is done
        """
        experience = Experience(state, action, reward, next_state, done)
        self.buffer.append(experience)
    
    def sample(self, batch_size: int) -> List[Experience]:
        """
        Sample a batch of experiences from the buffer.
        
        Args:
            batch_size: Number of experiences to sample
            
        Returns:
            List of sampled experiences
        """
        return random.sample(self.buffer, min(len(self.buffer), batch_size))
    
    def __len__(self) -> int:
        """
        Get the current size of the buffer.
        
        Returns:
            Current number of experiences in buffer
        """
        return len(self.buffer)

class DQNetwork(nn.Module):
    """
    Deep Q-Network for value function approximation.
    """
    
    def __init__(self, input_dim: int, output_dim: int):
        """
        Initialize the DQN with input and output dimensions.
        
        Args:
            input_dim: Size of state space
            output_dim: Size of action space
        """
        super(DQNetwork, self).__init__()
        
        # Define network architecture
        self.fc1 = nn.Linear(input_dim, 128)
        self.fc2 = nn.Linear(128, 128)
        self.fc3 = nn.Linear(128, 64)
        self.fc4 = nn.Linear(64, output_dim)
        
        # Initialize weights
        self._initialize_weights()
    
    def _initialize_weights(self):
        """Initialize weights with Xavier initialization."""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.zeros_(m.bias)
    
    def forward(self, x):
        """
        Forward pass through the network.
        
        Args:
            x: Input tensor
            
        Returns:
            Output tensor
        """
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        x = self.fc4(x)
        return x

class ActorNetwork(nn.Module):
    """
    Actor network for policy-based methods.
    """
    
    def __init__(self, input_dim: int, output_dim: int):
        """
        Initialize the actor network.
        
        Args:
            input_dim: Size of state space
            output_dim: Size of action space
        """
        super(ActorNetwork, self).__init__()
        
        # Define network architecture
        self.fc1 = nn.Linear(input_dim, 128)
        self.fc2 = nn.Linear(128, 128)
        self.fc3 = nn.Linear(128, 64)
        self.fc4 = nn.Linear(64, output_dim)
        
        # Initialize weights
        self._initialize_weights()
    
    def _initialize_weights(self):
        """Initialize weights with Xavier initialization."""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.zeros_(m.bias)
    
    def forward(self, x):
        """
        Forward pass through the network.
        
        Args:
            x: Input tensor
            
        Returns:
            Action probabilities
        """
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        x = F.softmax(self.fc4(x), dim=-1)
        return x

class CriticNetwork(nn.Module):
    """
    Critic network for value estimation in actor-critic methods.
    """
    
    def __init__(self, input_dim: int):
        """
        Initialize the critic network.
        
        Args:
            input_dim: Size of state space
        """
        super(CriticNetwork, self).__init__()
        
        # Define network architecture
        self.fc1 = nn.Linear(input_dim, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, 1)
        
        # Initialize weights
        self._initialize_weights()
    
    def _initialize_weights(self):
        """Initialize weights with Xavier initialization."""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.zeros_(m.bias)
    
    def forward(self, x):
        """
        Forward pass through the network.
        
        Args:
            x: Input tensor
            
        Returns:
            Estimated value
        """
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x

class DQNAgent:
    """
    Deep Q-Network agent for reinforcement learning.
    """
    
    def __init__(self, 
                state_dim: int, 
                action_dim: int,
                learning_rate: float = 0.001,
                gamma: float = 0.99,
                epsilon_start: float = 1.0,
                epsilon_end: float = 0.01,
                epsilon_decay: float = 0.995,
                target_update_freq: int = 10,
                batch_size: int = 64,
                buffer_size: int = 10000,
                device: str = None):
        """
        Initialize the DQN agent.
        
        Args:
            state_dim: Dimension of the state space
            action_dim: Dimension of the action space
            learning_rate: Learning rate for optimizer
            gamma: Discount factor
            epsilon_start: Starting value of epsilon for ε-greedy exploration
            epsilon_end: Minimum value of epsilon
            epsilon_decay: Decay rate of epsilon per episode
            target_update_freq: Frequency (in episodes) to update target network
            batch_size: Batch size for training
            buffer_size: Size of the replay buffer
            device: Device to run the model on ('cpu' or 'cuda')
        """
        # Set hyperparameters
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.target_update_freq = target_update_freq
        self.batch_size = batch_size
        
        # Set device
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        
        logger.info(f"Using device: {self.device}")
        
        # Initialize networks
        self.policy_net = DQNetwork(state_dim, action_dim).to(self.device)
        self.target_net = DQNetwork(state_dim, action_dim).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()  # Target network is only used for inference
        
        # Initialize optimizer
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=learning_rate)
        
        # Initialize replay buffer
        self.replay_buffer = ReplayBuffer(capacity=buffer_size)
        
        # Initialize training metrics
        self.episode_count = 0
        self.loss_history = []
        self.q_value_history = []
    
    def select_action(self, state: np.ndarray, evaluation: bool = False) -> int:
        """
        Select an action using ε-greedy policy.
        
        Args:
            state: Current state
            evaluation: Whether to use greedy policy (for evaluation)
            
        Returns:
            Selected action
        """
        # Convert state to tensor
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        
        # Use greedy policy during evaluation
        if evaluation or random.random() > self.epsilon:
            # Select best action
            with torch.no_grad():
                q_values = self.policy_net(state_tensor)
                action = q_values.max(1)[1].item()
        else:
            # Select random action
            action = random.randrange(self.action_dim)
        
        return action
    
    def update(self) -> Optional[float]:
        """
        Update the policy network using a batch of experiences.
        
        Returns:
            Loss value or None if buffer doesn't have enough samples
        """
        # Check if buffer has enough samples
        if len(self.replay_buffer) < self.batch_size:
            return None
        
        # Sample a batch
        batch = self.replay_buffer.sample(self.batch_size)
        
        # Convert batch to tensors
        states = torch.FloatTensor([exp.state for exp in batch]).to(self.device)
        actions = torch.LongTensor([[exp.action] for exp in batch]).to(self.device)
        rewards = torch.FloatTensor([exp.reward for exp in batch]).to(self.device)
        next_states = torch.FloatTensor([exp.next_state for exp in batch]).to(self.device)
        dones = torch.FloatTensor([exp.done for exp in batch]).to(self.device)
        
        # Compute current Q values
        current_q_values = self.policy_net(states).gather(1, actions)
        
        # Compute target Q values (using next state and target network)
        with torch.no_grad():
            next_q_values = self.target_net(next_states).max(1)[0]
        
        # Compute target values using Bellman equation
        target_q_values = rewards + (1 - dones) * self.gamma * next_q_values
        target_q_values = target_q_values.unsqueeze(1)
        
        # Compute loss
        loss = F.smooth_l1_loss(current_q_values, target_q_values)
        
        # Optimize the model
        self.optimizer.zero_grad()
        loss.backward()
        # Clip gradients to stabilize training
        for param in self.policy_net.parameters():
            param.grad.data.clamp_(-1, 1)
        self.optimizer.step()
        
        # Record metrics
        self.loss_history.append(loss.item())
        self.q_value_history.append(current_q_values.mean().item())
        
        return loss.item()
    
    def update_target_network(self):
        """Update the target network with the policy network's weights."""
        self.target_net.load_state_dict(self.policy_net.state_dict())
    
    def decay_epsilon(self):
        """Decay the exploration rate after each episode."""
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
    
    def episode_completed(self):
        """
        Handle end-of-episode updates.
        Updates target network if needed and decays exploration rate.
        """
        self.episode_count += 1
        
        # Update target network periodically
        if self.episode_count % self.target_update_freq == 0:
            self.update_target_network()
            logger.info(f"Target network updated at episode {self.episode_count}")
        
        # Decay exploration rate
        self.decay_epsilon()
    
    def save(self, path: str):
        """
        Save the agent's networks and training state.
        
        Args:
            path: Directory path to save to
        """
        # Create directory if it doesn't exist
        os.makedirs(path, exist_ok=True)
        
        # Save networks
        torch.save(self.policy_net.state_dict(), os.path.join(path, 'policy_net.pth'))
        torch.save(self.target_net.state_dict(), os.path.join(path, 'target_net.pth'))
        
        # Save training state
        training_state = {
            'epsilon': self.epsilon,
            'episode_count': self.episode_count,
            'loss_history': self.loss_history,
            'q_value_history': self.q_value_history
        }
        torch.save(training_state, os.path.join(path, 'training_state.pth'))
        
        logger.info(f"Agent saved to {path}")
    
    def load(self, path: str) -> bool:
        """
        Load the agent's networks and training state.
        
        Args:
            path: Directory path to load from
            
        Returns:
            Whether the load was successful
        """
        try:
            # Load networks
            self.policy_net.load_state_dict(torch.load(os.path.join(path, 'policy_net.pth'), map_location=self.device))
            self.target_net.load_state_dict(torch.load(os.path.join(path, 'target_net.pth'), map_location=self.device))
            
            # Load training state
            training_state = torch.load(os.path.join(path, 'training_state.pth'), map_location=self.device)
            self.epsilon = training_state['epsilon']
            self.episode_count = training_state['episode_count']
            self.loss_history = training_state['loss_history']
            self.q_value_history = training_state['q_value_history']
            
            logger.info(f"Agent loaded from {path}")
            return True
        except Exception as e:
            logger.error(f"Error loading agent: {e}")
            return False

class ActorCriticAgent:
    """
    Actor-Critic agent for reinforcement learning with policy gradients.
    """
    
    def __init__(self, 
                state_dim: int, 
                action_dim: int,
                actor_lr: float = 0.0003,
                critic_lr: float = 0.001,
                gamma: float = 0.99,
                tau: float = 0.01,
                buffer_size: int = 10000,
                batch_size: int = 64,
                device: str = None):
        """
        Initialize the Actor-Critic agent.
        
        Args:
            state_dim: Dimension of the state space
            action_dim: Dimension of the action space
            actor_lr: Learning rate for actor optimizer
            critic_lr: Learning rate for critic optimizer
            gamma: Discount factor
            tau: Soft update parameter for target networks
            buffer_size: Size of the replay buffer
            batch_size: Batch size for training
            device: Device to run the model on ('cpu' or 'cuda')
        """
        # Set hyperparameters
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.tau = tau
        self.batch_size = batch_size
        
        # Set device
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        
        logger.info(f"Using device: {self.device}")
        
        # Initialize networks
        self.actor = ActorNetwork(state_dim, action_dim).to(self.device)
        self.critic = CriticNetwork(state_dim).to(self.device)
        
        # Initialize optimizers
        self.actor_optimizer = optim.Adam(self.actor.parameters(), lr=actor_lr)
        self.critic_optimizer = optim.Adam(self.critic.parameters(), lr=critic_lr)
        
        # Initialize replay buffer
        self.replay_buffer = ReplayBuffer(capacity=buffer_size)
        
        # Initialize training metrics
        self.episode_count = 0
        self.actor_loss_history = []
        self.critic_loss_history = []
        self.value_history = []
    
    def select_action(self, state: np.ndarray, evaluation: bool = False) -> int:
        """
        Select an action using the actor network.
        
        Args:
            state: Current state
            evaluation: Whether to use deterministic policy (for evaluation)
            
        Returns:
            Selected action
        """
        # Convert state to tensor
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        
        # Get action probabilities
        with torch.no_grad():
            action_probs = self.actor(state_tensor).cpu().numpy()[0]
        
        if evaluation:
            # Use deterministic policy (highest probability action)
            action = np.argmax(action_probs)
        else:
            # Sample from probability distribution
            action = np.random.choice(self.action_dim, p=action_probs)
        
        return action
    
    def update(self) -> Optional[Tuple[float, float]]:
        """
        Update the actor and critic networks using a batch of experiences.
        
        Returns:
            Tuple of (actor_loss, critic_loss) or None if buffer doesn't have enough samples
        """
        # Check if buffer has enough samples
        if len(self.replay_buffer) < self.batch_size:
            return None
        
        # Sample a batch
        batch = self.replay_buffer.sample(self.batch_size)
        
        # Convert batch to tensors
        states = torch.FloatTensor([exp.state for exp in batch]).to(self.device)
        actions = torch.LongTensor([exp.action for exp in batch]).to(self.device)
        rewards = torch.FloatTensor([exp.reward for exp in batch]).to(self.device)
        next_states = torch.FloatTensor([exp.next_state for exp in batch]).to(self.device)
        dones = torch.FloatTensor([exp.done for exp in batch]).to(self.device)
        
        # Update critic
        value_targets = rewards + (1 - dones) * self.gamma * self.critic(next_states).squeeze()
        current_values = self.critic(states).squeeze()
        
        # Compute critic loss
        critic_loss = F.mse_loss(current_values, value_targets.detach())
        
        # Optimize critic
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        self.critic_optimizer.step()
        
        # Update actor
        action_probs = self.actor(states)
        advantages = (value_targets - current_values).detach()
        
        # Compute log probabilities
        action_log_probs = torch.log(action_probs.gather(1, actions.unsqueeze(1)).squeeze())
        
        # Compute actor loss (policy gradient)
        actor_loss = -(action_log_probs * advantages).mean()
        
        # Optimize actor
        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        self.actor_optimizer.step()
        
        # Record metrics
        self.actor_loss_history.append(actor_loss.item())
        self.critic_loss_history.append(critic_loss.item())
        self.value_history.append(current_values.mean().item())
        
        return actor_loss.item(), critic_loss.item()
    
    def episode_completed(self):
        """
        Handle end-of-episode updates.
        """
        self.episode_count += 1
    
    def save(self, path: str):
        """
        Save the agent's networks and training state.
        
        Args:
            path: Directory path to save to
        """
        # Create directory if it doesn't exist
        os.makedirs(path, exist_ok=True)
        
        # Save networks
        torch.save(self.actor.state_dict(), os.path.join(path, 'actor.pth'))
        torch.save(self.critic.state_dict(), os.path.join(path, 'critic.pth'))
        
        # Save training state
        training_state = {
            'episode_count': self.episode_count,
            'actor_loss_history': self.actor_loss_history,
            'critic_loss_history': self.critic_loss_history,
            'value_history': self.value_history
        }
        torch.save(training_state, os.path.join(path, 'training_state.pth'))
        
        logger.info(f"Agent saved to {path}")
    
    def load(self, path: str) -> bool:
        """
        Load the agent's networks and training state.
        
        Args:
            path: Directory path to load from
            
        Returns:
            Whether the load was successful
        """
        try:
            # Load networks
            self.actor.load_state_dict(torch.load(os.path.join(path, 'actor.pth'), map_location=self.device))
            self.critic.load_state_dict(torch.load(os.path.join(path, 'critic.pth'), map_location=self.device))
            
            # Load training state
            training_state = torch.load(os.path.join(path, 'training_state.pth'), map_location=self.device)
            self.episode_count = training_state['episode_count']
            self.actor_loss_history = training_state['actor_loss_history']
            self.critic_loss_history = training_state['critic_loss_history']
            self.value_history = training_state['value_history']
            
            logger.info(f"Agent loaded from {path}")
            return True
        except Exception as e:
            logger.error(f"Error loading agent: {e}")
            return False

# For testing
if __name__ == "__main__":
    # Test DQN agent
    state_dim = 50
    action_dim = 10
    
    # Create DQN agent
    dqn_agent = DQNAgent(state_dim, action_dim)
    
    # Test action selection
    state = np.random.rand(state_dim)
    action = dqn_agent.select_action(state)
    print(f"DQN Selected action: {action}")
    
    # Test Actor-Critic agent
    ac_agent = ActorCriticAgent(state_dim, action_dim)
    
    # Test action selection
    action = ac_agent.select_action(state)
    print(f"AC Selected action: {action}")