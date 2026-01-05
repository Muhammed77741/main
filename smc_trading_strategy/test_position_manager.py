#!/usr/bin/env python3
"""
Advanced Position Manager Test Script

Этот скрипт симулирует полный цикл управления позицией:
1. Открывает позицию с V9 параметрами
2. Добавляет её в tracking бота
3. Бот автоматически управляет (TP/SL/trailing)

Можно также вручную модифицировать позиции для тестирования.
"""

import MetaTrader5 as mt5
from datetime import datetime
import time
import argparse


class PositionManagerTester:
    """Тестер управления позициями"""

    def __init__(self, symbol='XAUUSD'):
        self.symbol = symbol

        # V9 LONG TREND parameters
        self.long_trend_tp1 = 35
        self.long_trend_tp2 = 65
        self.long_trend_tp3 = 100
        self.long_trend_trailing = 25
        self.long_trend_sl = 20

        # V9 SHORT TREND parameters
        self.short_trend_tp1 = 18
        self.short_trend_tp2 = 30
        self.short_trend_tp3 = 42
        self.short_trend_trailing = 13
        self.short_trend_sl = 15

    def connect_mt5(self):
        """Подключиться к MT5"""
        if not mt5.initialize():
            print("❌ Failed to connect to MT5")
            return False
        print("✅ Connected to MT5")
        return True

    def open_v9_position(self, direction='LONG', regime='TREND', lot_size=0.01):
        """
        Открыть позицию с V9 параметрами

        Args:
            direction: 'LONG' or 'SHORT'
            regime: 'TREND' or 'RANGE'
            lot_size: Размер лота
        """
        print(f"\n{'='*80}")
        print(f"📊 OPENING V9 {direction} {regime} POSITION")
        print(f"{'='*80}")

        # Получить текущую цену
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            print(f"❌ Failed to get tick for {self.symbol}")
            return None

        # Определить параметры
        if direction == 'LONG':
            entry = tick.ask
            sl = entry - self.long_trend_sl
            tp1 = entry + self.long_trend_tp1
            tp2 = entry + self.long_trend_tp2
            tp3 = entry + self.long_trend_tp3
            trailing = self.long_trend_trailing
            order_type = mt5.ORDER_TYPE_BUY
        else:
            entry = tick.bid
            sl = entry + self.short_trend_sl
            tp1 = entry - self.short_trend_tp1
            tp2 = entry - self.short_trend_tp2
            tp3 = entry - self.short_trend_tp3
            trailing = self.short_trend_trailing
            order_type = mt5.ORDER_TYPE_SELL

        print(f"\n   📍 Entry: {entry:.2f}")
        print(f"   🛑 SL: {sl:.2f}")
        print(f"   🎯 TP1: {tp1:.2f} (close 30%)")
        print(f"   🎯 TP2: {tp2:.2f} (close 30%)")
        print(f"   🎯 TP3: {tp3:.2f} (close 40%)")
        print(f"   📊 Trailing: {trailing}п")
        print(f"   💼 Lot: {lot_size}")

        # Открыть позицию БЕЗ TP (бот будет управлять)
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": lot_size,
            "type": order_type,
            "price": entry,
            "sl": sl,
            "tp": 0,  # No TP - bot manages
            "deviation": 20,
            "magic": 234000,
            "comment": f"V9_{direction}_{regime}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        print(f"\n   ⏳ Sending order...")
        result = mt5.order_send(request)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"   ❌ Failed: {result.comment if result else 'No result'}")
            return None

        print(f"\n   ✅ Position opened!")
        print(f"   🎫 Ticket: {result.order}")

        # Создать tracking data для бота
        position_data = {
            'ticket': result.order,
            'direction': direction,
            'regime': regime,
            'entry_price': result.price,
            'entry_time': datetime.now(),
            'stop_loss': sl,
            'tp1_price': tp1,
            'tp2_price': tp2,
            'tp3_price': tp3,
            'tp1_hit': False,
            'tp2_hit': False,
            'tp3_hit': False,
            'trailing_distance': trailing,
            'timeout_hours': 60 if regime == 'TREND' else 48,
            'initial_volume': lot_size,
            'current_volume': lot_size,
        }

        # Вывести tracking data для добавления в бот
        print(f"\n   📝 Position tracking data:")
        print(f"   (Add this to bot.open_positions list)")
        print(f"   {'-'*40}")
        for key, value in position_data.items():
            if isinstance(value, datetime):
                print(f"   {key}: {value.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"   {key}: {value}")

        return result, position_data

    def modify_position_sl_tp(self, ticket, new_sl=None, new_tp=None):
        """Изменить SL/TP позиции"""
        print(f"\n{'='*40}")
        print(f"📊 MODIFYING POSITION {ticket}")
        print(f"{'='*40}")

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": new_sl if new_sl else 0,
            "tp": new_tp if new_tp else 0,
        }

        result = mt5.order_send(request)

        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"   ✅ Modified successfully")
            if new_sl:
                print(f"   🛑 New SL: {new_sl:.2f}")
            if new_tp:
                print(f"   🎯 New TP: {new_tp:.2f}")
            return True
        else:
            print(f"   ❌ Failed: {result.comment}")
            return False

    def close_position_partial(self, ticket, volume):
        """Частично закрыть позицию"""
        print(f"\n{'='*40}")
        print(f"📊 PARTIAL CLOSE: {ticket}")
        print(f"{'='*40}")

        # Получить позицию
        positions = mt5.positions_get(ticket=ticket)
        if not positions or len(positions) == 0:
            print(f"   ❌ Position {ticket} not found")
            return False

        pos = positions[0]

        # Противоположный ордер
        if pos.type == mt5.POSITION_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(self.symbol).bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(self.symbol).ask

        print(f"   Current volume: {pos.volume:.2f}")
        print(f"   Closing: {volume:.2f}")

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.symbol,
            "volume": volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "Partial close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"   ✅ Closed {volume:.2f} lots")
            print(f"   Remaining: {pos.volume - volume:.2f}")
            return True
        else:
            print(f"   ❌ Failed: {result.comment}")
            return False

    def show_position_details(self, ticket):
        """Показать детали позиции"""
        positions = mt5.positions_get(ticket=ticket)
        if not positions or len(positions) == 0:
            print(f"   ❌ Position {ticket} not found")
            return

        pos = positions[0]
        direction = "LONG" if pos.type == mt5.POSITION_TYPE_BUY else "SHORT"

        print(f"\n{'='*80}")
        print(f"📊 POSITION DETAILS: {ticket}")
        print(f"{'='*80}")
        print(f"   Direction: {direction}")
        print(f"   Volume: {pos.volume:.2f} lots")
        print(f"   Entry: {pos.price_open:.2f}")
        print(f"   Current: {pos.price_current:.2f}")
        print(f"   SL: {pos.sl:.2f}" if pos.sl else "   SL: None")
        print(f"   TP: {pos.tp:.2f}" if pos.tp else "   TP: None")
        print(f"   Profit: ${pos.profit:.2f}")
        print(f"   Comment: {pos.comment}")
        print(f"   Open time: {datetime.fromtimestamp(pos.time)}")

    def monitor_position(self, ticket, duration_seconds=60):
        """Мониторить позицию в реальном времени"""
        print(f"\n{'='*80}")
        print(f"📊 MONITORING POSITION {ticket} for {duration_seconds}s")
        print(f"{'='*80}")

        start_time = time.time()
        last_price = None

        while time.time() - start_time < duration_seconds:
            positions = mt5.positions_get(ticket=ticket)
            if not positions or len(positions) == 0:
                print(f"\n   ❌ Position {ticket} closed")
                break

            pos = positions[0]
            current_price = pos.price_current

            if last_price is None or abs(current_price - last_price) > 0.5:
                direction = "LONG" if pos.type == mt5.POSITION_TYPE_BUY else "SHORT"
                profit_pct = (pos.profit / (pos.volume * pos.price_open * 100)) * 100

                print(f"\n   {datetime.now().strftime('%H:%M:%S')}")
                print(f"   {direction} {pos.volume:.2f} @ {pos.price_open:.2f}")
                print(f"   Current: {current_price:.2f}")
                print(f"   Profit: ${pos.profit:.2f} ({profit_pct:+.2f}%)")
                print(f"   SL: {pos.sl:.2f}" if pos.sl else "   SL: None")

                last_price = current_price

            time.sleep(5)  # Проверять каждые 5 секунд

    def simulate_tp_hit(self, ticket, tp_level=1):
        """
        Симулировать достижение TP путём модификации SL
        (Используется для тестирования логики partial close)
        """
        print(f"\n{'='*80}")
        print(f"🎯 SIMULATING TP{tp_level} HIT")
        print(f"{'='*80}")

        positions = mt5.positions_get(ticket=ticket)
        if not positions or len(positions) == 0:
            print(f"   ❌ Position not found")
            return

        pos = positions[0]
        current_price = pos.price_current

        print(f"   Current price: {current_price:.2f}")
        print(f"   Will execute partial close at TP{tp_level}")

        # Симулировать partial close
        if tp_level == 1:
            close_pct = 0.3
        elif tp_level == 2:
            close_pct = 0.3
        else:
            close_pct = 0.4

        volume_to_close = pos.volume * close_pct
        volume_to_close = round(volume_to_close, 2)

        if volume_to_close < 0.01:
            volume_to_close = 0.01

        print(f"   Closing {close_pct*100:.0f}% = {volume_to_close:.2f} lots")

        return self.close_position_partial(ticket, volume_to_close)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Advanced Position Manager Test')
    parser.add_argument('--action', type=str,
                        choices=['open-long', 'open-short', 'show', 'modify', 'partial', 'monitor', 'sim-tp'],
                        required=True, help='Action to perform')
    parser.add_argument('--ticket', type=int, help='Position ticket')
    parser.add_argument('--lot', type=float, default=0.01, help='Lot size')
    parser.add_argument('--sl', type=float, help='New stop loss')
    parser.add_argument('--tp', type=float, help='New take profit')
    parser.add_argument('--volume', type=float, help='Volume to close')
    parser.add_argument('--tp-level', type=int, choices=[1, 2, 3], default=1, help='TP level to simulate')
    parser.add_argument('--duration', type=int, default=60, help='Monitor duration in seconds')
    args = parser.parse_args()

    print("\n" + "="*80)
    print("🧪 ADVANCED POSITION MANAGER TEST")
    print("="*80)
    print("\n⚠️  Use only on DEMO account!")

    # Create tester
    tester = PositionManagerTester(symbol='XAUUSD')

    # Connect
    if not tester.connect_mt5():
        return

    try:
        if args.action == 'open-long':
            result, data = tester.open_v9_position('LONG', 'TREND', args.lot)

        elif args.action == 'open-short':
            result, data = tester.open_v9_position('SHORT', 'TREND', args.lot)

        elif args.action == 'show':
            if not args.ticket:
                print("❌ --ticket required")
                return
            tester.show_position_details(args.ticket)

        elif args.action == 'modify':
            if not args.ticket:
                print("❌ --ticket required")
                return
            tester.modify_position_sl_tp(args.ticket, args.sl, args.tp)

        elif args.action == 'partial':
            if not args.ticket or not args.volume:
                print("❌ --ticket and --volume required")
                return
            tester.close_position_partial(args.ticket, args.volume)

        elif args.action == 'monitor':
            if not args.ticket:
                print("❌ --ticket required")
                return
            tester.monitor_position(args.ticket, args.duration)

        elif args.action == 'sim-tp':
            if not args.ticket:
                print("❌ --ticket required")
                return
            tester.simulate_tp_hit(args.ticket, args.tp_level)

    finally:
        mt5.shutdown()
        print("\n✅ Disconnected from MT5")


if __name__ == "__main__":
    main()
