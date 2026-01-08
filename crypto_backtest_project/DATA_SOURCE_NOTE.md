# IMPORTANT NOTE ON DATA SOURCE

## Data Used in This Project

Due to network restrictions in the execution environment, **real historical data from Yahoo Finance could not be downloaded**. The project uses **simulated data generated via Geometric Brownian Motion**.

### Attempted Real Data Download

The `download_crypto_data.py` script was designed to fetch real BTC-USD and ETH-USD data from Yahoo Finance API, but network access to `guce.yahoo.com` is blocked in this environment:

```
Failed to get ticker 'BTC-USD' reason: Failed to perform, curl: (6) 
Could not resolve host: guce.yahoo.com
```

### Simulated Data Characteristics

The simulated data used in this project:

**Bitcoin (BTC)**
- Initial price: $40,000
- Final price: $94,558 (+136.4%)
- Price range: $23,290 - $102,234
- 17,521 hourly candles (2 years)
- Generated with random seed 42

**Ethereum (ETH)**
- Initial price: $2,200
- Final price: $3,070 (+39.6%)
- Price range: $1,660 - $11,511
- 17,521 hourly candles (2 years)
- Generated with random seed 43

### Using Real Data in Production

To use this project with **real data**, follow these steps:

1. **Run the download script manually** on a system with internet access:
   ```bash
   python download_crypto_data.py --years 2
   ```

2. **Alternative data sources**:
   - Download from cryptocurrency exchanges (Binance, Coinbase, etc.)
   - Use exchange APIs directly
   - Export from TradingView
   - Use professional data providers (CryptoCompare, CoinGecko)

3. **Data format required**:
   ```
   datetime,open,high,low,close,volume
   2024-01-07 00:00:00,42000.0,42500.0,41800.0,42300.0,1500.5
   ```

4. **Replace files** in `crypto_backtest_project/data/`:
   - `BTC_1h_YYYYMMDD_YYYYMMDD.csv`
   - `ETH_1h_YYYYMMDD_YYYYMMDD.csv`

5. **Rerun backtests** with the same scripts:
   ```bash
   python run_final_backtest.py
   ```

## Impact on Results

⚠️ **Important Considerations:**

1. **Simulated vs Real**: Simulated data does not capture:
   - Real market microstructure
   - Actual volatility clustering
   - Real correlations and market events
   - Liquidity gaps and slippage

2. **Strategy Performance**: Results shown in this project are based on simulated data and should be **validated with real historical data** before any trading decisions.

3. **For Research Only**: These backtests are for **demonstration and research purposes**. Do not use these results for actual trading without validating on real data.

## Recommendations

✅ **Before live trading:**
1. Download 2+ years of real hourly data
2. Rerun all backtests with real data
3. Paper trade for at least 1-3 months
4. Monitor live vs backtest performance
5. Implement proper risk management

---

**Date**: 2026-01-06  
**Environment**: Sandboxed execution environment with restricted network access  
**Data Type**: Simulated (Geometric Brownian Motion)  
**Use Case**: Research, demonstration, and strategy development only
