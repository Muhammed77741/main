"""
Stock Screener Backtester - Test Signals on Historical Data

This script tests the screener on historical data:
1. Runs screener on past dates
2. Tracks which stocks got buy signals
3. Measures how much they grew afterwards

Example: If screener signals "BUY AAPL" on Jan 1st,
we check how much AAPL grew in the next 30/60/90 days.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import yfinance as yf
from stock_screener import StockScreener


class ScreenerBacktester:
    """
    Backtest the stock screener on historical data

    Process:
    1. For each date in the past, run the screener
    2. Take top N stocks (buy signals)
    3. Track their returns over next periods (30d, 60d, 90d)
    4. Calculate win rate and average returns
    """

    def __init__(
        self,
        screener: StockScreener,
        backtest_periods: List[int] = [30, 60, 90],
        top_n_signals: int = 5
    ):
        """
        Args:
            screener: StockScreener instance
            backtest_periods: Days to hold after buy signal
            top_n_signals: Take top N stocks from each screening
        """
        self.screener = screener
        self.backtest_periods = backtest_periods
        self.top_n_signals = top_n_signals
        self.signals = []

        print(f"\n📊 Screener Backtester Initialized")
        print(f"   Hold periods: {backtest_periods} days")
        print(f"   Signals per screening: {top_n_signals}")

    def get_historical_data(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """Download historical data for specific date range"""
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(start=start_date, end=end_date, interval='1d')

            if df.empty:
                return None

            df.columns = df.columns.str.lower()
            return df
        except Exception as e:
            return None

    def calculate_future_returns(
        self,
        ticker: str,
        signal_date: datetime,
        current_price: float,
        periods: List[int]
    ) -> Dict[int, float]:
        """
        Calculate returns after signal date

        Args:
            ticker: Stock ticker
            signal_date: Date of buy signal
            current_price: Price at signal
            periods: List of periods (30, 60, 90 days)

        Returns:
            Dict mapping period -> return %
        """
        returns = {}

        for period in periods:
            future_date = signal_date + timedelta(days=period + 10)  # Extra days for weekends

            # Get data from signal to future
            df = self.get_historical_data(ticker, signal_date, future_date)

            if df is None or len(df) < period * 0.7:  # At least 70% of days
                returns[period] = None
                continue

            # Find price at target period (or closest available)
            target_idx = min(period, len(df) - 1)
            future_price = df['close'].iloc[target_idx]

            # Calculate return
            ret = (future_price - current_price) / current_price * 100
            returns[period] = ret

        return returns

    def run_backtest_at_date(
        self,
        test_date: datetime,
        tickers: List[str]
    ) -> List[Dict]:
        """
        Run screener at a specific date and track future returns

        Args:
            test_date: Date to run screening
            tickers: Stocks to screen

        Returns:
            List of signal dicts with future returns
        """
        print(f"\n📅 Screening on {test_date.strftime('%Y-%m-%d')}...")

        # Temporarily modify screener to use historical data
        # We need data BEFORE test_date
        lookback_start = test_date - timedelta(days=self.screener.lookback_days + 30)

        # Get SPY data
        spy_df = self.get_historical_data('SPY', lookback_start, test_date)
        if spy_df is None:
            print(f"   ⚠️  Could not get SPY data")
            return []

        results = []

        for ticker in tickers:
            # Get historical data up to test_date
            df = self.get_historical_data(ticker, lookback_start, test_date)

            if df is None or len(df) < 50:
                continue

            # Calculate scores using only data up to test_date
            try:
                momentum_score, _ = self.screener.calculate_momentum_score(df)
                rs_score, _ = self.screener.calculate_relative_strength(df, spy_df)
                trend_score, _ = self.screener.calculate_trend_quality(df)
                volume_score, _ = self.screener.calculate_volume_score(df)
                rr_score, _ = self.screener.calculate_risk_reward(df)

                total_score = momentum_score + rs_score + trend_score + volume_score + rr_score

                if total_score >= self.screener.min_score:
                    results.append({
                        'ticker': ticker,
                        'signal_date': test_date,
                        'score': total_score,
                        'price': df['close'].iloc[-1]
                    })
            except:
                continue

        # Sort by score and take top N
        results = sorted(results, key=lambda x: x['score'], reverse=True)
        results = results[:self.top_n_signals]

        print(f"   ✅ Found {len(results)} signals")

        # Calculate future returns for each signal
        signals_with_returns = []

        for signal in results:
            print(f"      {signal['ticker']} (score: {signal['score']:.0f})")

            future_returns = self.calculate_future_returns(
                signal['ticker'],
                signal['signal_date'],
                signal['price'],
                self.backtest_periods
            )

            signal['returns'] = future_returns
            signals_with_returns.append(signal)

        return signals_with_returns

    def run_backtest(
        self,
        start_date: datetime,
        end_date: datetime,
        tickers: List[str],
        frequency_days: int = 30
    ) -> pd.DataFrame:
        """
        Run backtest over a date range

        Args:
            start_date: Start of backtest period
            end_date: End of backtest period
            tickers: Stocks to screen
            frequency_days: How often to run screening (default: monthly)

        Returns:
            DataFrame with all signals and their returns
        """
        print(f"\n{'='*80}")
        print(f"🚀 STARTING BACKTEST")
        print(f"{'='*80}")
        print(f"   Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"   Screening every {frequency_days} days")
        print(f"   Stock universe: {len(tickers)} stocks")

        all_signals = []

        # Generate test dates
        current_date = start_date
        test_dates = []

        while current_date <= end_date:
            test_dates.append(current_date)
            current_date += timedelta(days=frequency_days)

        print(f"   Total screenings: {len(test_dates)}")

        # Run backtest at each date
        for i, test_date in enumerate(test_dates, 1):
            # Make sure we have enough time for future returns
            if test_date > datetime.now() - timedelta(days=max(self.backtest_periods) + 30):
                print(f"\n⚠️  Stopping at {test_date.strftime('%Y-%m-%d')} - not enough future data")
                break

            print(f"\n[{i}/{len(test_dates)}]", end=' ')
            signals = self.run_backtest_at_date(test_date, tickers)
            all_signals.extend(signals)

        # Convert to DataFrame
        if not all_signals:
            print(f"\n❌ No signals found in backtest period")
            return pd.DataFrame()

        # Flatten the returns into columns
        rows = []
        for signal in all_signals:
            row = {
                'ticker': signal['ticker'],
                'signal_date': signal['signal_date'],
                'score': signal['score'],
                'entry_price': signal['price']
            }

            for period, ret in signal['returns'].items():
                row[f'return_{period}d'] = ret

            rows.append(row)

        df = pd.DataFrame(rows)

        return df

    def analyze_results(self, results_df: pd.DataFrame):
        """
        Analyze and print backtest results

        Shows:
        - Win rate for each period
        - Average returns
        - Best/worst trades
        """
        if results_df.empty:
            print("\n❌ No results to analyze")
            return

        print(f"\n{'='*80}")
        print(f"📈 BACKTEST RESULTS")
        print(f"{'='*80}")

        total_signals = len(results_df)
        print(f"\n📊 Total signals: {total_signals}")

        # Analyze each period
        for period in self.backtest_periods:
            col = f'return_{period}d'

            if col not in results_df.columns:
                continue

            # Filter out None values
            valid_returns = results_df[results_df[col].notna()][col]

            if len(valid_returns) == 0:
                continue

            wins = (valid_returns > 0).sum()
            losses = (valid_returns <= 0).sum()
            win_rate = wins / len(valid_returns) * 100

            avg_return = valid_returns.mean()
            avg_win = valid_returns[valid_returns > 0].mean() if wins > 0 else 0
            avg_loss = valid_returns[valid_returns <= 0].mean() if losses > 0 else 0

            best_return = valid_returns.max()
            worst_return = valid_returns.min()

            print(f"\n📅 {period}-Day Hold Period:")
            print(f"   Win Rate: {win_rate:.1f}% ({wins} wins, {losses} losses)")
            print(f"   Avg Return: {avg_return:+.2f}%")
            print(f"   Avg Win: {avg_win:+.2f}%")
            print(f"   Avg Loss: {avg_loss:+.2f}%")
            print(f"   Best Trade: {best_return:+.2f}%")
            print(f"   Worst Trade: {worst_return:+.2f}%")

        # Show best trades
        print(f"\n{'='*80}")
        print(f"🏆 TOP 10 BEST TRADES (30-day returns)")
        print(f"{'='*80}")

        if 'return_30d' in results_df.columns:
            top_trades = results_df.nlargest(10, 'return_30d')[
                ['ticker', 'signal_date', 'entry_price', 'score', 'return_30d']
            ]

            for idx, row in top_trades.iterrows():
                print(f"   {row['ticker']:6s} | {row['signal_date'].strftime('%Y-%m-%d')} | "
                      f"${row['entry_price']:7.2f} | Score: {row['score']:3.0f} | "
                      f"Return: {row['return_30d']:+7.2f}%")

        # Show worst trades
        print(f"\n{'='*80}")
        print(f"⚠️  TOP 10 WORST TRADES (30-day returns)")
        print(f"{'='*80}")

        if 'return_30d' in results_df.columns:
            worst_trades = results_df.nsmallest(10, 'return_30d')[
                ['ticker', 'signal_date', 'entry_price', 'score', 'return_30d']
            ]

            for idx, row in worst_trades.iterrows():
                print(f"   {row['ticker']:6s} | {row['signal_date'].strftime('%Y-%m-%d')} | "
                      f"${row['entry_price']:7.2f} | Score: {row['score']:3.0f} | "
                      f"Return: {row['return_30d']:+7.2f}%")


def create_stock_universe() -> List[str]:
    """Create stock universe for testing"""
    # Tech Giants
    tech = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'AMD', 'TSLA']

    # Growth
    growth = ['PLTR', 'SNOW', 'NET', 'CRWD', 'ZS']

    # Semiconductors
    semis = ['TSM', 'ASML', 'MU']

    # Combine
    universe = tech + growth + semis

    return list(set(universe))


if __name__ == "__main__":
    # Create screener with moderate settings
    screener = StockScreener(
        lookback_days=180,
        min_score=60,  # Only strong signals
        top_n=10
    )

    # Create backtester
    backtester = ScreenerBacktester(
        screener=screener,
        backtest_periods=[30, 60, 90],  # Test 1, 2, 3 month holds
        top_n_signals=5  # Top 5 stocks each screening
    )

    # Define backtest period
    # Test last 2 years (but leave 3 months for future returns)
    end_date = datetime.now() - timedelta(days=100)  # Leave room for future returns
    start_date = end_date - timedelta(days=365 * 2)  # 2 years back

    # Get stock universe
    universe = create_stock_universe()

    # Run backtest
    results = backtester.run_backtest(
        start_date=start_date,
        end_date=end_date,
        tickers=universe,
        frequency_days=30  # Screen monthly
    )

    # Analyze results
    backtester.analyze_results(results)

    # Save results
    if not results.empty:
        results.to_csv('screener_backtest_results.csv', index=False)
        print(f"\n💾 Results saved to 'screener_backtest_results.csv'")
