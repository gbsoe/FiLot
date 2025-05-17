"""
Direct profile setting fix for the FiLot Telegram bot.

This module bypasses the callback handler and directly sets the user's profile
in the database.
"""

import logging
import time
from typing import Dict, Any, Optional
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

def set_user_profile(user_id: int, profile_type: str) -> Dict[str, Any]:
    """
    Directly set a user's profile in the database.
    
    Args:
        user_id: The user ID
        profile_type: The profile type ('high-risk' or 'stable')
        
    Returns:
        Dictionary with status information
    """
    logger.info(f"Direct profile fix: Setting user {user_id} profile to {profile_type}")
    
    try:
        # Import the necessary modules
        from app import db
        from models import User
        
        # Check if we have a valid profile type
        if profile_type not in ['high-risk', 'stable', 'moderate']:
            logger.warning(f"Invalid profile type: {profile_type}, defaulting to 'moderate'")
            profile_type = 'moderate'
        
        # Create a simplified function to update or create the user
        def update_or_create_user():
            # Get the user or create a new one (using raw SQL for reliability)
            import sqlite3
            
            try:
                # Connect to the database directly
                db_path = 'filot_bot.db'
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Check if the user exists
                cursor.execute('SELECT id, risk_profile FROM users WHERE id = ?', (user_id,))
                user_row = cursor.fetchone()
                
                if user_row:
                    # User exists, update profile
                    old_profile = user_row[1]
                    cursor.execute('UPDATE users SET risk_profile = ? WHERE id = ?', (profile_type, user_id))
                    conn.commit()
                    logger.info(f"Direct SQL: Updated user {user_id} profile from '{old_profile}' to '{profile_type}'")
                else:
                    # User doesn't exist, create a new one
                    cursor.execute(
                        'INSERT INTO users (id, risk_profile, created_at, last_active) VALUES (?, ?, datetime("now"), datetime("now"))',
                        (user_id, profile_type)
                    )
                    conn.commit()
                    logger.info(f"Direct SQL: Created new user {user_id} with '{profile_type}' profile")
                
                conn.close()
                return True
            except Exception as sql_err:
                logger.error(f"Direct SQL error: {sql_err}")
                logger.error(traceback.format_exc())
                return False
        
        # First try with SQLAlchemy ORM
        try:
            # Get the user or create a new one
            user = db.session.query(User).filter_by(id=user_id).first()
            
            if user:
                # User exists, update profile
                old_profile = user.risk_profile
                user.risk_profile = profile_type
                db.session.commit()
                logger.info(f"Direct profile fix: Updated user {user_id} from '{old_profile}' to '{profile_type}'")
            else:
                # User doesn't exist, create a new one
                new_user = User(id=user_id)  # Use the correct constructor
                setattr(new_user, 'risk_profile', profile_type)  # Set attribute using setattr
                db.session.add(new_user)
                db.session.commit()
                logger.info(f"Direct profile fix: Created new user {user_id} with '{profile_type}' profile")
                
            # Return success
            return {
                "success": True,
                "user_id": user_id,
                "profile": profile_type,
                "message": f"Profile set to {profile_type}"
            }
        except Exception as orm_err:
            logger.warning(f"ORM approach failed: {orm_err}, trying direct SQL")
            
            # Try direct SQL as a fallback
            if update_or_create_user():
                return {
                    "success": True,
                    "user_id": user_id,
                    "profile": profile_type,
                    "message": f"Profile set to {profile_type} using direct SQL"
                }
            else:
                raise Exception(f"Both ORM and direct SQL approaches failed: {orm_err}")
        
    except Exception as e:
        logger.error(f"Direct profile fix: Error setting profile for {user_id}: {e}")
        logger.error(traceback.format_exc())
        
        # Return failure
        return {
            "success": False,
            "user_id": user_id,
            "error": str(e)
        }

def process_profile_callback(callback_data: str, user_id: int, chat_id: int) -> Dict[str, Any]:
    """
    Process a profile callback directly.
    
    Args:
        callback_data: The callback data from the button
        user_id: The user ID
        chat_id: The chat ID
        
    Returns:
        Dictionary with response data
    """
    logger.info(f"Direct profile fix: Processing {callback_data} for user {user_id}")
    
    try:
        # Extract profile type from callback data
        if callback_data == "high-risk" or callback_data == "profile_high-risk":
            profile_type = "high-risk"
        elif callback_data == "stable" or callback_data == "profile_stable":
            profile_type = "stable"
        else:
            logger.warning(f"Direct profile fix: Unknown profile type in {callback_data}")
            return {
                "success": False,
                "error": f"Unknown profile type: {callback_data}",
                "chat_id": chat_id
            }
            
        # Set the profile
        result = set_user_profile(user_id, profile_type)
        
        # Prepare response for Telegram
        if result.get("success", False):
            # Create appropriate emoji and message
            emoji = "🔴" if profile_type == "high-risk" else "🟢"
            
            if profile_type == "high-risk":
                message = (
                    f"{emoji} *High-Risk Profile Selected*\n\n"
                    f"Your investment recommendations will now focus on:\n"
                    f"• Higher APR opportunities\n"
                    f"• Newer pools with growth potential\n"
                    f"• More volatile but potentially rewarding options\n\n"
                    f"_Note: Higher returns come with increased risk_"
                )
            else:  # stable
                message = (
                    f"{emoji} *Stable Profile Selected*\n\n"
                    f"Your investment recommendations will now focus on:\n"
                    f"• Established, reliable pools\n"
                    f"• Lower volatility options\n"
                    f"• More consistent but potentially lower APR\n\n"
                    f"_Note: Stability typically means more moderate returns_"
                )
                
            # Return success response
            return {
                "success": True,
                "action": "profile_set",
                "profile": profile_type,
                "message": message,
                "chat_id": chat_id
            }
        else:
            # Return error response
            return {
                "success": False,
                "action": "error",
                "message": f"Sorry, there was an error setting your profile. Please try again in a moment. Error: {result.get('error', 'Unknown error')}",
                "chat_id": chat_id
            }
            
    except Exception as e:
        logger.error(f"Direct profile fix: Error processing profile callback: {e}")
        logger.error(traceback.format_exc())
        
        # Return error response
        return {
            "success": False,
            "action": "error",
            "message": "Sorry, there was an error processing your profile selection. Please try again in a moment.",
            "error": str(e),
            "chat_id": chat_id
        }