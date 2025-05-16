"""
Wallet security module for FiLot Telegram bot.

This module provides comprehensive security controls for wallet operations,
implementing the security requirements identified in the security audit.
"""

import logging
import os
import json
import base64
import hashlib
import time
import uuid
from typing import Dict, Any, List, Optional, Union, Tuple

# Configure logging
logger = logging.getLogger(__name__)

# Define constants
MAX_TRANSACTION_AMOUNT = 100000  # $100k maximum transaction
DEFAULT_SLIPPAGE_TOLERANCE = 0.5  # 0.5% default slippage tolerance
MAX_SLIPPAGE_TOLERANCE = 5.0     # 5% maximum slippage tolerance
SESSION_TIMEOUT = 3600           # 1 hour session timeout

# Transaction registry
# Format: {transaction_id: {"user_id": user_id, "data": data, "created_at": timestamp}}
PENDING_TRANSACTIONS = {}

# Wallet session registry
# Format: {session_id: {"user_id": user_id, "wallet_address": address, "created_at": timestamp}}
WALLET_SESSIONS = {}

# Whitelist of allowed pools (would be loaded from a database in production)
WHITELISTED_POOLS = [
    "SOL/USDC",
    "BTC/USDC",
    "ETH/USDC",
    "RAY/USDC",
    "ORCA/USDC"
]

# Initialize encryption
ENCRYPTION_AVAILABLE = False
ENCRYPTION_KEY = os.environ.get("WALLET_ENCRYPTION_KEY")
cipher = None  # Initialize cipher as None

# Try to set up encryption
try:
    # Import here to handle potential import errors cleanly
    from cryptography.fernet import Fernet
    ENCRYPTION_AVAILABLE = True
except ImportError:
    logger.warning("cryptography package not available, sensitive data will not be encrypted")

# Initialize encryption key
if ENCRYPTION_AVAILABLE:
    if not ENCRYPTION_KEY:
        # For development only - in production, require a real key
        logger.warning("No encryption key found - generating temporary key. THIS IS NOT SECURE FOR PRODUCTION!")
        # Create a temporary key that's valid for Fernet
        temp_key = hashlib.sha256(os.urandom(32)).digest()
        ENCRYPTION_KEY = base64.urlsafe_b64encode(temp_key)
    
    # Create cipher for encryption
    try:
        from cryptography.fernet import Fernet
        cipher = Fernet(ENCRYPTION_KEY)
    except (ImportError, Exception) as e:
        logger.error(f"Failed to initialize encryption: {e}")
        ENCRYPTION_AVAILABLE = False

def encrypt_data(data: Any) -> str:
    """
    Encrypt sensitive data.
    
    Args:
        data: Data to encrypt
        
    Returns:
        Encrypted string
    """
    if not ENCRYPTION_AVAILABLE or cipher is None:
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
    if not ENCRYPTION_AVAILABLE or cipher is None:
        try:
            decoded = base64.b64decode(encrypted_data.encode())
            return json.loads(decoded.decode())
        except Exception as e:
            logger.error(f"Error decoding unencrypted data: {e}")
            return {}
    
    try:
        decoded = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted = cipher.decrypt(decoded)
        return json.loads(decrypted.decode())
    except Exception as e:
        logger.error(f"Error decrypting data: {e}")
        return {}

def validate_wallet_address(address: str) -> bool:
    """
    Validate a Solana wallet address.
    
    Args:
        address: Wallet address to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Basic validation for demo purposes
    if not address or not isinstance(address, str):
        return False
        
    # Check for minimum length and format
    if len(address) < 32 or len(address) > 44:
        return False
        
    # Additional validation would be implemented in production
    # This might include Base58 validation and checksum verification
        
    return True

def validate_transaction_parameters(tx_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate transaction parameters for security.
    
    Args:
        tx_data: Transaction data
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate transaction type
    tx_type = tx_data.get("transaction_type")
    if not tx_type or tx_type not in ["add_liquidity", "remove_liquidity", "swap"]:
        return False, "Invalid transaction type"
        
    # Validate amount is reasonable
    amount = tx_data.get("amount", 0)
    if amount <= 0 or amount > MAX_TRANSACTION_AMOUNT:
        return False, f"Invalid amount: {amount}"
        
    # Validate pool is whitelisted (if applicable)
    if tx_type in ["add_liquidity", "remove_liquidity"]:
        token_a = tx_data.get("token_a", "")
        token_b = tx_data.get("token_b", "")
        pool = f"{token_a}/{token_b}"
        
        if pool not in WHITELISTED_POOLS:
            return False, f"Pool {pool} is not whitelisted"
            
    # Validate slippage tolerance
    slippage = tx_data.get("slippage_tolerance", DEFAULT_SLIPPAGE_TOLERANCE)
    if slippage < 0 or slippage > MAX_SLIPPAGE_TOLERANCE:
        return False, f"Invalid slippage tolerance: {slippage}%"
        
    return True, ""

def create_wallet_session(user_id: int) -> Dict[str, Any]:
    """
    Create a secure wallet session for a user.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        Session details including URI
    """
    # Generate a unique session ID
    session_id = str(uuid.uuid4())
    
    # Create session data
    session_data = {
        "user_id": user_id,
        "created_at": time.time(),
        "wallet_address": None,  # Will be populated when wallet connects
        "session_id": session_id,
        "uri": f"https://wallet.connect.example.com/session/{session_id}"  # Example URI
    }
    
    # Store session
    WALLET_SESSIONS[session_id] = session_data
    
    # Clean up expired sessions
    cleanup_expired_sessions()
    
    return session_data

def check_session(session_id: str) -> Dict[str, Any]:
    """
    Check status of a wallet session.
    
    Args:
        session_id: Session ID
        
    Returns:
        Session status and details
    """
    # Clean up expired sessions first
    cleanup_expired_sessions()
    
    # Check if session exists
    if session_id not in WALLET_SESSIONS:
        return {"success": False, "error": "Session not found or expired"}
        
    # Get session data
    session = WALLET_SESSIONS[session_id]
    
    # Check if wallet is connected
    if not session.get("wallet_address"):
        return {
            "success": True,
            "status": "pending",
            "message": "Waiting for wallet connection"
        }
        
    # Session is active with connected wallet
    return {
        "success": True,
        "status": "connected",
        "wallet_address": session.get("wallet_address"),
        "user_id": session.get("user_id")
    }

def create_transaction(
    user_id: int,
    wallet_address: str,
    transaction_type: str,
    transaction_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a secure transaction that requires explicit confirmation.
    
    Args:
        user_id: Telegram user ID
        wallet_address: User's wallet address
        transaction_type: Type of transaction (add_liquidity, remove_liquidity, swap)
        transaction_data: Transaction details
        
    Returns:
        Transaction details including confirmation status
    """
    # Verify wallet address
    if not validate_wallet_address(wallet_address):
        return {
            "success": False,
            "error": "Invalid wallet address"
        }
        
    # Complete the transaction data
    complete_tx_data = {
        **transaction_data,
        "transaction_type": transaction_type,
        "user_id": user_id,
        "wallet_address": wallet_address,
        "created_at": time.time()
    }
    
    # Apply security validation
    is_valid, error_message = validate_transaction_parameters(complete_tx_data)
    if not is_valid:
        return {
            "success": False,
            "error": error_message
        }
        
    # Generate transaction ID
    transaction_id = str(uuid.uuid4())
    
    # Store pending transaction
    PENDING_TRANSACTIONS[transaction_id] = {
        "user_id": user_id,
        "data": complete_tx_data,
        "created_at": time.time(),
        "status": "pending",
        "transaction_id": transaction_id
    }
    
    # Clean up expired transactions
    cleanup_expired_transactions()
    
    # Return transaction details
    return {
        "success": True,
        "status": "pending_confirmation",
        "transaction_id": transaction_id,
        "message": "Transaction created, awaiting confirmation",
        "details": {
            "transaction_type": transaction_type,
            "wallet_address": wallet_address,
            **transaction_data
        }
    }

