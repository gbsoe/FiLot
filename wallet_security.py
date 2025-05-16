"""
Wallet security module for the FiLot Telegram bot.

This module implements security measures for wallet transactions, including:
1. Transaction validation with detailed previews
2. Explicit user confirmation requirement
3. Anomaly detection
4. Slippage protection
5. Session isolation by user ID
"""

import os
import base64
import json
import logging
import time
import uuid
import hashlib
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import urllib.parse

try:
    from cryptography.fernet import Fernet
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# In-memory storage for pending transactions that require confirmation
# Format: {transaction_id: {transaction_data, user_id, created_at, confirmed}}
PENDING_TRANSACTIONS = {}

# In-memory session storage for user wallet connections
# Format: {session_id: {user_id, wallet_address, created_at, expires_at, status}}
WALLET_SESSIONS = {}

# Whitelist of allowed pools and tokens
WHITELISTED_POOLS = set([
    "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2",
    "AVs9TA4nWDzfPJE9gGVNJMVhcQy3V9PGazuz33BfG2RA",
    "6UmmUiYoBjSrhakAobJw8BvkmJtDVxaeBtbt7rxWo1mg",
    "FtEaLvQAeGNrMBqK6rpZ3n7TXZmyLovEVXZT9Xt6Lquo",
    "CPxYyQB2ZG58QWu7JmCCqZU8TsMnWyhGDBaNGEXZ5Spo"
])

WHITELISTED_TOKENS = {
    "SOL": "So11111111111111111111111111111111111111112",
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "RAY": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
    "mSOL": "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
}

# User transaction history for anomaly detection
# Format: {user_id: [{timestamp, amount, type}]}
USER_TRANSACTION_HISTORY = {}

# Initialize encryption if available
if ENCRYPTION_AVAILABLE:
    # Generate encryption key from environment or create a temporary one
    ENCRYPTION_KEY = os.environ.get("WALLET_SESSION_ENCRYPTION_KEY")
    if not ENCRYPTION_KEY:
        # For development only - in production, require a real key
        logger.warning("No encryption key found - generating temporary key. THIS IS NOT SECURE FOR PRODUCTION!")
        # Create a temporary key that's valid for Fernet
        temp_key = hashlib.sha256(os.urandom(32)).digest()
        ENCRYPTION_KEY = base64.urlsafe_b64encode(temp_key)
    
    # Create cipher for encryption
    cipher = Fernet(ENCRYPTION_KEY)

def encrypt_data(data: Any) -> str:
    """
    Encrypt sensitive data.
    
    Args:
        data: Data to encrypt
        
    Returns:
        Encrypted string
    """
    if not ENCRYPTION_AVAILABLE:
        return base64.b64encode(json.dumps(data).encode()).decode()
        
    json_data = json.dumps(data)
    encrypted = cipher.encrypt(json_data.encode())
    return base64.urlsafe_b64encode(encrypted).decode()

def decrypt_data(encrypted_data: str) -> Any:
    """
    Decrypt sensitive data.
    
    Args:
        encrypted_data: Encrypted string
        
    Returns:
        Decrypted data
    """
    try:
        if not ENCRYPTION_AVAILABLE:
            return json.loads(base64.b64decode(encrypted_data).decode())
            
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data)
        decrypted = cipher.decrypt(encrypted_bytes)
        return json.loads(decrypted.decode())
    except Exception as e:
        logger.error(f"Error decrypting data: {e}")
        return {}

def validate_wallet_address(address: str) -> bool:
    """
    Validate that a string is a valid Solana wallet address.
    
    Args:
        address: Wallet address to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Solana addresses are 44 characters, base58 encoded
        if not address or len(address) != 44:
            return False
            
        # Validate base58 character set
        allowed_chars = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")
        if not all(c in allowed_chars for c in address):
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error validating wallet address: {e}")
        return False

def validate_pool_id(pool_id: str) -> bool:
    """
    Validate that a pool ID is on the whitelist.
    
    Args:
        pool_id: Pool ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    return pool_id in WHITELISTED_POOLS

