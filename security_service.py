"""
Central security service for the FiLot Telegram bot.

This module encapsulates all security-related functionality including:
1. Transaction validation and simulation
2. Input sanitization and validation
3. Session management and authentication
4. Rate limiting
5. Pool and token address whitelisting
6. Anomaly detection for transactions
"""

import os
import json
import time
import logging
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple, Set
from functools import wraps

import aiohttp
from pydantic import BaseModel, validator, Field, ValidationError

# Configure logging with redaction
class SensitiveDataFilter(logging.Filter):
    """Filter that redacts sensitive data in log records."""
    
    def __init__(self, name=""):
        super().__init__(name)
        self.sensitive_patterns = [
            "wc:", "symKey=", "relay-url=", "projectId=", 
            "seed", "private", "secret", "key"
        ]
    
    def filter(self, record):
        if isinstance(record.msg, str):
            # Redact sensitive data from strings
            msg = record.msg
            for pattern in self.sensitive_patterns:
                if pattern in msg.lower():
                    # Find the sensitive part and redact it
                    start_idx = msg.lower().find(pattern)
                    if start_idx >= 0:
                        # Determine end of sensitive data (whitespace or end of string)
                        end_idx = msg.find(" ", start_idx)
                        if end_idx < 0:
                            end_idx = len(msg)
                        
                        # Keep first few chars and replace rest with asterisks
                        visible_prefix = min(8, end_idx - start_idx)
                        redacted = msg[start_idx:start_idx+visible_prefix] + "..."
                        msg = msg[:start_idx] + redacted + msg[end_idx:]
            
            record.msg = msg
            
        # Also check args for strings that might contain sensitive data
        if hasattr(record, 'args') and record.args:
            args = list(record.args)
            for i, arg in enumerate(args):
                if isinstance(arg, str):
                    for pattern in self.sensitive_patterns:
                        if pattern in arg.lower():
                            # Redact the sensitive argument
                            visible_prefix = min(8, len(arg))
                            args[i] = arg[:visible_prefix] + "..." if len(arg) > visible_prefix else "***"
            record.args = tuple(args)
            
        return True

# Set up logger with sensitive data filter
logger = logging.getLogger(__name__)
logger.addFilter(SensitiveDataFilter())

# Database connection (will be implemented later)
db_connection = None

#########################
# Input Validation Models
#########################

class WalletAddress(BaseModel):
    """Model for validating wallet addresses."""
    address: str
    
    @validator('address')
    def validate_address(cls, v):
        # Solana addresses are 44 characters, base58 encoded
        if not v or len(v) != 44:
            raise ValueError("Invalid wallet address length")
            
        # Validate base58 character set
        allowed_chars = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")
        if not all(c in allowed_chars for c in v):
            raise ValueError("Invalid characters in wallet address")
            
        return v

class TokenAmount(BaseModel):
    """Model for validating token amounts."""
    amount: float
    token: str
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be positive")
        if v > 1_000_000_000:  # Reasonable upper limit
            raise ValueError("Amount exceeds reasonable limits")
        return v
    
    @validator('token')
    def validate_token(cls, v):
        valid_tokens = {"SOL", "USDC", "USDT", "RAY", "mSOL", "BONK"}
        if v not in valid_tokens:
            raise ValueError(f"Unsupported token: {v}")
        return v

class PoolData(BaseModel):
    """Model for validating pool data."""
    pool_id: str
    token_a: str
    token_b: str
    apr: float
    tvl: float
    
    @validator('apr')
    def validate_apr(cls, v):
        # Reasonableness check for APR (0-300%)
        if v < 0 or v > 300:
            raise ValueError(f"APR value {v}% is outside reasonable range")
        return v
    
    @validator('tvl')
    def validate_tvl(cls, v):
        # Minimum TVL requirement
        if v < 1000:
            raise ValueError(f"TVL ${v} is too low for safe investments")
        return v

