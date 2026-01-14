#!/usr/bin/env python3
"""
Script to take a screenshot of the trading bot GUI
"""

import subprocess
import time
import os

# Start Xvfb
xvfb_process = subprocess.Popen([
    'Xvfb', ':99', '-screen', '0', '1200x800x24'
], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Set DISPLAY environment variable
os.environ['DISPLAY'] = ':99'

# Wait for Xvfb to start
time.sleep(2)

# Import after setting DISPLAY
import tkinter as tk
from PIL import ImageGrab
from trading_bot_gui import TradingBotGUI

# Create the GUI
root = tk.Tk()
app = TradingBotGUI(root)

# Wait for the GUI to render
root.update()
time.sleep(1)

# Take screenshot using import command
subprocess.run([
    'import', '-window', 'root', '-display', ':99',
    '/home/runner/work/main/main/trading_bot_gui_screenshot.png'
], check=True)

print("Screenshot saved as trading_bot_gui_screenshot.png")

# Clean up
root.destroy()
xvfb_process.terminate()
