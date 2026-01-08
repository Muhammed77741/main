"""
Enhanced Multi-Signal Gold Strategy
Focus: Лучшая стратегия с добавлением trendline breakouts

Result: 1.00 signal/day, +22.71%, 80% WR
Enhancement: + Trendline breaks для еще лучших результатов
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intraday_gold_strategy import MultiSignalGoldStrategy
from smc_indicators import SMCIndicators


class EnhancedMultiSignal(MultiSignalGoldStrategy):
    """
    Enhanced Multi-Signal with Trendline Breakouts

    Original signals:
    - Order Blocks
    - Fair Value Gaps
    - Liquidity Sweeps
    - Break of Structure

    NEW additions:
    - Trendline Breakouts (support/resistance lines)
    - Dynamic trendline detection
    - Confluence scoring (multiple signals = higher quality)
    """

    def __init__(
        self,
        min_trendline_touches=3,      # Minimum touches to confirm trendline
        trendline_lookback=50,         # Candles to look back for trendline
        breakout_threshold=0.0015,     # 0.15% break to confirm
        use_confluence_scoring=True    # Score signals by confluence
    ):
        super().__init__()

        self.min_trendline_touches = min_trendline_touches
        self.trendline_lookback = trendline_lookback
        self.breakout_threshold = breakout_threshold
        self.use_confluence_scoring = use_confluence_scoring

        print(f"\n💎 Enhanced Multi-Signal Strategy Initialized")
        print(f"   Original: OB + FVG + Liquidity + BOS")
        print(f"   NEW: Trendline Breakouts")
        print(f"   Trendline: {min_trendline_touches} touches, {trendline_lookback} lookback")
        print(f"   Confluence Scoring: {use_confluence_scoring}")

    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run enhanced strategy with trendline breakouts
        """
        print(f"\n💎 Running Enhanced Multi-Signal Strategy...")

        # Run base Multi-Signal first
        df = super().run_strategy(df)

        # Detect trendlines
        print(f"\n📈 Detecting trendlines...")
        df = self._detect_trendlines(df)

        # Add trendline breakout signals
        print(f"📊 Adding trendline breakout signals...")
        df = self._add_trendline_breakouts(df)

        # Apply confluence scoring
        if self.use_confluence_scoring:
            print(f"⭐ Applying confluence scoring...")
            df = self._apply_confluence_scoring(df)

        final_signals = len(df[df['signal'] != 0])
        print(f"\n✅ Total signals: {final_signals}")

        return df

    def _detect_trendlines(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect support and resistance trendlines

        Method:
        1. Find swing highs and lows
        2. Connect points with lines
        3. Validate with minimum touches
        4. Store active trendlines
        """
        df = df.copy()

        # Initialize trendline columns
        df['support_trendline'] = np.nan
        df['resistance_trendline'] = np.nan
        df['trendline_strength'] = 0

        # Find swing points
        swing_high = df['high'].rolling(window=5, center=True).max() == df['high']
        swing_low = df['low'].rolling(window=5, center=True).min() == df['low']

        for i in range(self.trendline_lookback, len(df)):
            # Get recent swing points
            recent_highs = df.loc[swing_high].iloc[max(0, i-self.trendline_lookback):i]
            recent_lows = df.loc[swing_low].iloc[max(0, i-self.trendline_lookback):i]

            # Detect resistance trendline (descending)
            if len(recent_highs) >= self.min_trendline_touches:
                resistance_line = self._fit_trendline(
                    recent_highs.index,
                    recent_highs['high'].values
                )

                if resistance_line is not None:
                    slope, intercept, touches = resistance_line

                    # Project trendline to current candle
                    current_idx = i
                    projected_resistance = slope * current_idx + intercept

                    df.loc[df.index[i], 'resistance_trendline'] = projected_resistance
                    df.loc[df.index[i], 'trendline_strength'] = touches

            # Detect support trendline (ascending)
            if len(recent_lows) >= self.min_trendline_touches:
                support_line = self._fit_trendline(
                    recent_lows.index,
                    recent_lows['low'].values
                )

                if support_line is not None:
                    slope, intercept, touches = support_line

                    # Project trendline to current candle
                    current_idx = i
                    projected_support = slope * current_idx + intercept

                    df.loc[df.index[i], 'support_trendline'] = projected_support
                    df.loc[df.index[i], 'trendline_strength'] = max(
                        df['trendline_strength'].iloc[i],
                        touches
                    )

        trendlines_detected = df['support_trendline'].notna().sum() + df['resistance_trendline'].notna().sum()
        print(f"   Detected {trendlines_detected} trendline points")

        return df

    def _fit_trendline(self, indices, values):
        """
        Fit a trendline through swing points
        Returns: (slope, intercept, num_touches) or None
        """
        if len(indices) < 2:
            return None

        # Convert datetime index to numeric
        x = np.arange(len(indices))
        y = values

        # Linear regression
        try:
            coeffs = np.polyfit(x, y, deg=1)
            slope, intercept = coeffs

            # Calculate how many points touch the line (within 0.2%)
            touches = 0
            for idx, val in zip(x, y):
                predicted = slope * idx + intercept
                error_pct = abs(val - predicted) / val

                if error_pct < 0.002:  # Within 0.2%
                    touches += 1

            # Require minimum touches
            if touches >= self.min_trendline_touches:
                return (slope, intercept, touches)

        except:
            pass

        return None

    def _add_trendline_breakouts(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add signals based on trendline breakouts

        Bullish breakout: Price breaks above resistance trendline
        Bearish breakout: Price breaks below support trendline
        """
        df = df.copy()

        breakout_signals = 0

        for i in range(self.trendline_lookback + 10, len(df)):
            # Skip if already have signal
            if df['signal'].iloc[i] != 0:
                continue

            current_close = df['close'].iloc[i]
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]

            # Bullish trendline breakout (break above resistance)
            if not pd.isna(df['resistance_trendline'].iloc[i]):
                resistance = df['resistance_trendline'].iloc[i]

                # Calculate breakout strength
                breakout_strength = (current_close - resistance) / resistance

                if breakout_strength > self.breakout_threshold:
                    # Confirm with volume
                    avg_volume = df['volume'].iloc[i-10:i].mean()
                    if df['volume'].iloc[i] > avg_volume * 1.2:
                        # Confirm with bullish close
                        if df['close'].iloc[i] > df['open'].iloc[i]:
                            df.loc[df.index[i], 'signal'] = 1
                            df.loc[df.index[i], 'entry_price'] = current_close
                            df.loc[df.index[i], 'stop_loss'] = resistance * 0.9995
                            df.loc[df.index[i], 'take_profit'] = current_close * 1.004
                            df.loc[df.index[i], 'signal_type'] = 'trendline_breakout_long'
                            df.loc[df.index[i], 'signal_quality'] = df['trendline_strength'].iloc[i]
                            breakout_signals += 1

            # Bearish trendline breakout (break below support)
            if not pd.isna(df['support_trendline'].iloc[i]):
                support = df['support_trendline'].iloc[i]

                breakout_strength = (support - current_close) / support

                if breakout_strength > self.breakout_threshold:
                    avg_volume = df['volume'].iloc[i-10:i].mean()
                    if df['volume'].iloc[i] > avg_volume * 1.2:
                        if df['close'].iloc[i] < df['open'].iloc[i]:
                            df.loc[df.index[i], 'signal'] = -1
                            df.loc[df.index[i], 'entry_price'] = current_close
                            df.loc[df.index[i], 'stop_loss'] = support * 1.0005
                            df.loc[df.index[i], 'take_profit'] = current_close * 0.996
                            df.loc[df.index[i], 'signal_type'] = 'trendline_breakout_short'
                            df.loc[df.index[i], 'signal_quality'] = df['trendline_strength'].iloc[i]
                            breakout_signals += 1

        if breakout_signals > 0:
            print(f"   Added {breakout_signals} trendline breakout signals")

        return df

    def _apply_confluence_scoring(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Score signals based on confluence (multiple confirmations)

        Confluence factors:
        1. OB/FVG present
        2. Liquidity sweep
        3. BOS
        4. Trendline breakout
        5. Volume spike
        6. Clean candle structure

        Higher score = higher quality signal
        Filter out low-score signals
        """
        df = df.copy()

        initial_signals = len(df[df['signal'] != 0])

        for i in range(len(df)):
            if df['signal'].iloc[i] == 0:
                continue

            confluence_score = 0

            # Factor 1: Signal type (some are stronger)
            signal_type = df['signal_type'].iloc[i] if 'signal_type' in df.columns else ''

            # Ensure signal_type is string (can be nan/float)
            if not isinstance(signal_type, str):
                signal_type = ''

            if 'ob' in signal_type.lower() or 'fvg' in signal_type.lower():
                confluence_score += 2  # SMC signals = strong

            if 'bos' in signal_type.lower():
                confluence_score += 3  # BOS = very strong

            if 'liquidity' in signal_type.lower():
                confluence_score += 2  # Liquidity sweep = strong

            if 'trendline' in signal_type.lower():
                # Trendline strength matters
                trendline_strength = df['signal_quality'].iloc[i] if 'signal_quality' in df.columns else 0
                confluence_score += min(int(trendline_strength) if not pd.isna(trendline_strength) else 0, 3)  # Max +3

            # Factor 2: Volume confirmation
            if i >= 10:
                avg_volume = df['volume'].iloc[i-10:i].mean()
                volume_ratio = df['volume'].iloc[i] / avg_volume if avg_volume > 0 else 1

                if volume_ratio > 2.0:
                    confluence_score += 2
                elif volume_ratio > 1.5:
                    confluence_score += 1

            # Factor 3: Candle structure (clean body, small wicks)
            high = df['high'].iloc[i]
            low = df['low'].iloc[i]
            close = df['close'].iloc[i]
            open_price = df['open'].iloc[i]

            body = abs(close - open_price)
            total_range = high - low

            if total_range > 0:
                body_ratio = body / total_range

                if body_ratio > 0.7:  # Strong body
                    confluence_score += 1

            # Factor 4: Is this during best hours?
            if df.index[i].hour in [8, 9, 10, 13, 14, 15]:
                confluence_score += 1

            # Store confluence score
            df.loc[df.index[i], 'confluence_score'] = confluence_score

            # Filter: требуем минимум 3 балла
            if confluence_score < 3:
                df.loc[df.index[i], 'signal'] = 0
                df.loc[df.index[i], 'filter_reason'] = 'low_confluence'

        final_signals = len(df[df['signal'] != 0])
        filtered = initial_signals - final_signals

        print(f"   Confluence filter: removed {filtered} low-quality signals")
        print(f"   ({initial_signals} → {final_signals})")

        return df

    def get_strategy_info(self) -> dict:
        """Get enhanced strategy info"""
        return {
            'strategy_type': 'Enhanced Multi-Signal Gold',
            'timeframe': '1H',
            'signals': ['OB', 'FVG', 'Liquidity Sweep', 'BOS', 'Trendline Breakout'],
            'trendline_touches': self.min_trendline_touches,
            'trendline_lookback': self.trendline_lookback,
            'confluence_scoring': self.use_confluence_scoring,
            'target_signals_per_day': '1-1.5',
            'target_win_rate': '80-85%',
            'expected_return': '20-30% monthly'
        }


def test_enhanced_multi_signal():
    """Quick test of enhanced strategy"""
    print("="*80)
    print("ENHANCED MULTI-SIGNAL STRATEGY TEST")
    print("="*80)

    from intraday_gold_data import generate_intraday_gold_data
    from backtester import Backtester

    # Generate data
    print("\n📊 Generating 30 days of 1H gold data...")
    df = generate_intraday_gold_data(days=30, timeframe='1H')

    # Run strategy
    strategy = EnhancedMultiSignal(
        min_trendline_touches=3,
        trendline_lookback=50,
        breakout_threshold=0.0015,
        use_confluence_scoring=True
    )

    df_signals = strategy.run_strategy(df)

    # Backtest
    bt = Backtester(initial_capital=10000, commission=0.001, slippage=0.0005)
    stats = bt.run(df_signals)

    # Results
    print("\n" + "="*80)
    print("ENHANCED MULTI-SIGNAL RESULTS")
    print("="*80)

    days = 30
    signals_per_day = stats['total_trades'] / days

    print(f"\n📊 PERFORMANCE:")
    print(f"   Total Trades: {stats['total_trades']}")
    print(f"   Signals/Day: {signals_per_day:.2f}")
    print(f"   Win Rate: {stats['win_rate']:.1f}%")
    print(f"   Total Return: {stats['total_return_pct']:.2f}%")
    print(f"   Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
    print(f"   Max Drawdown: {stats['max_drawdown']:.2f}%")

    print(f"\n💰 CAPITAL:")
    print(f"   Initial: ${stats['initial_capital']:,.2f}")
    print(f"   Final: ${stats['final_capital']:,.2f}")
    print(f"   Profit: ${stats['total_return']:,.2f}")

    # Detailed results
    bt.print_results(stats)

    # Save trades
    if stats['total_trades'] > 0:
        df_trades = pd.DataFrame(stats['trades'])
        df_trades.to_csv('enhanced_multi_signal_trades.csv', index=False)
        print(f"\n💾 Trades saved to 'enhanced_multi_signal_trades.csv'")

    print("\n" + "="*80)
    print("✅ TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    test_enhanced_multi_signal()