class TransactionRequest(BaseModel):
    """Model for validating transaction requests."""
    wallet_address: str
    transaction_type: str
    amount: Optional[float] = None
    pool_id: Optional[str] = None
    token_a: Optional[str] = None
    token_b: Optional[str] = None
    percentage: Optional[float] = None
    slippage_tolerance: float = 0.5  # Default 0.5%
    
    @validator('slippage_tolerance')
    def validate_slippage(cls, v):
        # Maximum allowed slippage
        MAX_SLIPPAGE = 5.0  # 5%
        if v < 0.1:
            return 0.1  # Minimum slippage for transaction to succeed
        if v > MAX_SLIPPAGE:
            return MAX_SLIPPAGE  # Cap at maximum allowed
        return v
    
    @validator('transaction_type')
    def validate_transaction_type(cls, v):
        valid_types = {"swap", "add_liquidity", "remove_liquidity"}
        if v not in valid_types:
            raise ValueError(f"Unsupported transaction type: {v}")
        return v

class CommandRequest(BaseModel):
    """Model for validating Telegram command requests."""
    user_id: int
    command: str
    args: Optional[List[str]] = None
    
    @validator('command')
    def validate_command(cls, v):
        # Only allow registered commands
        valid_commands = {
            "start", "help", "account", "explore", "invest", 
            "info", "simulate", "subscribe", "unsubscribe",
            "status", "verify", "wallet", "profile", "faq"
        }
        if v not in valid_commands:
            raise ValueError(f"Unrecognized command: {v}")
        return v

#########################
# Whitelist Management
#########################

# Load pool & token whitelist
try:
    WHITELISTED_POOLS = set()
    WHITELISTED_TOKENS = {
        "SOL": "So11111111111111111111111111111111111111112",  # Native SOL wrapped
        "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
        "RAY": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
        "mSOL": "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",
        "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
    }
    
    # In production, load from a secure database
    # For now we'll include some sample whitelisted pools
    default_pools = [
        "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2",
        "AVs9TA4nWDzfPJE9gGVNJMVhcQy3V9PGazuz33BfG2RA",
        "6UmmUiYoBjSrhakAobJw8BvkmJtDVxaeBtbt7rxWo1mg",
        "FtEaLvQAeGNrMBqK6rpZ3n7TXZmyLovEVXZT9Xt6Lquo",
        "CPxYyQB2ZG58QWu7JmCCqZU8TsMnWyhGDBaNGEXZ5Spo"
    ]
    
    for pool_id in default_pools:
        WHITELISTED_POOLS.add(pool_id)
        
    logger.info(f"Loaded {len(WHITELISTED_POOLS)} whitelisted pools and {len(WHITELISTED_TOKENS)} tokens")
except Exception as e:
    logger.error(f"Error loading whitelist data: {e}")
    # Ensure defaults are set
    WHITELISTED_POOLS = set()
    WHITELISTED_TOKENS = {
        "SOL": "So11111111111111111111111111111111111111112"
    }

def is_pool_whitelisted(pool_id: str) -> bool:
    """Check if a pool ID is on the whitelist."""
    return pool_id in WHITELISTED_POOLS

def is_token_whitelisted(token_symbol: str) -> bool:
    """Check if a token symbol is on the whitelist."""
    return token_symbol in WHITELISTED_TOKENS

def get_token_mint(token_symbol: str) -> Optional[str]:
    """Get the token mint address for a symbol."""
    return WHITELISTED_TOKENS.get(token_symbol)

