"""
Direct profile button fix module.
This is a simple, focused solution just for the profile buttons.
"""

import sqlite3
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Messages for each profile type
HIGH_RISK_MESSAGE = """
🔴 *High-Risk Profile Selected*

Your investment recommendations will now focus on:
• Higher APR opportunities
• Newer pools with growth potential
• More volatile but potentially rewarding options

_Note: Higher returns come with increased risk_
"""

STABLE_PROFILE_MESSAGE = """
🟢 *Stable Profile Selected*

Your investment recommendations will now focus on:
• Established, reliable pools
• Lower volatility options
• More consistent but potentially lower APR

_Note: Stability typically means more moderate returns_
"""

def fix_profile(user_id, is_high_risk=True):
    """
    Direct fix for profile setting - extremely simple with no dependencies.
    
    Args:
        user_id: User's Telegram ID
        is_high_risk: True for high-risk profile, False for stable
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Set profile type based on parameter
        profile_type = "high-risk" if is_high_risk else "stable"
        message = HIGH_RISK_MESSAGE if is_high_risk else STABLE_PROFILE_MESSAGE
        
        # Connect directly to database
        conn = sqlite3.connect('filot_bot.db')
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT risk_profile FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            # Update existing user
            cursor.execute(
                "UPDATE users SET risk_profile = ? WHERE id = ?", 
                (profile_type, user_id)
            )
            logger.info(f"Updated user {user_id} profile to {profile_type}")
        else:
            # Insert new user
            cursor.execute(
                "INSERT INTO users (id, risk_profile) VALUES (?, ?)",
                (user_id, profile_type)
            )
            logger.info(f"Created new user {user_id} with {profile_type} profile")
        
        # Commit and close
        conn.commit()
        conn.close()
        
        return True, message
        
    except Exception as e:
        logger.error(f"Error fixing profile: {e}")
        return False, f"Error setting profile: {str(e)}"