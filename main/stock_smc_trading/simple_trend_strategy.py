"""
Simple Trend Following Strategy for Stocks

KISS Principle: Keep It Simple, Stupid!

No SMC, no patterns, no complexity.
Just CLASSIC trend-following that WORKS:
- EMA crossovers
- ADX for trend strength
- RSI for entry timing
- Volume confirmation
- Simple fixed TP/SL

Target: 1-2 trades/week, 55%+ WR, slow steady gains
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional


class SimpleTrendStrategy:
    """
    Simple, Robust, Proven Trend Following
    
    Entry Rules:
    1. EMA 20 > EMA 50 (uptrend)
    2. ADX > 25 (strong trend)
    3. RSI pullback to 40-60 (not overbought)
    4. Volume > average
    5. Price near EMA 20 (good entry point)
    
    Exit:
    - TP: +2.5% (simple, achievable)
    - SL: -1.5% (tight risk control)
    - Trailing: 1.0% after +1.5% profit
    - Max hold: 10 days
    """
    
    def __init__(
        self,
        timeframe: str = '4H',
        tp_pct: float = 0.025,      # 2.5% take profit
        sl_pct: float = 0.015,      # 1.5% stop loss
        trailing_pct: float = 0.010, # 1.0% trailing stop
        trailing_trigger: float = 0.015,  # Activate trailing at +1.5%
        max_hold_candles: int = 60,  # 10 days (60 * 4H candles)
        min_adx: float = 25,         # Minimum trend strength
        rsi_range: tuple = (40, 60), # RSI entry range
        volume_factor: float = 1.1,  # Volume > 110% average
        long_only: bool = True
    ):
        self.timeframe = timeframe
        self.tp_pct = tp_pct
        self.sl_pct = sl_pct
        self.trailing_pct = trailing_pct
        self.trailing_trigger = trailing_trigger
        self.max_hold_candles = max_hold_candles
        self.min_adx = min_adx
        self.rsi_range = rsi_range
        self.volume_factor = volume_factor
        self.long_only = long_only
        
        print(f"\n📈 Simple Trend Strategy Initialized")
        print(f"   TP: {tp_pct*100:.1f}%, SL: {sl_pct*100:.1f}%")
        print(f"   Trailing: {trailing_pct*100:.1f}% after +{trailing_trigger*100:.1f}%")
        print(f"   Max hold: {max_hold_candles} candles (~{max_hold_candles*4/24:.1f} days)")
        print(f"   ADX min: {min_adx}")
        print(f"   RSI range: {rsi_range}")
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate simple, proven indicators
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            DataFrame with indicators
        """
        print(f"\n📊 Calculating Simple Indicators...")
        
        # EMAs for trend
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        # RSI for timing
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ADX for trend strength
        df['adx'] = self._calculate_adx(df, period=14)
        
        # Volume
        df['volume_ma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # Distance from EMAs
        df['dist_ema20'] = (df['close'] - df['ema_20']) / df['ema_20'] * 100
        
        print(f"   ✅ Indicators calculated")
        
        return df
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate ADX (Average Directional Index)"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        # Directional Movement
        up = high - high.shift()
        down = low.shift() - low
        
        plus_dm = up.where((up > down) & (up > 0), 0)
        minus_dm = down.where((down > up) & (down > 0), 0)
        
        # Directional Indicators
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate simple trend-following signals
        
        Args:
            df: DataFrame with indicators
            
        Returns:
            DataFrame with signals
        """
        print(f"\n🎯 Generating Trend Signals...")
        
        df['signal'] = 0
        df['entry_price'] = 0.0
        df['stop_loss'] = 0.0
        df['take_profit'] = 0.0
        df['trailing_stop_pct'] = self.trailing_pct
        df['trailing_trigger'] = self.trailing_trigger
        df['signal_reason'] = ''
        
        signals = 0
        cooldown = 12  # 2 days cooldown (12 * 4H)
        last_signal = -cooldown
        
        for i in range(200, len(df)):  # Start after 200 candles for indicators
            
            # Cooldown check
            if i - last_signal < cooldown:
                continue
            
            # Get current values
            ema_20 = df['ema_20'].iloc[i]
            ema_50 = df['ema_50'].iloc[i]
            ema_200 = df['ema_200'].iloc[i]
            rsi = df['rsi'].iloc[i]
            adx = df['adx'].iloc[i]
            volume_ratio = df['volume_ratio'].iloc[i]
            dist_ema20 = df['dist_ema20'].iloc[i]
            close = df['close'].iloc[i]
            
            # Check for NaN
            if pd.isna([ema_20, ema_50, ema_200, rsi, adx, volume_ratio]).any():
                continue
            
            # === LONG SIGNAL ===
            if self.long_only:
                # 1. Uptrend: EMA 20 > EMA 50 > EMA 200
                trend_up = ema_20 > ema_50 and ema_50 > ema_200
                
                # 2. Strong trend: ADX > 25
                strong_trend = adx > self.min_adx
                
                # 3. RSI pullback (40-60 = not overbought, ready to go up)
                rsi_ok = self.rsi_range[0] <= rsi <= self.rsi_range[1]
                
                # 4. Volume confirmation
                volume_ok = volume_ratio > self.volume_factor
                
                # 5. Price near EMA 20 (within 2%)
                near_ema = abs(dist_ema20) < 2.0
                
                # 6. Price action: not at recent high (room to grow)
                recent_high = df['high'].iloc[max(0, i-20):i].max()
                room_to_grow = close < recent_high * 0.98  # At least 2% below recent high
                
                # ALL conditions must be true
                if trend_up and strong_trend and rsi_ok and volume_ok and near_ema and room_to_grow:
                    entry = close
                    sl = entry * (1 - self.sl_pct)
                    tp = entry * (1 + self.tp_pct)
                    
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'entry_price'] = entry
                    df.loc[df.index[i], 'stop_loss'] = sl
                    df.loc[df.index[i], 'take_profit'] = tp
                    df.loc[df.index[i], 'signal_reason'] = f'TREND_UP|ADX:{adx:.1f}|RSI:{rsi:.1f}'
                    
                    signals += 1
                    last_signal = i
        
        print(f"   Generated {signals} signals")
        
        # Expected: 50-100 signals per year for 4H
        candles_per_year = 365 * 6  # 6 candles per day
        years = len(df) / candles_per_year
        signals_per_year = signals / years if years > 0 else 0
        
        print(f"   Signals/year: {signals_per_year:.0f} (target: 50-100)")
        
        if signals_per_year < 30:
            print(f"   ⚠️  Too few signals. Consider:")
            print(f"      - Lower min_adx (20)")
            print(f"      - Wider RSI range (35-65)")
        elif signals_per_year > 150:
            print(f"   ⚠️  Too many signals. Consider:")
            print(f"      - Higher min_adx (30)")
            print(f"      - Narrower RSI range (45-55)")
        else:
            print(f"   ✅ Good signal frequency!")
        
        return df
    
    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run complete simple trend strategy
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            DataFrame with signals
        """
        # Calculate indicators
        df = self.calculate_indicators(df)
        
        # Generate signals
        df = self.generate_signals(df)
        
        return df


class SimpleTrendBacktester:
    """
    Simple backtester with trailing stop
    """
    
    def __init__(
        self,
        initial_capital: float = 10000,
        risk_per_trade: float = 0.02,
        max_positions: int = 2,
        commission: float = 0.001
    ):
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.max_positions = max_positions
        self.commission = commission
        
        self.capital = initial_capital
        self.positions = []
        self.closed_trades = []
        self.equity_curve = [initial_capital]
    
    def run(self, df: pd.DataFrame) -> Dict:
        """Run backtest"""
        print(f"\n🔄 Running Simple Backtest...")
        print(f"   Max positions: {self.max_positions}")
        
        for i in range(len(df)):
            time = df.index[i]
            high = df['high'].iloc[i]
            low = df['low'].iloc[i]
            close = df['close'].iloc[i]
            
            # Update positions
            self._update_positions(i, time, high, low, close, df)
            
            # New signal
            signal = df['signal'].iloc[i]
            if signal != 0 and len(self.positions) < self.max_positions:
                entry = df['entry_price'].iloc[i]
                sl = df['stop_loss'].iloc[i]
                tp = df['take_profit'].iloc[i]
                trailing_pct = df.get('trailing_stop_pct', pd.Series([0.01]*len(df))).iloc[i]
                trailing_trigger = df.get('trailing_trigger', pd.Series([0.015]*len(df))).iloc[i]
                
                if entry > 0 and sl > 0:
                    self._open_position(i, time, entry, sl, tp, trailing_pct, trailing_trigger)
            
            # Track equity
            equity = self.capital
            for pos in self.positions:
                unrealized = (close - pos['entry']) / pos['entry'] * pos['size'] * close
                equity += unrealized
            
            self.equity_curve.append(equity)
        
        # Close remaining
        if len(df) > 0:
            for pos in self.positions[:]:
                self._close_position(pos, df['close'].iloc[-1], df.index[-1], 'END')
        
        return self._calculate_stats()
    
    def _open_position(self, idx, time, entry, sl, tp, trailing_pct, trailing_trigger):
        """Open position"""
        risk_amount = self.capital * self.risk_per_trade
        risk_per_unit = abs(entry - sl)
        
        if risk_per_unit == 0:
            return
        
        size = risk_amount / risk_per_unit
        
        self.positions.append({
            'entry_idx': idx,
            'entry_time': time,
            'entry': entry,
            'sl': sl,
            'tp': tp,
            'size': size,
            'highest': entry,
            'trailing_active': False,
            'trailing_pct': trailing_pct,
            'trailing_trigger': trailing_trigger
        })
    
    def _update_positions(self, idx, time, high, low, close, df):
        """Update positions and check exits"""
        to_close = []
        
        for pos in self.positions:
            # Update trailing
            profit_pct = (close - pos['entry']) / pos['entry']
            
            if profit_pct >= pos['trailing_trigger']:
                pos['trailing_active'] = True
            
            if close > pos['highest']:
                pos['highest'] = close
            
            if pos['trailing_active']:
                trailing_sl = pos['highest'] * (1 - pos['trailing_pct'])
            else:
                trailing_sl = pos['sl']
            
            # Check TP
            if high >= pos['tp']:
                to_close.append((pos, pos['tp'], time, 'TP'))
                continue
            
            # Check SL
            if low <= trailing_sl:
                exit_price = trailing_sl
                reason = 'TRAIL' if pos['trailing_active'] else 'SL'
                to_close.append((pos, exit_price, time, reason))
                continue
            
            # Check timeout
            hold_time = idx - pos['entry_idx']
            max_hold = df.get('max_hold_candles', pd.Series([60]*len(df))).iloc[0] if 'max_hold_candles' in df.columns else 60
            
            if hold_time >= max_hold:
                to_close.append((pos, close, time, 'TIMEOUT'))
        
        # Close positions
        for pos, exit_price, exit_time, reason in to_close:
            self._close_position(pos, exit_price, exit_time, reason)
    
    def _close_position(self, pos, exit_price, exit_time, reason):
        """Close position"""
        pnl_pct = (exit_price - pos['entry']) / pos['entry'] * 100
        pnl = (exit_price - pos['entry']) / pos['entry'] * pos['size'] * pos['entry']
        
        # Commission
        pnl -= pos['size'] * pos['entry'] * self.commission * 2  # Entry + exit
        
        self.capital += pnl
        
        self.closed_trades.append({
            'entry_time': pos['entry_time'],
            'exit_time': exit_time,
            'entry': pos['entry'],
            'exit': exit_price,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'exit_reason': reason
        })
        
        self.positions.remove(pos)
    
    def _calculate_stats(self) -> Dict:
        """Calculate stats"""
        if len(self.closed_trades) == 0:
            return {'total_trades': 0, 'total_return_pct': 0, 'win_rate': 0}
        
        df_trades = pd.DataFrame(self.closed_trades)
        
        wins = df_trades[df_trades['pnl'] > 0]
        losses = df_trades[df_trades['pnl'] <= 0]
        
        return {
            'total_trades': len(self.closed_trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': len(wins) / len(self.closed_trades) * 100,
            'total_return_pct': (self.capital - self.initial_capital) / self.initial_capital * 100,
            'final_capital': self.capital,
            'avg_win': wins['pnl'].mean() if len(wins) > 0 else 0,
            'avg_loss': losses['pnl'].mean() if len(losses) > 0 else 0,
            'profit_factor': abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else 0,
            'trades': self.closed_trades
        }
    
    def print_results(self, stats: Dict):
        """Print results"""
        print("\n" + "="*70)
        print("SIMPLE TREND BACKTEST RESULTS")
        print("="*70)
        
        print(f"\n💰 CAPITAL")
        print(f"  Initial:  ${self.initial_capital:,.2f}")
        print(f"  Final:    ${stats['final_capital']:,.2f}")
        print(f"  Return:   {stats['total_return_pct']:+.2f}%")
        
        print(f"\n📊 TRADES")
        print(f"  Total:    {stats['total_trades']}")
        print(f"  Wins:     {stats['winning_trades']}")
        print(f"  Losses:   {stats['losing_trades']}")
        print(f"  Win Rate: {stats['win_rate']:.1f}%")
        
        print(f"\n💵 PNL")
        print(f"  Avg Win:  ${stats['avg_win']:.2f}")
        print(f"  Avg Loss: ${stats['avg_loss']:.2f}")
        print(f"  PF:       {stats['profit_factor']:.2f}")
        
        print("\n" + "="*70)


if __name__ == "__main__":
    from stock_adaptive_strategy import get_real_stock_data
    
    # Test on NVDA
    df = get_real_stock_data('NVDA', days=730)
    
    strategy = SimpleTrendStrategy(
        timeframe='4H',
        tp_pct=0.025,
        sl_pct=0.015,
        min_adx=25,
        rsi_range=(40, 60)
    )
    
    df_signals = strategy.run_strategy(df)
    
    # Backtest
    bt = SimpleTrendBacktester(initial_capital=10000, max_positions=2)
    results = bt.run(df_signals)
    bt.print_results(results)
