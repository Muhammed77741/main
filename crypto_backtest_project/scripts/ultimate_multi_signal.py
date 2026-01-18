"""
Ultimate Multi-Signal Gold Strategy
Maximum patterns for best signal coverage

Original 5 signals + 6 new candlestick patterns
Target: 1.5-2 signals/day with 75%+ win rate
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_multi_signal import EnhancedMultiSignal
from smc_indicators import SMCIndicators


class UltimateMultiSignal(EnhancedMultiSignal):
    """
    Ultimate Multi-Signal with all patterns

    Original 5:
    1. Order Blocks
    2. Fair Value Gaps
    3. Liquidity Sweeps
    4. Break of Structure
    5. Trendline Breakouts

    NEW 6 patterns:
    6. Inside Bar Breakouts
    7. Three-Candle Momentum
    8. Hammer/Shooting Star
    9. Morning Star/Evening Star
    10. Strong Marubozu
    11. Supply/Demand Zones
    """

    def __init__(
        self,
        min_trendline_touches=3,
        trendline_lookback=50,
        breakout_threshold=0.0015,
        use_confluence_scoring=True,
        # New pattern parameters
        inside_bar_breakout_threshold=0.0012,  # 0.12%
        hammer_wick_ratio=2.0,                 # Lower wick 2x body
        marubozu_body_ratio=0.85,              # 85% body
        supply_demand_lookback=30              # Lookback for zones
    ):
        super().__init__(
            min_trendline_touches=min_trendline_touches,
            trendline_lookback=trendline_lookback,
            breakout_threshold=breakout_threshold,
            use_confluence_scoring=use_confluence_scoring
        )

        self.inside_bar_breakout_threshold = inside_bar_breakout_threshold
        self.hammer_wick_ratio = hammer_wick_ratio
        self.marubozu_body_ratio = marubozu_body_ratio
        self.supply_demand_lookback = supply_demand_lookback

        print(f"\n🌟 Ultimate Multi-Signal Strategy Initialized")
        print(f"   Base: 5 patterns (OB, FVG, Liquidity, BOS, Trendlines)")
        print(f"   NEW: 6 candlestick patterns")
        print(f"   Total: 11 signal types")
        print(f"   Target: 1.5-2.0 signals/day")

    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run ultimate strategy with all patterns
        """
        print(f"\n🌟 Running Ultimate Multi-Signal Strategy...")

        # Run base Enhanced Multi-Signal (5 patterns)
        df = super().run_strategy(df)

        # Add new candlestick patterns
        print(f"\n📊 Adding candlestick patterns...")

        df = self._add_inside_bar_breakouts(df)
        df = self._add_three_candle_momentum(df)
        df = self._add_hammer_shooting_star(df)
        df = self._add_morning_evening_star(df)
        df = self._add_marubozu_patterns(df)
        df = self._add_supply_demand_zones(df)

        # Re-apply confluence scoring to new signals
        if self.use_confluence_scoring:
            print(f"\n⭐ Re-applying confluence scoring to all signals...")
            df = self._apply_confluence_scoring(df)

        final_signals = len(df[df['signal'] != 0])
        print(f"\n✅ Total signals: {final_signals}")

        # Signal type breakdown
        if 'signal_type' in df.columns:
            signal_counts = df[df['signal'] != 0]['signal_type'].value_counts()
            print(f"\n📋 Signal breakdown:")
            for sig_type, count in signal_counts.head(10).items():
                print(f"   {sig_type}: {count}")

        return df

    def _add_inside_bar_breakouts(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Inside Bar: Current candle range inside previous candle
        Breakout = strong directional move after consolidation

        Entry: Break of inside bar high/low
        """
        df = df.copy()
        signals = 0

        for i in range(5, len(df)):
            if df['signal'].iloc[i] != 0:
                continue

            # Check if previous candle is inside bar
            curr_high = df['high'].iloc[i]
            curr_low = df['low'].iloc[i]
            prev_high = df['high'].iloc[i-1]
            prev_low = df['low'].iloc[i-1]

            # Previous candle contained in prior candle?
            parent_high = df['high'].iloc[i-2]
            parent_low = df['low'].iloc[i-2]

            is_inside_bar = (prev_high <= parent_high and prev_low >= parent_low)

            if not is_inside_bar:
                continue

            # Bullish breakout (current breaks above inside bar)
            if curr_high > prev_high:
                breakout_strength = (curr_high - prev_high) / prev_high

                if breakout_strength > self.inside_bar_breakout_threshold:
                    # Volume confirmation
                    if i >= 5:
                        avg_vol = df['volume'].iloc[i-5:i].mean()
                        if df['volume'].iloc[i] > avg_vol * 1.1:
                            df.loc[df.index[i], 'signal'] = 1
                            df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                            df.loc[df.index[i], 'stop_loss'] = prev_low * 0.9995
                            df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 1.0035
                            df.loc[df.index[i], 'signal_type'] = 'inside_bar_breakout_long'
                            signals += 1

            # Bearish breakout (current breaks below inside bar)
            if curr_low < prev_low:
                breakout_strength = (prev_low - curr_low) / prev_low

                if breakout_strength > self.inside_bar_breakout_threshold:
                    if i >= 5:
                        avg_vol = df['volume'].iloc[i-5:i].mean()
                        if df['volume'].iloc[i] > avg_vol * 1.1:
                            df.loc[df.index[i], 'signal'] = -1
                            df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                            df.loc[df.index[i], 'stop_loss'] = prev_high * 1.0005
                            df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 0.9965
                            df.loc[df.index[i], 'signal_type'] = 'inside_bar_breakout_short'
                            signals += 1

        if signals > 0:
            print(f"   Added {signals} inside bar breakout signals")

        return df

    def _add_three_candle_momentum(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Three consecutive candles in same direction
        Shows strong momentum

        Entry: On 4th candle continuation
        """
        df = df.copy()
        signals = 0

        for i in range(10, len(df)):
            if df['signal'].iloc[i] != 0:
                continue

            # Check last 3 candles
            last_3 = df.iloc[i-3:i]

            # All bullish?
            all_bullish = all(last_3['close'] > last_3['open'])
            increasing = all(
                last_3['close'].iloc[j] > last_3['close'].iloc[j-1]
                for j in range(1, 3)
            )

            if all_bullish and increasing:
                # Current candle also bullish?
                if df['close'].iloc[i] > df['open'].iloc[i]:
                    # Volume increasing
                    if df['volume'].iloc[i] > df['volume'].iloc[i-3:i].mean() * 1.0:
                        df.loc[df.index[i], 'signal'] = 1
                        df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                        df.loc[df.index[i], 'stop_loss'] = df['low'].iloc[i-3:i].min() * 0.9995
                        df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 1.004
                        df.loc[df.index[i], 'signal_type'] = 'three_candle_momentum_long'
                        signals += 1

            # All bearish?
            all_bearish = all(last_3['close'] < last_3['open'])
            decreasing = all(
                last_3['close'].iloc[j] < last_3['close'].iloc[j-1]
                for j in range(1, 3)
            )

            if all_bearish and decreasing:
                if df['close'].iloc[i] < df['open'].iloc[i]:
                    if df['volume'].iloc[i] > df['volume'].iloc[i-3:i].mean() * 1.0:
                        df.loc[df.index[i], 'signal'] = -1
                        df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                        df.loc[df.index[i], 'stop_loss'] = df['high'].iloc[i-3:i].max() * 1.0005
                        df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 0.996
                        df.loc[df.index[i], 'signal_type'] = 'three_candle_momentum_short'
                        signals += 1

        if signals > 0:
            print(f"   Added {signals} three-candle momentum signals")

        return df

    def _add_hammer_shooting_star(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Hammer: Long lower wick, bullish reversal
        Shooting Star: Long upper wick, bearish reversal

        Requirements:
        - Wick at least 2x body size
        - Small body
        - Close near high (hammer) or low (shooting star)
        """
        df = df.copy()
        signals = 0

        for i in range(10, len(df)):
            if df['signal'].iloc[i] != 0:
                continue

            high = df['high'].iloc[i]
            low = df['low'].iloc[i]
            close = df['close'].iloc[i]
            open_price = df['open'].iloc[i]

            body = abs(close - open_price)
            total_range = high - low

            if total_range == 0:
                continue

            upper_wick = high - max(close, open_price)
            lower_wick = min(close, open_price) - low

            # Hammer (bullish reversal)
            if lower_wick > body * self.hammer_wick_ratio:
                # Close in upper 30%
                if (close - low) / total_range > 0.7:
                    # Check we're in potential downtrend
                    recent_trend = (df['close'].iloc[i-5:i].mean() - df['close'].iloc[i-10:i-5].mean())
                    if recent_trend <= 0:  # Downtrend or flat
                        # Volume confirmation
                        if df['volume'].iloc[i] > df['volume'].iloc[i-5:i].mean() * 1.1:
                            df.loc[df.index[i], 'signal'] = 1
                            df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                            df.loc[df.index[i], 'stop_loss'] = low * 0.9993
                            df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 1.0035
                            df.loc[df.index[i], 'signal_type'] = 'hammer_reversal_long'
                            signals += 1

            # Shooting Star (bearish reversal)
            if upper_wick > body * self.hammer_wick_ratio:
                # Close in lower 30%
                if (high - close) / total_range > 0.7:
                    # Check we're in potential uptrend
                    recent_trend = (df['close'].iloc[i-5:i].mean() - df['close'].iloc[i-10:i-5].mean())
                    if recent_trend >= 0:  # Uptrend or flat
                        if df['volume'].iloc[i] > df['volume'].iloc[i-5:i].mean() * 1.1:
                            df.loc[df.index[i], 'signal'] = -1
                            df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                            df.loc[df.index[i], 'stop_loss'] = high * 1.0007
                            df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 0.9965
                            df.loc[df.index[i], 'signal_type'] = 'shooting_star_reversal_short'
                            signals += 1

        if signals > 0:
            print(f"   Added {signals} hammer/shooting star signals")

        return df

    def _add_morning_evening_star(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Morning Star: 3-candle bullish reversal
        - Bearish candle
        - Small indecision candle (star)
        - Large bullish candle

        Evening Star: 3-candle bearish reversal
        - Bullish candle
        - Small indecision candle (star)
        - Large bearish candle
        """
        df = df.copy()
        signals = 0

        for i in range(10, len(df)):
            if df['signal'].iloc[i] != 0:
                continue

            if i < 2:
                continue

            # Get 3 candles
            c1_open = df['open'].iloc[i-2]
            c1_close = df['close'].iloc[i-2]
            c1_body = abs(c1_close - c1_open)

            c2_open = df['open'].iloc[i-1]
            c2_close = df['close'].iloc[i-1]
            c2_body = abs(c2_close - c2_open)

            c3_open = df['open'].iloc[i]
            c3_close = df['close'].iloc[i]
            c3_body = abs(c3_close - c3_open)

            # Morning Star (bullish reversal)
            if (c1_close < c1_open and           # First bearish
                c2_body < c1_body * 0.3 and      # Star small
                c3_close > c3_open and           # Third bullish
                c3_body > c1_body * 0.8):        # Third large

                # Close above first candle midpoint
                c1_mid = (c1_open + c1_close) / 2
                if c3_close > c1_mid:
                    # Volume on third candle
                    if df['volume'].iloc[i] > df['volume'].iloc[i-5:i].mean() * 1.2:
                        df.loc[df.index[i], 'signal'] = 1
                        df.loc[df.index[i], 'entry_price'] = c3_close
                        df.loc[df.index[i], 'stop_loss'] = df['low'].iloc[i-2:i+1].min() * 0.9995
                        df.loc[df.index[i], 'take_profit'] = c3_close * 1.004
                        df.loc[df.index[i], 'signal_type'] = 'morning_star_reversal_long'
                        signals += 1

            # Evening Star (bearish reversal)
            if (c1_close > c1_open and           # First bullish
                c2_body < c1_body * 0.3 and      # Star small
                c3_close < c3_open and           # Third bearish
                c3_body > c1_body * 0.8):        # Third large

                # Close below first candle midpoint
                c1_mid = (c1_open + c1_close) / 2
                if c3_close < c1_mid:
                    if df['volume'].iloc[i] > df['volume'].iloc[i-5:i].mean() * 1.2:
                        df.loc[df.index[i], 'signal'] = -1
                        df.loc[df.index[i], 'entry_price'] = c3_close
                        df.loc[df.index[i], 'stop_loss'] = df['high'].iloc[i-2:i+1].max() * 1.0005
                        df.loc[df.index[i], 'take_profit'] = c3_close * 0.996
                        df.loc[df.index[i], 'signal_type'] = 'evening_star_reversal_short'
                        signals += 1

        if signals > 0:
            print(f"   Added {signals} morning/evening star signals")

        return df

    def _add_marubozu_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Marubozu: Strong directional candle with minimal wicks
        Shows strong buying/selling pressure

        Requirements:
        - Body > 85% of total range
        - Large candle (> avg range)
        - Volume confirmation
        """
        df = df.copy()
        signals = 0

        for i in range(10, len(df)):
            if df['signal'].iloc[i] != 0:
                continue

            high = df['high'].iloc[i]
            low = df['low'].iloc[i]
            close = df['close'].iloc[i]
            open_price = df['open'].iloc[i]

            body = abs(close - open_price)
            total_range = high - low

            if total_range == 0:
                continue

            body_ratio = body / total_range

            # Check if marubozu (85%+ body)
            if body_ratio < self.marubozu_body_ratio:
                continue

            # Check if larger than average
            avg_range = (df['high'].iloc[i-10:i] - df['low'].iloc[i-10:i]).mean()
            if total_range < avg_range * 1.2:
                continue

            # Bullish Marubozu
            if close > open_price:
                # Volume confirmation
                if df['volume'].iloc[i] > df['volume'].iloc[i-10:i].mean() * 1.3:
                    df.loc[df.index[i], 'signal'] = 1
                    df.loc[df.index[i], 'entry_price'] = close
                    df.loc[df.index[i], 'stop_loss'] = low * 0.9995
                    df.loc[df.index[i], 'take_profit'] = close * 1.0045
                    df.loc[df.index[i], 'signal_type'] = 'marubozu_long'
                    signals += 1

            # Bearish Marubozu
            else:
                if df['volume'].iloc[i] > df['volume'].iloc[i-10:i].mean() * 1.3:
                    df.loc[df.index[i], 'signal'] = -1
                    df.loc[df.index[i], 'entry_price'] = close
                    df.loc[df.index[i], 'stop_loss'] = high * 1.0005
                    df.loc[df.index[i], 'take_profit'] = close * 0.9955
                    df.loc[df.index[i], 'signal_type'] = 'marubozu_short'
                    signals += 1

        if signals > 0:
            print(f"   Added {signals} marubozu signals")

        return df

    def _add_supply_demand_zones(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Supply/Demand Zones: Areas where price reversed strongly
        Similar to Order Blocks but with zone concept

        Supply Zone: Area where price dropped from
        Demand Zone: Area where price rallied from
        """
        df = df.copy()
        signals = 0

        for i in range(self.supply_demand_lookback + 10, len(df)):
            if df['signal'].iloc[i] != 0:
                continue

            # Find recent demand zones (strong rallies)
            for j in range(i - self.supply_demand_lookback, i - 5):
                # Check for strong rally after this candle
                rally_start = df['close'].iloc[j]
                rally_high = df['high'].iloc[j+1:j+6].max()

                rally_strength = (rally_high - rally_start) / rally_start

                # Strong rally (>0.3%)
                if rally_strength > 0.003:
                    # Current price testing this zone?
                    zone_low = df['low'].iloc[j]
                    zone_high = df['high'].iloc[j]
                    current_low = df['low'].iloc[i]

                    # Price touching demand zone?
                    if current_low <= zone_high and current_low >= zone_low * 0.995:
                        # Bullish reaction from zone?
                        if df['close'].iloc[i] > df['open'].iloc[i]:
                            # Volume confirmation
                            if df['volume'].iloc[i] > df['volume'].iloc[i-5:i].mean() * 1.2:
                                df.loc[df.index[i], 'signal'] = 1
                                df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                                df.loc[df.index[i], 'stop_loss'] = zone_low * 0.9995
                                df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 1.0035
                                df.loc[df.index[i], 'signal_type'] = 'demand_zone_long'
                                signals += 1
                                break

            # Find recent supply zones (strong drops)
            for j in range(i - self.supply_demand_lookback, i - 5):
                # Check for strong drop after this candle
                drop_start = df['close'].iloc[j]
                drop_low = df['low'].iloc[j+1:j+6].min()

                drop_strength = (drop_start - drop_low) / drop_start

                # Strong drop (>0.3%)
                if drop_strength > 0.003:
                    # Current price testing this zone?
                    zone_low = df['low'].iloc[j]
                    zone_high = df['high'].iloc[j]
                    current_high = df['high'].iloc[i]

                    # Price touching supply zone?
                    if current_high >= zone_low and current_high <= zone_high * 1.005:
                        # Bearish reaction from zone?
                        if df['close'].iloc[i] < df['open'].iloc[i]:
                            if df['volume'].iloc[i] > df['volume'].iloc[i-5:i].mean() * 1.2:
                                df.loc[df.index[i], 'signal'] = -1
                                df.loc[df.index[i], 'entry_price'] = df['close'].iloc[i]
                                df.loc[df.index[i], 'stop_loss'] = zone_high * 1.0005
                                df.loc[df.index[i], 'take_profit'] = df['close'].iloc[i] * 0.9965
                                df.loc[df.index[i], 'signal_type'] = 'supply_zone_short'
                                signals += 1
                                break

        if signals > 0:
            print(f"   Added {signals} supply/demand zone signals")

        return df

    def get_strategy_info(self) -> dict:
        """Get ultimate strategy info"""
        return {
            'strategy_type': 'Ultimate Multi-Signal Gold',
            'timeframe': '1H',
            'total_patterns': 11,
            'smc_patterns': ['OB', 'FVG', 'Liquidity Sweep', 'BOS', 'Trendline Breakout'],
            'candlestick_patterns': ['Inside Bar', '3-Candle Momentum', 'Hammer/Shooting Star',
                                     'Morning/Evening Star', 'Marubozu', 'Supply/Demand Zones'],
            'confluence_scoring': self.use_confluence_scoring,
            'target_signals_per_day': '1.5-2.0',
            'target_win_rate': '75-80%',
            'expected_return': '25-35% monthly'
        }


def test_ultimate_strategy():
    """Test ultimate multi-signal"""
    print("="*80)
    print("ULTIMATE MULTI-SIGNAL STRATEGY TEST")
    print("="*80)

    from intraday_gold_data import generate_intraday_gold_data
    from backtester import Backtester

    # Generate data
    print("\n📊 Generating 30 days of 1H gold data...")
    df = generate_intraday_gold_data(days=30, timeframe='1H')

    # Run strategy
    strategy = UltimateMultiSignal()
    df_signals = strategy.run_strategy(df)

    # Backtest
    bt = Backtester(initial_capital=10000, commission=0.001, slippage=0.0005)
    stats = bt.run(df_signals)

    # Results
    print("\n" + "="*80)
    print("ULTIMATE MULTI-SIGNAL RESULTS")
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
    print(f"   Profit Factor: {stats['profit_factor']:.2f}")

    # Detailed results
    bt.print_results(stats)

    # Save trades
    if stats['total_trades'] > 0:
        df_trades = pd.DataFrame(stats['trades'])
        df_trades.to_csv('ultimate_multi_signal_trades.csv', index=False)
        print(f"\n💾 Trades saved to 'ultimate_multi_signal_trades.csv'")

    print("\n" + "="*80)
    print("✅ TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    test_ultimate_strategy()
