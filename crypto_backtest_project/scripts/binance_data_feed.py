#!/usr/bin/env python3
"""
Binance Data Feed Module
Provides real-time data streaming from Binance via WebSocket
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import websocket
import json
import threading
import time


class BinanceDataFeed:
    """
    Real-time data feed from Binance
    """
    
    def __init__(self, symbol, timeframe='1h'):
        self.symbol = symbol
        self.timeframe = timeframe
        self.data = pd.DataFrame()
        self.ws = None
        self.running = False
        
        # Initialize exchange
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
        # Load historical data
        self.load_historical_data()
    
    def load_historical_data(self, limit=500):
        """Load historical OHLCV data"""
        try:
            print(f"📥 Loading historical data for {self.symbol}...")
            ohlcv = self.exchange.fetch_ohlcv(
                self.symbol, 
                self.timeframe, 
                limit=limit
            )
            
            self.data = pd.DataFrame(
                ohlcv, 
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            self.data['datetime'] = pd.to_datetime(self.data['timestamp'], unit='ms')
            
            print(f"✅ Loaded {len(self.data)} candles")
            
        except Exception as e:
            print(f"❌ Error loading historical data: {e}")
    
    def start_websocket(self):
        """Start WebSocket connection for real-time updates"""
        stream_name = self.symbol.lower().replace('/', '') + f'@kline_{self.timeframe}'
        ws_url = f"wss://fstream.binance.com/ws/{stream_name}"
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                kline = data['k']
                
                # Update latest candle
                new_candle = {
                    'timestamp': kline['t'],
                    'open': float(kline['o']),
                    'high': float(kline['h']),
                    'low': float(kline['l']),
                    'close': float(kline['c']),
                    'volume': float(kline['v']),
                    'datetime': pd.to_datetime(kline['t'], unit='ms')
                }
                
                # Check if candle is closed
                if kline['x']:
                    # Append new closed candle
                    self.data = pd.concat([
                        self.data, 
                        pd.DataFrame([new_candle])
                    ], ignore_index=True)
                    
                    # Keep only last 500 candles
                    if len(self.data) > 500:
                        self.data = self.data.iloc[-500:]
                    
                    print(f"📊 New candle: {self.symbol} - Close: {new_candle['close']:.2f}")
                else:
                    # Update last candle
                    if len(self.data) > 0:
                        self.data.iloc[-1] = new_candle
                        
            except Exception as e:
                print(f"⚠️ Error processing message: {e}")
        
        def on_error(ws, error):
            print(f"❌ WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            print(f"🔌 WebSocket closed: {close_msg}")
            
            # Reconnect after delay if still running
            if self.running:
                print("🔄 Reconnecting in 5 seconds...")
                time.sleep(5)
                self.start_websocket()
        
        def on_open(ws):
            print(f"✅ WebSocket connected: {self.symbol}")
        
        # Create WebSocket connection
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        # Run WebSocket in separate thread
        self.running = True
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
    
    def stop_websocket(self):
        """Stop WebSocket connection"""
        self.running = False
        if self.ws:
            self.ws.close()
    
    def get_data(self):
        """Get current data DataFrame"""
        return self.data.copy()
    
    def get_latest_price(self):
        """Get latest close price"""
        if len(self.data) > 0:
            return self.data['close'].iloc[-1]
        return None
    
    def calculate_ema(self, period):
        """Calculate EMA"""
        if len(self.data) >= period:
            return self.data['close'].ewm(span=period, adjust=False).mean().iloc[-1]
        return None
    
    def calculate_rsi(self, period=14):
        """Calculate RSI"""
        if len(self.data) < period + 1:
            return None
        
        delta = self.data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1]
    
    def calculate_atr(self, period=14):
        """Calculate ATR"""
        if len(self.data) < period + 1:
            return None
        
        high_low = self.data['high'] - self.data['low']
        high_close = np.abs(self.data['high'] - self.data['close'].shift())
        low_close = np.abs(self.data['low'] - self.data['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(period).mean()
        
        return atr.iloc[-1]
    
    def get_indicators(self):
        """Get all indicators"""
        return {
            'price': self.get_latest_price(),
            'ema_20': self.calculate_ema(20),
            'ema_50': self.calculate_ema(50),
            'ema_200': self.calculate_ema(200),
            'rsi': self.calculate_rsi(14),
            'atr': self.calculate_atr(14)
        }


class MultiSymbolDataFeed:
    """
    Manage data feeds for multiple symbols
    """
    
    def __init__(self, symbols, timeframe='1h'):
        self.symbols = symbols
        self.timeframe = timeframe
        self.feeds = {}
        
        # Create feed for each symbol
        for symbol in symbols:
            self.feeds[symbol] = BinanceDataFeed(symbol, timeframe)
    
    def start_all(self):
        """Start WebSocket for all symbols"""
        for symbol, feed in self.feeds.items():
            feed.start_websocket()
            time.sleep(1)  # Delay between connections
    
    def stop_all(self):
        """Stop all WebSocket connections"""
        for feed in self.feeds.values():
            feed.stop_websocket()
    
    def get_feed(self, symbol):
        """Get feed for specific symbol"""
        return self.feeds.get(symbol)
    
    def get_all_data(self):
        """Get data for all symbols"""
        return {symbol: feed.get_data() for symbol, feed in self.feeds.items()}
    
    def get_all_indicators(self):
        """Get indicators for all symbols"""
        return {symbol: feed.get_indicators() for symbol, feed in self.feeds.items()}


if __name__ == "__main__":
    # Test data feed
    print("Testing Binance Data Feed...")
    
    feed = BinanceDataFeed('BTC/USDT', '1h')
    feed.start_websocket()
    
    try:
        while True:
            time.sleep(10)
            indicators = feed.get_indicators()
            print(f"\n📊 Indicators:")
            for key, value in indicators.items():
                if value is not None:
                    print(f"  {key}: {value:.2f}")
    except KeyboardInterrupt:
        print("\nStopping...")
        feed.stop_websocket()
