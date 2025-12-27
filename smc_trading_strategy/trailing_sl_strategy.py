"""
Original Multi-Signal Strategy with Trailing Stop Loss
When TP1 is hit, move SL to breakeven to lock in profits
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intraday_gold_strategy import MultiSignalGoldStrategy


class TrailingSLStrategy(MultiSignalGoldStrategy):
    """
    Original Multi-Signal with Trailing Stop Loss

    Key Features:
    - Multiple TP levels (TP1 @ 1R, TP2 @ 1.8R, TP3 @ 2.5R)
    - When TP1 is hit, move SL to breakeven + 0.3R
    - Lock in 30% of risk as guaranteed profit
    - Partial profit taking: 33% at TP1, 33% at TP2, 34% at TP3
    """

    def __init__(self):
        super().__init__()

        self.tp1_ratio = 1.0   # First TP at 1R
        self.tp2_ratio = 1.8   # Second TP at 1.8R
        self.tp3_ratio = 2.5   # Third TP at 2.5R
        self.breakeven_offset = 0.3  # Move SL to BE + 0.3R when TP1 hit

        print(f"   Mode: TRAILING STOP LOSS")
        print(f"   TP1: {self.tp1_ratio}R (33% close, move SL to BE+{self.breakeven_offset}R)")
        print(f"   TP2: {self.tp2_ratio}R (33% close)")
        print(f"   TP3: {self.tp3_ratio}R (34% close)")

    def run_strategy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run strategy with multiple TPs and trailing SL
        """
        # Run base multi-signal strategy
        df = super().run_strategy(df)

        # Add multiple TP levels
        df = self._add_multiple_tps(df)

        return df

    def _add_multiple_tps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add TP1, TP2, TP3 levels to each signal
        """
        df = df.copy()

        for i in range(len(df)):
            if df['signal'].iloc[i] == 0:
                continue

            entry_price = df['entry_price'].iloc[i]
            stop_loss = df['stop_loss'].iloc[i]

            if pd.isna(entry_price) or pd.isna(stop_loss):
                continue

            # Calculate risk
            risk = abs(entry_price - stop_loss)

            if df['signal'].iloc[i] == 1:  # Long
                df.loc[df.index[i], 'tp1'] = entry_price + (risk * self.tp1_ratio)
                df.loc[df.index[i], 'tp2'] = entry_price + (risk * self.tp2_ratio)
                df.loc[df.index[i], 'tp3'] = entry_price + (risk * self.tp3_ratio)
                df.loc[df.index[i], 'breakeven_sl'] = entry_price + (risk * self.breakeven_offset)
            else:  # Short
                df.loc[df.index[i], 'tp1'] = entry_price - (risk * self.tp1_ratio)
                df.loc[df.index[i], 'tp2'] = entry_price - (risk * self.tp2_ratio)
                df.loc[df.index[i], 'tp3'] = entry_price - (risk * self.tp3_ratio)
                df.loc[df.index[i], 'breakeven_sl'] = entry_price - (risk * self.breakeven_offset)

        return df

    def backtest(self, df: pd.DataFrame) -> tuple:
        """
        Enhanced backtest with trailing stop loss logic
        Tracks TP1/TP2/TP3 hits and moves SL accordingly
        """
        df = df.copy()

        trades = []
        current_position = None
        monthly_stats = {}  # Track monthly results

        for i in range(len(df)):
            current_time = df.index[i]
            current_month = current_time.strftime('%Y-%m')

            # Initialize monthly stats
            if current_month not in monthly_stats:
                monthly_stats[current_month] = {
                    'trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'pnl': 0.0,
                    'tp1_hits': 0,
                    'tp2_hits': 0,
                    'tp3_hits': 0,
                    'breakeven_moves': 0
                }

            # Check for exit if in position
            if current_position:
                exit_price = None
                exit_reason = None
                partial_exits = []

                current_high = df['high'].iloc[i]
                current_low = df['low'].iloc[i]

                if current_position['direction'] == 1:  # Long
                    # Check TP levels
                    if not current_position['tp1_hit'] and current_high >= current_position['tp1']:
                        current_position['tp1_hit'] = True
                        partial_exits.append(('TP1', current_position['tp1'], 0.33))
                        # Move SL to breakeven + offset
                        current_position['stop_loss'] = current_position['breakeven_sl']
                        current_position['sl_moved_to_be'] = True
                        monthly_stats[current_month]['tp1_hits'] += 1
                        monthly_stats[current_month]['breakeven_moves'] += 1

                    if not current_position['tp2_hit'] and current_high >= current_position['tp2']:
                        current_position['tp2_hit'] = True
                        partial_exits.append(('TP2', current_position['tp2'], 0.33))
                        monthly_stats[current_month]['tp2_hits'] += 1

                    if not current_position['tp3_hit'] and current_high >= current_position['tp3']:
                        current_position['tp3_hit'] = True
                        partial_exits.append(('TP3', current_position['tp3'], 0.34))
                        monthly_stats[current_month]['tp3_hits'] += 1
                        exit_price = current_position['tp3']
                        exit_reason = 'TP3'

                    # Check SL
                    if current_low <= current_position['stop_loss']:
                        exit_price = current_position['stop_loss']
                        exit_reason = 'SL_BE' if current_position['sl_moved_to_be'] else 'SL'

                else:  # Short
                    # Check TP levels
                    if not current_position['tp1_hit'] and current_low <= current_position['tp1']:
                        current_position['tp1_hit'] = True
                        partial_exits.append(('TP1', current_position['tp1'], 0.33))
                        current_position['stop_loss'] = current_position['breakeven_sl']
                        current_position['sl_moved_to_be'] = True
                        monthly_stats[current_month]['tp1_hits'] += 1
                        monthly_stats[current_month]['breakeven_moves'] += 1

                    if not current_position['tp2_hit'] and current_low <= current_position['tp2']:
                        current_position['tp2_hit'] = True
                        partial_exits.append(('TP2', current_position['tp2'], 0.33))
                        monthly_stats[current_month]['tp2_hits'] += 1

                    if not current_position['tp3_hit'] and current_low <= current_position['tp3']:
                        current_position['tp3_hit'] = True
                        partial_exits.append(('TP3', current_position['tp3'], 0.34))
                        monthly_stats[current_month]['tp3_hits'] += 1
                        exit_price = current_position['tp3']
                        exit_reason = 'TP3'

                    # Check SL
                    if current_high >= current_position['stop_loss']:
                        exit_price = current_position['stop_loss']
                        exit_reason = 'SL_BE' if current_position['sl_moved_to_be'] else 'SL'

                # Process partial exits
                total_pnl = 0
                for tp_level, tp_price, portion in partial_exits:
                    if current_position['direction'] == 1:
                        pnl = (tp_price - current_position['entry_price']) / current_position['entry_price']
                    else:
                        pnl = (current_position['entry_price'] - tp_price) / current_position['entry_price']

                    total_pnl += pnl * portion

                # Full exit
                if exit_price:
                    # Calculate remaining position PnL
                    remaining_portion = 1.0 - sum([p[2] for p in partial_exits])
                    if remaining_portion > 0:
                        if current_position['direction'] == 1:
                            pnl = (exit_price - current_position['entry_price']) / current_position['entry_price']
                        else:
                            pnl = (current_position['entry_price'] - exit_price) / current_position['entry_price']
                        total_pnl += pnl * remaining_portion

                    # Record trade
                    trades.append({
                        'entry_time': current_position['entry_time'],
                        'exit_time': current_time,
                        'direction': 'LONG' if current_position['direction'] == 1 else 'SHORT',
                        'entry_price': current_position['entry_price'],
                        'exit_price': exit_price,
                        'stop_loss': current_position['original_sl'],
                        'tp1': current_position['tp1'],
                        'tp2': current_position['tp2'],
                        'tp3': current_position['tp3'],
                        'tp1_hit': current_position['tp1_hit'],
                        'tp2_hit': current_position['tp2_hit'],
                        'tp3_hit': current_position['tp3_hit'],
                        'sl_moved_to_be': current_position['sl_moved_to_be'],
                        'pnl_pct': total_pnl * 100,
                        'exit_reason': exit_reason,
                        'signal_type': current_position['signal_type']
                    })

                    # Update monthly stats
                    monthly_stats[current_month]['trades'] += 1
                    monthly_stats[current_month]['pnl'] += total_pnl * 100
                    if total_pnl > 0:
                        monthly_stats[current_month]['wins'] += 1
                    else:
                        monthly_stats[current_month]['losses'] += 1

                    current_position = None

            # Check for new entry
            if current_position is None and df['signal'].iloc[i] != 0:
                current_position = {
                    'entry_time': current_time,
                    'direction': df['signal'].iloc[i],
                    'entry_price': df['entry_price'].iloc[i],
                    'stop_loss': df['stop_loss'].iloc[i],
                    'original_sl': df['stop_loss'].iloc[i],
                    'tp1': df['tp1'].iloc[i],
                    'tp2': df['tp2'].iloc[i],
                    'tp3': df['tp3'].iloc[i],
                    'breakeven_sl': df['breakeven_sl'].iloc[i],
                    'tp1_hit': False,
                    'tp2_hit': False,
                    'tp3_hit': False,
                    'sl_moved_to_be': False,
                    'signal_type': df['signal_type'].iloc[i] if 'signal_type' in df.columns else 'unknown'
                }

        return trades, monthly_stats

    def get_strategy_info(self) -> dict:
        """Get strategy info"""
        info = super().get_strategy_info()

        info.update({
            'strategy_type': 'Original Multi-Signal + Trailing SL',
            'tp_levels': f"TP1:{self.tp1_ratio}R, TP2:{self.tp2_ratio}R, TP3:{self.tp3_ratio}R",
            'trailing_sl': f"Move to BE+{self.breakeven_offset}R at TP1"
        })

        return info
