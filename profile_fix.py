"""
Simple module to fix profile button issues.
This provides direct functions to be called from the command line.
"""

import sqlite3
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def set_profile(user_id, profile_type):
    """
    Set user profile directly in the database.
    
    Args:
        user_id: The user's Telegram ID as an integer
        profile_type: Either 'high-risk' or 'stable'
    """
    try:
        # Validate profile type
        if profile_type not in ['high-risk', 'stable']:
            logger.error(f"Invalid profile type: {profile_type}")
            print(f"ERROR: Invalid profile type '{profile_type}'. Must be 'high-risk' or 'stable'.")
            return False
        
        # Connect to database directly
        conn = sqlite3.connect('filot_bot.db')
        cursor = conn.cursor()
        
        # Create table if it doesn't exist
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            risk_profile TEXT DEFAULT 'stable',
            subscribed BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            wallet_address TEXT,
            verification_code TEXT,
            is_verified BOOLEAN DEFAULT 0
        )
        ''')
        
        # Check if user exists
        cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
        user_exists = cursor.fetchone()
        
        if user_exists:
            # Update existing user
            cursor.execute(
                'UPDATE users SET risk_profile = ? WHERE id = ?',
                (profile_type, user_id)
            )
            logger.info(f"Updated profile for existing user {user_id} to {profile_type}")
        else:
            # Create new user
            cursor.execute(
                'INSERT INTO users (id, risk_profile) VALUES (?, ?)',
                (user_id, profile_type)
            )
            logger.info(f"Created new user {user_id} with profile {profile_type}")
        
        # Commit and close
        conn.commit()
        conn.close()
        
        print(f"SUCCESS: Profile for user {user_id} set to '{profile_type}'")
        return True
        
    except Exception as e:
        logger.error(f"Error in set_profile: {e}")
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    # Get command line arguments
    if len(sys.argv) != 3:
        print("Usage: python profile_fix.py <user_id> <profile_type>")
        print("Example: python profile_fix.py 123456789 high-risk")
        sys.exit(1)
    
    try:
        user_id = int(sys.argv[1])
        profile_type = sys.argv[2]
        
        success = set_profile(user_id, profile_type)
        
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    except ValueError:
        print(f"ERROR: User ID must be an integer. Got '{sys.argv[1]}'")
        sys.exit(1)