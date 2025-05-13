"""
This script fixes the SQLite connection issue in walletconnect_utils.py
by removing references to conn.closed attribute which is not available in SQLite3.
"""

import re
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_walletconnect_utils():
    """
    Fix the sqlite3.Connection object has no attribute 'closed' error
    by replacing the problematic code in walletconnect_utils.py
    """
    try:
        # Path to the file
        file_path = 'walletconnect_utils.py'
        
        # Read the file content
        with open(file_path, 'r') as file:
            content = file.read()
        
        # Define the search pattern
        pattern = r'if conn and conn\.closed == 0:\s+conn\.close\(\)'
        
        # Define replacement
        replacement = """# SQLite connection doesn't have a 'closed' attribute
                if conn:
                    try:
                        conn.close()
                    except Exception as close_error:
                        logger.error(f"Error closing connection: {close_error}")"""
        
        # Replace all occurrences
        modified_content = re.sub(pattern, replacement, content)
        
        # Check if any replacements were made
        if content == modified_content:
            logger.warning("No replacements were made, pattern not found")
            return False
        
        # Create a backup of the original file
        backup_path = f"{file_path}.bak"
        with open(backup_path, 'w') as backup_file:
            backup_file.write(content)
        
        # Write the modified content back to the file
        with open(file_path, 'w') as file:
            file.write(modified_content)
        
        logger.info(f"Fixed conn.closed references in {file_path}")
        return True
    
    except Exception as e:
        logger.error(f"Error fixing walletconnect_utils.py: {e}")
        return False

if __name__ == "__main__":
    if fix_walletconnect_utils():
        logger.info("Successfully applied fixes to walletconnect_utils.py")
    else:
        logger.error("Failed to apply fixes to walletconnect_utils.py")