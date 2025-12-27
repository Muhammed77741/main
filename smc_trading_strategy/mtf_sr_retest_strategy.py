"""
Multi-Timeframe Support/Resistance Retest Strategy
Simplified approach: Find key S/R levels and trade retests

Concept:
1. Identify key S/R zones from price action
2. Wait for price to retest these zones
3. Enter on confirmation (rejection candle + volume)
4. Higher profit target on strong zones

Pro Trading Approach:
- S/R = previous highs/lows that acted as barriers
- Retest = price returns to zone and bounces
- Confluence = zone + volume + rejection = high probability
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intraday_gold_strategy import MultiSignalGoldStrategy


class MTF_SR_Retest_Strategy(MultiSignalGoldStrategy):
    """
    Multi-Timeframe Support/Resistance Retest Strategy

    Simplified: Find swing highs/lows, trade retests with confirmation
    """

    def __init__(self):
        super().__init__()

        # Simplified S/R parameters (OPTIMIZED)
        self.swing_window = 8            # Window to find swing highs/lows
        self.max_zones = 6               # Keep top 6 strongest zones
        self.zone_width_pct = 0.004      # Zone width: 0.4% of price
        self.min_touches = 3             # Minimum 3 touches (filter weak zones)
        self.max_touches = 15            # Maximum 15 touches (filter over-used zones)

        # Retest parameters (OPTIMIZED)
        self.min_retest_score = 4        # Minimum confluence score
        self.retest_cooldown_hours = 6   # Hours between retests

        # Time filters (scoring will handle quality)
        self.best_hours_only = False     # Don't filter by time, use scoring
        self.best_hours = [8, 9, 10, 13, 14, 15]  # GMT best hours

        print(f"   Mode: SIMPLIFIED S/R RETEST (IMPROVED)")
        print(f"   Swing window: {self.swing_window} candles")
        print(f"   Max zones: {self.max_zones}")
        print(f"   Touch range: {self.min_touches}-{self.max_touches}")
        print(f"   Min retest score: {self.min_retest_score}")
        print(f"   Cooldown: {self.retest_cooldown_hours}h")
        print(f"   Best hours only: {self.best_hours_only}")

    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run simplified S/R retest strategy
        """
        # Run base strategy first
        df = super().run_strategy(df)

        # Find S/R zones from swing points
        support_zones, resistance_zones = self._find_sr_zones(df)

        # Detect and trade retests
        df = self._trade_retests(df, support_zones, resistance_zones)

        return df

    def _find_sr_zones(self, df: pd.DataFrame) -> tuple:
        """
        Find Support and Resistance zones from swing points

        Returns: (support_zones, resistance_zones) as lists of dicts
        """
        support_levels = []
        resistance_levels = []

        # Find swing lows and highs
        for i in range(self.swing_window, len(df) - self.swing_window):
            # Swing low = support
            window_lows = df['low'].iloc[i-self.swing_window:i+self.swing_window+1]
            if df['low'].iloc[i] == window_lows.min():
                support_levels.append({
                    'price': df['low'].iloc[i],
                    'index': df.index[i],
                    'touches': 1
                })

            # Swing high = resistance
            window_highs = df['high'].iloc[i-self.swing_window:i+self.swing_window+1]
            if df['high'].iloc[i] == window_highs.max():
                resistance_levels.append({
                    'price': df['high'].iloc[i],
                    'index': df.index[i],
                    'touches': 1
                })

        print(f"   Found {len(support_levels)} swing lows + {len(resistance_levels)} swing highs")

        # Merge nearby levels and count touches
        support_zones = self._merge_and_count_touches(support_levels, df, is_support=True)
        resistance_zones = self._merge_and_count_touches(resistance_levels, df, is_support=False)
        print(f"   After merge: {len(support_zones)} support + {len(resistance_zones)} resistance zones")

        # Filter by touch count range (min and max)
        support_zones_before = len(support_zones)
        resistance_zones_before = len(resistance_zones)
        support_zones = [z for z in support_zones if self.min_touches <= z['touches'] <= self.max_touches]
        resistance_zones = [z for z in resistance_zones if self.min_touches <= z['touches'] <= self.max_touches]
        print(f"   After touch filter ({self.min_touches}-{self.max_touches}): {len(support_zones)}/{support_zones_before} support + {len(resistance_zones)}/{resistance_zones_before} resistance")

        # Keep only strongest zones (but not too many touches)
        support_zones = sorted(support_zones, key=lambda z: z['touches'], reverse=True)[:self.max_zones]
        resistance_zones = sorted(resistance_zones, key=lambda z: z['touches'], reverse=True)[:self.max_zones]

        print(f"   Final zones: {len(support_zones)} support + {len(resistance_zones)} resistance")

        return support_zones, resistance_zones

    def _merge_and_count_touches(self, levels: list, df: pd.DataFrame, is_support: bool) -> list:
        """
        Merge nearby levels and count how many times price touched each zone
        """
        if not levels:
            return []

        # Sort by price
        levels = sorted(levels, key=lambda x: x['price'])

        # Merge nearby levels (within zone_width_pct)
        merged_zones = []
        current_zone = levels[0].copy()
        current_zone['upper'] = current_zone['price'] * (1 + self.zone_width_pct)
        current_zone['lower'] = current_zone['price'] * (1 - self.zone_width_pct)

        for level in levels[1:]:
            # If close enough, merge
            if abs(level['price'] - current_zone['price']) / current_zone['price'] < self.zone_width_pct:
                current_zone['touches'] += 1
                # Update price to average
                current_zone['price'] = (current_zone['price'] + level['price']) / 2
                current_zone['upper'] = current_zone['price'] * (1 + self.zone_width_pct)
                current_zone['lower'] = current_zone['price'] * (1 - self.zone_width_pct)
            else:
                merged_zones.append(current_zone)
                current_zone = level.copy()
                current_zone['upper'] = current_zone['price'] * (1 + self.zone_width_pct)
                current_zone['lower'] = current_zone['price'] * (1 - self.zone_width_pct)

        merged_zones.append(current_zone)

        # Count swing touches only (not every candle)
        # This prevents zones from having 100+ touches
        for zone in merged_zones:
            swing_touches = 0
            for level in levels:
                if zone['lower'] <= level['price'] <= zone['upper']:
                    swing_touches += 1

            zone['touches'] = swing_touches

        return merged_zones

    def _trade_retests(self, df: pd.DataFrame, support_zones: list, resistance_zones: list) -> pd.DataFrame:
        """
        Detect retests and generate trading signals
        """
        df = df.copy()

        # Clear existing signals
        df['signal'] = 0
        df['entry_price'] = np.nan
        df['stop_loss'] = np.nan
        df['take_profit'] = np.nan
        df['signal_type'] = ''
        df['retest_score'] = 0

        signals_generated = 0

        # Track last retest time for each zone (cooldown)
        zone_last_trade = {}

        for i in range(20, len(df)):
            # Time filter: only trade during best hours
            if self.best_hours_only:
                current_hour = df.index[i].hour
                if current_hour not in self.best_hours:
                    continue
            current_price = df['close'].iloc[i]
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            current_open = df['open'].iloc[i]

            # Check support retest (buy signal)
            for zone_idx, zone in enumerate(support_zones):
                # Price is in or near zone
                if zone['lower'] * 0.998 <= current_low <= zone['upper'] * 1.002:
                    # Check cooldown
                    zone_key = f"support_{zone_idx}"
                    if zone_key in zone_last_trade:
                        hours_since_last = (df.index[i] - zone_last_trade[zone_key]).total_seconds() / 3600
                        if hours_since_last < self.retest_cooldown_hours:
                            continue  # Skip: cooldown period not elapsed

                    # Calculate retest score
                    score = self._score_retest(df, i, zone, is_support=True)

                    if score >= self.min_retest_score:
                        # Bullish confirmation: close above open (rejection)
                        if current_price >= current_open:
                            df.loc[df.index[i], 'signal'] = 1
                            df.loc[df.index[i], 'entry_price'] = current_price
                            df.loc[df.index[i], 'stop_loss'] = zone['lower'] * 0.9995

                            # TP based on zone strength
                            risk = current_price - df.loc[df.index[i], 'stop_loss']
                            rr = 2.0 + (zone['touches'] / 20)  # More touches = higher TP (adjusted)
                            df.loc[df.index[i], 'take_profit'] = current_price + (risk * rr)

                            df.loc[df.index[i], 'signal_type'] = f"support_retest_{zone['touches']}T"
                            df.loc[df.index[i], 'retest_score'] = score
                            signals_generated += 1

                            # Update last trade time for this zone
                            zone_last_trade[zone_key] = df.index[i]
                            break

            # Check resistance retest (sell signal)
            if df['signal'].iloc[i] == 0:
                for zone_idx, zone in enumerate(resistance_zones):
                    if zone['lower'] * 0.998 <= current_high <= zone['upper'] * 1.002:
                        # Check cooldown
                        zone_key = f"resistance_{zone_idx}"
                        if zone_key in zone_last_trade:
                            hours_since_last = (df.index[i] - zone_last_trade[zone_key]).total_seconds() / 3600
                            if hours_since_last < self.retest_cooldown_hours:
                                continue  # Skip: cooldown period not elapsed

                        score = self._score_retest(df, i, zone, is_support=False)

                        if score >= self.min_retest_score:
                            # Bearish confirmation: close below open
                            if current_price <= current_open:
                                df.loc[df.index[i], 'signal'] = -1
                                df.loc[df.index[i], 'entry_price'] = current_price
                                df.loc[df.index[i], 'stop_loss'] = zone['upper'] * 1.0005

                                risk = df.loc[df.index[i], 'stop_loss'] - current_price
                                rr = 2.0 + (zone['touches'] / 20)  # More touches = higher TP (adjusted)
                                df.loc[df.index[i], 'take_profit'] = current_price - (risk * rr)

                                df.loc[df.index[i], 'signal_type'] = f"resistance_retest_{zone['touches']}T"
                                df.loc[df.index[i], 'retest_score'] = score
                                signals_generated += 1

                                # Update last trade time for this zone
                                zone_last_trade[zone_key] = df.index[i]
                                break

        print(f"   Generated {signals_generated} retest signals")

        return df

    def _score_retest(self, df: pd.DataFrame, idx: int, zone: dict, is_support: bool) -> int:
        """
        Score retest quality (0-10)

        Scoring:
        +2: Strong zone (4+ touches)
        +2: High volume (1.3x+ average)
        +2: Rejection candle (long wick)
        +1: Recent zone (within 100 candles)
        +1: Gradual approach (not spike)
        +1: Clean price action (no deep pierce)
        +1: Multiple timeframe alignment
        """
        score = 0

        # 1. Zone strength
        if zone['touches'] >= 4:
            score += 2
        elif zone['touches'] >= 3:
            score += 1

        # 2. Volume confirmation
        if idx >= 10:
            avg_volume = df['volume'].iloc[idx-10:idx].mean()
            if df['volume'].iloc[idx] > avg_volume * 1.3:
                score += 2
            elif df['volume'].iloc[idx] > avg_volume * 1.1:
                score += 1

        # 3. Rejection candle
        open_p = df['open'].iloc[idx]
        close = df['close'].iloc[idx]
        high = df['high'].iloc[idx]
        low = df['low'].iloc[idx]

        body = abs(close - open_p)
        full_range = high - low

        if full_range > 0:
            if is_support:
                # Long lower wick
                lower_wick = min(open_p, close) - low
                if lower_wick > body * 2:
                    score += 2
                elif lower_wick > body:
                    score += 1
            else:
                # Long upper wick
                upper_wick = high - max(open_p, close)
                if upper_wick > body * 2:
                    score += 2
                elif upper_wick > body:
                    score += 1

        # 4. Recent zone
        candles_ago = (df.index[idx] - zone['index']).total_seconds() / 3600
        if candles_ago <= 100:
            score += 1

        # 5. Gradual approach (previous candle moving toward zone)
        if idx >= 1:
            prev_close = df['close'].iloc[idx-1]
            if is_support:
                if prev_close > zone['price']:
                    score += 1
            else:
                if prev_close < zone['price']:
                    score += 1

        # 6. Clean bounce (didn't pierce deep)
        zone_middle = (zone['upper'] + zone['lower']) / 2
        if is_support:
            if low >= zone_middle:
                score += 1
        else:
            if high <= zone_middle:
                score += 1

        return score

    def get_strategy_info(self) -> dict:
        """Get strategy info"""
        return {
            'strategy_type': 'Simplified S/R Retest',
            'approach': 'Find swing points, trade retests with confirmation',
            'max_zones': self.max_zones,
            'min_retest_score': self.min_retest_score
        }
