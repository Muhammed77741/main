#!/usr/bin/env python3
"""
Trading Bot Manager - GUI Application
An attractive and informative interface for managing trading bots
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import threading
import time


class TradingBotGUI:
    """Main GUI application for Trading Bot Manager"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Trading Bot Manager")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # Configure colors - Modern dark theme
        self.colors = {
            'bg': '#1e1e2e',
            'fg': '#cdd6f4',
            'accent': '#89b4fa',
            'success': '#a6e3a1',
            'danger': '#f38ba8',
            'warning': '#f9e2af',
            'card_bg': '#313244',
            'border': '#45475a',
            'title': '#cba6f7'
        }
        
        # Configure root window
        self.root.configure(bg=self.colors['bg'])
        
        # Bot status tracking
        self.bots_status = {
            'BTC/USDT': {'running': False, 'pnl': 0.0, 'positions': 0},
            'ETH/USDT': {'running': False, 'pnl': 0.0, 'positions': 0},
            'XAUUSD': {'running': False, 'pnl': 0.0, 'positions': 0}
        }
        
        self.selected_bot = None
        
        # Create main UI
        self.create_widgets()
        
    def create_widgets(self):
        """Create all GUI widgets"""
        
        # Header with larger title
        header_frame = tk.Frame(self.root, bg=self.colors['bg'], height=100)
        header_frame.pack(fill=tk.X, padx=20, pady=(20, 10))
        header_frame.pack_propagate(False)
        
        # Main title - Make it larger and more prominent
        title_label = tk.Label(
            header_frame,
            text="🤖 TRADING BOT MANAGER",
            font=('Helvetica', 32, 'bold'),  # Larger font size
            bg=self.colors['bg'],
            fg=self.colors['title']
        )
        title_label.pack(pady=(15, 0))
        
        # Subtitle
        subtitle_label = tk.Label(
            header_frame,
            text="Advanced Cryptocurrency & Forex Trading System",
            font=('Helvetica', 12),
            bg=self.colors['bg'],
            fg=self.colors['accent']
        )
        subtitle_label.pack()
        
        # Main content area
        content_frame = tk.Frame(self.root, bg=self.colors['bg'])
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Left panel - Bot selection
        self.create_bot_selection_panel(content_frame)
        
        # Right panel - Bot details and controls
        self.create_bot_details_panel(content_frame)
        
        # Bottom panel - Statistics and logs
        self.create_statistics_panel()
        
        # Footer
        footer_frame = tk.Frame(self.root, bg=self.colors['card_bg'], height=40)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        footer_frame.pack_propagate(False)
        
        footer_label = tk.Label(
            footer_frame,
            text=f"© 2026 Trading Bot Manager | Status: Connected | Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            font=('Helvetica', 9),
            bg=self.colors['card_bg'],
            fg=self.colors['fg']
        )
        footer_label.pack(pady=10)
        
        # Start updating the time
        self.update_footer_time(footer_label)
        
    def create_bot_selection_panel(self, parent):
        """Create the left panel with bot selection"""
        left_panel = tk.Frame(parent, bg=self.colors['card_bg'], width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        # Panel title
        title_label = tk.Label(
            left_panel,
            text="📊 Available Bots",
            font=('Helvetica', 16, 'bold'),
            bg=self.colors['card_bg'],
            fg=self.colors['accent']
        )
        title_label.pack(pady=(20, 10), padx=20, anchor='w')
        
        # Bot cards
        for bot_name in self.bots_status.keys():
            self.create_bot_card(left_panel, bot_name)
            
    def create_bot_card(self, parent, bot_name):
        """Create an individual bot card"""
        card = tk.Frame(parent, bg=self.colors['bg'], relief=tk.RAISED, borderwidth=2)
        card.pack(pady=10, padx=20, fill=tk.X)
        
        # Bot name
        name_label = tk.Label(
            card,
            text=bot_name,
            font=('Helvetica', 14, 'bold'),
            bg=self.colors['bg'],
            fg=self.colors['fg']
        )
        name_label.pack(pady=(10, 5), padx=10, anchor='w')
        
        # Status indicator
        status = self.bots_status[bot_name]
        status_text = "● RUNNING" if status['running'] else "○ STOPPED"
        status_color = self.colors['success'] if status['running'] else self.colors['danger']
        
        status_label = tk.Label(
            card,
            text=status_text,
            font=('Helvetica', 10),
            bg=self.colors['bg'],
            fg=status_color
        )
        status_label.pack(padx=10, anchor='w')
        
        # P&L
        pnl_text = f"P&L: ${status['pnl']:+.2f}"
        pnl_color = self.colors['success'] if status['pnl'] >= 0 else self.colors['danger']
        
        pnl_label = tk.Label(
            card,
            text=pnl_text,
            font=('Helvetica', 10),
            bg=self.colors['bg'],
            fg=pnl_color
        )
        pnl_label.pack(padx=10, anchor='w')
        
        # Positions
        positions_label = tk.Label(
            card,
            text=f"Positions: {status['positions']}",
            font=('Helvetica', 10),
            bg=self.colors['bg'],
            fg=self.colors['fg']
        )
        positions_label.pack(padx=10, pady=(0, 10), anchor='w')
        
        # Select button
        select_btn = tk.Button(
            card,
            text="Select",
            font=('Helvetica', 10, 'bold'),
            bg=self.colors['accent'],
            fg='#1e1e2e',
            activebackground=self.colors['success'],
            relief=tk.FLAT,
            cursor='hand2',
            command=lambda: self.select_bot(bot_name)
        )
        select_btn.pack(pady=(0, 10), padx=10, fill=tk.X)
        
    def create_bot_details_panel(self, parent):
        """Create the right panel with bot details and controls"""
        right_panel = tk.Frame(parent, bg=self.colors['bg'])
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Details card
        details_card = tk.Frame(right_panel, bg=self.colors['card_bg'], relief=tk.RAISED, borderwidth=2)
        details_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Title
        self.details_title = tk.Label(
            details_card,
            text="Select a bot to view details",
            font=('Helvetica', 18, 'bold'),
            bg=self.colors['card_bg'],
            fg=self.colors['accent']
        )
        self.details_title.pack(pady=(20, 10), padx=20)
        
        # Info frame
        info_frame = tk.Frame(details_card, bg=self.colors['card_bg'])
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Balance
        balance_frame = self.create_info_row(info_frame, "💰 Balance:", "$10,000.00")
        balance_frame.pack(fill=tk.X, pady=5)
        
        # P&L
        self.pnl_frame = self.create_info_row(info_frame, "📈 Total P&L:", "$0.00 (0.00%)")
        self.pnl_frame.pack(fill=tk.X, pady=5)
        
        # Open Positions
        self.positions_frame = self.create_info_row(info_frame, "📊 Open Positions:", "0/3")
        self.positions_frame.pack(fill=tk.X, pady=5)
        
        # Win Rate
        winrate_frame = self.create_info_row(info_frame, "🎯 Win Rate:", "0.0%")
        winrate_frame.pack(fill=tk.X, pady=5)
        
        # Total Trades
        trades_frame = self.create_info_row(info_frame, "📝 Total Trades:", "0")
        trades_frame.pack(fill=tk.X, pady=5)
        
        # Strategy
        strategy_frame = self.create_info_row(info_frame, "⚙️ Strategy:", "V3 Adaptive Pattern Recognition")
        strategy_frame.pack(fill=tk.X, pady=5)
        
        # Controls
        controls_frame = tk.Frame(details_card, bg=self.colors['card_bg'])
        controls_frame.pack(pady=20)
        
        self.start_btn = tk.Button(
            controls_frame,
            text="▶ START BOT",
            font=('Helvetica', 12, 'bold'),
            bg=self.colors['success'],
            fg='#1e1e2e',
            activebackground='#7dc96f',
            relief=tk.FLAT,
            width=15,
            height=2,
            cursor='hand2',
            command=self.start_bot
        )
        self.start_btn.pack(side=tk.LEFT, padx=10)
        
        self.stop_btn = tk.Button(
            controls_frame,
            text="⏹ STOP BOT",
            font=('Helvetica', 12, 'bold'),
            bg=self.colors['danger'],
            fg='#1e1e2e',
            activebackground='#e67396',
            relief=tk.FLAT,
            width=15,
            height=2,
            cursor='hand2',
            command=self.stop_bot,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=10)
        
        settings_btn = tk.Button(
            controls_frame,
            text="⚙️ SETTINGS",
            font=('Helvetica', 12, 'bold'),
            bg=self.colors['accent'],
            fg='#1e1e2e',
            activebackground='#6c9ce3',
            relief=tk.FLAT,
            width=15,
            height=2,
            cursor='hand2',
            command=self.open_settings
        )
        settings_btn.pack(side=tk.LEFT, padx=10)
        
    def create_info_row(self, parent, label, value):
        """Create an information row"""
        row = tk.Frame(parent, bg=self.colors['card_bg'])
        
        label_widget = tk.Label(
            row,
            text=label,
            font=('Helvetica', 12, 'bold'),
            bg=self.colors['card_bg'],
            fg=self.colors['accent'],
            width=20,
            anchor='w'
        )
        label_widget.pack(side=tk.LEFT, padx=(0, 10))
        
        value_widget = tk.Label(
            row,
            text=value,
            font=('Helvetica', 12),
            bg=self.colors['card_bg'],
            fg=self.colors['fg'],
            anchor='w'
        )
        value_widget.pack(side=tk.LEFT)
        
        return row
        
    def create_statistics_panel(self):
        """Create the bottom statistics and logs panel"""
        stats_frame = tk.Frame(self.root, bg=self.colors['card_bg'], relief=tk.RAISED, borderwidth=2)
        stats_frame.pack(fill=tk.BOTH, padx=20, pady=(0, 10), ipady=10)
        
        # Title
        title_label = tk.Label(
            stats_frame,
            text="📋 Live Activity Log",
            font=('Helvetica', 14, 'bold'),
            bg=self.colors['card_bg'],
            fg=self.colors['accent']
        )
        title_label.pack(pady=(10, 5), padx=20, anchor='w')
        
        # Log text widget
        log_frame = tk.Frame(stats_frame, bg=self.colors['bg'])
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
        
        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(
            log_frame,
            height=8,
            bg=self.colors['bg'],
            fg=self.colors['fg'],
            font=('Consolas', 10),
            relief=tk.FLAT,
            yscrollcommand=scrollbar.set,
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)
        
        # Add initial log messages
        self.add_log("System initialized successfully")
        self.add_log("Waiting for bot selection...")
        
    def add_log(self, message, level='INFO'):
        """Add a log message to the log panel"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        color_map = {
            'INFO': self.colors['fg'],
            'SUCCESS': self.colors['success'],
            'WARNING': self.colors['warning'],
            'ERROR': self.colors['danger']
        }
        
        color = color_map.get(level, self.colors['fg'])
        
        self.log_text.insert(tk.END, f"[{timestamp}] ", 'timestamp')
        self.log_text.insert(tk.END, f"{message}\n", level)
        
        self.log_text.tag_config('timestamp', foreground=self.colors['accent'])
        self.log_text.tag_config(level, foreground=color)
        
        self.log_text.see(tk.END)
        
    def select_bot(self, bot_name):
        """Handle bot selection"""
        self.selected_bot = bot_name
        self.details_title.config(text=f"Bot Details - {bot_name}")
        self.add_log(f"Selected bot: {bot_name}", 'INFO')
        
        # Update button states
        if self.bots_status[bot_name]['running']:
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
        else:
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
        
    def start_bot(self):
        """Start the selected bot"""
        if not self.selected_bot:
            messagebox.showwarning("No Bot Selected", "Please select a bot first")
            return
            
        self.bots_status[self.selected_bot]['running'] = True
        self.add_log(f"Starting {self.selected_bot} bot...", 'SUCCESS')
        self.add_log(f"{self.selected_bot} bot is now running", 'SUCCESS')
        
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # Simulate bot activity
        self.simulate_bot_activity()
        
        # Refresh the bot cards
        self.refresh_ui()
        
    def stop_bot(self):
        """Stop the selected bot"""
        if not self.selected_bot:
            return
            
        self.bots_status[self.selected_bot]['running'] = False
        self.add_log(f"Stopping {self.selected_bot} bot...", 'WARNING')
        self.add_log(f"{self.selected_bot} bot stopped", 'WARNING')
        
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        # Refresh the bot cards
        self.refresh_ui()
        
    def simulate_bot_activity(self):
        """Simulate bot trading activity (for demonstration)"""
        if not self.selected_bot or not self.bots_status[self.selected_bot]['running']:
            return
            
        import random
        
        # Simulate a trade
        pnl_change = random.uniform(-50, 100)
        self.bots_status[self.selected_bot]['pnl'] += pnl_change
        
        if random.random() > 0.7:  # 30% chance of opening a position
            self.bots_status[self.selected_bot]['positions'] = min(
                self.bots_status[self.selected_bot]['positions'] + 1, 3
            )
            self.add_log(f"{self.selected_bot}: New position opened", 'SUCCESS')
        
        if random.random() > 0.8 and self.bots_status[self.selected_bot]['positions'] > 0:  # 20% chance of closing
            self.bots_status[self.selected_bot]['positions'] -= 1
            self.add_log(f"{self.selected_bot}: Position closed with ${pnl_change:+.2f} P&L", 
                        'SUCCESS' if pnl_change > 0 else 'WARNING')
        
        # Schedule next activity
        self.root.after(5000, self.simulate_bot_activity)
        
    def open_settings(self):
        """Open settings dialog"""
        messagebox.showinfo("Settings", "Settings panel coming soon!\n\nHere you'll be able to configure:\n- API Keys\n- Risk Parameters\n- Telegram Notifications\n- Strategy Settings")
        
    def refresh_ui(self):
        """Refresh the UI to show updated bot status"""
        # This would normally recreate the bot cards with updated info
        # For now, just log the refresh
        pass
        
    def update_footer_time(self, label):
        """Update the footer time every second"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        label.config(text=f"© 2026 Trading Bot Manager | Status: Connected | Time: {current_time}")
        self.root.after(1000, lambda: self.update_footer_time(label))


def main():
    """Main entry point"""
    root = tk.Tk()
    app = TradingBotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