def validate_token(token: str) -> bool:
    """
    Validate that a token is on the whitelist.
    
    Args:
        token: Token to validate
        
    Returns:
        True if valid, False otherwise
    """
    return token in WHITELISTED_TOKENS

def create_wallet_session(user_id: int) -> Dict[str, Any]:
    """
    Create a secure wallet session.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        Session details
    """
    # Generate secure session ID
    session_id = str(uuid.uuid4())
    
    # Create secure session
    session = {
        "user_id": user_id,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
        "status": "pending",
        "wallet_address": None,
        "security_level": "read_only",
        "permissions": ["view_balance"]
    }
    
    # Generate WalletConnect URI with improved security
    try:
        # Generate required components with strong randomness
        topic = uuid.uuid4().hex
        
        # Use os.urandom for better randomness
        random_bytes = os.urandom(32)
        sym_key = base64.urlsafe_b64encode(random_bytes).decode()[:32]
        
        # Current relay server
        relay_url = "wss://relay.walletconnect.org"
        
        # Standard WalletConnect v2 format with minimal data exposure
        wc_uri = f"wc:{topic}@2?relay-protocol=irn&relay-url={relay_url}&symKey={sym_key}"
        
        # Include project ID if available
        project_id = os.environ.get("WALLETCONNECT_PROJECT_ID")
        if project_id:
            wc_uri = f"{wc_uri}&projectId={project_id}"
        
        # URL encode for compatibility
        uri_encoded = urllib.parse.quote(wc_uri)
        
        # Format for most wallets
        deep_link_uri = f"https://walletconnect.com/wc?uri={uri_encoded}"
        
        # Store secure URI in session
        session["uri"] = deep_link_uri
        
        # Store in memory
        WALLET_SESSIONS[session_id] = session
        
        # Return minimal data
        return {
            "success": True,
            "session_id": session_id,
            "uri": deep_link_uri,
            "user_id": user_id,
            "status": "pending",
            "expires_at": session["expires_at"],
            "expires_in_seconds": 3600,
            "requires_confirmation": True
        }
    except Exception as e:
        logger.error(f"Error creating WalletConnect URI: {e}")
        return {
            "success": False,
            "error": f"Error creating wallet session: {str(e)}"
        }

def check_session(session_id: str) -> Dict[str, Any]:
    """
    Check wallet session status.
    
    Args:
        session_id: Session ID
        
    Returns:
        Session status
    """
    session = WALLET_SESSIONS.get(session_id)
    
    if not session:
        return {"success": False, "error": "Session not found"}
        
    # Check expiration
    expires_at = datetime.fromisoformat(session["expires_at"])
    if datetime.now() > expires_at:
        return {
            "success": True,
            "status": "expired",
            "message": "Session has expired"
        }
        
    # Return session status
    return {
        "success": True,
        "session_id": session_id,
        "user_id": session["user_id"],
        "status": session["status"],
        "wallet_address": session.get("wallet_address"),
        "expires_at": session["expires_at"],
        "security_level": session["security_level"]
    }

def connect_wallet(session_id: str, wallet_address: str) -> Dict[str, Any]:
    """
    Connect wallet to session.
    
    Args:
        session_id: Session ID
        wallet_address: Wallet address
        
    Returns:
        Result of connection
    """
    session = WALLET_SESSIONS.get(session_id)
    
    if not session:
        return {"success": False, "error": "Session not found"}
        
    # Check expiration
    expires_at = datetime.fromisoformat(session["expires_at"])
    if datetime.now() > expires_at:
        return {"success": False, "error": "Session has expired"}
        
    # Validate wallet address
    if not validate_wallet_address(wallet_address):
        return {"success": False, "error": "Invalid wallet address"}
        
    # Update session
    session["wallet_address"] = wallet_address
    session["status"] = "connected"
    
    # Store updated session
    WALLET_SESSIONS[session_id] = session
    
    return {
        "success": True,
        "session_id": session_id,
        "user_id": session["user_id"],
        "wallet_address": wallet_address,
        "status": "connected"
    }

