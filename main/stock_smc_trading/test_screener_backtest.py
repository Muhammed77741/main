"""
Quick test of screener backtester
Tests on a small set of stocks and short period
"""

from datetime import datetime, timedelta
from stock_screener import StockScreener
from screener_backtest import ScreenerBacktester

# Create screener
screener = StockScreener(
    lookback_days=180,
    min_score=50,  # Lower threshold for testing
    top_n=10
)

# Create backtester
backtester = ScreenerBacktester(
    screener=screener,
    backtest_periods=[30, 60],  # Test 1 and 2 month holds
    top_n_signals=3  # Top 3 stocks each screening
)

# Short backtest period (last 6 months, leave 3 months for future returns)
end_date = datetime.now() - timedelta(days=100)
start_date = end_date - timedelta(days=180)

# Small stock universe for quick test
test_stocks = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMD']

print(f"\n🧪 QUICK TEST")
print(f"   Stocks: {test_stocks}")
print(f"   Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

# Run backtest
results = backtester.run_backtest(
    start_date=start_date,
    end_date=end_date,
    tickers=test_stocks,
    frequency_days=60  # Screen every 2 months (less frequent for quick test)
)

# Analyze results
backtester.analyze_results(results)

# Save
if not results.empty:
    results.to_csv('test_backtest_results.csv', index=False)
    print(f"\n💾 Test results saved to 'test_backtest_results.csv'")