async def verify_pool_data(pool_data: Dict[str, Any]) -> bool:
    """
    Verify pool data against the whitelist and by cross-referencing sources.
    
    Args:
        pool_data: Dictionary with pool information including ID, tokens, and APR
        
    Returns:
        True if the pool is verified, False otherwise
    """
    try:
        # First check whitelist
        pool_id = pool_data.get("pool_id")
        if not pool_id or not is_pool_whitelisted(pool_id):
            logger.warning(f"Pool {pool_id} is not on the whitelist")
            return False
            
        # Verify tokens
        token_a = pool_data.get("token_a")
        token_b = pool_data.get("token_b")
        
        if not token_a or not is_token_whitelisted(token_a):
            logger.warning(f"Token {token_a} is not on the whitelist")
            return False
            
        if not token_b or not is_token_whitelisted(token_b):
            logger.warning(f"Token {token_b} is not on the whitelist")
            return False
            
        # Verify APR within reasonable range
        apr = pool_data.get("apr", 0)
        if apr < 0 or apr > 300:  # 0-300% is a reasonable range
            logger.warning(f"APR {apr}% for pool {pool_id} outside reasonable range")
            return False
            
        # In production, add cross-reference with another API source
        # For this example, we'll just use the whitelist check
            
        return True
    except Exception as e:
        logger.error(f"Error verifying pool data: {e}")
        return False

#########################
# Rate Limiting
#########################

# Simple in-memory rate limiter
class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self):
        self.buckets = {}  # user_id -> (tokens, last_refill)
        self.lock = asyncio.Lock()
    
    async def check_rate_limit(self, user_id: int, action_type: str = "default") -> bool:
        """
        Check if a user has exceeded their rate limit.
        
        Args:
            user_id: The Telegram user ID
            action_type: The type of action (different limits for different actions)
            
        Returns:
            True if allowed, False if rate limited
        """
        async with self.lock:
            # Define limits based on action type
            if action_type == "transaction":
                max_tokens = 3
                refill_rate = 1  # token per second
            elif action_type == "query":
                max_tokens = 10
                refill_rate = 2  # tokens per second
            else:
                max_tokens = 5
                refill_rate = 1  # token per second
                
            # Get or create bucket
            bucket_key = f"{user_id}:{action_type}"
            if bucket_key not in self.buckets:
                self.buckets[bucket_key] = (max_tokens, time.time())
                return True
                
            tokens, last_refill = self.buckets[bucket_key]
            
            # Refill tokens based on time elapsed
            now = time.time()
            elapsed = now - last_refill
            new_tokens = min(max_tokens, tokens + elapsed * refill_rate)
            
            # Check if enough tokens available
            if new_tokens < 1:
                logger.warning(f"Rate limit exceeded for user {user_id} on {action_type}")
                return False
                
            # Consume a token
            self.buckets[bucket_key] = (new_tokens - 1, now)
            return True

# Create global rate limiter instance
rate_limiter = RateLimiter()

