"""
Fixed profile handler for FiLot Telegram bot.

This module provides a specialized profile handler that fixes issues with
the high-risk and stable profile buttons.
"""

import logging
import traceback
import time
from typing import Dict, Any, Optional, List, Tuple
import json
from sqlalchemy.exc import NoResultFound

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Keep track of profile setting attempts to prevent rapid clicking
profile_attempts = {}  # {user_id: last_attempt_time}
PROFILE_ATTEMPT_THRESHOLD = 2.0  # seconds

def handle_profile_setting(user_id: int, chat_id: int, profile_type: str) -> Dict[str, Any]:
    """
    Handle profile setting with enhanced error handling.
    
    Args:
        user_id: The Telegram user ID
        chat_id: The Telegram chat ID
        profile_type: The profile type ('high-risk' or 'stable')
        
    Returns:
        Dict with response data
    """
    try:
        logger.info(f"User {user_id} selecting profile: {profile_type}")
        
        # Check for rate limiting (prevent rapid clicks)
        current_time = time.time()
        if user_id in profile_attempts:
            time_diff = current_time - profile_attempts[user_id]
            
            # If clicking too rapidly, throttle
            if time_diff < PROFILE_ATTEMPT_THRESHOLD:
                logger.warning(f"User {user_id} clicking profile buttons too rapidly ({time_diff:.2f}s)")
                return {
                    "success": False,
                    "action": "error",
                    "message": "Please wait a moment before changing your profile again.",
                    "throttled": True,
                    "chat_id": chat_id
                }
        
        # Record this attempt
        profile_attempts[user_id] = current_time
        
        # Handle the profile setting based on type
        if profile_type == "high-risk":
            return set_high_risk_profile(user_id, chat_id)
        elif profile_type == "stable":
            return set_stable_profile(user_id, chat_id)
        else:
            logger.error(f"Unknown profile type: {profile_type}")
            return {
                "success": False,
                "action": "error",
                "message": "Unknown profile type. Please select either 'High Risk' or 'Stable'.",
                "chat_id": chat_id
            }
            
    except Exception as e:
        logger.error(f"Error setting profile: {e}")
        logger.error(traceback.format_exc())
        
        # Fallback message if something goes wrong
        return {
            "success": False,
            "action": "error",
            "message": "Sorry, there was an error setting your profile. Please try again in a moment.",
            "error": str(e),
            "chat_id": chat_id
        }

def set_high_risk_profile(user_id: int, chat_id: int) -> Dict[str, Any]:
    """
    Set a user's profile to high-risk.
    
    Args:
        user_id: The Telegram user ID
        chat_id: The Telegram chat ID
        
    Returns:
        Dict with response data
    """
    try:
        # Import the database modules
        from app import db
        from models import User
        
        # Check if the user exists
        try:
            user = db.session.query(User).filter_by(telegram_id=user_id).one()
            old_profile = user.risk_profile
            
            # Update the user's profile
            setattr(user, 'risk_profile', 'high-risk')
            db.session.commit()
            
            logger.info(f"Updated user {user_id} profile from '{old_profile}' to 'high-risk'")
        except NoResultFound:
            # Create a new user with the id field (which is the telegram_id)
            new_user = User(id=user_id)
            setattr(new_user, 'risk_profile', 'high-risk')
            db.session.add(new_user)
            db.session.commit()
            
            logger.info(f"Created new user {user_id} with 'high-risk' profile")
        
        # Return success response
        return {
            "success": True,
            "action": "profile_set",
            "profile": "high-risk",
            "message": "✅ Your profile has been set to High Risk.\n\nThis profile focuses on pools with potentially higher returns but may have higher volatility. You'll receive recommendations for pools with higher APR but potentially more risk.",
            "chat_id": chat_id
        }
        
    except Exception as e:
        logger.error(f"Error setting high-risk profile: {e}")
        logger.error(traceback.format_exc())
        
        # Try an alternative approach if the first one fails
        try:
            # Import database utils directly
            import db_utils
            db_utils.set_user_profile(user_id, "high-risk")
            
            logger.info(f"Set user {user_id} profile to 'high-risk' using db_utils")
            
            # Return success response
            return {
                "success": True,
                "action": "profile_set",
                "profile": "high-risk",
                "message": "✅ Your profile has been set to High Risk.\n\nThis profile focuses on pools with potentially higher returns but may have higher volatility. You'll receive recommendations for pools with higher APR but potentially more risk.",
                "chat_id": chat_id
            }
        except Exception as inner_e:
            logger.error(f"Alternative approach also failed: {inner_e}")
            logger.error(traceback.format_exc())
        
        # Fallback message if something goes wrong
        return {
            "success": False,
            "action": "error",
            "message": "Sorry, there was an error setting your profile to High Risk. Please try again in a moment.",
            "error": str(e),
            "chat_id": chat_id
        }

def set_stable_profile(user_id: int, chat_id: int) -> Dict[str, Any]:
    """
    Set a user's profile to stable.
    
    Args:
        user_id: The Telegram user ID
        chat_id: The Telegram chat ID
        
    Returns:
        Dict with response data
    """
    try:
        # Import the database modules
        from app import db
        from models import User
        
        # Check if the user exists
        try:
            user = db.session.query(User).filter_by(telegram_id=user_id).one()
            old_profile = user.risk_profile
            
            # Update the user's profile
            setattr(user, 'risk_profile', 'stable')
            db.session.commit()
            
            logger.info(f"Updated user {user_id} profile from '{old_profile}' to 'stable'")
        except NoResultFound:
            # Create a new user with the id field (which is the telegram_id)
            new_user = User(id=user_id)
            setattr(new_user, 'risk_profile', 'stable')
            db.session.add(new_user)
            db.session.commit()
            
            logger.info(f"Created new user {user_id} with 'stable' profile")
        
        # Return success response
        return {
            "success": True,
            "action": "profile_set",
            "profile": "stable",
            "message": "✅ Your profile has been set to Stable.\n\nThis profile focuses on more established pools with potentially lower but more consistent returns. You'll receive recommendations for pools with moderate APR but higher stability.",
            "chat_id": chat_id
        }
        
    except Exception as e:
        logger.error(f"Error setting stable profile: {e}")
        logger.error(traceback.format_exc())
        
        # Try an alternative approach if the first one fails
        try:
            # Import database utils directly
            import db_utils
            db_utils.set_user_profile(user_id, "stable")
            
            logger.info(f"Set user {user_id} profile to 'stable' using db_utils")
            
            # Return success response
            return {
                "success": True,
                "action": "profile_set",
                "profile": "stable",
                "message": "✅ Your profile has been set to Stable.\n\nThis profile focuses on more established pools with potentially lower but more consistent returns. You'll receive recommendations for pools with moderate APR but higher stability.",
                "chat_id": chat_id
            }
        except Exception as inner_e:
            logger.error(f"Alternative approach also failed: {inner_e}")
            logger.error(traceback.format_exc())
        
        # Fallback message if something goes wrong
        return {
            "success": False,
            "action": "error",
            "message": "Sorry, there was an error setting your profile to Stable. Please try again in a moment.",
            "error": str(e),
            "chat_id": chat_id
        }

def cleanup_profile_data(max_age: int = 3600) -> None:
    """
    Clean up old profile attempt data.
    
    Args:
        max_age: Maximum age in seconds to keep profile data
    """
    current_time = time.time()
    
    for user_id in list(profile_attempts.keys()):
        timestamp = profile_attempts[user_id]
        if current_time - timestamp > max_age:
            del profile_attempts[user_id]
            
    logger.debug(f"Cleaned up profile attempts data, now tracking {len(profile_attempts)} users")