"""
SMC Pattern Recognition Strategy - SCALPING VERSION
Optimized for M5/M15 timeframes with faster entries and smaller targets
"""

import pandas as pd
import numpy as np


class PatternRecognitionScalping:
    """
    Pattern Recognition strategy optimized for scalping

    Key differences from H1 version:
    - Smaller lookback periods (adapted for M5/M15)
    - Tighter Fibonacci levels
    - Faster pattern detection
    - Smaller TP/SL targets
    """

    def __init__(self, fib_mode='standard', lookback_swing=20, lookback_ob=10):
        """
        Initialize scalping strategy

        Args:
            fib_mode: 'standard' (1.618) or 'aggressive' (2.618)
            lookback_swing: Swing high/low lookback (default: 20 for M5/M15)
            lookback_ob: Order block lookback (default: 10 for M5/M15)
        """
        self.fib_mode = fib_mode
        self.lookback_swing = lookback_swing
        self.lookback_ob = lookback_ob

        # Fibonacci levels for scalping
        if fib_mode == 'standard':
            self.fib_tp = 1.618  # Target
            self.fib_sl = 0.5    # Stop loss (tighter for scalping)
        else:  # aggressive
            self.fib_tp = 2.618
            self.fib_sl = 0.382

    def identify_swing_points(self, df):
        """Identify swing highs and lows (optimized for scalping)"""

        df['swing_high'] = df['high'].rolling(window=self.lookback_swing, center=True).max()
        df['swing_low'] = df['low'].rolling(window=self.lookback_swing, center=True).min()

        df['is_swing_high'] = (df['high'] == df['swing_high'])
        df['is_swing_low'] = (df['low'] == df['swing_low'])

        return df

    def identify_order_blocks(self, df):
        """Identify order blocks (faster detection for scalping)"""

        df['ob_bull'] = False
        df['ob_bear'] = False

        for i in range(self.lookback_ob, len(df)):
            # Bullish OB: strong down move followed by reversal
            if df['close'].iloc[i] > df['open'].iloc[i]:  # Bullish candle
                prev_candles = df.iloc[i-self.lookback_ob:i]
                if (prev_candles['close'] < prev_candles['open']).sum() >= self.lookback_ob * 0.6:
                    df.loc[df.index[i], 'ob_bull'] = True

            # Bearish OB: strong up move followed by reversal
            if df['close'].iloc[i] < df['open'].iloc[i]:  # Bearish candle
                prev_candles = df.iloc[i-self.lookback_ob:i]
                if (prev_candles['close'] > prev_candles['open']).sum() >= self.lookback_ob * 0.6:
                    df.loc[df.index[i], 'ob_bear'] = True

        return df

    def identify_fvg(self, df):
        """Identify Fair Value Gaps (optimized for scalping)"""

        df['fvg_bull'] = False
        df['fvg_bear'] = False

        for i in range(2, len(df)):
            # Bullish FVG: gap between candle i-2 high and candle i low
            if df['low'].iloc[i] > df['high'].iloc[i-2]:
                gap_size = df['low'].iloc[i] - df['high'].iloc[i-2]
                # Only consider significant gaps for scalping (min 3 points)
                if gap_size >= 3:
                    df.loc[df.index[i], 'fvg_bull'] = True

            # Bearish FVG: gap between candle i-2 low and candle i high
            if df['high'].iloc[i] < df['low'].iloc[i-2]:
                gap_size = df['low'].iloc[i-2] - df['high'].iloc[i]
                if gap_size >= 3:
                    df.loc[df.index[i], 'fvg_bear'] = True

        return df

    def identify_bos(self, df):
        """Identify Break of Structure (faster for scalping)"""

        df['bos_bull'] = False
        df['bos_bear'] = False

        # Recent swing high/low for faster detection
        recent_window = 30

        for i in range(recent_window, len(df)):
            window = df.iloc[i-recent_window:i]

            # Bullish BOS: price breaks above recent swing high
            recent_high = window['high'].max()
            if df['close'].iloc[i] > recent_high:
                df.loc[df.index[i], 'bos_bull'] = True

            # Bearish BOS: price breaks below recent swing low
            recent_low = window['low'].min()
            if df['close'].iloc[i] < recent_low:
                df.loc[df.index[i], 'bos_bear'] = True

        return df

    def identify_liquidity_sweeps(self, df):
        """Identify liquidity sweeps (critical for scalping)"""

        df['sweep_bull'] = False
        df['sweep_bear'] = False

        lookback = 15  # Shorter lookback for scalping

        for i in range(lookback, len(df)):
            window = df.iloc[i-lookback:i]

            # Bullish sweep: wick below recent lows then reversal
            recent_low = window['low'].min()
            if (df['low'].iloc[i] <= recent_low and
                df['close'].iloc[i] > df['open'].iloc[i]):
                df.loc[df.index[i], 'sweep_bull'] = True

            # Bearish sweep: wick above recent highs then reversal
            recent_high = window['high'].max()
            if (df['high'].iloc[i] >= recent_high and
                df['close'].iloc[i] < df['open'].iloc[i]):
                df.loc[df.index[i], 'sweep_bear'] = True

        return df

    def identify_continuation_patterns(self, df):
        """Identify continuation patterns (optimized for scalping)"""

        df['pattern'] = None
        lookback = 10  # Shorter lookback for scalping

        for i in range(lookback, len(df)):
            window = df.iloc[i-lookback:i+1]

            # Calculate price range and trend
            price_range = window['high'].max() - window['low'].min()
            trend_up = window['close'].iloc[-1] > window['close'].iloc[0]

            # Flag pattern (tight consolidation in trend)
            recent_range = window['high'].iloc[-5:].max() - window['low'].iloc[-5:].min()
            if recent_range < price_range * 0.3:  # Consolidation
                if trend_up:
                    df.loc[df.index[i], 'pattern'] = 'bull_flag'
                else:
                    df.loc[df.index[i], 'pattern'] = 'bear_flag'

            # Pennant (converging price action)
            highs_std = window['high'].iloc[-5:].std()
            lows_std = window['low'].iloc[-5:].std()
            if highs_std < price_range * 0.15 and lows_std < price_range * 0.15:
                if trend_up:
                    df.loc[df.index[i], 'pattern'] = 'bull_pennant'
                else:
                    df.loc[df.index[i], 'pattern'] = 'bear_pennant'

        return df

    def calculate_entry_exit(self, df, row_idx):
        """Calculate entry, SL, and TP for scalping"""

        row = df.iloc[row_idx]

        entry_price = row['close']

        # Calculate range for SL/TP (smaller for scalping)
        recent_window = df.iloc[max(0, row_idx-20):row_idx+1]
        atr = (recent_window['high'] - recent_window['low']).mean()

        if row['signal'] == 1:  # LONG
            # Stop loss (tighter for scalping)
            stop_loss = entry_price - (atr * self.fib_sl)

            # Take profit
            take_profit = entry_price + (atr * self.fib_tp)

        else:  # SHORT
            # Stop loss
            stop_loss = entry_price + (atr * self.fib_sl)

            # Take profit
            take_profit = entry_price - (atr * self.fib_tp)

        return entry_price, stop_loss, take_profit

    def generate_signals(self, df):
        """Generate trading signals for scalping"""

        df['signal'] = 0
        df['entry_price'] = np.nan
        df['stop_loss'] = np.nan
        df['take_profit'] = np.nan

        for i in range(50, len(df)):
            row = df.iloc[i]

            # LONG signal conditions (scalping optimized)
            if (row['bos_bull'] or row['sweep_bull']) and row['ob_bull']:
                # Confirm with pattern or FVG
                if row['pattern'] in ['bull_flag', 'bull_pennant'] or row['fvg_bull']:
                    # Check market hours (important for scalping)
                    if row.get('is_active', True):
                        df.loc[df.index[i], 'signal'] = 1

                        entry, sl, tp = self.calculate_entry_exit(df, i)
                        df.loc[df.index[i], 'entry_price'] = entry
                        df.loc[df.index[i], 'stop_loss'] = sl
                        df.loc[df.index[i], 'take_profit'] = tp

            # SHORT signal conditions
            elif (row['bos_bear'] or row['sweep_bear']) and row['ob_bear']:
                if row['pattern'] in ['bear_flag', 'bear_pennant'] or row['fvg_bear']:
                    if row.get('is_active', True):
                        df.loc[df.index[i], 'signal'] = -1

                        entry, sl, tp = self.calculate_entry_exit(df, i)
                        df.loc[df.index[i], 'entry_price'] = entry
                        df.loc[df.index[i], 'stop_loss'] = sl
                        df.loc[df.index[i], 'take_profit'] = tp

        return df

    def run_strategy(self, df):
        """Run complete scalping strategy"""

        # Identify all SMC elements
        df = self.identify_swing_points(df)
        df = self.identify_order_blocks(df)
        df = self.identify_fvg(df)
        df = self.identify_bos(df)
        df = self.identify_liquidity_sweeps(df)
        df = self.identify_continuation_patterns(df)

        # Generate signals
        df = self.generate_signals(df)

        return df
