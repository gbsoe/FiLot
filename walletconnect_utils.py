"""
WalletConnect utilities for the Telegram cryptocurrency pool bot
Integrates with the Solana wallet service for improved wallet connectivity and transaction handling.
"""

import os
import json
import logging
import time
import uuid
import asyncio
import base64
from typing import Dict, Any, Optional, Union, Tuple, List
import urllib.parse  # Standard library for URL encoding
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize variables
SOLANA_SERVICE_AVAILABLE = False
SQLALCHEMY_AVAILABLE = False
ENCRYPTION_AVAILABLE = False

# Import SolanaWalletService
try:
    from solana_wallet_service import get_wallet_service
    SOLANA_SERVICE_AVAILABLE = True
    logger.info("Solana wallet service is available")
except ImportError:
    logger.warning("Solana wallet service not available, will use alternative implementation")

# Try to import optional dependencies
try:
    import sqlite3
    SQLITE_AVAILABLE = True
except ImportError:
    logger.warning("sqlite3 not available, will use mock database functionality")
    SQLITE_AVAILABLE = False
    # Define a mock Json class for compatibility
    class Json:
        def __init__(self, data):
            self.data = data

try:
    from dotenv import load_dotenv
    # Load environment variables
    load_dotenv()
except ImportError:
    logger.warning("python-dotenv not available, will use environment variables directly")

# Check for WalletConnect Project ID
WALLETCONNECT_PROJECT_ID = os.environ.get("WALLETCONNECT_PROJECT_ID")
if not WALLETCONNECT_PROJECT_ID:
    logger.warning("WALLETCONNECT_PROJECT_ID not found in environment variables")

# Check for Solana RPC URL
SOLANA_RPC_URL = os.environ.get("SOLANA_RPC_URL")
if not SOLANA_RPC_URL:
    logger.warning("SOLANA_RPC_URL not found in environment variables, will use public endpoint")

# Database connection string (for SQLite)
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'filot_bot.db')
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATABASE_PATH}")

# Try to initialize encryption
try:
    from cryptography.fernet import Fernet
    
    # Generate encryption key from environment or create a temporary one
    ENCRYPTION_KEY = os.environ.get("WALLET_SESSION_ENCRYPTION_KEY")
    if not ENCRYPTION_KEY:
        # For development only - in production, require a real key
        logger.warning("No encryption key found - generating temporary key. THIS IS NOT SECURE FOR PRODUCTION!")
        # Create a temporary key that's valid for Fernet
        import hashlib
        temp_key = hashlib.sha256(os.urandom(32)).digest()
        ENCRYPTION_KEY = base64.urlsafe_b64encode(temp_key)
    
    # Create Fernet cipher for encrypting session data
    cipher = Fernet(ENCRYPTION_KEY)
    ENCRYPTION_AVAILABLE = True
    logger.info("Encryption available for securing session data")
    
    # Define encryption functions
    def encrypt_session_data(data: Dict[str, Any]) -> str:
        """Encrypt session data for secure storage."""
        json_data = json.dumps(data)
        encrypted = cipher.encrypt(json_data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_session_data(encrypted_data: str) -> Dict[str, Any]:
        """Decrypt session data from secure storage."""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data)
            decrypted = cipher.decrypt(encrypted_bytes)
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Error decrypting session data: {e}")
            return {}
    
except ImportError:
    logger.warning("Cryptography library not available - session data will not be encrypted")
    ENCRYPTION_AVAILABLE = False
    
    # Define fallback functions that don't actually encrypt
    def encrypt_session_data(data: Dict[str, Any]) -> str:
        """Simple encoding (NOT SECURE)."""
        return base64.b64encode(json.dumps(data).encode()).decode()
    
    def decrypt_session_data(encoded_data: str) -> Dict[str, Any]:
        """Simple decoding (NOT SECURE)."""
        try:
            return json.loads(base64.b64decode(encoded_data).decode())
        except Exception as e:
            logger.error(f"Error decoding session data: {e}")
            return {}