def create_transaction(
    user_id: int,
    wallet_address: str,
    transaction_type: str,
    transaction_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a transaction that requires explicit confirmation.
    
    Args:
        user_id: User ID
        wallet_address: Wallet address
        transaction_type: Type of transaction (swap, add_liquidity, remove_liquidity)
        transaction_data: Transaction details
        
    Returns:
        Transaction preview with confirmation details
    """
    # Validate wallet address
    if not validate_wallet_address(wallet_address):
        return {"success": False, "error": "Invalid wallet address"}
        
    # Validate transaction type
    valid_types = {"swap", "add_liquidity", "remove_liquidity"}
    if transaction_type not in valid_types:
        return {"success": False, "error": f"Invalid transaction type: {transaction_type}"}
        
    # Apply slippage protection
    slippage = transaction_data.get("slippage_tolerance", 0.5)
    MAX_SLIPPAGE = 5.0  # 5% maximum
    if slippage > MAX_SLIPPAGE:
        slippage = MAX_SLIPPAGE
        transaction_data["slippage_tolerance"] = MAX_SLIPPAGE
        logger.warning(f"Slippage capped at {MAX_SLIPPAGE}% for user {user_id}")
        
    # Check for anomalies
    if detect_anomalies(user_id, transaction_type, transaction_data):
        return {
            "success": False, 
            "error": "Unusual transaction pattern detected - please contact support",
            "anomaly_detected": True
        }
        
    # Validate pool if applicable
    if "pool_id" in transaction_data and transaction_data["pool_id"]:
        pool_id = transaction_data["pool_id"]
        if not validate_pool_id(pool_id):
            return {
                "success": False,
                "error": f"Pool {pool_id} not verified - transaction rejected"
            }
    
    # Simulate transaction
    simulation = simulate_transaction(transaction_type, transaction_data)
    if not simulation["success"]:
        return simulation
        
    # Generate transaction ID
    transaction_id = str(uuid.uuid4())
    
    # Create transaction record with preview
    transaction_record = {
        "id": transaction_id,
        "user_id": user_id,
        "wallet_address": wallet_address,
        "type": transaction_type,
        "data": transaction_data,
        "simulation": simulation,
        "created_at": datetime.now().isoformat(),
        "confirmed": False,
        "executed": False
    }
    
    # Store for confirmation
    PENDING_TRANSACTIONS[transaction_id] = transaction_record
    
    # Generate preview for user confirmation
    preview = generate_transaction_preview(transaction_record)
    
    # Return preview with transaction ID
    return {
        "success": True,
        "transaction_id": transaction_id,
        "preview": preview,
        "requires_confirmation": True,
        "confirmed": False
    }

def confirm_transaction(transaction_id: str, user_id: int) -> Dict[str, Any]:
    """
    Confirm a pending transaction.
    
    Args:
        transaction_id: Transaction ID
        user_id: User ID
        
    Returns:
        Result of confirmation
    """
    transaction = PENDING_TRANSACTIONS.get(transaction_id)
    
    if not transaction:
        return {"success": False, "error": "Transaction not found"}
        
    # Verify user ID for security
    if transaction["user_id"] != user_id:
        logger.warning(f"User {user_id} attempted to confirm transaction for user {transaction['user_id']}")
        return {"success": False, "error": "Unauthorized confirmation attempt"}
        
    # Check if already confirmed
    if transaction["confirmed"]:
        return {"success": True, "message": "Transaction already confirmed"}
        
    # Mark as confirmed
    transaction["confirmed"] = True
    PENDING_TRANSACTIONS[transaction_id] = transaction
    
    # Record in transaction history for anomaly detection
    record_transaction(user_id, transaction["type"], transaction["data"])
    
    return {
        "success": True,
        "transaction_id": transaction_id,
        "message": "Transaction confirmed, ready for execution"
    }

def execute_transaction(transaction_id: str, user_id: int) -> Dict[str, Any]:
    """
    Execute a confirmed transaction.
    
    Args:
        transaction_id: Transaction ID
        user_id: User ID
        
    Returns:
        Transaction result
    """
    transaction = PENDING_TRANSACTIONS.get(transaction_id)
    
    if not transaction:
        return {"success": False, "error": "Transaction not found"}
        
    # Verify user ID for security
    if transaction["user_id"] != user_id:
        logger.warning(f"User {user_id} attempted to execute transaction for user {transaction['user_id']}")
        return {"success": False, "error": "Unauthorized execution attempt"}
        
    # Verify confirmation
    if not transaction["confirmed"]:
        return {
            "success": False, 
            "error": "Transaction must be confirmed before execution",
            "requires_confirmation": True
        }
        
    # Check if already executed
    if transaction["executed"]:
        return {"success": True, "message": "Transaction already executed"}
        
    # Mark as executed
    transaction["executed"] = True
    transaction["executed_at"] = datetime.now().isoformat()
    PENDING_TRANSACTIONS[transaction_id] = transaction
    
    # In a real implementation, this would send the transaction to the blockchain
    # For now, we'll return the simulation results
    simulation = transaction["simulation"]
    
    # Add success data
    result = {
        "success": True,
        "transaction_id": transaction_id,
        "user_id": user_id,
        "wallet_address": transaction["wallet_address"],
        "type": transaction["type"],
        "executed_at": transaction["executed_at"],
        "message": f"Transaction executed successfully",
        **simulation
    }
    
    return result

def simulate_transaction(transaction_type: str, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate a transaction to estimate outcome.
    
    Args:
        transaction_type: Type of transaction
        transaction_data: Transaction details
        
    Returns:
        Simulation results
    """
    try:
        if transaction_type == "swap":
            from_token = transaction_data.get("from_token", transaction_data.get("token_a", "SOL"))
            to_token = transaction_data.get("to_token", transaction_data.get("token_b", "USDC"))
            amount = transaction_data.get("amount", 0)
            
            # Validate tokens
            if not validate_token(from_token) or not validate_token(to_token):
                return {"success": False, "error": "Invalid token(s)"}
                
            # Calculate fees and slippage
            fee_percent = 0.3  # 0.3% fee
            slippage = transaction_data.get("slippage_tolerance", 0.5) / 100
            
            # Simulate trade
            fees = amount * (fee_percent / 100)
            
            # Get conversion rate (this would come from an oracle in production)
            rate = 130.0 if from_token == "SOL" and to_token == "USDC" else 0.0077
            
            # Calculate expected outcome
            receive_amount = (amount - fees) * rate * (1 - slippage)
            
            return {
                "success": True,
                "from_token": from_token,
                "to_token": to_token,
                "send_amount": amount,
                "receive_amount": receive_amount,
                "fee_amount": fees,
                "slippage": slippage * 100,
                "rate": rate
            }
            
        elif transaction_type == "add_liquidity":
            pool_id = transaction_data.get("pool_id")
            token_a = transaction_data.get("token_a", "SOL")
            token_b = transaction_data.get("token_b", "USDC")
            amount = transaction_data.get("amount", 0)
            
            # Validate pool and tokens
            if pool_id and not validate_pool_id(pool_id):
                return {"success": False, "error": "Invalid pool ID"}
                
            if not validate_token(token_a) or not validate_token(token_b):
                return {"success": False, "error": "Invalid token(s)"}
                
            # Calculate fees
            fee_percent = 0.2  # 0.2% fee
            fees = amount * (fee_percent / 100)
            
            # Estimate APR (would come from API in production)
            # Use pool ID hash for consistent random value
            if pool_id:
                pool_hash = sum(ord(c) for c in pool_id) % 100
                estimated_apr = 12.0 + (pool_hash / 10.0)  # 12-22% range
            else:
                estimated_apr = 15.0 + (hash(token_a + token_b) % 35)  # 15-50% range
                
            return {
                "success": True,
                "token_a": token_a,
                "token_b": token_b,
                "amount": amount,
                "fee_amount": fees,
                "lp_tokens": amount - fees,
                "estimated_apr": estimated_apr
            }
            
        elif transaction_type == "remove_liquidity":
            pool_id = transaction_data.get("pool_id")
            token_a = transaction_data.get("token_a", "SOL")
            token_b = transaction_data.get("token_b", "USDC")
            percentage = transaction_data.get("percentage", 100)
            amount = transaction_data.get("amount", 0)
            
            # Validate pool and tokens
            if pool_id and not validate_pool_id(pool_id):
                return {"success": False, "error": "Invalid pool ID"}
                
            if not validate_token(token_a) or not validate_token(token_b):
                return {"success": False, "error": "Invalid token(s)"}
                
            # Calculate fees
            fee_percent = 0.2  # 0.2% fee
            fees = amount * (fee_percent / 100) * (percentage / 100)
            
            # Calculate token amounts
            token_a_amount = (amount * 0.5 - fees) * (percentage / 100)
            token_b_amount = (amount * 0.5 - fees) * (percentage / 100)
            
            return {
                "success": True,
                "token_a": token_a,
                "token_b": token_b,
                "percentage": percentage,
                "amount": amount,
                "fee_amount": fees,
                "token_a_amount": token_a_amount,
                "token_b_amount": token_b_amount
            }
            
        else:
            return {"success": False, "error": f"Unknown transaction type: {transaction_type}"}
            
    except Exception as e:
        logger.error(f"Error simulating transaction: {e}")
        return {"success": False, "error": f"Error simulating transaction: {str(e)}"}

def generate_transaction_preview(transaction: Dict[str, Any]) -> str:
    """
    Generate a user-friendly preview of the transaction.
    
    Args:
        transaction: Transaction data
        
    Returns:
        Formatted preview for display
    """
    transaction_type = transaction["type"]
    data = transaction["data"]
    simulation = transaction["simulation"]
    wallet_address = transaction["wallet_address"]
    
    # Format wallet address for display
    short_address = wallet_address[:6] + "..." + wallet_address[-4:] if wallet_address else "Unknown"
    
    preview = f"📝 *Transaction Preview*\n\n"
    preview += f"Wallet: `{short_address}`\n"
    preview += f"Type: {transaction_type.replace('_', ' ').title()}\n\n"
    
    if transaction_type == "swap":
        from_token = simulation["from_token"]
        to_token = simulation["to_token"]
        send_amount = simulation["send_amount"]
        receive_amount = simulation["receive_amount"]
        fee_amount = simulation["fee_amount"]
        rate = simulation["rate"]
        slippage = simulation["slippage"]
        
        preview += f"💱 *Swap Details*\n"
        preview += f"From: {send_amount:.4f} {from_token}\n"
        preview += f"To: ~{receive_amount:.4f} {to_token}\n"
        preview += f"Rate: 1 {from_token} = {rate:.4f} {to_token}\n"
        preview += f"Fees: {fee_amount:.4f} {from_token}\n"
        preview += f"Slippage Protection: {slippage}%\n"
        
    elif transaction_type == "add_liquidity":
        token_a = simulation["token_a"]
        token_b = simulation["token_b"]
        amount = simulation["amount"]
        fee_amount = simulation["fee_amount"]
        lp_tokens = simulation["lp_tokens"]
        estimated_apr = simulation["estimated_apr"]
        pool_id = data.get("pool_id", "")
        
        preview += f"🏊 *Add Liquidity Details*\n"
        preview += f"Pool: {token_a}-{token_b}\n"
        preview += f"Amount: {amount:.2f} USD\n"
        preview += f"Fees: {fee_amount:.4f} USD\n"
        preview += f"LP Tokens: ~{lp_tokens:.4f}\n"
        preview += f"Estimated APR: {estimated_apr:.2f}%\n"
        
        if pool_id:
            short_pool_id = pool_id[:6] + "..." + pool_id[-4:]
            preview += f"Pool ID: `{short_pool_id}`\n"
        
    elif transaction_type == "remove_liquidity":
        token_a = simulation["token_a"]
        token_b = simulation["token_b"]
        percentage = simulation["percentage"]
        fee_amount = simulation["fee_amount"]
        token_a_amount = simulation["token_a_amount"]
        token_b_amount = simulation["token_b_amount"]
        pool_id = data.get("pool_id", "")
        
        preview += f"🏊 *Remove Liquidity Details*\n"
        preview += f"Pool: {token_a}-{token_b}\n"
        preview += f"Percentage: {percentage}%\n"
        preview += f"Fees: {fee_amount:.4f} USD\n"
        preview += f"Expected Return:\n"
        preview += f"• {token_a_amount:.4f} {token_a}\n"
        preview += f"• {token_b_amount:.4f} {token_b}\n"
        
        if pool_id:
            short_pool_id = pool_id[:6] + "..." + pool_id[-4:]
            preview += f"Pool ID: `{short_pool_id}`\n"
    
    # Add confirmation instructions
    preview += f"\n⚠️ Press *Confirm* to execute this transaction or *Cancel* to abort."
    
    return preview

def detect_anomalies(user_id: int, transaction_type: str, transaction_data: Dict[str, Any]) -> bool:
    """
    Detect unusual transaction patterns.
    
    Args:
        user_id: User ID
        transaction_type: Transaction type
        transaction_data: Transaction details
        
    Returns:
        True if anomaly detected, False otherwise
    """
    # Get amount from transaction
    amount = transaction_data.get("amount", 0)
    if not amount:
        return False
        
    # Get transaction history for this user
    history = USER_TRANSACTION_HISTORY.get(user_id, [])
    
    # Check frequency - more than 3 transactions in 1 minute is suspicious
    recent_count = sum(1 for tx in history if time.time() - tx["timestamp"] < 60)
    if recent_count >= 3:
        logger.warning(f"Frequency anomaly: user {user_id} made {recent_count} transactions in the last minute")
        return True
        
    # Check for unusually large transactions
    if history:
        avg_amount = sum(tx["amount"] for tx in history) / len(history)
        if amount > avg_amount * 5 and amount > 500:
            logger.warning(f"Size anomaly: transaction amount {amount} is 5x larger than average {avg_amount}")
            return True
    
    return False

def record_transaction(user_id: int, transaction_type: str, transaction_data: Dict[str, Any]) -> None:
    """
    Record transaction in history for anomaly detection.
    
    Args:
        user_id: User ID
        transaction_type: Transaction type
        transaction_data: Transaction details
    """
    # Initialize history if not exists
    if user_id not in USER_TRANSACTION_HISTORY:
        USER_TRANSACTION_HISTORY[user_id] = []
        
    # Get amount from transaction
    amount = transaction_data.get("amount", 0)
    
    # Record transaction
    USER_TRANSACTION_HISTORY[user_id].append({
        "timestamp": time.time(),
        "type": transaction_type,
        "amount": amount
    })
    
    # Keep only the last 10 transactions
    if len(USER_TRANSACTION_HISTORY[user_id]) > 10:
        USER_TRANSACTION_HISTORY[user_id] = USER_TRANSACTION_HISTORY[user_id][-10:]

def cleanup_expired_sessions() -> None:
    """Periodically cleanup expired sessions and transactions."""
    now = datetime.now()
    
    # Clean up expired sessions
    expired_sessions = []
    for session_id, session in WALLET_SESSIONS.items():
        expires_at = datetime.fromisoformat(session["expires_at"])
        if now > expires_at:
            expired_sessions.append(session_id)
            
    for session_id in expired_sessions:
        logger.info(f"Removing expired session {session_id}")
        del WALLET_SESSIONS[session_id]
        
    # Clean up old transactions (older than 24 hours)
    expired_transactions = []
    for tx_id, transaction in PENDING_TRANSACTIONS.items():
        created_at = datetime.fromisoformat(transaction["created_at"])
        if (now - created_at).total_seconds() > 86400:  # 24 hours
            expired_transactions.append(tx_id)
            
    for tx_id in expired_transactions:
        logger.info(f"Removing expired transaction {tx_id}")
        del PENDING_TRANSACTIONS[tx_id]

# Initialize module
def init_wallet_security():
    """Initialize the wallet security module."""
    logger.info("Wallet security module initialized")
    # In a real implementation, this would start a background task to cleanup expired sessions
    return True