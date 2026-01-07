#!/usr/bin/env python3
"""
Crypto Live Trading Bot
Fetches real-time data from Binance and executes trades based on SMC strategy
"""

import ccxt
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import sys
import os

# Import configuration
from config_live_bot import CONFIG

# Import strategy components
from pattern_recognition_strategy import PatternRecognitionStrategy
from smc_indicators import SMCIndicators


class CryptoLiveBot:
    """
    Live trading bot for cryptocurrency markets
    """
    
    def __init__(self, config):
        self.config = config
        self.exchange = None
        self.positions = {}
        self.daily_pnl = 0
        self.daily_trades = 0
        self.last_reset = datetime.now().date()
        
        # Initialize exchange connection
        self.connect_exchange()
        
        # Initialize strategy
        self.strategy = PatternRecognitionStrategy()
        self.indicators = SMCIndicators()
        
        print(f"✅ Bot initialized - Mode: {'TESTNET' if config['testnet'] else 'PRODUCTION'}")
        print(f"📊 Trading pairs: {', '.join(config['symbols'])}")
        
    def connect_exchange(self):
        """Connect to Binance exchange"""
        try:
            if self.config['testnet']:
                self.exchange = ccxt.binance({
                    'apiKey': self.config['api_key'],
                    'secret': self.config['api_secret'],
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'future',
                        'test': True
                    }
                })
            else:
                self.exchange = ccxt.binance({
                    'apiKey': self.config['api_key'],
                    'secret': self.config['api_secret'],
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'future'
                    }
                })
            
            # Test connection
            balance = self.exchange.fetch_balance()
            print(f"✅ Connected to Binance - Balance: {balance['USDT']['free']:.2f} USDT")
            
        except Exception as e:
            print(f"❌ Failed to connect to exchange: {e}")
            sys.exit(1)
    
    def fetch_ohlcv(self, symbol, timeframe='1h', limit=200):
        """Fetch OHLCV data from exchange"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"⚠️ Error fetching data for {symbol}: {e}")
            return None
    
    def calculate_indicators(self, df):
        """Calculate technical indicators"""
        # EMA
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()
        
        return df
    
    def detect_regime(self, df):
        """Detect market regime (TREND or RANGE)"""
        current_price = df['close'].iloc[-1]
        ema_20 = df['ema_20'].iloc[-1]
        ema_50 = df['ema_50'].iloc[-1]
        ema_200 = df['ema_200'].iloc[-1]
        
        # TREND if EMAs are aligned
        if ema_20 > ema_50 > ema_200:
            return 'TREND_UP'
        elif ema_20 < ema_50 < ema_200:
            return 'TREND_DOWN'
        else:
            return 'RANGE'
    
    def generate_signal(self, df, symbol):
        """Generate trading signal based on SMC strategy"""
        if len(df) < 200:
            return None
        
        df = self.calculate_indicators(df)
        regime = self.detect_regime(df)
        
        current_price = df['close'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        atr = df['atr'].iloc[-1]
        
        # LONG signal conditions
        if regime == 'TREND_UP' and rsi < 70:
            if df['close'].iloc[-1] > df['ema_20'].iloc[-1]:
                signal = {
                    'type': 'LONG',
                    'entry': current_price,
                    'sl': current_price - (2 * atr),
                    'tp1': current_price + (3 * atr),
                    'tp2': current_price + (5 * atr),
                    'tp3': current_price + (9 * atr),
                    'regime': regime,
                    'symbol': symbol
                }
                return signal
        
        # SHORT signal conditions
        elif regime == 'TREND_DOWN' and rsi > 30:
            if df['close'].iloc[-1] < df['ema_20'].iloc[-1]:
                signal = {
                    'type': 'SHORT',
                    'entry': current_price,
                    'sl': current_price + (2 * atr),
                    'tp1': current_price - (3 * atr),
                    'tp2': current_price - (5 * atr),
                    'tp3': current_price - (9 * atr),
                    'regime': regime,
                    'symbol': symbol
                }
                return signal
        
        return None
    
    def calculate_position_size(self, balance, risk_percent=1.0):
        """Calculate position size based on account balance and risk"""
        position_size = balance * (risk_percent / 100.0)
        return position_size
    
    def place_order(self, signal):
        """Place order on exchange"""
        try:
            symbol = signal['symbol']
            side = 'buy' if signal['type'] == 'LONG' else 'sell'
            
            # Get account balance
            balance = self.exchange.fetch_balance()
            usdt_balance = balance['USDT']['free']
            
            # Calculate position size
            position_size_usd = self.calculate_position_size(
                usdt_balance, 
                self.config['risk']['position_size_percent']
            )
            
            # Convert to quantity
            quantity = position_size_usd / signal['entry']
            
            # Place market order
            order = self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=quantity
            )
            
            # Store position
            self.positions[symbol] = {
                'signal': signal,
                'order': order,
                'entry_time': datetime.now(),
                'quantity': quantity,
                'remaining': quantity
            }
            
            print(f"✅ Order placed: {signal['type']} {symbol} @ {signal['entry']:.2f}")
            
            # Send Telegram notification if configured
            if self.config.get('telegram'):
                self.send_telegram_notification(f"🚀 {signal['type']} {symbol} @ {signal['entry']:.2f}")
            
            return order
            
        except Exception as e:
            print(f"❌ Error placing order: {e}")
            return None
    
    def manage_positions(self):
        """Manage open positions with partial TPs and trailing stops"""
        for symbol, position in list(self.positions.items()):
            try:
                # Get current price
                ticker = self.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                
                signal = position['signal']
                remaining = position['remaining']
                
                # Check TPs
                if signal['type'] == 'LONG':
                    # TP1 - close 50%
                    if current_price >= signal['tp1'] and remaining >= position['quantity'] * 0.5:
                        self.close_partial_position(symbol, 0.5, 'TP1')
                    
                    # TP2 - close 30%
                    elif current_price >= signal['tp2'] and remaining >= position['quantity'] * 0.3:
                        self.close_partial_position(symbol, 0.3, 'TP2')
                    
                    # TP3 - close remaining
                    elif current_price >= signal['tp3']:
                        self.close_full_position(symbol, 'TP3')
                    
                    # Check SL
                    elif current_price <= signal['sl']:
                        self.close_full_position(symbol, 'SL')
                
                else:  # SHORT
                    # TP1 - close 50%
                    if current_price <= signal['tp1'] and remaining >= position['quantity'] * 0.5:
                        self.close_partial_position(symbol, 0.5, 'TP1')
                    
                    # TP2 - close 30%
                    elif current_price <= signal['tp2'] and remaining >= position['quantity'] * 0.3:
                        self.close_partial_position(symbol, 0.3, 'TP2')
                    
                    # TP3 - close remaining
                    elif current_price <= signal['tp3']:
                        self.close_full_position(symbol, 'TP3')
                    
                    # Check SL
                    elif current_price >= signal['sl']:
                        self.close_full_position(symbol, 'SL')
                        
            except Exception as e:
                print(f"⚠️ Error managing position {symbol}: {e}")
    
    def close_partial_position(self, symbol, percent, reason):
        """Close partial position"""
        try:
            position = self.positions[symbol]
            close_quantity = position['quantity'] * percent
            
            side = 'sell' if position['signal']['type'] == 'LONG' else 'buy'
            
            order = self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=close_quantity
            )
            
            position['remaining'] -= close_quantity
            
            print(f"✅ Partial close: {symbol} {int(percent*100)}% @ {reason}")
            
            if self.config.get('telegram'):
                self.send_telegram_notification(f"📊 Partial close: {symbol} {int(percent*100)}% @ {reason}")
            
        except Exception as e:
            print(f"❌ Error closing partial position: {e}")
    
    def close_full_position(self, symbol, reason):
        """Close full position"""
        try:
            position = self.positions[symbol]
            
            side = 'sell' if position['signal']['type'] == 'LONG' else 'buy'
            
            order = self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=position['remaining']
            )
            
            print(f"✅ Position closed: {symbol} @ {reason}")
            
            if self.config.get('telegram'):
                self.send_telegram_notification(f"🏁 Position closed: {symbol} @ {reason}")
            
            # Remove from positions
            del self.positions[symbol]
            
        except Exception as e:
            print(f"❌ Error closing position: {e}")
    
    def send_telegram_notification(self, message):
        """Send Telegram notification"""
        # Implementation would use telegram bot API
        pass
    
    def check_daily_limits(self):
        """Check if daily limits are reached"""
        today = datetime.now().date()
        
        # Reset daily counters if new day
        if today != self.last_reset:
            self.daily_pnl = 0
            self.daily_trades = 0
            self.last_reset = today
        
        # Check daily loss limit
        if self.daily_pnl < -self.config['risk']['max_daily_loss_percent']:
            print(f"⚠️ Daily loss limit reached: {self.daily_pnl:.2f}%")
            return False
        
        return True
    
    def run(self):
        """Main bot loop"""
        print("🤖 Bot started - Monitoring markets...")
        
        while True:
            try:
                # Check daily limits
                if not self.check_daily_limits():
                    print("⏸️ Trading paused due to daily limits")
                    time.sleep(3600)  # Wait 1 hour
                    continue
                
                # Manage existing positions
                if self.positions:
                    self.manage_positions()
                
                # Check for new signals
                for symbol in self.config['symbols']:
                    # Skip if already have position
                    if symbol in self.positions:
                        continue
                    
                    # Fetch data
                    df = self.fetch_ohlcv(symbol)
                    if df is None:
                        continue
                    
                    # Generate signal
                    signal = self.generate_signal(df, symbol)
                    
                    if signal:
                        print(f"📈 Signal generated: {signal['type']} {symbol}")
                        self.place_order(signal)
                
                # Sleep before next iteration
                time.sleep(self.config['check_interval'])
                
            except KeyboardInterrupt:
                print("\n⏹️ Bot stopped by user")
                break
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                time.sleep(60)


if __name__ == "__main__":
    bot = CryptoLiveBot(CONFIG)
    bot.run()
