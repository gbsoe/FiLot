#!/usr/bin/env python3
"""
Kill any running Telegram bot instances to fix the conflict error
"""

import os
import sys
import time
import signal
import subprocess

def get_bot_pids():
    """Get PIDs of any Python processes that could be running the Telegram bot"""
    try:
        # Run ps command to find any Python processes
        ps_output = subprocess.check_output(
            ["ps", "aux"], 
            universal_newlines=True
        )
        
        # Parse the output to find PIDs
        pids = []
        for line in ps_output.splitlines():
            # Check for any Python process that might be the bot, excluding this script
            if ("python main.py" in line or "wsgi.py" in line or "app.py" in line) and not "kill_telegram_bot.py" in line:
                # Extract the second column (PID)
                parts = line.split()
                if len(parts) > 1:
                    try:
                        pid = int(parts[1])
                        pids.append(pid)
                    except ValueError:
                        continue
        
        return pids
    except Exception as e:
        print(f"Error getting PIDs: {e}")
        return []

def release_telegram_api_lock():
    """
    Make a dummy API request to Telegram to force release the getUpdates lock
    """
    try:
        import requests
        import os
        from dotenv import load_dotenv
        
        # Load environment variables
        load_dotenv()
        
        # Get bot token
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            print("TELEGRAM_BOT_TOKEN not found in environment variables")
            return False
            
        # Telegram API base URL
        base_url = f"https://api.telegram.org/bot{bot_token}"
        
        # Make a getMe request to force API reset
        response = requests.get(f"{base_url}/getMe", timeout=10)
        
        # Make a deleteWebhook request to ensure no webhook is active
        webhook_response = requests.get(f"{base_url}/deleteWebhook", timeout=10)
        
        if response.status_code == 200 and webhook_response.status_code == 200:
            print("Successfully released Telegram API lock")
            return True
        else:
            print(f"Failed to release API lock: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        print(f"Error in release_telegram_api_lock: {e}")
        return False

def kill_bot_processes():
    """Kill any running Telegram bot processes"""
    pids = get_bot_pids()
    
    if not pids:
        print("No Telegram bot processes found.")
        # Even if no processes found, try to release the API lock
        release_telegram_api_lock()
        return False
    
    print(f"Found {len(pids)} Telegram bot processes: {pids}")
    
    # Kill each process
    for pid in pids:
        try:
            # Send SIGTERM signal
            os.kill(pid, signal.SIGTERM)
            print(f"Sent SIGTERM to process {pid}")
        except OSError as e:
            print(f"Error killing process {pid}: {e}")
    
    # Wait a moment and check if processes are actually terminated
    time.sleep(2)
    
    # Check if any processes still exist
    remaining_pids = get_bot_pids()
    if remaining_pids:
        print(f"Some processes still running: {remaining_pids}")
        
        # Try with SIGKILL for remaining processes
        for pid in remaining_pids:
            try:
                os.kill(pid, signal.SIGKILL)
                print(f"Sent SIGKILL to process {pid}")
            except OSError as e:
                print(f"Error killing process {pid} with SIGKILL: {e}")
    
    # Final check
    final_check = get_bot_pids()
    if not final_check:
        print("All Telegram bot processes successfully terminated.")
        # Also release the API lock to be safe
        release_telegram_api_lock()
        return True
    else:
        print(f"Failed to kill all processes. Remaining: {final_check}")
        # Still try to release the API lock
        release_telegram_api_lock()
        return False

if __name__ == "__main__":
    print("Checking for running Telegram bot instances...")
    killed = kill_bot_processes()
    
    if killed:
        print("Ready to start a new clean Telegram bot instance.")
    else:
        print("No action needed or could not kill all processes.")