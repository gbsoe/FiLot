"""
Fixed profile button handler for FiLot Telegram bot.

This module provides enhanced profile button handling with robust error handling
to prevent JavaScript errors like "Cannot read properties of null (reading 'value')".
"""

import logging
import traceback
import time
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Keep track of profile selection actions to prevent rapid clicks
profile_selections = {}  # {user_id: {"timestamp": time, "profile": profile_type}}
PROFILE_SELECTION_COOLDOWN = 3.0  # seconds

def handle_profile_selection(user_id: int, chat_id: int, profile_type: str) -> Dict[str, Any]:
    """
    Handle a risk profile selection button press.
    
    Args:
        user_id: The Telegram user ID
        chat_id: The Telegram chat ID
        profile_type: The profile type selected (e.g., "high-risk", "stable")
        
    Returns:
        Dict with response data
    """
    try:
        logger.info(f"User {user_id} selected profile: {profile_type}")
        
        # Check for rate limiting (prevent rapid clicks)
        current_time = time.time()
        if user_id in profile_selections:
            last_selection = profile_selections[user_id]
            time_diff = current_time - last_selection.get("timestamp", 0)
            
            # If clicking too rapidly, throttle
            if time_diff < PROFILE_SELECTION_COOLDOWN:
                logger.warning(f"User {user_id} clicking profile buttons too rapidly ({time_diff:.2f}s)")
                return {
                    "success": False,
                    "action": "profile_throttled",
                    "message": f"Please wait a moment before changing your profile again.",
                    "throttled": True,
                    "profile_type": profile_type
                }
        
        # Record this selection
        profile_selections[user_id] = {
            "timestamp": current_time,
            "profile": profile_type
        }
        
        # Save the profile selection in the database
        try:
            from models import User, db
            
            try:
                # SQLAlchemy session approach
                session = db.session()
                # In the database, the 'id' column stores the Telegram user ID directly
                user = session.query(User).filter(User.id == user_id).first()
                
                if user:
                    # Update risk profile
                    user.risk_profile = profile_type
                    session.commit()
                    logger.info(f"Updated risk profile {profile_type} for existing user {user_id}")
                else:
                    # Create new user if not exists
                    try:
                        # Use the direct ID approach (since ID is telegram_id in our model)
                        new_user = User(id=user_id)
                        new_user.risk_profile = profile_type
                        session.add(new_user)
                        session.commit()
                        logger.info(f"Created new user {user_id} with risk profile {profile_type}")
                    except Exception as user_creation_error:
                        logger.error(f"Error creating user: {user_creation_error}")
                    
                logger.info(f"Saved risk profile {profile_type} for user {user_id} to database")
            except Exception as db_error:
                logger.error(f"Primary DB save failed: {db_error}")
                
                # Alternative approach if session-based fails
                try:
                    # Check if user exists
                    user = User.query.filter_by(id=user_id).first()
                    
                    if user:
                        # Update risk profile
                        user.risk_profile = profile_type
                        db.session.commit()
                        logger.info(f"Updated risk profile {profile_type} for user {user_id} (alt)")
                    else:
                        # Try to create new user
                        try:
                            new_user = User(id=user_id)
                            new_user.risk_profile = profile_type
                            db.session.add(new_user)
                            db.session.commit()
                            logger.info(f"Created new user {user_id} (alt)")
                        except Exception as alt_user_error:
                            logger.error(f"Alt user creation error: {alt_user_error}")
                except Exception as alt_db_error:
                    logger.error(f"Alternative DB save also failed: {alt_db_error}")
                    
        except ImportError:
            logger.warning("Could not import models, profile will not be saved to database")
            
        # Prepare appropriate emojis and messages
        if profile_type == "high-risk":
            emoji = "🔴"
            description = "You've selected the High-Risk profile. This targets pools with higher potential returns but also higher volatility."
        elif profile_type == "stable":
            emoji = "🟢"
            description = "You've selected the Stable profile. This targets pools with lower risk and more consistent returns."
        else:
            emoji = "🟡"
            description = "You've selected a custom profile. This will be used for your investment recommendations."
            
        # Compose the success message
        message = (
            f"{emoji} *Risk Profile Updated: {profile_type}*\n\n"
            f"{description}\n\n"
            f"Your investment recommendations will now be tailored to this risk profile."
        )
        
        # Return success response
        return {
            "success": True,
            "action": "profile_updated",
            "profile_type": profile_type,
            "message": message,
            "profile_emoji": emoji,
            "chat_id": chat_id
        }
        
    except Exception as e:
        logger.error(f"Error handling profile selection: {e}")
        logger.error(traceback.format_exc())
        
        # Fallback message if something goes wrong
        message = (
            "Sorry, I couldn't process your risk profile selection. "
            "Please try again in a moment."
        )
        
        return {
            "success": False,
            "action": "profile_error",
            "error": str(e),
            "message": message,
            "profile_type": profile_type,
            "chat_id": chat_id
        }

def cleanup_profile_data(max_age: int = 3600) -> None:
    """
    Clean up old profile selection data.
    
    Args:
        max_age: Maximum age in seconds to keep profile data
    """
    current_time = time.time()
    
    for user_id in list(profile_selections.keys()):
        data = profile_selections[user_id]
        if current_time - data.get("timestamp", 0) > max_age:
            del profile_selections[user_id]
            
    logger.debug(f"Cleaned up profile selections data, now tracking {len(profile_selections)} users")