def confirm_transaction(transaction_id: str, user_id: int) -> bool:
    """
    Confirm a pending transaction.
    
    Args:
        transaction_id: Transaction ID
        user_id: User ID confirming the transaction
        
    Returns:
        True if confirmed, False otherwise
    """
    # Check if transaction exists
    if transaction_id not in PENDING_TRANSACTIONS:
        logger.warning(f"Transaction {transaction_id} not found or expired")
        return False
        
    # Get transaction
    transaction = PENDING_TRANSACTIONS[transaction_id]
    
    # Security check: Ensure the user confirming is the one who initiated
    if transaction["user_id"] != user_id:
        logger.warning(f"User {user_id} tried to confirm transaction for user {transaction['user_id']}")
        return False
        
    # Mark as confirmed
    transaction["status"] = "confirmed"
    return True

def execute_transaction(transaction_id: str, user_id: int) -> Dict[str, Any]:
    """
    Execute a confirmed transaction.
    
    Args:
        transaction_id: Transaction ID
        user_id: User ID executing the transaction
        
    Returns:
        Transaction result
    """
    # Check if transaction exists
    if transaction_id not in PENDING_TRANSACTIONS:
        return {
            "success": False,
            "error": "Transaction not found or expired"
        }
        
    # Get transaction
    transaction = PENDING_TRANSACTIONS[transaction_id]
    tx_data = transaction["data"]
    
    # Security check: Ensure the user executing is the one who initiated
    if transaction["user_id"] != user_id:
        logger.warning(f"User {user_id} tried to execute transaction for user {transaction['user_id']}")
        return {
            "success": False,
            "error": "Unauthorized transaction execution"
        }
        
    # Check if transaction is confirmed
    if transaction["status"] != "confirmed":
        return {
            "success": False,
            "error": "Transaction not confirmed"
        }
        
    # Execute transaction based on type (simulated)
    transaction_type = tx_data.get("transaction_type")
    
    # In a real implementation, this would call the appropriate blockchain transaction
    # For this security implementation, we simulate success
    
    # Mark as executed
    transaction["status"] = "executed"
    
    # Remove from pending transactions
    del PENDING_TRANSACTIONS[transaction_id]
    
    # Return success with transaction details
    return {
        "success": True,
        "transaction_id": transaction_id,
        "message": f"Transaction executed successfully: {transaction_type}",
        "details": tx_data
    }

def cleanup_expired_sessions() -> None:
    """Clean up expired wallet sessions."""
    current_time = time.time()
    expired_sessions = []
    
    # Find expired sessions
    for session_id, session in WALLET_SESSIONS.items():
        if current_time - session["created_at"] > SESSION_TIMEOUT:
            expired_sessions.append(session_id)
    
    # Remove expired sessions
    for session_id in expired_sessions:
        logger.info(f"Removing expired wallet session: {session_id}")
        WALLET_SESSIONS.pop(session_id, None)

def cleanup_expired_transactions() -> None:
    """Clean up expired pending transactions."""
    current_time = time.time()
    expired_transactions = []
    
    # Find expired transactions (older than 10 minutes)
    for tx_id, tx_data in PENDING_TRANSACTIONS.items():
        if current_time - tx_data["created_at"] > 600:  # 10 minutes
            expired_transactions.append(tx_id)
    
    # Remove expired transactions
    for tx_id in expired_transactions:
        logger.info(f"Removing expired transaction: {tx_id}")
        PENDING_TRANSACTIONS.pop(tx_id, None)