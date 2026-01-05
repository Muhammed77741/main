"""
Monthly Analysis with Fibonacci Levels
Анализирует результаты бэктеста V9/V11 по месяцам и добавляет уровни Фибоначчи
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse


class MonthlyFibonacciAnalyzer:
    """Анализ по месяцам с уровнями Фибоначчи"""

    def __init__(self):
        # Fibonacci levels (ретрейсмент)
        self.fib_levels = {
            '0.236': 0.236,
            '0.382': 0.382,
            '0.500': 0.500,
            '0.618': 0.618,  # Золотое сечение
            '0.786': 0.786,
        }

        # Fibonacci extensions (цели)
        self.fib_extensions = {
            '1.272': 1.272,
            '1.414': 1.414,
            '1.618': 1.618,  # Золотое сечение
            '2.000': 2.000,
            '2.618': 2.618,
        }

    def load_backtest_results(self, file_path):
        """Загрузить результаты бэктеста"""
        df = pd.read_csv(file_path)
        df['entry_time'] = pd.to_datetime(df['entry_time'])
        df['exit_time'] = pd.to_datetime(df['exit_time'])

        return df

    def calculate_fibonacci_levels(self, monthly_df):
        """
        Рассчитать уровни Фибоначчи для месячных данных

        Args:
            monthly_df: DataFrame с месячными результатами

        Returns:
            DataFrame с Fibonacci levels
        """
        fib_data = []

        for idx, row in monthly_df.iterrows():
            month_pnl = row['total_pnl_pct']
            month_start = row['start_balance']
            month_end = row['end_balance']

            month_high = row['max_balance']
            month_low = row['min_balance']

            # Рассчитать диапазон месяца
            month_range = month_high - month_low

            # Fibonacci retracement levels (от высокой точки вниз)
            fib_retracement = {}
            for level_name, level_value in self.fib_levels.items():
                fib_price = month_high - (month_range * level_value)
                fib_retracement[f'Fib_{level_name}'] = fib_price

            # Fibonacci extension levels (цели от диапазона)
            fib_extension = {}
            for level_name, level_value in self.fib_extensions.items():
                fib_price = month_low + (month_range * level_value)
                fib_extension[f'Ext_{level_name}'] = fib_price

            # Определить ближайший уровень Фибоначчи
            closest_fib = self._find_closest_fib_level(month_end, fib_retracement)

            fib_data.append({
                'month': row['month'],
                'balance_start': month_start,
                'balance_end': month_end,
                'balance_high': month_high,
                'balance_low': month_low,
                'range': month_range,
                'pnl_pct': month_pnl,
                **fib_retracement,
                **fib_extension,
                'closest_fib_level': closest_fib['level'],
                'closest_fib_price': closest_fib['price'],
                'distance_from_fib': closest_fib['distance']
            })

        return pd.DataFrame(fib_data)

    def _find_closest_fib_level(self, current_price, fib_levels_dict):
        """Найти ближайший уровень Фибоначчи"""
        min_distance = float('inf')
        closest_level = None
        closest_price = None

        for level_name, fib_price in fib_levels_dict.items():
            distance = abs(current_price - fib_price)
            if distance < min_distance:
                min_distance = distance
                closest_level = level_name
                closest_price = fib_price

        return {
            'level': closest_level,
            'price': closest_price,
            'distance': min_distance
        }

    def analyze_monthly_performance(self, trades_df, initial_balance=500):
        """
        Анализировать результаты по месяцам

        Args:
            trades_df: DataFrame с результатами сделок
            initial_balance: Начальный баланс

        Returns:
            DataFrame с месячными результатами
        """
        trades_df = trades_df.copy()
        trades_df['month'] = trades_df['exit_time'].dt.to_period('M')

        monthly_results = []
        current_balance = initial_balance

        # Track running balance
        trades_df['cumulative_pnl_pct'] = trades_df['pnl_pct'].cumsum()

        for month in trades_df['month'].unique():
            month_trades = trades_df[trades_df['month'] == month]

            # Начальный баланс месяца
            first_trade_idx = month_trades.index[0]
            if first_trade_idx > 0:
                prev_cumulative = trades_df.loc[:first_trade_idx-1, 'pnl_pct'].sum()
                month_start_balance = initial_balance * (1 + prev_cumulative / 100)
            else:
                month_start_balance = initial_balance

            # Месячная прибыль
            month_pnl_pct = month_trades['pnl_pct'].sum()
            month_end_balance = month_start_balance * (1 + month_pnl_pct / 100)

            # Min/Max баланс внутри месяца
            cumulative_within_month = month_trades['pnl_pct'].cumsum()
            month_balances = month_start_balance * (1 + cumulative_within_month / 100)
            month_max_balance = month_balances.max()
            month_min_balance = month_balances.min()

            # Статистика сделок
            wins = len(month_trades[month_trades['pnl_pct'] > 0])
            losses = len(month_trades[month_trades['pnl_pct'] <= 0])
            win_rate = (wins / len(month_trades) * 100) if len(month_trades) > 0 else 0

            avg_win = month_trades[month_trades['pnl_pct'] > 0]['pnl_pct'].mean() if wins > 0 else 0
            avg_loss = month_trades[month_trades['pnl_pct'] <= 0]['pnl_pct'].mean() if losses > 0 else 0

            # TP hit rates
            tp1_hits = month_trades['tp1_hit'].sum()
            tp2_hits = month_trades['tp2_hit'].sum()
            tp3_hits = month_trades['tp3_hit'].sum()

            # Exit types
            exit_types = month_trades['exit_type'].value_counts()

            monthly_results.append({
                'month': str(month),
                'trades': len(month_trades),
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate,
                'total_pnl_pct': month_pnl_pct,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'start_balance': month_start_balance,
                'end_balance': month_end_balance,
                'max_balance': month_max_balance,
                'min_balance': month_min_balance,
                'profit_usd': month_end_balance - month_start_balance,
                'tp1_hits': tp1_hits,
                'tp2_hits': tp2_hits,
                'tp3_hits': tp3_hits,
                'sl_exits': exit_types.get('SL', 0),
                'trailing_sl_exits': exit_types.get('TRAILING_SL', 0),
                'timeout_exits': exit_types.get('TIMEOUT', 0),
            })

        return pd.DataFrame(monthly_results)

    def print_monthly_report(self, monthly_df, fib_df):
        """Вывести месячный отчет с Фибоначчи"""

        print(f"\n{'='*120}")
        print(f"📅 MONTHLY PERFORMANCE ANALYSIS WITH FIBONACCI LEVELS")
        print(f"{'='*120}")

        for idx, row in monthly_df.iterrows():
            fib_row = fib_df[fib_df['month'] == row['month']].iloc[0]

            print(f"\n{'─'*120}")
            print(f"📆 {row['month']}")
            print(f"{'─'*120}")

            # Performance
            print(f"\n   💰 PERFORMANCE:")
            print(f"   Trades: {row['trades']:3d} | Wins: {row['wins']:3d} ({row['win_rate']:.1f}%) | Losses: {row['losses']:3d}")
            print(f"   Total PnL: {row['total_pnl_pct']:+.2f}% | Profit: ${row['profit_usd']:+,.2f}")
            print(f"   Avg Win: {row['avg_win']:+.2f}% | Avg Loss: {row['avg_loss']:+.2f}%")

            # Balance range
            print(f"\n   📊 BALANCE MOVEMENT:")
            print(f"   Start:  ${row['start_balance']:,.2f}")
            print(f"   End:    ${row['end_balance']:,.2f}")
            print(f"   High:   ${row['max_balance']:,.2f}")
            print(f"   Low:    ${row['min_balance']:,.2f}")
            print(f"   Range:  ${fib_row['range']:,.2f}")

            # Fibonacci levels
            print(f"\n   🌟 FIBONACCI RETRACEMENT LEVELS:")
            print(f"   23.6%: ${fib_row['Fib_0.236']:,.2f}")
            print(f"   38.2%: ${fib_row['Fib_0.382']:,.2f}")
            print(f"   50.0%: ${fib_row['Fib_0.500']:,.2f}")
            print(f"   61.8%: ${fib_row['Fib_0.618']:,.2f} ← Golden Ratio")
            print(f"   78.6%: ${fib_row['Fib_0.786']:,.2f}")

            print(f"\n   🎯 FIBONACCI EXTENSION TARGETS:")
            print(f"   127.2%: ${fib_row['Ext_1.272']:,.2f}")
            print(f"   141.4%: ${fib_row['Ext_1.414']:,.2f}")
            print(f"   161.8%: ${fib_row['Ext_1.618']:,.2f} ← Golden Ratio")
            print(f"   200.0%: ${fib_row['Ext_2.000']:,.2f}")
            print(f"   261.8%: ${fib_row['Ext_2.618']:,.2f}")

            print(f"\n   📍 CURRENT POSITION:")
            print(f"   Closest Fib Level: {fib_row['closest_fib_level']}")
            print(f"   Distance: ${fib_row['distance_from_fib']:.2f}")

            # TP hits
            print(f"\n   🎯 TP HITS:")
            print(f"   TP1: {row['tp1_hits']:3d} | TP2: {row['tp2_hits']:3d} | TP3: {row['tp3_hits']:3d}")

            # Exit types
            print(f"\n   🚪 EXITS:")
            print(f"   SL: {row['sl_exits']:3d} | Trailing SL: {row['trailing_sl_exits']:3d} | Timeout: {row['timeout_exits']:3d}")

        # Summary
        print(f"\n{'='*120}")
        print(f"📊 OVERALL SUMMARY")
        print(f"{'='*120}")

        total_trades = monthly_df['trades'].sum()
        total_pnl = monthly_df['total_pnl_pct'].sum()
        start_balance = monthly_df.iloc[0]['start_balance']
        end_balance = monthly_df.iloc[-1]['end_balance']
        total_profit = end_balance - start_balance

        avg_monthly_pnl = monthly_df['total_pnl_pct'].mean()
        best_month = monthly_df.loc[monthly_df['total_pnl_pct'].idxmax()]
        worst_month = monthly_df.loc[monthly_df['total_pnl_pct'].idxmin()]

        print(f"\n   Total Trades: {total_trades}")
        print(f"   Total PnL: {total_pnl:+.2f}%")
        print(f"   Total Profit: ${total_profit:+,.2f}")
        print(f"   ROI: {(end_balance / start_balance - 1) * 100:+.2f}%")
        print(f"\n   Average Monthly PnL: {avg_monthly_pnl:+.2f}%")
        print(f"   Best Month: {best_month['month']} ({best_month['total_pnl_pct']:+.2f}%)")
        print(f"   Worst Month: {worst_month['month']} ({worst_month['total_pnl_pct']:+.2f}%)")

        print(f"\n{'='*120}\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Monthly Analysis with Fibonacci Levels')
    parser.add_argument('--file', type=str, required=True, help='Backtest results CSV file')
    parser.add_argument('--initial-balance', type=float, default=500, help='Initial balance (default: $500)')
    args = parser.parse_args()

    # Create analyzer
    analyzer = MonthlyFibonacciAnalyzer()

    # Load backtest results
    print(f"\n📂 Loading backtest results from {args.file}...")
    trades_df = analyzer.load_backtest_results(args.file)
    print(f"   Loaded {len(trades_df)} trades")

    # Analyze monthly performance
    monthly_df = analyzer.analyze_monthly_performance(trades_df, args.initial_balance)

    # Calculate Fibonacci levels
    fib_df = analyzer.calculate_fibonacci_levels(monthly_df)

    # Print report
    analyzer.print_monthly_report(monthly_df, fib_df)

    # Save results
    output_file = args.file.replace('.csv', '_monthly_fibonacci.csv')
    combined_df = pd.merge(monthly_df, fib_df, on='month')
    combined_df.to_csv(output_file, index=False)
    print(f"💾 Results saved to {output_file}")


if __name__ == "__main__":
    main()