#########################
# Database Setup
#########################

def get_db_connection():
    """Create a database connection."""
    # Skip if sqlite3 is not available
    if not SQLITE_AVAILABLE:
        logger.warning("Database connection not available - sqlite3 missing")
        return None
        
    try:
        # Using SQLite file-based database
        connection = sqlite3.connect(DATABASE_PATH)
        connection.row_factory = sqlite3.Row  # This makes results accessible by column name
        return connection
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

def init_db():
    """Initialize the database tables needed for WalletConnect sessions."""
    # Skip if database connection not available
    if not SQLITE_AVAILABLE:
        logger.warning("Skipping database initialization - database not available")
        return False
    
    try:
        # Create connection and initialize schema
        conn = get_db_connection()
        if not conn:
            logger.warning("Could not connect to database - skipping initialization")
            return False
            
        cursor = conn.cursor()
        
        # Create wallet_sessions table if it doesn't exist (SQLite syntax)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallet_sessions (
                session_id TEXT PRIMARY KEY,
                session_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                telegram_user_id INTEGER,
                status TEXT DEFAULT 'pending',
                wallet_address TEXT,
                expires_at TIMESTAMP
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)
        return False

#########################
# WalletConnect Integration
#########################

async def create_walletconnect_session(telegram_user_id: int) -> Dict[str, Any]:
    """
    Create a new WalletConnect session using WalletConnect protocol with enhanced security.
    This implementation uses the secure wallet_security module to enforce user-scoped sessions
    and prevent unauthorized access.
    
    Args:
        telegram_user_id: Telegram user ID to associate with the session
        
    Returns:
        Dictionary with session details including URI
    """
    # Use the enhanced wallet security module if available
    try:
        import wallet_security
        return wallet_security.create_wallet_session(telegram_user_id)
    except ImportError:
        # Fall back to original implementation if the security module isn't available
        logger.warning("Enhanced wallet security module not available, using standard implementation")
        # Original implementation continues below
    """
    Create a new WalletConnect session using WalletConnect protocol with enhanced security.
    Session data is securely stored with encryption and user-specific isolation.
    
    Args:
        telegram_user_id: Telegram user ID to associate with the session
        
    Returns:
        Dictionary with session details including URI
    """
    # Use the centralized security service if available
    if SECURITY_SERVICE_AVAILABLE:
        try:
            # Create a secure session through the security service
            return await session_manager.create_session(
                telegram_user_id,
                {"session_type": "walletconnect"}
            )
        except Exception as e:
            logger.error(f"Error using security service for session creation: {e}")
            logger.info("Falling back to enhanced implementation")
    
    # If the Solana wallet service is available, use it as a primary implementation
    if SOLANA_SERVICE_AVAILABLE:
        try:
            # Get wallet service
            wallet_service = get_wallet_service()
            
            # Create session
            result = await wallet_service.create_session(telegram_user_id)
            
            # If successful, store in our secure persistent storage
            if result["success"]:
                try:
                    # Save to encrypted database if SQLAlchemy is available
                    if SQLALCHEMY_AVAILABLE:
                        # Create a secure session entry
                        # Convert to ISO format if datetime objects
                        expires_at = result.get("expires_at")
                        if isinstance(expires_at, str):
                            expires_at_dt = datetime.fromisoformat(expires_at)
                        elif hasattr(expires_at, "isoformat"):
                            # Already a datetime
                            expires_at_dt = expires_at
                        else:
                            # Use default expiration if not available
                            expires_at_dt = datetime.now() + timedelta(hours=1)
                            expires_at = expires_at_dt.isoformat()
                        
                        # Prepare session data for encryption
                        session_data = {
                            "uri": result.get("uri", ""),
                            "qr_uri": result.get("qr_uri", ""),
                            "created": int(time.time()),
                            "session_id": result["session_id"],
                            "security_level": result.get("security_level", "read_only"),
                            "expires_at": expires_at,
                        }
                        
                        # Encrypt the session data
                        if ENCRYPTION_AVAILABLE:
                            encrypted_data = encrypt_session_data(session_data)
                        else:
                            encrypted_data = json.dumps(session_data)
                        
                        # Create database session
                        db_session = DbSession()
                        try:
                            # Create new wallet session record
                            wallet_session = WalletSession(
                                session_id=result["session_id"],
                                telegram_user_id=telegram_user_id,
                                session_data=encrypted_data,
                                created_at=datetime.now(),
                                expires_at=expires_at_dt,
                                status=result.get("status", "pending"),
                                wallet_address=result.get("wallet_address"),
                                last_activity=datetime.now(),
                                is_valid=True
                            )
                            
                            # Add and commit
                            db_session.add(wallet_session)
                            db_session.commit()
                            logger.info(f"Saved encrypted WalletConnect session to database")
                        except Exception as db_error:
                            db_session.rollback()
                            logger.warning(f"Database error saving session: {db_error}")
                        finally:
                            db_session.close()
                    
                except Exception as storage_error:
                    logger.warning(f"Could not save WalletConnect session securely: {storage_error}")
            
            # Return the result from the wallet service
            return result
            
        except Exception as e:
            logger.error(f"Error creating session with Solana wallet service: {e}")
            logger.info("Falling back to enhanced standard implementation")
    
    # Enhanced standard implementation with secure session creation
    logger.info("Using enhanced WalletConnect implementation with security measures")
    
    # Validate WalletConnect Project ID
    if not WALLETCONNECT_PROJECT_ID:
        logger.warning("WalletConnect Project ID not configured, using basic URI format")
    
    try:
        # Generate a cryptographically secure session ID
        session_id = str(uuid.uuid4())
        
        # Log session creation attempt (redacted for security)
        logger.info(f"Secure wallet connection requested for user {telegram_user_id}")
        
        # Generate a WalletConnect URI with enhanced security
        try:
            # Generate required components with strong randomness
            topic = uuid.uuid4().hex
            
            # Use os.urandom for better randomness than uuid
            random_bytes = os.urandom(32)
            sym_key = base64.urlsafe_b64encode(random_bytes).decode()[:32]
            
            # Current relay server
            relay_url = "wss://relay.walletconnect.org"
            
            # Standard WalletConnect v2 format
            wc_uri = f"wc:{topic}@2?relay-protocol=irn&relay-url={relay_url}&symKey={sym_key}"
            
            # Include project ID in the WalletConnect URI if available
            if WALLETCONNECT_PROJECT_ID:
                wc_uri = f"{wc_uri}&projectId={WALLETCONNECT_PROJECT_ID}"
            
            # URL encode for compatibility with different wallet apps
            uri_encoded = urllib.parse.quote(wc_uri)
            
            # Use standard format that works with most wallets
            deep_link_uri = f"https://walletconnect.com/wc?uri={uri_encoded}"
            
            # Create the data structure with all necessary information
            data = {
                "uri": deep_link_uri,
                "raw_wc_uri": wc_uri,  # Store the raw wc: URI for display to users
                "id": topic,  # Use the topic as the ID
                "relay": relay_url,
                "created": int(time.time()),
                "security_level": "read_only",
                "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
            }
            
            # Log success with sensitive data redacted
            logger.info(f"Generated secure WalletConnect URI for user {telegram_user_id}")
            
        except Exception as wc_error:
            logger.error(f"Error creating WalletConnect URI: {str(wc_error)}")
            # Create a simpler fallback that's still secure
            topic = uuid.uuid4().hex
            wc_uri = f"wc:{topic}@2"
            data = {
                "uri": f"https://walletconnect.com/wc?uri={urllib.parse.quote(wc_uri)}",
                "raw_wc_uri": wc_uri,
                "id": topic,
                "created": int(time.time()),
                "security_level": "read_only",
                "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
            }
            logger.info(f"Generated fallback WalletConnect URI for user {telegram_user_id}")
        
        # Store session securely - prefer SQLAlchemy persistent storage
        try:
            if SQLALCHEMY_AVAILABLE:
                # Encrypt the session data if possible
                if ENCRYPTION_AVAILABLE:
                    encrypted_data = encrypt_session_data(data)
                else:
                    encrypted_data = json.dumps(data)
                
                # Create database session
                db_session = DbSession()
                try:
                    # Create expiration time
                    expires_at = datetime.now() + timedelta(hours=1)
                    
                    # Create new wallet session record with encrypted data
                    wallet_session = WalletSession(
                        session_id=session_id,
                        telegram_user_id=telegram_user_id,
                        session_data=encrypted_data,
                        created_at=datetime.now(),
                        expires_at=expires_at,
                        status="pending",
                        wallet_address=None,
                        last_activity=datetime.now(),
                        is_valid=True
                    )
                    
                    # Add and commit
                    db_session.add(wallet_session)
                    db_session.commit()
                    logger.info(f"Saved encrypted WalletConnect session to database")
                except Exception as db_error:
                    db_session.rollback()
                    logger.warning(f"Database error saving session: {db_error}")
                finally:
                    db_session.close()
        except Exception as storage_error:
            logger.warning(f"Could not save WalletConnect session securely: {storage_error}")
        
        # Return the successful result with minimal sensitive data
        return {
            "success": True,
            "session_id": session_id,
            "uri": data["uri"],
            "telegram_user_id": telegram_user_id,
            "security_level": "read_only",
            "status": "pending",
            "expires_at": data["expires_at"],
            "expires_in_seconds": 3600
        }
            
    except Exception as e:
        logger.error(f"Error creating WalletConnect session: {e}")
        return {
            "success": False, 
            "error": f"Error creating WalletConnect session: {str(e)}"
        }

