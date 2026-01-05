"""
Скрипт для мониторинга открытых позиций в MT5

Показывает:
- Текущие открытые позиции
- Entry price, Current price, PnL
- SL и TP уровни
- Время в позиции
- Прибыль/убыток в $ и %

Использование:
    python monitor_positions.py

Параметры:
    --symbol XAUUSD    - фильтр по инструменту (опционально)
    --refresh 5        - автообновление каждые N секунд (опционально)
"""

import MetaTrader5 as mt5
from datetime import datetime
import time
import argparse
import os
from dotenv import load_dotenv


def init_mt5():
    """Инициализация MT5"""
    # Load environment variables
    load_dotenv()

    mt5_path = os.getenv('MT5_PATH')
    mt5_login = int(os.getenv('MT5_LOGIN', 0))
    mt5_password = os.getenv('MT5_PASSWORD')
    mt5_server = os.getenv('MT5_SERVER')

    # Initialize MT5
    if mt5_path and os.path.exists(mt5_path):
        if not mt5.initialize(path=mt5_path):
            print(f"❌ MT5 initialization failed (with path)")
            return False
    else:
        if not mt5.initialize():
            print(f"❌ MT5 initialization failed")
            return False

    # Login if credentials provided
    if mt5_login and mt5_password and mt5_server:
        if not mt5.login(mt5_login, password=mt5_password, server=mt5_server):
            print(f"❌ MT5 login failed")
            return False
        print(f"✅ Logged in to MT5: {mt5_login}@{mt5_server}")
    else:
        print(f"✅ Connected to MT5 (no login)")

    return True


def get_positions(symbol_filter=None):
    """Получить все открытые позиции"""
    if symbol_filter:
        positions = mt5.positions_get(symbol=symbol_filter)
    else:
        positions = mt5.positions_get()

    if positions is None:
        return []

    return list(positions)


def format_duration(seconds):
    """Форматировать длительность"""
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)

    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


def print_positions(positions, show_header=True):
    """Красиво вывести позиции"""
    if show_header:
        print(f"\n{'='*100}")
        print(f"📊 ОТКРЫТЫЕ ПОЗИЦИИ MT5 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*100}")

    if not positions or len(positions) == 0:
        print("   ℹ️  Нет открытых позиций")
        return

    # Account info
    account_info = mt5.account_info()
    if account_info:
        print(f"\n💼 СЧЕТ:")
        print(f"   Balance: ${account_info.balance:.2f}")
        print(f"   Equity: ${account_info.equity:.2f}")
        print(f"   Margin: ${account_info.margin:.2f}")
        print(f"   Free Margin: ${account_info.margin_free:.2f}")
        print(f"   Profit: ${account_info.profit:.2f}")

    print(f"\n📍 ПОЗИЦИИ ({len(positions)}):")
    print(f"{'─'*100}")

    for i, pos in enumerate(positions, 1):
        # Direction
        direction = "🟢 LONG" if pos.type == mt5.ORDER_TYPE_BUY else "🔴 SHORT"

        # PnL
        pnl_dollars = pos.profit
        pnl_emoji = "✅" if pnl_dollars > 0 else "❌" if pnl_dollars < 0 else "⚪"

        # Time in position
        open_time = datetime.fromtimestamp(pos.time)
        duration = (datetime.now() - open_time).total_seconds()
        duration_str = format_duration(duration)

        # Price info
        entry_price = pos.price_open
        current_price = pos.price_current
        price_diff = current_price - entry_price
        price_diff_pct = (price_diff / entry_price) * 100

        if pos.type == mt5.ORDER_TYPE_SELL:
            price_diff_pct = -price_diff_pct

        print(f"\n{i}. {direction} {pos.symbol} - Ticket #{pos.ticket}")
        print(f"   📈 Entry: {entry_price:.2f}")
        print(f"   💰 Current: {current_price:.2f} ({price_diff:+.2f} points, {price_diff_pct:+.2f}%)")
        print(f"   📊 Volume: {pos.volume:.2f} lots")

        # SL/TP
        sl_str = f"{pos.sl:.2f}" if pos.sl > 0 else "None"
        tp_str = f"{pos.tp:.2f}" if pos.tp > 0 else "None"
        print(f"   🛑 SL: {sl_str}")
        print(f"   🎯 TP: {tp_str}")

        # PnL
        print(f"   {pnl_emoji} Profit: ${pnl_dollars:+.2f}")

        # Time
        print(f"   ⏰ Opened: {open_time.strftime('%Y-%m-%d %H:%M:%S')} ({duration_str} ago)")

        # Comment
        if pos.comment:
            print(f"   💬 Comment: {pos.comment}")

    print(f"{'─'*100}")


def monitor_positions(symbol_filter=None, refresh_interval=None):
    """Мониторить позиции с автообновлением"""

    if refresh_interval is None:
        # Одноразовый вывод
        positions = get_positions(symbol_filter)
        print_positions(positions)
        return

    # Непрерывный мониторинг
    try:
        while True:
            # Clear screen (работает на Windows и Linux)
            os.system('cls' if os.name == 'nt' else 'clear')

            positions = get_positions(symbol_filter)
            print_positions(positions)

            print(f"\n🔄 Автообновление каждые {refresh_interval} секунд... (Ctrl+C для выхода)")
            time.sleep(refresh_interval)

    except KeyboardInterrupt:
        print("\n\n⚠️  Мониторинг остановлен пользователем")


def main():
    parser = argparse.ArgumentParser(description='Monitor MT5 positions')
    parser.add_argument('--symbol', type=str, default=None, help='Filter by symbol (e.g., XAUUSD)')
    parser.add_argument('--refresh', type=int, default=None, help='Auto-refresh interval in seconds (e.g., 5)')

    args = parser.parse_args()

    # Initialize MT5
    if not init_mt5():
        return

    try:
        # Monitor positions
        monitor_positions(args.symbol, args.refresh)

    finally:
        # Shutdown MT5
        mt5.shutdown()
        print("✅ MT5 connection closed")


if __name__ == "__main__":
    main()
