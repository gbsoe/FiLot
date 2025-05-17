"""
Direct command handlers for critical bot functionality.
This includes profile selection commands that bypass the button system entirely.
"""

import logging
import sqlite3
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database file
DB_FILE = "filot_bot.db"

def set_profile(user_id: int, profile_type: str) -> Dict[str, Any]:
    """
    Set user profile directly in the database.
    
    Args:
        user_id: User ID
        profile_type: Either 'high-risk' or 'stable'
        
    Returns:
        Response with success status and message
    """
    try:
        # Connect to database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Make sure the table exists
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            risk_profile TEXT DEFAULT 'stable',
            investment_horizon TEXT DEFAULT 'medium',
            subscribed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            wallet_address TEXT,
            verification_code TEXT,
            verified BOOLEAN DEFAULT 0
        )
        ''')
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        user_exists = cursor.fetchone() is not None
        
        if user_exists:
            # Update existing user
            logger.info(f"Direct command: Updating user {user_id} to {profile_type} profile")
            cursor.execute("UPDATE users SET risk_profile = ? WHERE id = ?", (profile_type, user_id))
        else:
            # Create new user
            logger.info(f"Direct command: Creating user {user_id} with {profile_type} profile")
            cursor.execute(
                "INSERT INTO users (id, risk_profile, username) VALUES (?, ?, ?)",
                (user_id, profile_type, f"user_{user_id}")
            )
            
        # Commit changes
        conn.commit()
        conn.close()
        
        # Format response message
        if profile_type == "high-risk":
            message = """
🔴 *High-Risk Profile Selected*

Your investment recommendations will now focus on:
• Higher APR opportunities
• Newer pools with growth potential
• More volatile but potentially rewarding options

_Note: Higher returns come with increased risk_
"""
        else:  # stable
            message = """
🟢 *Stable Profile Selected*

Your investment recommendations will now focus on:
• Established, reliable pools
• Lower volatility options
• More consistent but potentially lower APR

_Note: Stability typically means more moderate returns_
"""
        
        return {
            "success": True,
            "message": message
        }
    except Exception as e:
        logger.error(f"Error in direct command profile setting: {e}")
        return {
            "success": False,
            "message": "Sorry, there was an error setting your profile. Please try again later."
        }

# Command handlers
def handle_high_risk_command(update: Any, context: Any) -> None:
    """Handle /high_risk command."""
    user_id = update.message.from_user.id
    result = set_profile(user_id, "high-risk")
    
    if result["success"]:
        update.message.reply_markdown(result["message"])
    else:
        update.message.reply_text(result["message"])

def handle_stable_command(update: Any, context: Any) -> None:
    """Handle /stable command."""
    user_id = update.message.from_user.id
    result = set_profile(user_id, "stable")
    
    if result["success"]:
        update.message.reply_markdown(result["message"])
    else:
        update.message.reply_text(result["message"])

# Main function for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python direct_commands.py <user_id> <profile_type>")
        sys.exit(1)
        
    user_id = int(sys.argv[1])
    profile_type = sys.argv[2]
    
    if profile_type not in ["high-risk", "stable"]:
        print(f"Invalid profile type: {profile_type}")
        sys.exit(1)
        
    result = set_profile(user_id, profile_type)
    print(f"Success: {result['success']}")
    print(f"Message: {result['message']}")