# Rate limiting decorator
def rate_limited(action_type="default"):
    """
    Decorator to apply rate limiting to functions.
    
    Args:
        action_type: The type of action for rate limiting
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user_id from update object (assumes first arg is Update)
            user_id = None
            if args and hasattr(args[0], "effective_user") and hasattr(args[0].effective_user, "id"):
                user_id = args[0].effective_user.id
            elif "user_id" in kwargs:
                user_id = kwargs["user_id"]
                
            if not user_id:
                logger.warning("Cannot apply rate limiting: user_id not found")
                return await func(*args, **kwargs)
                
            # Check rate limit
            if await rate_limiter.check_rate_limit(user_id, action_type):
                return await func(*args, **kwargs)
            else:
                # If rate limited, return appropriate response
                return {
                    "success": False,
                    "error": "Rate limit exceeded. Please try again later.",
                    "rate_limited": True
                }
        return wrapper
    return decorator

#########################
# Transaction Security
#########################

class TransactionGuard:
    """Guards transactions with simulation, slippage protection, and anomaly detection."""
    
    def __init__(self):
        # Track recent transactions per user for anomaly detection
        self.recent_transactions = {}  # user_id -> list of (timestamp, amount) tuples
        
    async def validate_transaction(self, 
                                  user_id: int, 
                                  wallet_address: str, 
                                  transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a transaction before execution.
        
        Args:
            user_id: Telegram user ID
            wallet_address: User's wallet address
            transaction_data: Transaction parameters
            
        Returns:
            Dict with validation result and transaction details
        """
        try:
            # 1. Validate inputs with Pydantic
            try:
                # Add wallet address to transaction data if not present
                if "wallet_address" not in transaction_data:
                    transaction_data["wallet_address"] = wallet_address
                    
                tx_request = TransactionRequest(**transaction_data)
                # Update transaction_data with validated data
                transaction_data = tx_request.dict()
            except ValidationError as e:
                return {
                    "success": False,
                    "error": f"Invalid transaction parameters: {str(e)}",
                    "validation_errors": e.errors()
                }
                
            # 2. Check if wallet address matches context
            if wallet_address != transaction_data["wallet_address"]:
                return {
                    "success": False,
                    "error": "Wallet address mismatch. Transaction not authorized."
                }
                
            # 3. Check for anomalies in transaction history
            if await self._detect_anomalies(user_id, transaction_data):
                return {
                    "success": False,
                    "error": "Anomaly detected in transaction pattern. Please confirm manually."
                }
                
            # 4. For pools, verify they are whitelisted
            if "pool_id" in transaction_data and transaction_data["pool_id"]:
                pool_id = transaction_data["pool_id"]
                if not is_pool_whitelisted(pool_id):
                    return {
                        "success": False,
                        "error": f"Pool {pool_id} is not verified. Transaction rejected."
                    }
                    
            # 5. Enforce slippage protection
            slippage = transaction_data.get("slippage_tolerance", 0.5)
            MAX_SLIPPAGE = 5.0  # 5%
            if slippage > MAX_SLIPPAGE:
                transaction_data["slippage_tolerance"] = MAX_SLIPPAGE
                logger.warning(f"Slippage capped at {MAX_SLIPPAGE}% for user {user_id}")
                
            # 6. Simulate transaction to check for potential issues
            simulation_result = await self._simulate_transaction(transaction_data)
            if not simulation_result["success"]:
                return simulation_result
                
            # Record this transaction for anomaly detection
            self._record_transaction(user_id, transaction_data)
                
            # 7. Add preview data for user confirmation
            preview = self._generate_preview(transaction_data, simulation_result)
            
            # Return successful validation with preview
            return {
                "success": True,
                "preview": preview,
                "transaction_data": transaction_data,
                "simulation_result": simulation_result
            }
            
        except Exception as e:
            logger.error(f"Error validating transaction: {e}")
            return {
                "success": False,
                "error": f"Transaction validation error: {str(e)}"
            }
    
    async def _simulate_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate a transaction to check for errors without executing on-chain.
        
        Args:
            transaction_data: Transaction parameters
            
        Returns:
            Simulation results
        """
        # In production, this would use Solana's simulateTransaction RPC method
        # For now, we'll simulate successful results with realistic data
        
        transaction_type = transaction_data.get("transaction_type")
        amount = transaction_data.get("amount", 0)
        
        if transaction_type == "swap":
            # Calculate fees, slippage impact, etc.
            from_token = transaction_data.get("token_a", "SOL")
            to_token = transaction_data.get("token_b", "USDC")
            
            # Simulate realistic fees and slippage
            fee_percent = 0.3  # 0.3% fee
            slippage = transaction_data.get("slippage_tolerance", 0.5) / 100
            
            # Calculate simulated outcome
            fees = amount * (fee_percent / 100)
            slippage_impact = amount * slippage
            
            # Get simulated exchange rate
            rate = 133.0 if from_token == "SOL" and to_token == "USDC" else 0.0075
            
            # Calculate expected receive amount
            receive_amount = (amount - fees) * rate * (1 - slippage)
            
            return {
                "success": True,
                "transaction_type": transaction_type,
                "fees": fees,
                "slippage_impact": slippage_impact,
                "expected_receive": receive_amount,
                "from_token": from_token,
                "to_token": to_token,
                "exchange_rate": rate
            }
            
        elif transaction_type == "add_liquidity":
            # Simulate liquidity provisioning
            token_a = transaction_data.get("token_a", "SOL")
            token_b = transaction_data.get("token_b", "USDC")
            
            # Simulate fees for LP transaction
            fee_percent = 0.2  # 0.2% fee
            fees = amount * (fee_percent / 100)
            
            # Calculate estimated APR
            estimated_apr = 15.0 + (hash(token_a + token_b) % 30)  # Random APR between 15-45%
            
            return {
                "success": True,
                "transaction_type": transaction_type,
                "fees": fees,
                "estimated_apr": estimated_apr,
                "token_a": token_a,
                "token_b": token_b,
                "lp_tokens_received": amount - fees
            }
            
        elif transaction_type == "remove_liquidity":
            # Simulate liquidity removal
            token_a = transaction_data.get("token_a", "SOL")
            token_b = transaction_data.get("token_b", "USDC")
            percentage = transaction_data.get("percentage", 100)
            
            # Simulate fees for LP removal
            fee_percent = 0.2  # 0.2% fee
            fees = amount * (fee_percent / 100) * (percentage / 100)
            
            # Calculate received amounts for both tokens
            token_a_amount = (amount * 0.5 - fees) * (percentage / 100)
            token_b_amount = (amount * 0.5 - fees) * (percentage / 100)
            
            return {
                "success": True,
                "transaction_type": transaction_type,
                "fees": fees,
                "token_a": token_a,
                "token_b": token_b,
                "token_a_amount": token_a_amount,
                "token_b_amount": token_b_amount,
                "percentage": percentage
            }
            
        else:
            return {
                "success": False,
                "error": f"Unsupported transaction type: {transaction_type}"
            }
    
    async def _detect_anomalies(self, user_id: int, transaction_data: Dict[str, Any]) -> bool:
        """
        Detect anomalies in transaction patterns.
        
        Args:
            user_id: Telegram user ID
            transaction_data: Transaction parameters
            
        Returns:
            True if anomaly detected, False otherwise
        """
        # Get amount from transaction
        amount = transaction_data.get("amount", 0)
        if not amount:
            return False
            
        # Get recent transactions for this user
        user_transactions = self.recent_transactions.get(user_id, [])
        
        # Check frequency - more than 3 transactions in 1 minute is suspicious
        recent_tx_count = sum(1 for ts, _ in user_transactions if time.time() - ts < 60)
        if recent_tx_count >= 3:
            logger.warning(f"Frequency anomaly: user {user_id} has made {recent_tx_count} transactions in the last minute")
            return True
            
        # Check for unusually large transactions
        if user_transactions:
            avg_amount = sum(amt for _, amt in user_transactions) / len(user_transactions)
            if amount > avg_amount * 5 and amount > 500:  # 5x average and > $500
                logger.warning(f"Size anomaly: transaction of {amount} is much larger than user average of {avg_amount}")
                return True
                
        return False
    
    def _record_transaction(self, user_id: int, transaction_data: Dict[str, Any]) -> None:
        """
        Record a transaction for anomaly detection.
        
        Args:
            user_id: Telegram user ID
            transaction_data: Transaction parameters
        """
        amount = transaction_data.get("amount", 0)
        
        # Initialize or get user's transaction history
        if user_id not in self.recent_transactions:
            self.recent_transactions[user_id] = []
            
        # Add this transaction
        self.recent_transactions[user_id].append((time.time(), amount))
        
        # Keep only the most recent 10 transactions
        self.recent_transactions[user_id] = self.recent_transactions[user_id][-10:]
    
    def _generate_preview(self, transaction_data: Dict[str, Any], simulation_result: Dict[str, Any]) -> str:
        """
        Generate a user-friendly preview of the transaction.
        
        Args:
            transaction_data: Transaction parameters
            simulation_result: Simulation results
            
        Returns:
            Formatted preview string for Telegram
        """
        transaction_type = transaction_data.get("transaction_type")
        wallet_address = transaction_data.get("wallet_address", "")
        
        # Truncate wallet address for display
        short_address = wallet_address[:6] + "..." + wallet_address[-4:] if wallet_address else "Unknown"
        
        preview = f"📝 *Transaction Preview*\n\n"
        preview += f"Wallet: `{short_address}`\n"
        preview += f"Type: {transaction_type.replace('_', ' ').title()}\n\n"
        
        if transaction_type == "swap":
            from_token = transaction_data.get("token_a", "Unknown")
            to_token = transaction_data.get("token_b", "Unknown")
            amount = transaction_data.get("amount", 0)
            
            fees = simulation_result.get("fees", 0)
            expected_receive = simulation_result.get("expected_receive", 0)
            exchange_rate = simulation_result.get("exchange_rate", 0)
            
            preview += f"💱 *Swap Details*\n"
            preview += f"From: {amount:.4f} {from_token}\n"
            preview += f"To: ~{expected_receive:.4f} {to_token}\n"
            preview += f"Rate: 1 {from_token} = {exchange_rate:.4f} {to_token}\n"
            preview += f"Fees: {fees:.4f} {from_token}\n"
            preview += f"Slippage Protection: {transaction_data.get('slippage_tolerance', 0.5)}%\n"
            
        elif transaction_type == "add_liquidity":
            token_a = transaction_data.get("token_a", "Unknown")
            token_b = transaction_data.get("token_b", "Unknown")
            amount = transaction_data.get("amount", 0)
            pool_id = transaction_data.get("pool_id", "Unknown")
            
            fees = simulation_result.get("fees", 0)
            estimated_apr = simulation_result.get("estimated_apr", 0)
            
            preview += f"🏊 *Add Liquidity Details*\n"
            preview += f"Pool: {token_a}-{token_b}\n"
            preview += f"Amount: {amount:.2f} USD\n"
            preview += f"Fees: {fees:.4f} USD\n"
            preview += f"Estimated APR: {estimated_apr:.2f}%\n"
            preview += f"Pool ID: `{pool_id[:6]}...{pool_id[-4:]}`\n"
            
        elif transaction_type == "remove_liquidity":
            token_a = transaction_data.get("token_a", "Unknown")
            token_b = transaction_data.get("token_b", "Unknown")
            percentage = transaction_data.get("percentage", 100)
            pool_id = transaction_data.get("pool_id", "Unknown")
            
            token_a_amount = simulation_result.get("token_a_amount", 0)
            token_b_amount = simulation_result.get("token_b_amount", 0)
            
            preview += f"🏊 *Remove Liquidity Details*\n"
            preview += f"Pool: {token_a}-{token_b}\n"
            preview += f"Percentage: {percentage}%\n"
            preview += f"Expected Return:\n"
            preview += f"• {token_a_amount:.4f} {token_a}\n"
            preview += f"• {token_b_amount:.4f} {token_b}\n"
            preview += f"Pool ID: `{pool_id[:6]}...{pool_id[-4:]}`\n"
            
        # Add confirmation instructions
        preview += f"\n⚠️ Press 'Confirm' to execute this transaction or 'Cancel' to abort."
        
        return preview

# Create global transaction guard instance
transaction_guard = TransactionGuard()

#########################
# Session Management
#########################

class SessionManager:
    """Secure session management for wallet connections."""
    
    def __init__(self):
        self.sessions = {}  # temporary in-memory storage until database is set up
        
    async def create_session(self, user_id: int, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new secure session.
        
        Args:
            user_id: Telegram user ID
            session_data: Session data including URIs, keys, etc.
            
        Returns:
            Session information with ID
        """
        # Generate a secure session ID
        session_id = hashlib.sha256(f"{user_id}:{time.time()}:{os.urandom(8)}".encode()).hexdigest()
        
        # Set session expiration (1 hour by default)
        expires_at = datetime.now() + timedelta(hours=1)
        
        # Create session object
        session = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "expires_at": expires_at.isoformat(),
            "status": "pending",
            "wallet_address": None,
            "data": session_data
        }
        
        # Store session securely - in production this would be encrypted in a database
        # For now, store in memory
        self.sessions[session_id] = session
        
        # Log session creation (with sensitive data redacted)
        logger.info(f"Created session {session_id} for user {user_id}")
        
        # Return session data (excluding sensitive parts)
        return {
            "success": True,
            "session_id": session_id,
            "user_id": user_id,
            "status": "pending",
            "expires_at": expires_at.isoformat(),
            "uri": session_data.get("uri", "")[:20] + "..." if "uri" in session_data else None
        }
        
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session data if found, None otherwise
        """
        # In production, this would query the secure database
        session = self.sessions.get(session_id)
        
        if not session:
            return None
            
        # Check if session is expired
        expires_at = datetime.fromisoformat(session["expires_at"])
        if datetime.now() > expires_at:
            logger.info(f"Session {session_id} has expired")
            return {**session, "status": "expired"}
            
        return session
        
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a session with new data.
        
        Args:
            session_id: Session ID
            updates: Data to update
            
        Returns:
            Updated session data
        """
        session = await self.get_session(session_id)
        
        if not session:
            return {"success": False, "error": "Session not found"}
            
        # Check if session is expired
        expires_at = datetime.fromisoformat(session["expires_at"])
        if datetime.now() > expires_at:
            return {"success": False, "error": "Session has expired"}
            
        # Update session data
        for key, value in updates.items():
            if key != "session_id" and key != "user_id":
                session[key] = value
                
        # Store updated session
        self.sessions[session_id] = session
        
        # Return updated session (excluding sensitive data)
        return {
            "success": True,
            "session_id": session_id,
            "user_id": session["user_id"],
            "status": session["status"],
            "wallet_address": session.get("wallet_address"),
            "expires_at": session["expires_at"]
        }
        
    async def delete_session(self, session_id: str) -> Dict[str, Any]:
        """
        Delete a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Result of operation
        """
        if session_id in self.sessions:
            user_id = self.sessions[session_id]["user_id"]
            del self.sessions[session_id]
            logger.info(f"Deleted session {session_id} for user {user_id}")
            return {"success": True, "message": "Session deleted"}
        else:
            return {"success": False, "error": "Session not found"}
            
    async def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all sessions for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            List of active sessions
        """
        # Filter sessions by user_id and non-expired
        now = datetime.now()
        sessions = [
            session for session in self.sessions.values()
            if session["user_id"] == user_id and 
            datetime.fromisoformat(session["expires_at"]) > now
        ]
        
        # Return sessions without sensitive data
        return [
            {
                "session_id": s["session_id"],
                "status": s["status"],
                "wallet_address": s.get("wallet_address"),
                "created_at": s["created_at"],
                "expires_at": s["expires_at"]
            }
            for s in sessions
        ]

# Create global session manager instance
session_manager = SessionManager()

#########################
# Unified Security Interface
#########################

async def validate_input(input_data: Dict[str, Any], model_type: str) -> Dict[str, Any]:
    """
    Validate input data against a specified model.
    
    Args:
        input_data: Data to validate
        model_type: Type of model to use ("wallet", "token", "pool", "transaction", "command")
        
    Returns:
        Validation result
    """
    try:
        # Select model based on type
        if model_type == "wallet":
            model = WalletAddress(**input_data)
        elif model_type == "token":
            model = TokenAmount(**input_data)
        elif model_type == "pool":
            model = PoolData(**input_data)
        elif model_type == "transaction":
            model = TransactionRequest(**input_data)
        elif model_type == "command":
            model = CommandRequest(**input_data)
        else:
            return {
                "success": False,
                "error": f"Unknown model type: {model_type}"
            }
            
        # Return validated data
        return {
            "success": True,
            "validated_data": model.dict()
        }
    except ValidationError as e:
        return {
            "success": False,
            "error": f"Validation error: {str(e)}",
            "validation_errors": e.errors()
        }
    except Exception as e:
        logger.error(f"Error validating {model_type} data: {e}")
        return {
            "success": False,
            "error": f"Error validating data: {str(e)}"
        }

async def verify_transaction(
    user_id: int,
    wallet_address: str,
    transaction_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Comprehensive transaction verification.
    
    Args:
        user_id: Telegram user ID
        wallet_address: User's wallet address
        transaction_data: Transaction parameters
        
    Returns:
        Verification result with preview for confirmation
    """
    # Ensure transaction_data has the expected format
    if transaction_data is None:
        transaction_data = {}
        
    return await transaction_guard.validate_transaction(user_id, wallet_address, transaction_data)

