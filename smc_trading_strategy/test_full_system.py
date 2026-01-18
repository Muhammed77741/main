"""
Test script for the full auto trading bot components
Simulates the complete workflow without needing MT5
"""

import time
from datetime import datetime, timedelta
from trade_logger import TradeLogger
from telegram_notifier import TelegramNotifier
import os
from dotenv import load_dotenv


def simulate_trading_session():
    """Simulate a complete trading session"""
    
    print("\n" + "="*70)
    print("🧪 TESTING FULL AUTO TRADING BOT COMPONENTS")
    print("="*70 + "\n")
    
    # Load environment
    load_dotenv()
    
    # Initialize components
    logger = TradeLogger(log_dir='test_trade_logs')
    
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if telegram_token and telegram_chat_id and telegram_token != 'your_bot_token_here':
        notifier = TelegramNotifier(telegram_token, telegram_chat_id)
        print("✅ Telegram notifier enabled\n")
    else:
        notifier = None
        print("⚠️  Telegram notifier disabled (no credentials)\n")
    
    # Simulate 3 trades
    trades = []
    
    # Trade 1: Successful LONG with all TPs hit
    print("\n" + "-"*70)
    print("📝 TRADE 1: LONG Position - All TPs Hit")
    print("-"*70)
    
    trade1_entry_time = datetime.now() - timedelta(hours=5)
    trade1_id = logger.log_entry({
        'direction': 'LONG',
        'entry_price': 2650.50,
        'entry_time': trade1_entry_time,
        'stop_loss': 2630.00,
        'tp1_price': 2680.50,
        'tp2_price': 2700.50,
        'tp3_price': 2730.50,
        'pattern': 'Bullish Engulfing',
        'close_pct1': 0.5,
        'close_pct2': 0.3,
        'close_pct3': 0.2
    })
    trades.append(trade1_id)
    
    if notifier:
        notifier.send_entry_signal({
            'direction': 'LONG',
            'entry_price': 2650.50,
            'stop_loss': 2630.00,
            'tp1': 2680.50,
            'tp2': 2700.50,
            'tp3': 2730.50,
            'pattern': 'Bullish Engulfing',
            'timestamp': trade1_entry_time
        })
    
    print("\n⏰ Simulating price movement...")
    time.sleep(2)
    
    # TP1 hit
    print("\n🎯 TP1 reached!")
    logger.log_tp_hit(trade1_id, 'TP1', 2680.50, trade1_entry_time + timedelta(hours=2))
    
    if notifier:
        notifier.send_partial_close({
            'direction': 'LONG',
            'tp_level': 'TP1',
            'tp_price': 2680.50,
            'entry_price': 2650.50,
            'close_pct': 0.5,
            'pnl_pct': 0.57,
            'pnl_points': 15.0,
            'position_remaining': 0.5,
            'timestamp': trade1_entry_time + timedelta(hours=2)
        })
    
    time.sleep(1)
    
    # TP2 hit
    print("\n🎯 TP2 reached!")
    logger.log_tp_hit(trade1_id, 'TP2', 2700.50, trade1_entry_time + timedelta(hours=3))
    
    if notifier:
        notifier.send_partial_close({
            'direction': 'LONG',
            'tp_level': 'TP2',
            'tp_price': 2700.50,
            'entry_price': 2650.50,
            'close_pct': 0.3,
            'pnl_pct': 0.57,
            'pnl_points': 15.0,
            'position_remaining': 0.2,
            'timestamp': trade1_entry_time + timedelta(hours=3)
        })
    
    time.sleep(1)
    
    # TP3 hit
    print("\n🎯 TP3 reached!")
    logger.log_tp_hit(trade1_id, 'TP3', 2730.50, trade1_entry_time + timedelta(hours=4))
    
    if notifier:
        notifier.send_partial_close({
            'direction': 'LONG',
            'tp_level': 'TP3',
            'tp_price': 2730.50,
            'entry_price': 2650.50,
            'close_pct': 0.2,
            'pnl_pct': 0.60,
            'pnl_points': 16.0,
            'position_remaining': 0.0,
            'timestamp': trade1_entry_time + timedelta(hours=4)
        })
    
    # Close remaining position
    logger.log_exit(trade1_id, 2730.50, 'TIMEOUT', trade1_entry_time + timedelta(hours=4))
    
    if notifier:
        notifier.send_exit_signal({
            'direction': 'LONG',
            'entry_price': 2650.50,
            'exit_price': 2730.50,
            'exit_type': 'TIMEOUT',
            'pnl_pct': 1.74,
            'pnl_points': 46.0,
            'duration_hours': 4.0,
            'timestamp': trade1_entry_time + timedelta(hours=4)
        })
    
    time.sleep(2)
    
    # Trade 2: SHORT position with SL hit
    print("\n" + "-"*70)
    print("📝 TRADE 2: SHORT Position - Stop Loss Hit")
    print("-"*70)
    
    trade2_entry_time = datetime.now() - timedelta(hours=3)
    trade2_id = logger.log_entry({
        'direction': 'SHORT',
        'entry_price': 2680.00,
        'entry_time': trade2_entry_time,
        'stop_loss': 2700.00,
        'tp1_price': 2650.00,
        'tp2_price': 2630.00,
        'tp3_price': 2600.00,
        'pattern': 'Bearish Engulfing',
        'close_pct1': 0.5,
        'close_pct2': 0.3,
        'close_pct3': 0.2
    })
    trades.append(trade2_id)
    
    if notifier:
        notifier.send_entry_signal({
            'direction': 'SHORT',
            'entry_price': 2680.00,
            'stop_loss': 2700.00,
            'tp1': 2650.00,
            'tp2': 2630.00,
            'tp3': 2600.00,
            'pattern': 'Bearish Engulfing',
            'timestamp': trade2_entry_time
        })
    
    print("\n⏰ Simulating price movement...")
    time.sleep(2)
    
    # SL hit
    print("\n🛑 Stop Loss hit!")
    logger.log_sl_hit(trade2_id, 2700.00, trade2_entry_time + timedelta(hours=1))
    
    if notifier:
        notifier.send_exit_signal({
            'direction': 'SHORT',
            'entry_price': 2680.00,
            'exit_price': 2700.00,
            'exit_type': 'SL',
            'pnl_pct': -0.75,
            'pnl_points': -20.0,
            'duration_hours': 1.0,
            'timestamp': trade2_entry_time + timedelta(hours=1)
        })
    
    time.sleep(2)
    
    # Trade 3: LONG position with TP1 only
    print("\n" + "-"*70)
    print("📝 TRADE 3: LONG Position - TP1 Hit, Rest Closed Manually")
    print("-"*70)
    
    trade3_entry_time = datetime.now() - timedelta(hours=2)
    trade3_id = logger.log_entry({
        'direction': 'LONG',
        'entry_price': 2700.00,
        'entry_time': trade3_entry_time,
        'stop_loss': 2680.00,
        'tp1_price': 2730.00,
        'tp2_price': 2750.00,
        'tp3_price': 2780.00,
        'pattern': 'Morning Star',
        'close_pct1': 0.5,
        'close_pct2': 0.3,
        'close_pct3': 0.2
    })
    trades.append(trade3_id)
    
    if notifier:
        notifier.send_entry_signal({
            'direction': 'LONG',
            'entry_price': 2700.00,
            'stop_loss': 2680.00,
            'tp1': 2730.00,
            'tp2': 2750.00,
            'tp3': 2780.00,
            'pattern': 'Morning Star',
            'timestamp': trade3_entry_time
        })
    
    print("\n⏰ Simulating price movement...")
    time.sleep(2)
    
    # TP1 hit
    print("\n🎯 TP1 reached!")
    logger.log_tp_hit(trade3_id, 'TP1', 2730.00, trade3_entry_time + timedelta(hours=1))
    
    if notifier:
        notifier.send_partial_close({
            'direction': 'LONG',
            'tp_level': 'TP1',
            'tp_price': 2730.00,
            'entry_price': 2700.00,
            'close_pct': 0.5,
            'pnl_pct': 0.56,
            'pnl_points': 15.0,
            'position_remaining': 0.5,
            'timestamp': trade3_entry_time + timedelta(hours=1)
        })
    
    time.sleep(1)
    
    # Manual close of remaining
    print("\n💼 Closing remaining position manually...")
    logger.log_exit(trade3_id, 2720.00, 'MANUAL', trade3_entry_time + timedelta(hours=1.5))
    
    if notifier:
        notifier.send_exit_signal({
            'direction': 'LONG',
            'entry_price': 2700.00,
            'exit_price': 2720.00,
            'exit_type': 'MANUAL',
            'pnl_pct': 0.93,
            'pnl_points': 25.0,
            'duration_hours': 1.5,
            'timestamp': trade3_entry_time + timedelta(hours=1.5)
        })
    
    # Final statistics
    print("\n" + "="*70)
    logger.print_statistics()
    print("="*70)
    
    print("\n✅ Simulation complete!")
    print(f"   Log files saved in: test_trade_logs/")
    print(f"   - live_trades.json (history)")
    print(f"   - live_trades.csv (for Excel)")
    print(f"   - open_positions.json (current positions)")
    
    if notifier:
        print(f"\n📱 Check your Telegram for all notifications!")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    try:
        simulate_trading_session()
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