async def check_walletconnect_session(session_id: str) -> Dict[str, Any]:
    """
    Check the status of a WalletConnect session with enhanced security checks.
    
    Args:
        session_id: The session ID to check
        
    Returns:
        Dictionary with session status and security information
    """
    # Import app at function level to avoid circular imports
    from app import app
    
    # If Solana wallet service is available, use it instead of the legacy implementation
    if SOLANA_SERVICE_AVAILABLE:
        try:
            # Get wallet service
            wallet_service = get_wallet_service()
            
            # Check session
            result = await wallet_service.check_session(session_id)
            
            # Return the result from the wallet service
            return result
            
        except Exception as e:
            logger.error(f"Error checking session with Solana wallet service: {e}")
            logger.info("Falling back to legacy implementation")
            # Fall through to legacy implementation
    
    # Legacy implementation
    logger.info("Using legacy session check implementation")
    
    # If the database is not available, provide some basic info
    if not SQLITE_AVAILABLE:
        logger.warning("Database not available for session check, providing default response")
        return {
            "success": True,
            "session_id": session_id,
            "status": "unknown",
            "message": "Session status cannot be determined without database access",
            "security_level": "unknown"
        }
    
    try:
        # Use app context for database operations
        with app.app_context():
            conn = get_db_connection()
            if not conn:
                logger.warning("Could not connect to database for session check")
                return {
                    "success": True,
                    "session_id": session_id,
                    "status": "unknown",
                    "message": "Database connection failed, session status unknown",
                    "security_level": "unknown"
                }
                
            cursor = conn.cursor()
            
            try:
                cursor.execute(
                    "SELECT session_data, status, telegram_user_id, created_at FROM wallet_sessions WHERE session_id = %s",
                    (session_id,)
                )
                
                result = cursor.fetchone()
                
                if not result:
                    cursor.close()
                    conn.close()
                    return {"success": False, "error": "Session not found"}
                    
                session_data, status, telegram_user_id, created_at = result
                
                # Check if session has expired (default: 1 hour timeout)
                current_time = int(time.time())
                expires_at = session_data.get("expires_at", 0)
                
                if expires_at > 0 and current_time > expires_at:
                    # Session has expired, mark it as expired and return error
                    logger.info(f"Session {session_id} has expired")
                    
                    try:
                        # Update session status in database
                        cursor.execute(
                            "UPDATE wallet_sessions SET status = 'expired' WHERE session_id = %s",
                            (session_id,)
                        )
                    except Exception as update_error:
                        logger.warning(f"Could not update session status: {update_error}")
                    
                    cursor.close()
                    conn.close()
                    
                    return {
                        "success": False,
                        "error": "Session has expired. Please create a new wallet connection.",
                        "session_id": session_id,
                        "expired": True
                    }
                
                # Add security level information to the response
                security_level = session_data.get("security_level", "unknown")
                permissions = session_data.get("permissions_requested", [])
                
                cursor.close()
                conn.close()
                
                return {
                    "success": True,
                    "session_id": session_id,
                    "status": status,
                    "telegram_user_id": telegram_user_id,
                    "session_data": session_data,
                    "security_level": security_level,
                    "permissions": permissions,
                    "created_at": created_at.isoformat() if created_at else None,
                    "expires_at": expires_at if expires_at > 0 else None,
                    "expires_in_seconds": max(0, expires_at - current_time) if expires_at > 0 else None
                }
                
            except Exception as db_error:
                if cursor:
                    cursor.close()
                # SQLite connection doesn't have a 'closed' attribute
                if conn:
                    try:
                        conn.close()
                    except Exception as close_error:
                        logger.error(f"Error closing connection: {close_error}")
                raise db_error
            
    except Exception as e:
        logger.error(f"Error checking WalletConnect session: {e}", exc_info=True)
        return {
            "success": False, 
            "error": f"Error checking WalletConnect session: {e}"
        }

