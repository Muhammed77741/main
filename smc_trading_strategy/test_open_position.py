"""
Test script for opening positions in MT5
Usage: python test_open_position.py --action v9-long --lot 0.01
"""

import MetaTrader5 as mt5
import argparse
from datetime import datetime
import time


class MT5PositionTester:
    """Test opening positions in MT5 with proper error handling"""

    def __init__(self, symbol='XAUUSD'):
        self.symbol = symbol
        self.initialized = False

    def initialize(self):
        """Initialize MT5 connection"""
        print(f"\n{'='*80}")
        print(f"🔌 Initializing MT5 connection...")
        print(f"{'='*80}\n")

        if not mt5.initialize():
            error = mt5.last_error()
            print(f"❌ MT5 initialization failed: {error}")
            print("\n💡 Check:")
            print("   1. MT5 terminal is running")
            print("   2. You are on Windows")
            print("   3. MetaTrader5 module is installed")
            return False

        print(f"✅ MT5 initialized successfully")

        # Check account info
        account = mt5.account_info()
        if account is None:
            print(f"⚠️  Not logged in (this is OK if terminal is open)")
        else:
            print(f"\n📊 Account Info:")
            print(f"   Login: {account.login}")
            print(f"   Server: {account.server}")
            print(f"   Balance: {account.balance} {account.currency}")
            print(f"   Type: {'Demo' if account.trade_mode == 1 else 'Real'}")

        self.initialized = True
        return True

    def prepare_symbol(self):
        """Prepare symbol for trading"""
        print(f"\n🔍 Checking symbol {self.symbol}...")

        # Get symbol info
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(f"❌ Symbol {self.symbol} not found")
            print("\n💡 Try:")
            print("   - Add XAUUSD to Market Watch in MT5")
            print("   - Or try alternative symbols: GOLD, XAU/USD, XAUUSD.m")
            return False

        # Make symbol visible if needed
        if not symbol_info.visible:
            print(f"   Symbol not visible, adding to Market Watch...")
            if not mt5.symbol_select(self.symbol, True):
                print(f"❌ Failed to add symbol to Market Watch")
                return False

        print(f"✅ Symbol ready: {symbol_info.description}")
        print(f"   Spread: {symbol_info.spread} points")
        print(f"   Min volume: {symbol_info.volume_min}")
        print(f"   Max volume: {symbol_info.volume_max}")
        print(f"   Volume step: {symbol_info.volume_step}")

        return True

    def get_current_price(self):
        """Get current price"""
        tick = mt5.symbol_info_tick(self.symbol)
        if tick is None:
            error = mt5.last_error()
            print(f"❌ Failed to get price: {error}")
            return None, None

        return tick.bid, tick.ask

    def check_order_params(self, request):
        """Check if order parameters are valid"""
        print(f"\n🔍 Checking order parameters...")

        result = mt5.order_check(request)

        if result is None:
            error = mt5.last_error()
            print(f"❌ order_check returned None")
            print(f"   Error code: {error[0] if error else 'Unknown'}")
            print(f"   Error message: {error[1] if len(error) > 1 else 'Unknown'}")
            return False

        # For order_check, retcode 0 means success
        # For order_send, retcode 10009 (TRADE_RETCODE_DONE) means success
        if result.retcode != 0:
            print(f"❌ Order check failed")
            print(f"   Return code: {result.retcode}")
            print(f"   Comment: {result.comment}")

            # Common error codes
            if result.retcode == 10014:
                print(f"\n💡 Error 10014: Invalid volume")
                print(f"   - Check min/max volume for {self.symbol}")
            elif result.retcode == 10015:
                print(f"\n💡 Error 10015: Invalid price")
                print(f"   - Price might be too far from current market price")
            elif result.retcode == 10016:
                print(f"\n💡 Error 10016: Invalid stops")
                print(f"   - Check SL/TP distance requirements")
            elif result.retcode == 10018:
                print(f"\n💡 Error 10018: Market closed")
                print(f"   - Wait for market to open")
            elif result.retcode == 10019:
                print(f"\n💡 Error 10019: Not enough money")
                print(f"   - Reduce lot size or deposit more")
            elif result.retcode == 10027:
                print(f"\n💡 Error 10027: AutoTrading disabled")
                print(f"   - Enable AutoTrading in MT5 (Ctrl+E or Tools > Options > Expert Advisors)")
            elif result.retcode == 0:
                print(f"\n💡 Return code 0 with error comment")
                print(f"   This might indicate a check passed but with warnings")
            else:
                print(f"\n💡 Unknown error code: {result.retcode}")
                print(f"   Check MT5 documentation for this error code")

            return False

        print(f"✅ Order check passed")
        print(f"   Estimated balance after: ${result.balance:.2f}")
        print(f"   Margin required: ${result.margin:.2f}")
        print(f"   Comment: {result.comment}")
        return True

    def open_position(self, direction='long', lot=0.01, sl_points=100, tp_points=300):
        """
        Open a test position

        Args:
            direction: 'long' or 'short'
            lot: Position size
            sl_points: Stop loss in points
            tp_points: Take profit in points
        """
        if not self.initialized:
            print(f"❌ MT5 not initialized")
            return False

        print(f"\n{'='*80}")
        print(f"📊 Opening {direction.upper()} position")
        print(f"{'='*80}")
        print(f"   Symbol: {self.symbol}")
        print(f"   Lot: {lot}")
        print(f"   SL: {sl_points} points")
        print(f"   TP: {tp_points} points")

        # Get current price
        bid, ask = self.get_current_price()
        if bid is None or ask is None:
            return False

        print(f"\n💰 Current price:")
        print(f"   Bid: {bid:.2f}")
        print(f"   Ask: {ask:.2f}")

        # Get symbol info for point value
        symbol_info = mt5.symbol_info(self.symbol)
        if symbol_info is None:
            print(f"❌ Failed to get symbol info")
            return False

        point = symbol_info.point
        digits = symbol_info.digits

        # Prepare request
        if direction.lower() == 'long':
            order_type = mt5.ORDER_TYPE_BUY
            price = ask
            sl = price - sl_points * point
            tp = price + tp_points * point
        else:  # short
            order_type = mt5.ORDER_TYPE_SELL
            price = bid
            sl = price + sl_points * point
            tp = price - tp_points * point

        # Prepare order request
        request = {
            'action': mt5.TRADE_ACTION_DEAL,
            'symbol': self.symbol,
            'volume': lot,
            'type': order_type,
            'price': price,
            'sl': round(sl, digits),
            'tp': round(tp, digits),
            'deviation': 20,
            'magic': 234000,
            'comment': 'test_position',
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': mt5.ORDER_FILLING_IOC,
        }

        print(f"\n📋 Order details:")
        print(f"   Entry: {price:.{digits}f}")
        print(f"   SL: {request['sl']:.{digits}f}")
        print(f"   TP: {request['tp']:.{digits}f}")

        # Check order before sending
        if not self.check_order_params(request):
            return False

        # Send order
        print(f"\n📤 Sending order to MT5...")
        result = mt5.order_send(request)

        # Check result
        if result is None:
            error = mt5.last_error()
            print(f"❌ order_send returned None (No result)")
            print(f"   Error: {error}")
            print(f"\n💡 Possible reasons:")
            print(f"   1. AutoTrading is disabled")
            print(f"      → Enable in MT5: Tools > Options > Expert Advisors > Allow automated trading")
            print(f"   2. Account is read-only or trading is restricted")
            print(f"   3. Market is closed")
            print(f"   4. Insufficient permissions")
            return False

        # Check return code
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Order failed")
            print(f"   Return code: {result.retcode}")
            print(f"   Comment: {result.comment}")

            if result.retcode == 10027:
                print(f"\n💡 AutoTrading is disabled!")
                print(f"   Enable it: Tools > Options > Expert Advisors > Allow automated trading")

            return False

        # Success!
        print(f"\n✅ Position opened successfully!")
        print(f"   Order: #{result.order}")
        print(f"   Deal: #{result.deal}")
        print(f"   Volume: {result.volume}")
        print(f"   Price: {result.price:.{digits}f}")
        print(f"   Bid: {result.bid:.{digits}f}")
        print(f"   Ask: {result.ask:.{digits}f}")

        return True

    def check_positions(self):
        """Check open positions"""
        print(f"\n{'='*80}")
        print(f"📊 Checking open positions")
        print(f"{'='*80}\n")

        positions = mt5.positions_get(symbol=self.symbol)

        if positions is None:
            error = mt5.last_error()
            print(f"❌ Failed to get positions: {error}")
            return

        if len(positions) == 0:
            print(f"📭 No open positions")
            return

        print(f"📈 Found {len(positions)} open position(s):\n")

        for i, pos in enumerate(positions, 1):
            print(f"   Position #{i}:")
            print(f"   ├─ Ticket: {pos.ticket}")
            print(f"   ├─ Type: {'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL'}")
            print(f"   ├─ Volume: {pos.volume}")
            print(f"   ├─ Entry: {pos.price_open:.2f}")
            print(f"   ├─ Current: {pos.price_current:.2f}")
            print(f"   ├─ SL: {pos.sl:.2f}" if pos.sl else "   ├─ SL: None")
            print(f"   ├─ TP: {pos.tp:.2f}" if pos.tp else "   ├─ TP: None")
            account = mt5.account_info()
            currency = account.currency if account else 'USD'
            print(f"   ├─ Profit: {pos.profit:.2f} {currency}")
            print(f"   └─ Time: {datetime.fromtimestamp(pos.time)}\n")

    def shutdown(self):
        """Shutdown MT5 connection"""
        print(f"\n{'='*80}")
        print(f"🔌 Disconnecting from MT5")
        print(f"{'='*80}\n")
        mt5.shutdown()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Test opening positions in MT5')
    parser.add_argument('--action', type=str, required=True,
                       help='Action: v9-long, v9-short, v8-long, v8-short, etc.')
    parser.add_argument('--lot', type=float, default=0.01,
                       help='Lot size (default: 0.01)')
    parser.add_argument('--sl', type=int, default=100,
                       help='Stop loss in points (default: 100)')
    parser.add_argument('--tp', type=int, default=300,
                       help='Take profit in points (default: 300)')
    parser.add_argument('--symbol', type=str, default='XAUUSD',
                       help='Symbol to trade (default: XAUUSD)')

    args = parser.parse_args()

    # Parse direction from action
    direction = 'long' if 'long' in args.action.lower() else 'short'

    print(f"\n{'='*80}")
    print(f"🧪 MT5 POSITION OPENING TEST")
    print(f"{'='*80}")
    print(f"   Action: {args.action}")
    print(f"   Direction: {direction}")
    print(f"   Lot: {args.lot}")
    print(f"   SL: {args.sl} points")
    print(f"   TP: {args.tp} points")
    print(f"   Symbol: {args.symbol}")

    # Create tester
    tester = MT5PositionTester(symbol=args.symbol)

    try:
        # Initialize
        if not tester.initialize():
            return

        # Prepare symbol
        if not tester.prepare_symbol():
            return

        # Open position
        tester.open_position(
            direction=direction,
            lot=args.lot,
            sl_points=args.sl,
            tp_points=args.tp
        )

        # Check positions
        tester.check_positions()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Shutdown
        tester.shutdown()


if __name__ == "__main__":
    main()
