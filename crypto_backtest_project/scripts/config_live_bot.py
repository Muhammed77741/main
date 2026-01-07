#!/usr/bin/env python3
"""
Configuration file for Crypto Live Bot
"""

CONFIG = {
    # Exchange API credentials
    'api_key': 'YOUR_BINANCE_API_KEY',
    'api_secret': 'YOUR_BINANCE_API_SECRET',
    
    # Trading mode
    'testnet': True,  # Set to False for production trading
    
    # Trading pairs
    'symbols': [
        'BTC/USDT',
        'ETH/USDT'
    ],
    
    # Timeframe
    'timeframe': '1h',
    
    # Check interval (seconds)
    'check_interval': 60,  # Check every 60 seconds
    
    # Risk management
    'risk': {
        'position_size_percent': 1.0,  # Risk 1% of account per trade
        'max_daily_loss_percent': 5.0,  # Stop trading if daily loss exceeds 5%
        'max_positions': 2,  # Maximum concurrent positions
    },
    
    # Strategy parameters
    'strategy': {
        # TREND mode parameters
        'trend': {
            'tp1_multiplier': 3.0,  # TP1 = 3 * ATR
            'tp2_multiplier': 5.5,  # TP2 = 5.5 * ATR
            'tp3_multiplier': 9.0,  # TP3 = 9 * ATR
            'sl_multiplier': 2.0,   # SL = 2 * ATR
            'trailing_stop_pips': 18,
            'timeout_hours': 60
        },
        
        # RANGE mode parameters
        'range': {
            'tp1_multiplier': 2.0,  # TP1 = 2 * ATR
            'tp2_multiplier': 3.5,  # TP2 = 3.5 * ATR
            'tp3_multiplier': 5.0,  # TP3 = 5 * ATR
            'sl_multiplier': 2.0,   # SL = 2 * ATR
            'trailing_stop_pips': 15,
            'timeout_hours': 48
        },
        
        # Partial close percentages
        'tp1_close_percent': 50,  # Close 50% at TP1
        'tp2_close_percent': 30,  # Close 30% at TP2
        'tp3_close_percent': 20,  # Close remaining 20% at TP3
        
        # Entry filters
        'min_rsi': 30,  # Minimum RSI for LONG
        'max_rsi': 70,  # Maximum RSI for SHORT
    },
    
    # Costs (for backtesting/tracking)
    'costs': {
        'spread_pips': 2.0,
        'commission_pips': 0.5,
        'swap_per_day': -0.3
    },
    
    # Telegram notifications (optional)
    'telegram': {
        'enabled': False,
        'bot_token': 'YOUR_TELEGRAM_BOT_TOKEN',
        'chat_id': 'YOUR_TELEGRAM_CHAT_ID'
    },
    
    # Logging
    'logging': {
        'enabled': True,
        'log_file': 'crypto_bot.log',
        'log_level': 'INFO'
    }
}


# Testnet API endpoints (Binance Futures Testnet)
TESTNET_CONFIG = {
    'base_url': 'https://testnet.binancefuture.com',
    'ws_url': 'wss://stream.binancefuture.com'
}


# Production API endpoints
PRODUCTION_CONFIG = {
    'base_url': 'https://fapi.binance.com',
    'ws_url': 'wss://fstream.binance.com'
}


def get_config():
    """Get configuration based on mode"""
    if CONFIG['testnet']:
        print("⚠️ Running in TESTNET mode")
        return {**CONFIG, **TESTNET_CONFIG}
    else:
        print("🚀 Running in PRODUCTION mode")
        return {**CONFIG, **PRODUCTION_CONFIG}


if __name__ == "__main__":
    # Display configuration
    import json
    config = get_config()
    
    # Hide sensitive data
    config_display = config.copy()
    config_display['api_key'] = '***'
    config_display['api_secret'] = '***'
    
    print("\n📋 Configuration:")
    print(json.dumps(config_display, indent=2))