@rate_limited(action_type="transaction")
async def execute_transaction(
    user_id: int,
    wallet_address: str,
    transaction_data: Dict[str, Any],
    confirmed: bool = False
) -> Dict[str, Any]:
    """
    Execute a transaction after validation and confirmation.
    
    Args:
        user_id: Telegram user ID
        wallet_address: User's wallet address
        transaction_data: Transaction parameters
        confirmed: Whether the user has confirmed the transaction
        
    Returns:
        Transaction result
    """
    # Require confirmation
    if not confirmed:
        return {
            "success": False,
            "error": "Transaction must be confirmed before execution",
            "requires_confirmation": True
        }
        
    # Validate transaction
    validation = await verify_transaction(user_id, wallet_address, transaction_data)
    if not validation["success"]:
        return validation
        
    # In production, this would execute the actual transaction
    # For this example, we return the simulated transaction result
    simulation_result = validation.get("simulation_result", {})
    
    # Add actual transaction details
    transaction_result = {
        "success": True,
        "user_id": user_id,
        "wallet_address": wallet_address,
        "transaction_type": transaction_data.get("transaction_type"),
        "timestamp": datetime.now().isoformat(),
        "signature": f"simulated_signature_{str(int(time.time()))}",
        **simulation_result
    }
    
    # Log the transaction (with sensitive data redacted)
    logger.info(f"Executed {transaction_data.get('transaction_type')} transaction for user {user_id}")
    
    return transaction_result