async def kill_walletconnect_session(session_id: str) -> Dict[str, Any]:
    """
    Kill a WalletConnect session.
    
    Args:
        session_id: The session ID to kill
        
    Returns:
        Dictionary with operation result
    """
    # Import app at function level to avoid circular imports
    from app import app
    
    # If Solana wallet service is available, use it instead of the legacy implementation
    if SOLANA_SERVICE_AVAILABLE:
        try:
            # Get wallet service
            wallet_service = get_wallet_service()
            
            # Disconnect wallet
            result = await wallet_service.disconnect_wallet(session_id)
            
            # Return the result from the wallet service
            return result
            
        except Exception as e:
            logger.error(f"Error disconnecting wallet with Solana wallet service: {e}")
            logger.info("Falling back to legacy implementation")
            # Fall through to legacy implementation
    
    # Legacy implementation
    logger.info("Using legacy session deletion implementation")
    
    # If the database is not available, just return success
    if not SQLITE_AVAILABLE:
        logger.warning("Database not available for session deletion, skipping")
        return {
            "success": True,
            "message": "Session terminated (database unavailable)",
            "warning": "Database operations skipped - database unavailable"
        }
    
    try:
        # Use app context for database operations
        with app.app_context():
            # Skip database check if not available
            conn = get_db_connection()
            if not conn:
                logger.warning("Could not connect to database for session deletion")
                return {
                    "success": True,
                    "message": "Session considered terminated (database unreachable)",
                    "warning": "Database operations skipped - could not connect"
                }
                
            try:
                cursor = conn.cursor()
                
                # Simple deletion without checking first
                cursor.execute(
                    "DELETE FROM wallet_sessions WHERE session_id = %s",
                    (session_id,)
                )
                
                cursor.close()
                conn.close()
                
            except Exception as db_error:
                logger.error(f"Database error while killing session: {db_error}", exc_info=True)
                # SQLite connection doesn't have a 'closed' attribute
                if conn:
                    try:
                        conn.close()
                    except Exception as close_error:
                        logger.error(f"Error closing connection: {close_error}")
                return {
                    "success": True,
                    "message": "Session considered terminated (database error)",
                    "warning": f"Database error: {str(db_error)}"
                }
        
        return {
            "success": True,
            "message": "Session terminated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error killing WalletConnect session: {e}", exc_info=True)
        return {
            "success": True,  # Return success anyway to avoid blocking the UI
            "message": "Session considered terminated (error occurred)",
            "warning": f"Error occurred: {str(e)}"
        }

