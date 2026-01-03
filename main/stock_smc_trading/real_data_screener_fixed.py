"""
Real Data Stock Screener - FIXED VERSION for Windows SSL issues

This version works around SSL certificate problems on Windows
by copying certifi bundle to a path without Russian characters.
"""

import os
import sys
import shutil

# === SSL FIX - MUST BE FIRST ===
print("🔧 Applying SSL fix...")

try:
    # Fix 1: Copy certifi to safe location
    import certifi
    original_cert = certifi.where()

    # Create safe directory without Russian characters
    safe_dir = "C:\\temp_certs" if os.name == 'nt' else "/tmp/certs"
    os.makedirs(safe_dir, exist_ok=True)

    # Copy certificate bundle
    safe_cert = os.path.join(safe_dir, "cacert.pem")
    if not os.path.exists(safe_cert):
        shutil.copy2(original_cert, safe_cert)

    # Set environment variables BEFORE importing yfinance
    os.environ['SSL_CERT_FILE'] = safe_cert
    os.environ['REQUESTS_CA_BUNDLE'] = safe_cert
    os.environ['CURL_CA_BUNDLE'] = safe_cert

    print(f"✅ SSL certificate: {safe_cert}")

except Exception as e:
    print(f"⚠️  Warning: {e}")
    # Fallback: disable SSL verification
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
    print("✅ SSL verification disabled as fallback")

# === END SSL FIX ===

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
    print("✅ yfinance imported successfully")
except ImportError:
    YFINANCE_AVAILABLE = False
    print("❌ yfinance not available")


class RealFundamentalData:
    """Get real fundamental data from yfinance"""

    @staticmethod
    def get_fundamentals(ticker: str) -> Optional[Dict]:
        """Get real fundamental metrics from yfinance"""
        if not YFINANCE_AVAILABLE:
            return None

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info or len(info) < 5:
                print(f"   ⚠️  No data for {ticker}")
                return None

            fundamentals = {
                'revenue_growth': info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else 0,
                'earnings_growth': info.get('earningsGrowth', 0) * 100 if info.get('earningsGrowth') else 0,
                'profit_margin': info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 0,
                'roe': info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0,
                'roa': info.get('returnOnAssets', 0) * 100 if info.get('returnOnAssets') else 0,
                'pe_ratio': info.get('trailingPE', 0) or 0,
                'pb_ratio': info.get('priceToBook', 0) or 0,
                'eps': info.get('trailingEps', 0) or 0,
                'debt_to_equity': info.get('debtToEquity', 0) / 100 if info.get('debtToEquity') else 0,
                'current_ratio': info.get('currentRatio', 0) or 0,
                'free_cash_flow': info.get('freeCashflow', 0) / 1e9 if info.get('freeCashflow') else 0,
                'revenue_ttm': info.get('totalRevenue', 0) / 1e9 if info.get('totalRevenue') else 0,
                'market_cap': info.get('marketCap', 0) / 1e9 if info.get('marketCap') else 0,
            }

            return fundamentals

        except Exception as e:
            print(f"   ⚠️  Error: {ticker}: {str(e)[:80]}")
            return None