async def create_wallet_session(user_id: int) -> Dict[str, Any]:
    """
    Create a secure wallet connection session.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        Session details including connection URI
    """
    try:
        # Generate secure session data - in production, this would use WalletConnect
        import uuid
        
        # In production, these would be real WalletConnect parameters
        topic = str(uuid.uuid4())
        key = str(uuid.uuid4())
        
        # Create connection URI
        uri = f"wc:{topic}@2?relay-protocol=irn&symKey={key[:8]}...&projectId=..."
        
        # Store session securely
        session_data = {
            "uri": uri,
            "topic": topic,
            "key": key
        }
        
        return await session_manager.create_session(user_id, session_data)
    except Exception as e:
        logger.error(f"Error creating wallet session: {e}")
        return {
            "success": False,
            "error": f"Error creating wallet session: {str(e)}"
        }

async def check_wallet_session(session_id: str) -> Dict[str, Any]:
    """
    Check the status of a wallet session.
    
    Args:
        session_id: Session ID
        
    Returns:
        Session status
    """
    session = await session_manager.get_session(session_id)
    
    if not session:
        return {"success": False, "error": "Session not found"}
        
    return {
        "success": True,
        "session_id": session["session_id"],
        "user_id": session["user_id"],
        "status": session["status"],
        "wallet_address": session.get("wallet_address"),
        "expires_at": session["expires_at"]
    }

# Initialize the module
def init_security_service():
    """Initialize the security service."""
    logger.info("Security service initialized")
    return {
        "session_manager": session_manager,
        "transaction_guard": transaction_guard,
        "rate_limiter": rate_limiter
    }

# Initialize when imported
security_services = init_security_service()