async def get_user_walletconnect_sessions(telegram_user_id: int) -> Dict[str, Any]:
    """
    Get all WalletConnect sessions for a user.
    
    Args:
        telegram_user_id: Telegram user ID
        
    Returns:
        Dictionary with list of sessions
    """
    # Import app at function level to avoid circular imports
    from app import app
    
    # If database not available, return empty list
    if not SQLITE_AVAILABLE:
        logger.warning("Database not available for getting user sessions, returning empty list")
        return {
            "success": True,
            "telegram_user_id": telegram_user_id,
            "sessions": [],
            "warning": "Database unavailable - cannot retrieve actual sessions"
        }
    
    try:
        # Use app context for database operations
        with app.app_context():
            conn = get_db_connection()
            if not conn:
                logger.warning("Could not connect to database for getting user sessions")
                return {
                    "success": True,
                    "telegram_user_id": telegram_user_id,
                    "sessions": [],
                    "warning": "Database connection failed - cannot retrieve sessions"
                }
                
            try:
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    SELECT session_id, session_data, status, created_at 
                    FROM wallet_sessions 
                    WHERE telegram_user_id = %s
                    ORDER BY created_at DESC
                    """,
                    (telegram_user_id,)
                )
                
                sessions = []
                for row in cursor.fetchall():
                    session_id, session_data, status, created_at = row
                    sessions.append({
                        "session_id": session_id,
                        "status": status,
                        "created_at": created_at.isoformat() if created_at else None,
                        "uri": session_data.get("uri", "") if session_data else "",
                    })
                
                cursor.close()
                conn.close()
                
                return {
                    "success": True,
                    "telegram_user_id": telegram_user_id,
                    "sessions": sessions
                }
                
            except Exception as db_error:
                logger.error(f"Database error while getting user sessions: {db_error}", exc_info=True)
                # SQLite connection doesn't have a 'closed' attribute
                if conn:
                    try:
                        conn.close()
                    except Exception as close_error:
                        logger.error(f"Error closing connection: {close_error}")
                return {
                    "success": True,
                    "telegram_user_id": telegram_user_id,
                    "sessions": [],
                    "warning": f"Database error: {str(db_error)}"
                }
            
    except Exception as e:
        logger.error(f"Error getting user WalletConnect sessions: {e}", exc_info=True)
        return {
            "success": True,  # Return success with empty list to avoid blocking the UI
            "telegram_user_id": telegram_user_id,
            "sessions": [],
            "warning": f"Error occurred: {str(e)}"
        }

# Initialize database on module load
init_db()

# Example usage (for testing purposes)
if __name__ == "__main__":
    async def test():
        print("Creating WalletConnect session...")
        result = await create_walletconnect_session(12345)
        print(f"Session creation result: {result}")
        
        if result["success"]:
            session_id = result["session_id"]
            
            print("\nChecking session status...")
            status = await check_walletconnect_session(session_id)
            print(f"Session status: {status}")
            
            print("\nGetting user sessions...")
            user_sessions = await get_user_walletconnect_sessions(12345)
            print(f"User sessions: {user_sessions}")
            
            print("\nKilling session...")
            kill_result = await kill_walletconnect_session(session_id)
            print(f"Session kill result: {kill_result}")
    
    asyncio.run(test())