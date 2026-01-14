#!/usr/bin/env python3
"""
Script to take a screenshot of the trading bot GUI using xvfb
"""

import subprocess
import time
import os
import sys

# Create the screenshot
def take_screenshot():
    # Start the GUI with xvfb
    proc = subprocess.Popen(
        ['xvfb-run', '-a', '-s', '-screen 0 1200x800x24', 
         'python3', 'trading_bot_gui.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait a moment for the GUI to render
    time.sleep(3)
    
    # The GUI should be running, now get the window ID
    # For xvfb, we'll use scrot to take a full screen screenshot
    result = subprocess.run(
        ['DISPLAY=:99 scrot /home/runner/work/main/main/trading_bot_screenshot.png'],
        shell=True,
        capture_output=True,
        text=True
    )
    
    # Kill the GUI process
    proc.terminate()
    proc.wait(timeout=5)
    
    print("Screenshot attempt completed")
    print("stdout:", result.stdout)
    print("stderr:", result.stderr)

if __name__ == '__main__':
    take_screenshot()
