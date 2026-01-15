# 🔍 Signal Analysis Feature - Trading App GUI

## What is Signal Analysis?

The Signal Analysis feature allows you to analyze historical trading signals (backtest) for BTC and ETH bots directly from the GUI. This helps you understand:

- **Were signals generated in a specific date range?**
- **How many BUY/SELL signals were found?**
- **What were the entry prices and conditions?**
- **Were signals generated in the last 2 days?**

## How to Use

### 1. Open Signal Analysis

1. Select a **BTC** or **ETH** bot from the bot list
2. Click the **🔍 Signal Analysis** button in the Controls section

### 2. Set Analysis Parameters

**Option 1: Use Days**
- Set the number of days (1-365) to analyze from today backwards
- Example: 7 days = analyze last 7 days

**Option 2: Use Date Range**
- Select a custom date range (From/To dates)
- Useful for analyzing specific periods

**Symbol:**
- Automatically selected based on your bot (BTC/USDT or ETH/USDT)

### 3. Run Analysis

1. Click **🔍 Analyze Signals** button
2. Wait while the app:
   - Downloads historical 1H data from Binance
   - Runs the PatternRecognitionStrategy (same as live bot)
   - Finds all trading signals in the period

### 4. View Results

**Summary Section:**
- Total signals found
- Number of BUY vs SELL signals
- First and last signal dates
- **Status for last 2 days** (important!)

**Signals Table:**
- Date/Time of each signal
- Signal type (BUY 📈 or SELL 📉)
- Entry price
- Stop Loss and Take Profit levels
- Entry reason (why signal was generated)
- Market regime (TREND or RANGE)

### 5. Export Results

Click **💾 Export CSV** to save the analysis results to a CSV file for further analysis in Excel.

---

## Understanding Results

### ✅ Signals Found in Last 2 Days
```
✅ Signals in last 2 days: 2
Bot is generating signals normally!
```
**Meaning:** Your bot is working correctly and generating signals.

### ⚠️ No Signals in Last 2 Days
```
⚠️ No signals in last 2 days
Last signal was 4 days ago
Market may be in consolidation
```
**Meaning:** Bot is working, but market conditions don't meet entry criteria. This is normal during consolidation periods.

### ❌ No Signals at All
```
❌ No signals found in this period
```
**Possible reasons:**
- Market was in consolidation (no clear patterns)
- Volatility was too low
- No breakouts or reversals detected
- Strategy filters may be too strict (if this persists for 14+ days)

---

## Technical Details

### What Strategy is Used?
The analysis uses the **exact same PatternRecognitionStrategy** that the live bot uses:
- Pattern recognition (flags, triangles, wedges, etc.)
- SMC (Smart Money Concepts) indicators
- Gold-optimized filters adapted for crypto
- **Market regime detection (TREND vs RANGE)**
- **Adaptive TP/SL levels based on market regime**

### TP/SL Levels (Multi-TP Mode)
The backtest now uses **the exact same TP/SL levels as the live bot**:

#### For Crypto (BTC/ETH):
- **TREND Mode:** TP1: 1.5% | TP2: 2.75% | TP3: 4.5%
- **RANGE Mode:** TP1: 1.0% | TP2: 1.75% | TP3: 2.5%

#### For XAUUSD (Gold):
- **TREND Mode:** TP1: 30 points | TP2: 55 points | TP3: 90 points  
- **RANGE Mode:** TP1: 20 points | TP2: 35 points | TP3: 50 points

The backtest automatically detects market regime for each signal using the same algorithm as the live bot.

### Data Source
- **Exchange:** Binance Futures (crypto) or MetaTrader5 (XAUUSD)
- **Timeframe:** Configurable (default: 1 Hour)
- **Symbol:** BTC/USDT, ETH/USDT, or XAUUSD

### Requirements
To use this feature, you need:
- Internet connection (to download data from Binance/MT5)
- Python packages: `ccxt`, `pandas`, `numpy`
- For XAUUSD: MetaTrader5 installed and running

---

## Troubleshooting

### "Missing Dependencies" Error
```bash
pip install ccxt pandas numpy
```

### "No internet connection" Error
- Check your internet connection
- Binance API may be down (try again later)
- Firewall may be blocking connection

### "No data downloaded" Error
- Check that the date range is valid
- Ensure dates are not in the future
- Try a shorter date range

### Analysis Takes Too Long
- Large date ranges (30+ days) take longer
- 7 days typically takes 10-30 seconds
- Be patient, the app is downloading and processing data

---

## Use Cases

### 1. Diagnose "No Signals" Issue
If your bot hasn't opened positions in a while:
1. Run analysis for last 7-14 days
2. Check if signals were actually generated
3. If yes → Bot is working, market is just quiet
4. If no → May need to review strategy settings

### 2. Validate Bot Before Going Live
Before switching to live trading:
1. Analyze last 30 days
2. See how many signals would have been generated
3. Review signal quality and entry prices
4. Decide if you're comfortable with the frequency

### 3. Compare Different Periods
1. Analyze during high volatility period
2. Analyze during low volatility period
3. Understand when the strategy performs best

### 4. Test Date-Specific Events
1. Set exact date range for a major market event
2. See how the bot would have behaved
3. Example: Bitcoin halving, major news events

---

## FAQ

**Q: Does this place real trades?**
A: No! This is analysis only. It shows what signals would have been generated, but doesn't execute any trades.

**Q: Why are results different from my actual bot?**
A: The analysis uses historical data. Your live bot may have:
- Different API connection timing
- Slightly different market data (exchange differences)
- Been offline during some signals

**Q: Can I analyze XAUUSD (Gold)?**
A: Not yet. Currently only BTC and ETH are supported. Gold analysis may be added in the future.

**Q: How far back can I analyze?**
A: Up to 365 days, but keep in mind:
- Longer periods take more time
- Binance historical data availability
- 7-30 days is usually sufficient

**Q: What's the difference between this and Statistics?**
A: 
- **Statistics** = Actual trades executed by your bot (history)
- **Signal Analysis** = Potential signals that would have been generated (backtest)

---

## Tips

💡 **Run weekly analysis** to ensure your bot is detecting signals

💡 **Compare to Statistics** to see if your bot is catching the signals

💡 **Export CSV** for detailed Excel analysis and record keeping

💡 **Use date ranges** to analyze specific market conditions

💡 **Check "last 2 days"** summary to quickly verify bot health

---

Created: 2026-01-10
Feature: Signal Analysis (Backtest) in Trading App GUI
