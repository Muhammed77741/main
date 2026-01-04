#!/usr/bin/env python3
"""
Test Script - Open Position for Testing Semi-Auto Bot

Этот скрипт открывает тестовую позицию в MT5 для проверки
автоматического управления позициями ботом.

ВНИМАНИЕ: Использовать только на DEMO счёте!
"""

import MetaTrader5 as mt5
from datetime import datetime
import argparse


class TestPositionOpener:
    """Открывает тестовые позиции в MT5"""

    def __init__(self, symbol='XAUUSD'):
        self.symbol = symbol

    def connect_mt5(self):
        """Подключиться к MT5"""
        if not mt5.initialize():
            print("❌ Failed to connect to MT5")
            return False

        print("✅ Connected to MT5")
        return True

    def get_current_price(self):
        """Получить текущую цену"""
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            print(f"❌ Failed to get tick for {self.symbol}")
            return None, None

        return tick.bid, tick.ask

    def open_test_position(self, direction='LONG', lot_size=0.01, sl_points=20, tp_points=50):
        """
        Открыть тестовую позицию

        Args:
            direction: 'LONG' or 'SHORT'
            lot_size: Размер лота
            sl_points: Стоп-лосс в пунктах
            tp_points: Тейк-профит в пунктах (опционально)

        Returns:
            OrderSendResult or None
        """
        print(f"\n{'='*80}")
        print(f"📊 OPENING TEST POSITION")
        print(f"{'='*80}")

        # Получить текущую цену
        bid, ask = self.get_current_price()
        if bid is None or ask is None:
            return None

        print(f"   Current price: Bid={bid:.2f}, Ask={ask:.2f}")

        # Определить параметры ордера
        if direction == 'LONG':
            order_type = mt5.ORDER_TYPE_BUY
            price = ask
            sl_price = price - sl_points
            tp_price = price + tp_points if tp_points else None
        else:  # SHORT
            order_type = mt5.ORDER_TYPE_SELL
            price = bid
            sl_price = price + sl_points
            tp_price = price - tp_points if tp_points else None

        # Подготовить запрос
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": lot_size,
            "type": order_type,
            "price": price,
            "sl": sl_price,
            "tp": tp_price if tp_price else 0,
            "deviation": 20,
            "magic": 234000,
            "comment": f"TEST_{direction}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        print(f"\n   Direction: {direction}")
        print(f"   Lot size: {lot_size}")
        print(f"   Entry: {price:.2f}")
        print(f"   SL: {sl_price:.2f} ({sl_points}п)")
        if tp_price:
            print(f"   TP: {tp_price:.2f} ({tp_points}п)")
        else:
            print(f"   TP: None (will be managed by bot)")

        # Отправить ордер
        print(f"\n⏳ Sending order to MT5...")
        result = mt5.order_send(request)

        if result is None:
            print("❌ Order send failed: No result")
            return None

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Order failed: {result.retcode}")
            print(f"   Comment: {result.comment}")
            return None

        print(f"\n✅ Position opened successfully!")
        print(f"   Ticket: {result.order}")
        print(f"   Entry price: {result.price:.2f}")
        print(f"   Volume: {result.volume:.2f}")

        return result

    def open_v9_long_trend_position(self, lot_size=0.01):
        """Открыть позицию с V9 LONG TREND параметрами"""
        print("\n🎯 Opening V9 LONG TREND test position")

        bid, ask = self.get_current_price()
        if bid is None:
            return None

        # V9 LONG TREND parameters
        entry = ask
        sl = entry - 20  # Примерно 20 пунктов
        tp1 = entry + 35
        tp2 = entry + 65
        tp3 = entry + 100

        print(f"\n   V9 LONG TREND Parameters:")
        print(f"   Entry: {entry:.2f}")
        print(f"   SL: {sl:.2f}")
        print(f"   TP1: {tp1:.2f} (close 30%)")
        print(f"   TP2: {tp2:.2f} (close 30%)")
        print(f"   TP3: {tp3:.2f} (close 40%)")
        print(f"   Trailing: 25п after TP1")

        # Открыть без TP (бот будет управлять)
        return self.open_test_position(
            direction='LONG',
            lot_size=lot_size,
            sl_points=20,
            tp_points=0  # No TP, bot will manage
        )

    def open_v9_short_trend_position(self, lot_size=0.01):
        """Открыть позицию с V9 SHORT TREND параметрами"""
        print("\n🎯 Opening V9 SHORT TREND test position")

        bid, ask = self.get_current_price()
        if bid is None:
            return None

        # V9 SHORT TREND parameters
        entry = bid
        sl = entry + 15  # Примерно 15 пунктов
        tp1 = entry - 18
        tp2 = entry - 30
        tp3 = entry - 42

        print(f"\n   V9 SHORT TREND Parameters:")
        print(f"   Entry: {entry:.2f}")
        print(f"   SL: {sl:.2f}")
        print(f"   TP1: {tp1:.2f} (close 30%)")
        print(f"   TP2: {tp2:.2f} (close 30%)")
        print(f"   TP3: {tp3:.2f} (close 40%)")
        print(f"   Trailing: 13п after TP1")

        return self.open_test_position(
            direction='SHORT',
            lot_size=lot_size,
            sl_points=15,
            tp_points=0  # No TP, bot will manage
        )

    def show_open_positions(self):
        """Показать открытые позиции"""
        print(f"\n{'='*80}")
        print(f"📊 OPEN POSITIONS")
        print(f"{'='*80}")

        positions = mt5.positions_get(symbol=self.symbol)

        if not positions or len(positions) == 0:
            print("   No open positions")
            return

        for pos in positions:
            direction = "LONG" if pos.type == mt5.POSITION_TYPE_BUY else "SHORT"
            profit_pct = (pos.profit / (pos.volume * pos.price_open * 100)) * 100

            print(f"\n   Ticket: {pos.ticket}")
            print(f"   Direction: {direction}")
            print(f"   Volume: {pos.volume:.2f} lots")
            print(f"   Entry: {pos.price_open:.2f}")
            print(f"   Current: {pos.price_current:.2f}")
            print(f"   Profit: ${pos.profit:.2f} ({profit_pct:+.2f}%)")
            print(f"   SL: {pos.sl:.2f if pos.sl else 'None'}")
            print(f"   TP: {pos.tp:.2f if pos.tp else 'None'}")
            print(f"   Comment: {pos.comment}")
            print(f"   {'-'*40}")

    def close_all_test_positions(self):
        """Закрыть все тестовые позиции"""
        print(f"\n{'='*80}")
        print(f"🔴 CLOSING ALL TEST POSITIONS")
        print(f"{'='*80}")

        positions = mt5.positions_get(symbol=self.symbol)

        if not positions or len(positions) == 0:
            print("   No positions to close")
            return

        closed_count = 0
        for pos in positions:
            # Закрывать только тестовые позиции
            if pos.comment and 'TEST' in pos.comment:
                # Определить тип ордера для закрытия
                if pos.type == mt5.POSITION_TYPE_BUY:
                    order_type = mt5.ORDER_TYPE_SELL
                    price = mt5.symbol_info_tick(self.symbol).bid
                else:
                    order_type = mt5.ORDER_TYPE_BUY
                    price = mt5.symbol_info_tick(self.symbol).ask

                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": self.symbol,
                    "volume": pos.volume,
                    "type": order_type,
                    "position": pos.ticket,
                    "price": price,
                    "deviation": 20,
                    "magic": 234000,
                    "comment": "Close test",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC,
                }

                result = mt5.order_send(request)
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"   ✅ Closed position {pos.ticket}")
                    closed_count += 1
                else:
                    print(f"   ❌ Failed to close {pos.ticket}: {result.comment}")

        print(f"\n   Closed {closed_count} test positions")

    def shutdown(self):
        """Отключиться от MT5"""
        mt5.shutdown()
        print("\n✅ Disconnected from MT5")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Open test positions for Semi-Auto Bot testing')
    parser.add_argument('--action', type=str, choices=['long', 'short', 'v9-long', 'v9-short', 'show', 'close'],
                        default='show', help='Action to perform')
    parser.add_argument('--lot', type=float, default=0.01, help='Lot size (default: 0.01)')
    parser.add_argument('--sl', type=int, default=20, help='Stop loss in points (default: 20)')
    parser.add_argument('--tp', type=int, default=0, help='Take profit in points (default: 0 - bot managed)')
    args = parser.parse_args()

    print("\n" + "="*80)
    print("🧪 TEST POSITION OPENER - Semi-Auto Bot")
    print("="*80)
    print("\n⚠️  WARNING: Use only on DEMO account!")

    # Create opener
    opener = TestPositionOpener(symbol='XAUUSD')

    # Connect
    if not opener.connect_mt5():
        return

    # Get account info
    account = mt5.account_info()
    if account:
        print(f"\n💰 Account Info:")
        print(f"   Server: {account.server}")
        print(f"   Login: {account.login}")
        print(f"   Balance: ${account.balance:.2f}")
        print(f"   Equity: ${account.equity:.2f}")

    try:
        # Execute action
        if args.action == 'long':
            opener.open_test_position('LONG', args.lot, args.sl, args.tp)
            opener.show_open_positions()

        elif args.action == 'short':
            opener.open_test_position('SHORT', args.lot, args.sl, args.tp)
            opener.show_open_positions()

        elif args.action == 'v9-long':
            opener.open_v9_long_trend_position(args.lot)
            opener.show_open_positions()

        elif args.action == 'v9-short':
            opener.open_v9_short_trend_position(args.lot)
            opener.show_open_positions()

        elif args.action == 'show':
            opener.show_open_positions()

        elif args.action == 'close':
            opener.close_all_test_positions()
            opener.show_open_positions()

    finally:
        opener.shutdown()


if __name__ == "__main__":
    main()
