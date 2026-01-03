"""
Demo Stock Screener - Works without yfinance
Uses simulated data to demonstrate screener functionality
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from stock_data_loader import StockDataLoader


class DemoStockScreener:
    """
    Demo version of stock screener using simulated data
    """

    def __init__(
        self,
        lookback_days: int = 180,
        min_score: float = 60,
        top_n: int = 10
    ):
        self.lookback_days = lookback_days
        self.min_score = min_score
        self.top_n = top_n

        print(f"\n🔍 Demo Stock Screener Initialized")
        print(f"   Lookback: {lookback_days} days")
        print(f"   Min score: {min_score}/100")
        print(f"   Show top: {top_n}")
        print(f"   ⚠️  Using simulated data (no internet required)")

    def generate_stock_data(self, ticker: str, days: int = None) -> pd.DataFrame:
        """Generate simulated stock data"""
        if days is None:
            days = self.lookback_days

        # Different characteristics for different stocks
        configs = {
            'AAPL': {'price': 180, 'vol': 0.015, 'trend': 0.0005},  # Steady growth
            'MSFT': {'price': 370, 'vol': 0.018, 'trend': 0.0007},  # Strong growth
            'NVDA': {'price': 450, 'vol': 0.035, 'trend': 0.0012},  # Very strong but volatile
            'TSLA': {'price': 250, 'vol': 0.045, 'trend': 0.0003},  # Volatile, weak trend
            'AMD': {'price': 140, 'vol': 0.030, 'trend': 0.0009},   # Good growth, moderate vol
            'GOOGL': {'price': 140, 'vol': 0.020, 'trend': 0.0006}, # Solid growth
            'META': {'price': 350, 'vol': 0.025, 'trend': 0.0008},  # Strong growth
            'AMZN': {'price': 170, 'vol': 0.022, 'trend': 0.0004},  # Moderate
            'SPY': {'price': 450, 'vol': 0.012, 'trend': 0.0003},   # Market benchmark
        }

        config = configs.get(ticker, {'price': 100, 'vol': 0.02, 'trend': 0.0002})

        loader = StockDataLoader(
            ticker=ticker,
            initial_price=config['price'],
            volatility=config['vol'],
            trend_strength=config['trend']
        )

        return loader.generate_daily_data(days=days)

    def calculate_momentum_score(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """Momentum Score (0-30 points)"""
        if len(df) < 50:
            return 0, {}

        score = 0
        details = {}

        # Price performance
        returns_1m = (df['close'].iloc[-1] - df['close'].iloc[-20]) / df['close'].iloc[-20] * 100
        returns_3m = (df['close'].iloc[-1] - df['close'].iloc[-60]) / df['close'].iloc[-60] * 100
        returns_6m = (df['close'].iloc[-1] - df['close'].iloc[-120]) / df['close'].iloc[-120] * 100

        avg_return = (returns_1m + returns_3m + returns_6m) / 3

        if avg_return > 20:
            score += 10
        elif avg_return > 10:
            score += 7
        elif avg_return > 5:
            score += 4
        elif avg_return > 0:
            score += 2

        details['returns_1m'] = returns_1m
        details['returns_3m'] = returns_3m
        details['returns_6m'] = returns_6m

        # Trend consistency
        highs = df['high'].rolling(window=20).max()
        lows = df['low'].rolling(window=20).min()

        higher_highs = (highs.diff() > 0).sum() / len(highs) * 100
        higher_lows = (lows.diff() > 0).sum() / len(lows) * 100

        consistency = (higher_highs + higher_lows) / 2

        if consistency > 60:
            score += 10
        elif consistency > 50:
            score += 7
        elif consistency > 40:
            score += 4

        details['trend_consistency'] = consistency

        # Recent acceleration
        if returns_1m > returns_3m and returns_3m > 0:
            score += 10
        elif returns_1m > 0:
            score += 5

        details['accelerating'] = returns_1m > returns_3m

        return score, details

    def calculate_relative_strength(self, df: pd.DataFrame, spy_df: pd.DataFrame) -> Tuple[float, Dict]:
        """Relative Strength Score (0-25 points)"""
        if len(df) < 60 or spy_df is None or len(spy_df) < 60:
            return 0, {}

        score = 0
        details = {}

        # Compare returns vs SPY
        stock_1m = (df['close'].iloc[-1] - df['close'].iloc[-20]) / df['close'].iloc[-20] * 100
        stock_3m = (df['close'].iloc[-1] - df['close'].iloc[-60]) / df['close'].iloc[-60] * 100

        spy_1m = (spy_df['close'].iloc[-1] - spy_df['close'].iloc[-20]) / spy_df['close'].iloc[-20] * 100
        spy_3m = (spy_df['close'].iloc[-1] - spy_df['close'].iloc[-60]) / spy_df['close'].iloc[-60] * 100

        outperf_1m = stock_1m - spy_1m
        outperf_3m = stock_3m - spy_3m

        if outperf_1m > 10 and outperf_3m > 10:
            score += 25
        elif outperf_1m > 5 and outperf_3m > 5:
            score += 20
        elif outperf_1m > 0 and outperf_3m > 0:
            score += 15
        elif outperf_1m > 0 or outperf_3m > 0:
            score += 10

        details['outperf_1m'] = outperf_1m
        details['outperf_3m'] = outperf_3m
        details['beating_market'] = outperf_1m > 0 and outperf_3m > 0

        return score, details

    def calculate_trend_quality(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """Trend Quality Score (0-20 points)"""
        if len(df) < 50:
            return 0, {}

        score = 0
        details = {}

        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean() if len(df) >= 200 else df['ema_50']

        current_price = df['close'].iloc[-1]
        ema_20 = df['ema_20'].iloc[-1]
        ema_50 = df['ema_50'].iloc[-1]
        ema_200 = df['ema_200'].iloc[-1]

        # EMA alignment
        if current_price > ema_20 > ema_50 > ema_200:
            score += 10
        elif current_price > ema_20 > ema_50:
            score += 7
        elif current_price > ema_20:
            score += 4

        details['ema_aligned'] = current_price > ema_20 > ema_50

        # Distance from support
        dist_from_20 = (current_price - ema_20) / ema_20 * 100

        if 0 < dist_from_20 < 3:
            score += 5
        elif dist_from_20 < 0 and dist_from_20 > -2:
            score += 4
        elif dist_from_20 > 3 and dist_from_20 < 8:
            score += 2

        details['dist_from_ema20'] = dist_from_20

        # Clean trend
        returns = df['close'].pct_change()
        volatility = returns.std() * 100

        if volatility < 2:
            score += 5
        elif volatility < 3:
            score += 3
        elif volatility < 4:
            score += 1

        details['volatility'] = volatility

        return score, details

    def calculate_volume_score(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """Volume Score (0-15 points)"""
        if len(df) < 50:
            return 0, {}

        score = 0
        details = {}

        avg_volume = df['volume'].iloc[-50:].mean()
        recent_volume = df['volume'].iloc[-10:].mean()

        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1

        if volume_ratio > 1.5:
            score += 10
        elif volume_ratio > 1.2:
            score += 7
        elif volume_ratio > 1.0:
            score += 4

        details['volume_ratio'] = volume_ratio

        # Volume on up days vs down days
        recent_data = df.iloc[-20:].copy()
        recent_data['price_change'] = recent_data['close'].diff()

        up_days = recent_data[recent_data['price_change'] > 0]
        down_days = recent_data[recent_data['price_change'] < 0]

        avg_vol_up = up_days['volume'].mean() if len(up_days) > 0 else 0
        avg_vol_down = down_days['volume'].mean() if len(down_days) > 0 else 1

        vol_ratio_updown = avg_vol_up / avg_vol_down if avg_vol_down > 0 else 1

        if vol_ratio_updown > 1.3:
            score += 5
        elif vol_ratio_updown > 1.1:
            score += 3

        details['volume_on_up_days'] = vol_ratio_updown

        return score, details

    def calculate_risk_reward(self, df: pd.DataFrame) -> Tuple[float, Dict]:
        """Risk/Reward Score (0-10 points)"""
        if len(df) < 50:
            return 0, {}

        score = 0
        details = {}

        current_price = df['close'].iloc[-1]

        # Distance from recent high
        recent_high = df['high'].iloc[-60:].max()
        dist_from_high = (recent_high - current_price) / current_price * 100

        if dist_from_high < 5:
            score += 5
        elif dist_from_high < 10:
            score += 3
        elif dist_from_high < 20:
            score += 1

        details['dist_from_high'] = dist_from_high

        # Not in drawdown
        high_60d = df['high'].iloc[-60:].max()
        current_dd = (current_price - high_60d) / high_60d * 100

        if current_dd > -5:
            score += 5
        elif current_dd > -10:
            score += 3
        elif current_dd > -20:
            score += 1

        details['current_drawdown'] = current_dd

        return score, details

    def screen_stock(self, ticker: str, spy_df: pd.DataFrame = None) -> Dict:
        """Screen a single stock"""
        df = self.generate_stock_data(ticker, days=self.lookback_days)

        if df is None or len(df) < 50:
            return None

        # Calculate scores
        momentum_score, momentum_details = self.calculate_momentum_score(df)
        rs_score, rs_details = self.calculate_relative_strength(df, spy_df)
        trend_score, trend_details = self.calculate_trend_quality(df)
        volume_score, volume_details = self.calculate_volume_score(df)
        rr_score, rr_details = self.calculate_risk_reward(df)

        total_score = momentum_score + rs_score + trend_score + volume_score + rr_score

        return {
            'ticker': ticker,
            'total_score': total_score,
            'momentum_score': momentum_score,
            'rs_score': rs_score,
            'trend_score': trend_score,
            'volume_score': volume_score,
            'rr_score': rr_score,
            'current_price': df['close'].iloc[-1],
            'returns_1m': momentum_details.get('returns_1m', 0),
            'returns_3m': momentum_details.get('returns_3m', 0),
            'returns_6m': momentum_details.get('returns_6m', 0),
            'beating_market': rs_details.get('beating_market', False),
            'ema_aligned': trend_details.get('ema_aligned', False),
            'volume_increasing': volume_details.get('volume_ratio', 1) > 1.2,
        }

    def screen_multiple(self, tickers: List[str]) -> pd.DataFrame:
        """Screen multiple stocks"""
        print(f"\n🔍 Screening {len(tickers)} stocks...")

        # Get SPY data
        print(f"   Generating SPY (market benchmark)...")
        spy_df = self.generate_stock_data('SPY', days=self.lookback_days)

        results = []

        for i, ticker in enumerate(tickers, 1):
            print(f"   [{i}/{len(tickers)}] Analyzing {ticker}...", end='\r')

            result = self.screen_stock(ticker, spy_df)

            if result and result['total_score'] >= self.min_score:
                results.append(result)

        print(f"\n   ✅ Screening complete!")

        if len(results) == 0:
            print(f"   ⚠️  No stocks meet minimum score of {self.min_score}")
            return pd.DataFrame()

        df = pd.DataFrame(results)
        df = df.sort_values('total_score', ascending=False)
        df = df.head(self.top_n)

        return df

    def print_results(self, df: pd.DataFrame):
        """Print screening results"""
        if df.empty:
            print("\n❌ No stocks found matching criteria")
            return

        print("\n" + "="*80)
        print(f"🏆 TOP {len(df)} STOCKS WITH GROWTH POTENTIAL (SIMULATED DATA)")
        print("="*80)

        summary = df[['ticker', 'total_score', 'current_price', 'returns_1m', 'returns_3m',
                      'beating_market', 'ema_aligned', 'volume_increasing']].copy()

        summary['returns_1m'] = summary['returns_1m'].apply(lambda x: f"{x:+.1f}%")
        summary['returns_3m'] = summary['returns_3m'].apply(lambda x: f"{x:+.1f}%")
        summary['current_price'] = summary['current_price'].apply(lambda x: f"${x:.2f}")

        print("\n" + summary.to_string(index=False))

        print("\n" + "="*80)
        print("📊 DETAILED ANALYSIS - TOP 3")
        print("="*80)

        for idx, row in df.head(3).iterrows():
            print(f"\n{row['ticker']} - Score: {row['total_score']:.0f}/100")
            print(f"   Price: ${row['current_price']:.2f}")
            print(f"   Returns: 1M: {row['returns_1m']:+.1f}%, 3M: {row['returns_3m']:+.1f}%, 6M: {row['returns_6m']:+.1f}%")
            print(f"   Momentum: {row['momentum_score']:.0f}/30")
            print(f"   Rel Strength: {row['rs_score']:.0f}/25 {'✅' if row['beating_market'] else '❌'}")
            print(f"   Trend Quality: {row['trend_score']:.0f}/20 {'✅' if row['ema_aligned'] else '❌'}")
            print(f"   Volume: {row['volume_score']:.0f}/15 {'✅' if row['volume_increasing'] else '❌'}")
            print(f"   Risk/Reward: {row['rr_score']:.0f}/10")


if __name__ == "__main__":
    # Create demo screener
    screener = DemoStockScreener(
        lookback_days=180,
        min_score=0,  # Show all for demo
        top_n=10
    )

    # Stock universe
    universe = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'AMD', 'TSLA']

    print(f"\n📋 Stock Universe: {len(universe)} stocks")
    print(f"   {', '.join(universe)}")

    # Screen
    results = screener.screen_multiple(universe)

    # Print results
    screener.print_results(results)

    # Save
    if not results.empty:
        results.to_csv('demo_top_stocks.csv', index=False)
        print(f"\n💾 Results saved to 'demo_top_stocks.csv'")
        print(f"\n💡 Note: This is simulated data. For real data, use stock_screener.py with yfinance")