class RealDataScreener:
    """Stock screener with REAL data - SSL FIXED VERSION"""

    def __init__(self, lookback_days: int = 180, min_score: float = 60, top_n: int = 10):
        self.lookback_days = lookback_days
        self.min_score = min_score
        self.top_n = top_n

        print(f"\n🔍 Real Data Stock Screener (SSL Fixed)")
        print(f"   Min score: {min_score}/100")

    def get_stock_data(self, ticker: str, days: int = None) -> pd.DataFrame:
        """Download real stock price data"""
        if not YFINANCE_AVAILABLE:
            return None

        if days is None:
            days = self.lookback_days

        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=f"{days}d")

            if df is None or df.empty:
                return None

            df.columns = df.columns.str.lower()
            return df

        except Exception as e:
            print(f"   ⚠️  Error {ticker}: {str(e)[:80]}")
            return None

    def calculate_technical_score(self, df: pd.DataFrame, spy_df: pd.DataFrame) -> Tuple[float, Dict]:
        """Calculate technical score (0-50 points)"""
        if len(df) < 50:
            return 0, {}

        total_score = 0
        details = {}

        # Momentum
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

        # Relative Strength
        if spy_df is not None and len(spy_df) >= 60:
            spy_3m = (spy_df['close'].iloc[-1] - spy_df['close'].iloc[-60]) / spy_df['close'].iloc[-60] * 100
            outperf = returns_3m - spy_3m

            if outperf > 10:
                total_score += 12
            elif outperf > 5:
                total_score += 9
            elif outperf > 0:
                total_score += 6

            details['vs_market'] = outperf

        # Trend
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

        # Volume
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

        # Risk/Reward
        recent_high = df['high'].iloc[-60:].max()
        dist_from_high = (recent_high - current_price) / current_price * 100

        if dist_from_high < 5:
            total_score += 5
        elif dist_from_high < 10:
            total_score += 3

        details['near_high'] = dist_from_high < 5

        return total_score, details

    def calculate_fundamental_score(self, fundamentals: Dict) -> Tuple[float, Dict]:
        """Calculate fundamental score (0-50 points)"""
        if not fundamentals:
            return 0, {}

        total_score = 0
        details = {}

        # Growth
        growth_score = 0
        rev_growth = fundamentals.get('revenue_growth', 0)
        if rev_growth > 20:
            growth_score += 8
        elif rev_growth > 15:
            growth_score += 6
        elif rev_growth > 10:
            growth_score += 4
        elif rev_growth > 5:
            growth_score += 2

        eps_growth = fundamentals.get('earnings_growth', 0)
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

        # Profitability
        profit_score = 0
        margin = fundamentals.get('profit_margin', 0)
        if margin > 30:
            profit_score += 6
        elif margin > 20:
            profit_score += 4
        elif margin > 10:
            profit_score += 2

        roe = fundamentals.get('roe', 0)
        if roe > 25:
            profit_score += 5
        elif roe > 15:
            profit_score += 3
        elif roe > 10:
            profit_score += 1

        roa = fundamentals.get('roa', 0)
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

        # Valuation
        valuation_score = 0
        pe = fundamentals.get('pe_ratio', 0)
        if pe > 0:
            if 15 < pe < 25:
                valuation_score += 6
            elif 10 < pe < 35:
                valuation_score += 4
            elif pe < 50:
                valuation_score += 2

            if eps_growth > 0:
                peg = pe / eps_growth
                if peg < 1:
                    valuation_score += 6
                elif peg < 1.5:
                    valuation_score += 4
                elif peg < 2:
                    valuation_score += 2
                details['peg_ratio'] = peg
            else:
                details['peg_ratio'] = 999

        total_score += valuation_score
        details['valuation_score'] = valuation_score
        details['pe_ratio'] = pe

        # Financial Health
        health_score = 0
        de = fundamentals.get('debt_to_equity', 0)
        if de < 0.3:
            health_score += 4
        elif de < 0.5:
            health_score += 3
        elif de < 1.0:
            health_score += 2
        elif de < 2.0:
            health_score += 1

        cr = fundamentals.get('current_ratio', 0)
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
        """Screen stock with real data"""
        df = self.get_stock_data(ticker, days=self.lookback_days)
        if df is None or len(df) < 50:
            return None

        fundamentals = RealFundamentalData.get_fundamentals(ticker)
        if fundamentals is None:
            return None

        technical_score, tech_details = self.calculate_technical_score(df, spy_df)
        fundamental_score, fund_details = self.calculate_fundamental_score(fundamentals)

        total_score = technical_score + fundamental_score

        return {
            'ticker': ticker,
            'total_score': total_score,
            'technical_score': technical_score,
            'fundamental_score': fundamental_score,
            'current_price': df['close'].iloc[-1],
            'revenue_growth': fund_details.get('revenue_growth', 0),
            'earnings_growth': fund_details.get('earnings_growth', 0),
            'profit_margin': fund_details.get('profit_margin', 0),
            'pe_ratio': fund_details.get('pe_ratio', 0),
            'peg_ratio': fund_details.get('peg_ratio', 999),
            'roe': fund_details.get('roe', 0),
            'debt_to_equity': fund_details.get('debt_to_equity', 0),
            'momentum': tech_details.get('momentum', 0),
            'vs_market': tech_details.get('vs_market', 0),
        }

    def screen_multiple(self, tickers: List[str]) -> pd.DataFrame:
        """Screen multiple stocks"""
        print(f"\n🔍 Screening {len(tickers)} stocks...")

        print(f"   Getting SPY data...")
        spy_df = self.get_stock_data('SPY', days=self.lookback_days)

        if spy_df is None:
            print(f"   ⚠️  Could not get SPY data, continuing without market comparison")

        results = []

        for i, ticker in enumerate(tickers, 1):
            print(f"   [{i}/{len(tickers)}] {ticker}...")
            result = self.screen_stock(ticker, spy_df)

            if result and result['total_score'] >= self.min_score:
                results.append(result)
                print(f"      ✅ Score: {result['total_score']:.0f}/100")

        print(f"\n   ✅ Done! Found {len(results)} stocks above {self.min_score}")

        if len(results) == 0:
            return pd.DataFrame()

        df = pd.DataFrame(results)
        df = df.sort_values('total_score', ascending=False)
        df = df.head(self.top_n)

        return df

    def print_results(self, df: pd.DataFrame):
        """Print results"""
        if df.empty:
            print("\n❌ No stocks found")
            return

        print("\n" + "="*90)
        print(f"🏆 TOP {len(df)} STOCKS")
        print("="*90)

        for idx, row in df.iterrows():
            print(f"\n🔹 {row['ticker']} - {row['total_score']:.0f}/100")
            print(f"   Price: ${row['current_price']:.2f}")
            print(f"   Technical: {row['technical_score']:.0f}/50 | Fundamental: {row['fundamental_score']:.0f}/50")
            print(f"   Revenue: {row['revenue_growth']:+.1f}% | Earnings: {row['earnings_growth']:+.1f}%")
            print(f"   P/E: {row['pe_ratio']:.1f} | ROE: {row['roe']:.1f}%")


if __name__ == "__main__":
    if not YFINANCE_AVAILABLE:
        print("\n❌ yfinance not installed")
        print("   Install: pip install yfinance")
        print("\n   OR use demo_screener.py instead (works offline)")
        exit(1)

    screener = RealDataScreener(
        lookback_days=180,
        min_score=40,
        top_n=10
    )

    universe = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'AMD', 'TSLA']

    print(f"\n📋 Stocks: {', '.join(universe)}")

    results = screener.screen_multiple(universe)
    screener.print_results(results)

    if not results.empty:
        results.to_csv('real_data_screener_results.csv', index=False)
        print(f"\n💾 Saved: real_data_screener_results.csv")
