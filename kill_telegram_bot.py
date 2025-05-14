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
    """Get PIDs of any running Python main.py processes (the Telegram bot)"""
    try:
        # Run ps command to find any Python processes running main.py
        ps_output = subprocess.check_output(
            ["ps", "aux"], 
            universal_newlines=True
        )
        
        # Parse the output to find PIDs
        pids = []
        for line in ps_output.splitlines():
            if "python main.py" in line and not "kill_telegram_bot.py" in line:
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

def kill_bot_processes():
    """Kill any running Telegram bot processes"""
    pids = get_bot_pids()
    
    if not pids:
        print("No Telegram bot processes found.")
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
        return True
    else:
        print(f"Failed to kill all processes. Remaining: {final_check}")
        return False

if __name__ == "__main__":
    print("Checking for running Telegram bot instances...")
    killed = kill_bot_processes()
    
    if killed:
        print("Ready to start a new clean Telegram bot instance.")
    else:
        print("No action needed or could not kill all processes.")