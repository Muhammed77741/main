"""
Comprehensive Stock Screener - Technical + Fundamental Analysis

Combines:
1. Technical Analysis (50 points) - price, volume, trends
2. Fundamental Analysis (50 points) - financials, profitability, valuation

Total Score: 0-100 points
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from stock_data_loader import StockDataLoader


class FundamentalData:
    """Generate realistic fundamental data for stocks"""

    @staticmethod
    def generate_fundamentals(ticker: str) -> Dict:
        """
        Generate fundamental metrics for a stock

        Returns dict with:
        - Profitability metrics (margins, ROE, ROA)
        - Growth metrics (revenue growth, earnings growth)
        - Valuation metrics (P/E, P/B, PEG)
        - Financial health (debt/equity, current ratio)
        """

        # Different profiles for different stocks
        profiles = {
            'AAPL': {
                'revenue_growth': 8.5,      # 8.5% YoY
                'earnings_growth': 12.3,    # 12.3% YoY
                'profit_margin': 25.3,      # 25.3% net margin
                'roe': 147.0,               # Return on Equity
                'roa': 28.5,                # Return on Assets
                'pe_ratio': 29.5,           # Price to Earnings
                'pb_ratio': 45.2,           # Price to Book
                'debt_to_equity': 1.73,     # Debt/Equity ratio
                'current_ratio': 0.98,      # Current assets/liabilities
                'free_cash_flow': 99.5,     # Billions
                'revenue_ttm': 383.3,       # Trailing 12 months revenue (B)
                'eps': 6.13,                # Earnings per share
            },
            'MSFT': {
                'revenue_growth': 13.2,
                'earnings_growth': 18.7,
                'profit_margin': 36.2,
                'roe': 38.4,
                'roa': 15.8,
                'pe_ratio': 35.8,
                'pb_ratio': 11.5,
                'debt_to_equity': 0.34,
                'current_ratio': 1.77,
                'free_cash_flow': 73.4,
                'revenue_ttm': 227.6,
                'eps': 11.04,
            },
            'NVDA': {
                'revenue_growth': 126.0,    # Massive growth
                'earnings_growth': 168.0,
                'profit_margin': 48.9,      # Very high
                'roe': 98.3,
                'roa': 52.1,
                'pe_ratio': 68.5,           # High valuation
                'pb_ratio': 52.3,
                'debt_to_equity': 0.24,
                'current_ratio': 3.59,
                'free_cash_flow': 28.7,
                'revenue_ttm': 60.9,
                'eps': 11.93,
            },
            'TSLA': {
                'revenue_growth': 18.8,
                'earnings_growth': -23.4,   # Negative!
                'profit_margin': 14.4,
                'roe': 24.6,
                'roa': 8.9,
                'pe_ratio': 75.2,           # Very high
                'pb_ratio': 13.8,
                'debt_to_equity': 0.09,
                'current_ratio': 1.73,
                'free_cash_flow': 4.4,
                'revenue_ttm': 96.8,
                'eps': 3.65,
            },
            'GOOGL': {
                'revenue_growth': 9.5,
                'earnings_growth': 14.2,
                'profit_margin': 26.5,
                'roe': 28.9,
                'roa': 16.2,
                'pe_ratio': 23.4,
                'pb_ratio': 6.2,
                'debt_to_equity': 0.08,
                'current_ratio': 2.78,
                'free_cash_flow': 69.5,
                'revenue_ttm': 307.4,
                'eps': 5.80,
            },
            'META': {
                'revenue_growth': 16.3,
                'earnings_growth': 73.4,    # Big recovery
                'profit_margin': 36.4,
                'roe': 30.8,
                'roa': 18.9,
                'pe_ratio': 27.3,
                'pb_ratio': 7.8,
                'debt_to_equity': 0.00,     # No debt!
                'current_ratio': 2.76,
                'free_cash_flow': 43.0,
                'revenue_ttm': 134.9,
                'eps': 14.87,
            },
            'AMD': {
                'revenue_growth': 3.8,
                'earnings_growth': -48.6,   # Weak
                'profit_margin': 4.6,       # Low
                'roe': 3.1,
                'roa': 1.9,
                'pe_ratio': 145.3,          # Very expensive
                'pb_ratio': 3.9,
                'debt_to_equity': 0.04,
                'current_ratio': 2.41,
                'free_cash_flow': 0.6,      # Low
                'revenue_ttm': 22.7,
                'eps': 0.76,
            },
            'AMZN': {
                'revenue_growth': 11.2,
                'earnings_growth': -25.3,
                'profit_margin': 6.3,
                'roe': 17.2,
                'roa': 6.4,
                'pe_ratio': 52.8,
                'pb_ratio': 8.1,
                'debt_to_equity': 0.54,
                'current_ratio': 1.03,
                'free_cash_flow': 36.8,
                'revenue_ttm': 574.8,
                'eps': 2.90,
            },
        }

        # Get profile or use default
        return profiles.get(ticker, {
            'revenue_growth': 5.0,
            'earnings_growth': 8.0,
            'profit_margin': 15.0,
            'roe': 15.0,
            'roa': 8.0,
            'pe_ratio': 20.0,
            'pb_ratio': 3.0,
            'debt_to_equity': 0.5,
            'current_ratio': 1.5,
            'free_cash_flow': 5.0,
            'revenue_ttm': 50.0,
            'eps': 3.0,
        })


class ComprehensiveScreener:
    """
    Stock screener with technical + fundamental analysis

    Scoring (0-100 points):
    - Technical Analysis: 0-50 points
      - Momentum: 0-15
      - Relative Strength: 0-12
      - Trend Quality: 0-10
      - Volume: 0-8
      - Risk/Reward: 0-5

    - Fundamental Analysis: 0-50 points
      - Growth: 0-15 (revenue, earnings)
      - Profitability: 0-15 (margins, ROE, ROA)
      - Valuation: 0-12 (P/E, P/B, PEG)
      - Financial Health: 0-8 (debt, liquidity)
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

        print(f"\n🔍 Comprehensive Stock Screener Initialized")
        print(f"   Analysis: Technical (50pts) + Fundamental (50pts)")
        print(f"   Lookback: {lookback_days} days")
        print(f"   Min score: {min_score}/100")
        print(f"   Show top: {top_n}")

    def generate_stock_data(self, ticker: str, days: int = None) -> pd.DataFrame:
        """Generate simulated stock data"""
        if days is None:
            days = self.lookback_days

        configs = {
            'AAPL': {'price': 180, 'vol': 0.015, 'trend': 0.0005},
            'MSFT': {'price': 370, 'vol': 0.018, 'trend': 0.0007},
            'NVDA': {'price': 450, 'vol': 0.035, 'trend': 0.0012},
            'TSLA': {'price': 250, 'vol': 0.045, 'trend': 0.0003},
            'AMD': {'price': 140, 'vol': 0.030, 'trend': 0.0009},
            'GOOGL': {'price': 140, 'vol': 0.020, 'trend': 0.0006},
            'META': {'price': 350, 'vol': 0.025, 'trend': 0.0008},
            'AMZN': {'price': 170, 'vol': 0.022, 'trend': 0.0004},
            'SPY': {'price': 450, 'vol': 0.012, 'trend': 0.0003},
        }

        config = configs.get(ticker, {'price': 100, 'vol': 0.02, 'trend': 0.0002})

        loader = StockDataLoader(
            ticker=ticker,
            initial_price=config['price'],
            volatility=config['vol'],
            trend_strength=config['trend']
        )

        return loader.generate_daily_data(days=days)

    # Technical Analysis Methods (same as demo_screener)

    def calculate_technical_score(self, df: pd.DataFrame, spy_df: pd.DataFrame) -> Tuple[float, Dict]:
        """
        Calculate technical analysis score (0-50 points)
        """
        if len(df) < 50:
            return 0, {}

        total_score = 0
        details = {}

        # 1. Momentum (0-15 points)
        returns_1m = (df['close'].iloc[-1] - df['close'].iloc[-20]) / df['close'].iloc[-20] * 100
        returns_3m = (df['close'].iloc[-1] - df['close'].iloc[-60]) / df['close'].iloc[-60] * 100

        avg_return = (returns_1m + returns_3m) / 2

        if avg_return > 20:
            total_score += 15
        elif avg_return > 10:
            total_score += 12
        elif avg_return > 5:
            total_score += 8
        elif avg_return > 0:
            total_score += 4

        details['momentum'] = avg_return

        # 2. Relative Strength (0-12 points)
        if spy_df is not None and len(spy_df) >= 60:
            stock_3m = returns_3m
            spy_3m = (spy_df['close'].iloc[-1] - spy_df['close'].iloc[-60]) / spy_df['close'].iloc[-60] * 100
            outperf = stock_3m - spy_3m

            if outperf > 10:
                total_score += 12
            elif outperf > 5:
                total_score += 9
            elif outperf > 0:
                total_score += 6

            details['vs_market'] = outperf

        # 3. Trend Quality (0-10 points)
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()

        current_price = df['close'].iloc[-1]
        ema_20 = df['ema_20'].iloc[-1]
        ema_50 = df['ema_50'].iloc[-1]

        if current_price > ema_20 > ema_50:
            total_score += 10
        elif current_price > ema_20:
            total_score += 5

        details['trend_aligned'] = current_price > ema_20 > ema_50

        # 4. Volume (0-8 points)
        avg_volume = df['volume'].iloc[-50:].mean()
        recent_volume = df['volume'].iloc[-10:].mean()
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1

        if volume_ratio > 1.5:
            total_score += 8
        elif volume_ratio > 1.2:
            total_score += 5
        elif volume_ratio > 1.0:
            total_score += 3

        details['volume_trend'] = volume_ratio

        # 5. Risk/Reward (0-5 points)
        recent_high = df['high'].iloc[-60:].max()
        dist_from_high = (recent_high - current_price) / current_price * 100

        if dist_from_high < 5:
            total_score += 5
        elif dist_from_high < 10:
            total_score += 3

        details['near_high'] = dist_from_high < 5

        return total_score, details

    def calculate_fundamental_score(self, fundamentals: Dict) -> Tuple[float, Dict]:
        """
        Calculate fundamental analysis score (0-50 points)
        """
        total_score = 0
        details = {}

        # 1. Growth Score (0-15 points)
        growth_score = 0

        # Revenue growth
        rev_growth = fundamentals['revenue_growth']
        if rev_growth > 20:
            growth_score += 8
        elif rev_growth > 15:
            growth_score += 6
        elif rev_growth > 10:
            growth_score += 4
        elif rev_growth > 5:
            growth_score += 2

        # Earnings growth
        eps_growth = fundamentals['earnings_growth']
        if eps_growth > 25:
            growth_score += 7
        elif eps_growth > 15:
            growth_score += 5
        elif eps_growth > 10:
            growth_score += 3
        elif eps_growth > 0:
            growth_score += 1

        total_score += growth_score
        details['growth_score'] = growth_score
        details['revenue_growth'] = rev_growth
        details['earnings_growth'] = eps_growth

        # 2. Profitability Score (0-15 points)
        profit_score = 0

        # Profit margin
        margin = fundamentals['profit_margin']
        if margin > 30:
            profit_score += 6
        elif margin > 20:
            profit_score += 4
        elif margin > 10:
            profit_score += 2

        # ROE
        roe = fundamentals['roe']
        if roe > 25:
            profit_score += 5
        elif roe > 15:
            profit_score += 3
        elif roe > 10:
            profit_score += 1

        # ROA
        roa = fundamentals['roa']
        if roa > 15:
            profit_score += 4
        elif roa > 10:
            profit_score += 2
        elif roa > 5:
            profit_score += 1

        total_score += profit_score
        details['profitability_score'] = profit_score
        details['profit_margin'] = margin
        details['roe'] = roe

        # 3. Valuation Score (0-12 points)
        valuation_score = 0

        # P/E ratio (lower is better, but not too low)
        pe = fundamentals['pe_ratio']
        if 15 < pe < 25:
            valuation_score += 6  # Sweet spot
        elif 10 < pe < 35:
            valuation_score += 4
        elif pe < 50:
            valuation_score += 2

        # PEG ratio (P/E / Growth)
        peg = pe / eps_growth if eps_growth > 0 else 999
        if peg < 1:
            valuation_score += 6  # Undervalued
        elif peg < 1.5:
            valuation_score += 4
        elif peg < 2:
            valuation_score += 2

        total_score += valuation_score
        details['valuation_score'] = valuation_score
        details['pe_ratio'] = pe
        details['peg_ratio'] = peg

        # 4. Financial Health Score (0-8 points)
        health_score = 0

        # Debt/Equity (lower is better)
        de = fundamentals['debt_to_equity']
        if de < 0.3:
            health_score += 4
        elif de < 0.5:
            health_score += 3
        elif de < 1.0:
            health_score += 2
        elif de < 2.0:
            health_score += 1

        # Current ratio (>1 is good)
        cr = fundamentals['current_ratio']
        if cr > 2:
            health_score += 4
        elif cr > 1.5:
            health_score += 3
        elif cr > 1:
            health_score += 2

        total_score += health_score
        details['financial_health_score'] = health_score
        details['debt_to_equity'] = de
        details['current_ratio'] = cr

        return total_score, details

    def screen_stock(self, ticker: str, spy_df: pd.DataFrame = None) -> Dict:
        """Screen a single stock with technical + fundamental analysis"""

        # Technical data
        df = self.generate_stock_data(ticker, days=self.lookback_days)
        if df is None or len(df) < 50:
            return None

        # Fundamental data
        fundamentals = FundamentalData.generate_fundamentals(ticker)

        # Calculate scores
        technical_score, tech_details = self.calculate_technical_score(df, spy_df)
        fundamental_score, fund_details = self.calculate_fundamental_score(fundamentals)

        total_score = technical_score + fundamental_score

        return {
            'ticker': ticker,
            'total_score': total_score,
            'technical_score': technical_score,
            'fundamental_score': fundamental_score,
            'current_price': df['close'].iloc[-1],
            'revenue_growth': fund_details['revenue_growth'],
            'earnings_growth': fund_details['earnings_growth'],
            'profit_margin': fund_details['profit_margin'],
            'pe_ratio': fund_details['pe_ratio'],
            'peg_ratio': fund_details['peg_ratio'],
            'roe': fund_details['roe'],
            'debt_to_equity': fund_details['debt_to_equity'],
            'momentum': tech_details.get('momentum', 0),
            'vs_market': tech_details.get('vs_market', 0),
            'details': {
                'technical': tech_details,
                'fundamental': fund_details
            }
        }

    def screen_multiple(self, tickers: List[str]) -> pd.DataFrame:
        """Screen multiple stocks"""
        print(f"\n🔍 Screening {len(tickers)} stocks...")

        # Get SPY data
        print(f"   Generating market data...")
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

        print("\n" + "="*90)
        print(f"🏆 TOP {len(df)} STOCKS - TECHNICAL + FUNDAMENTAL ANALYSIS")
        print("="*90)

        # Summary table
        summary = df[['ticker', 'total_score', 'technical_score', 'fundamental_score',
                      'current_price', 'revenue_growth', 'earnings_growth',
                      'profit_margin', 'pe_ratio']].copy()

        summary['current_price'] = summary['current_price'].apply(lambda x: f"${x:.2f}")
        summary['revenue_growth'] = summary['revenue_growth'].apply(lambda x: f"{x:+.1f}%")
        summary['earnings_growth'] = summary['earnings_growth'].apply(lambda x: f"{x:+.1f}%")
        summary['profit_margin'] = summary['profit_margin'].apply(lambda x: f"{x:.1f}%")
        summary['pe_ratio'] = summary['pe_ratio'].apply(lambda x: f"{x:.1f}")

        print("\n" + summary.to_string(index=False))

        # Detailed analysis
        print("\n" + "="*90)
        print("📊 DETAILED ANALYSIS - TOP 3")
        print("="*90)

        for idx, row in df.head(3).iterrows():
            print(f"\n{'='*90}")
            print(f"🔹 {row['ticker']} - Total Score: {row['total_score']:.0f}/100")
            print(f"{'='*90}")
            print(f"   Price: ${row['current_price']:.2f}")
            print(f"\n   📈 TECHNICAL ({row['technical_score']:.0f}/50):")
            print(f"      Momentum: {row['momentum']:+.1f}%")
            print(f"      vs Market: {row['vs_market']:+.1f}%")

            print(f"\n   💰 FUNDAMENTAL ({row['fundamental_score']:.0f}/50):")
            print(f"      Revenue Growth: {row['revenue_growth']:+.1f}%")
            print(f"      Earnings Growth: {row['earnings_growth']:+.1f}%")
            print(f"      Profit Margin: {row['profit_margin']:.1f}%")
            print(f"      ROE: {row['roe']:.1f}%")
            print(f"      P/E Ratio: {row['pe_ratio']:.1f}")
            print(f"      PEG Ratio: {row['peg_ratio']:.2f}")
            print(f"      Debt/Equity: {row['debt_to_equity']:.2f}")


if __name__ == "__main__":
    # Create comprehensive screener
    screener = ComprehensiveScreener(
        lookback_days=180,
        min_score=40,  # Lower threshold to see more results
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
        results.to_csv('comprehensive_screener_results.csv', index=False)
        print(f"\n💾 Results saved to 'comprehensive_screener_results.csv'")
        print(f"\n💡 Note: Combines technical analysis (price/volume) with fundamentals (financials)")
