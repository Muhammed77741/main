# ICT Price Action Strategy

## Overview

This is an implementation of the **ICT (Inner Circle Trader) Price Action Strategy** - a trading methodology based on institutional trading concepts and smart money movements.

## Core ICT Concepts Implemented

### 1. **Liquidity Sweeps (Stop Hunts)**
- Identifies areas where smart money "hunts" retail trader stops
- Bullish Sweep: Price takes out recent lows then closes higher (bearish stops hunted)
- Bearish Sweep: Price takes out recent highs then closes lower (bullish stops hunted)
- These sweeps often precede reversals as institutions accumulate positions

### 2. **Order Blocks (OB)**
- Last opposing candle before a strong directional move
- Represents institutional entry zones
- Bullish OB: Down candle before strong up move
- Bearish OB: Up candle before strong down move
- Price often returns to these zones for re-entry

### 3. **Fair Value Gaps (FVG)**
- Price imbalances/inefficiencies in the market
- Created when price moves too quickly, leaving "gaps" in liquidity
- Bullish FVG: Gap between candle[i-2].high and candle[i].low
- Bearish FVG: Gap between candle[i-2].low and candle[i].high
- Market tends to "fill" these gaps over time

### 4. **Market Structure Shifts (MSS)**
- Also called "Change of Character" (ChoCh)
- Indicates trend changes in market structure
- Bullish MSS: Break above previous swing high
- Bearish MSS: Break below previous swing low
- Confirms the direction for entries

### 5. **Kill Zones**
- Optimal trading times when institutional traders are most active
- **London Kill Zone**: 02:00 - 05:00 UTC
- **New York Kill Zone**: 13:00 - 16:00 UTC (07:00 - 10:00 ET)
- Higher probability of successful trades during these times

### 6. **Power of 3**
- Institutional trading phases: Accumulation → Manipulation → Distribution
- Not explicitly coded but reflected in the liquidity sweep → order block → reversal pattern

## Strategy Rules

### Entry Conditions (Long)
1. ✅ Bullish Liquidity Sweep detected
2. ✅ Bullish Order Block OR Fair Value Gap present
3. ✅ Bullish Market Structure Shift confirmed
4. ✅ Entry during Kill Zone (London or New York)

### Entry Conditions (Short)
1. ✅ Bearish Liquidity Sweep detected
2. ✅ Bearish Order Block OR Fair Value Gap present
3. ✅ Bearish Market Structure Shift confirmed
4. ✅ Entry during Kill Zone (London or New York)

### Risk Management
- **Risk per Trade**: 2% of account balance
- **Risk/Reward Ratio**: 1:2 (minimum)
- **Stop Loss**: Below recent swing low (long) / Above recent swing high (short) with 0.2% buffer
- **Take Profit**: 2x the risk distance from entry

## Version 2 Improvements (CRITICAL FIXES)

### Changes Made:
1. ✅ **Flexible Entry Conditions**: Multi-level confidence scoring
   - Core requirement: Liq Sweep + (OB or FVG) + MSS (unchanged from V1)
   - High confidence: All 4 indicators present (Sweep + OB + FVG + MSS)
   - Medium confidence: 3 indicators present
   - Confidence tracking added for future optimization
   
2. ✅ **Extended Kill Zones**: 6h → 15h trading time
   - Asian: 00:00-03:00 GMT (3h) - NEW
   - London: 07:00-12:00 GMT (5h) - extended from 02:00-05:00
   - New York: 13:00-20:00 GMT (7h) - extended from 13:00-16:00
   - Result: 2.5x more trading opportunities

3. ✅ **Adaptive R:R by ATR**: Dynamic targets based on volatility
   - High volatility (>1.5x avg): 1:2.5
   - Normal volatility: 1:2.0
   - Low volatility: 1:1.8
   - More realistic than fixed 1:2 ratio

4. ✅ **Position Sizing Safety**: Prevent over-leveraging
   - Maximum position value capped at 50% of account
   - Prevents catastrophic losses from tight stop losses
   
5. ⚠️ **Premium/Discount Filter**: Not implemented in final version
   - Testing showed it reduced win rate without improving returns
   - Code present but not active - can be enabled for testing

### Actual Results (Version 2):

**Test Period**: June 2024 - January 2026 (9,371 hourly candles, same as V1)

| Metric | V1 (Original) | V2 (Improved) | Change |
|--------|---------------|---------------|---------|
| **Total Trades** | 11 | 28 | +155% ✅ |
| **Win Rate** | 45.45% | 32.14% | -29% ⚠️ |
| **Total Return** | +1.33% | -1.85% | -3.18% ⚠️ |
| **Max Drawdown** | -11.77% | -4.37% | +63% better ✅ |
| **Profit Factor** | 1.08 | 0.83 | -23% ⚠️ |
| **Avg Win** | $344.52 | $102.79 | -70% |
| **Avg Loss** | -$264.86 | -$58.44 | +78% better ✅ |
| **Sharpe Ratio** | 0.03 | -0.07 | Worse |

### Analysis:

**Improvements:**
- ✅ **2.5x more trades**: Extended kill zones working as intended
- ✅ **Lower drawdown**: Better risk management with position size caps
- ✅ **Smaller losses**: Adaptive R:R and safer position sizing

**Issues:**
- ⚠️ **Lower win rate**: Entry conditions need refinement
- ⚠️ **Slightly negative**: Not profitable but close to break-even
- ⚠️ **Lower profit factor**: Wins smaller than V1

### Recommendations for V3:
1. Add filter to improve entry quality (e.g., trend alignment)
2. Consider partial profit taking to improve win rate
3. Test premium/discount zones with different parameters
4. Optimize ATR period and R:R thresholds
5. Add volume confirmation or other confluence factors

### Important Notes:

**Reality Check**: The problem statement expected 150+ trades with 60%+ win rate and 150%+ profit. However, after implementing all requested improvements, the actual results show:
- Extended kill zones successfully increased trades by 2.5x
- Risk management improvements reduced maximum losses significantly
- Entry quality remains the core challenge

**What Worked**:
- ✅ Extended kill zones (3x more trading hours)
- ✅ Adaptive R:R based on volatility
- ✅ Position size limits prevent catastrophic losses
- ✅ Confidence scoring for future filtering

**What Didn't Work**:
- ⚠️ Premium/discount filter reduced trade count without improving quality
- ⚠️ More flexible entries led to worse win rate
- ⚠️ The fundamental strategy needs additional confluence factors

**Conclusion**: The improvements successfully addressed the technical requirements (more trades, better risk management, adaptive targets) but the ICT methodology itself requires additional filters or optimization to achieve profitability on this specific XAUUSD 1H dataset. The strategy benefits from extended trading hours but needs better entry selection criteria beyond the basic ICT concepts implemented here.

## Backtest Results (XAUUSD 1H Data)

**Test Period**: June 2024 - January 2026 (9,371 hourly candles)

### Performance Metrics
- **Total Trades**: 11
- **Win Rate**: 45.45% (5 wins, 6 losses)
- **Total Return**: +1.33% ($133.46 profit on $10,000 capital)
- **Profit Factor**: 1.08
- **Average Win**: $344.52
- **Average Loss**: -$264.86
- **Max Drawdown**: -11.77%
- **Sharpe Ratio**: 0.03

### Trade Breakdown
The strategy generated 21 signals, resulting in 11 executed trades:
- 5 Take Profit exits (TP)
- 6 Stop Loss exits (SL)

**Best Trade**: SHORT on 2024-07-17 → +$376.90 (+2.70%)  
**Worst Trade**: LONG on 2025-01-17 → -$368.41 (-0.56%)

### Kill Zone Performance
- **New York Kill Zone**: 9 trades
- **London Kill Zone**: 2 trades

All trades were filtered to occur only during these optimal institutional trading times.

## Files

- `ict_price_action_strategy.py` - Main strategy implementation
- `backtest_ict_strategy.py` - Backtesting engine and execution script
- `ict_strategy_trades.csv` - Detailed trade log
- `ict_strategy_backtest_results.png` - Visual results (equity curve, trades, P&L)

## Usage

```python
from ict_price_action_strategy import ICTPriceActionStrategy

# Initialize strategy
strategy = ICTPriceActionStrategy(
    risk_reward_ratio=2.0,
    risk_per_trade=0.02,
    swing_length=10,
    fvg_threshold=0.001,
    liquidity_lookback=20,
    use_kill_zones=True
)

# Generate signals on your data
df_with_signals = strategy.generate_signals(df)

# Get entry parameters for a signal
entry_params = strategy.get_entry_parameters(df_with_signals, signal_idx, account_balance)
```

## Running the Backtest

```bash
cd smc_trading_strategy
python3 backtest_ict_strategy.py
```

## Strategy Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `risk_reward_ratio` | 2.0 | Risk/Reward ratio (1:2) |
| `risk_per_trade` | 0.02 | Risk 2% per trade |
| `swing_length` | 10 | Lookback for swing points |
| `fvg_threshold` | 0.001 | Minimum 0.1% gap for FVG |
| `liquidity_lookback` | 20 | Candles to check for liquidity |
| `use_kill_zones` | True | Trade only in kill zones |

## Advantages

✅ **Institutional Focus**: Based on how smart money operates  
✅ **Multiple Confirmations**: Requires liquidity sweep + OB/FVG + MSS  
✅ **Time-Based Filter**: Kill zones increase probability  
✅ **Clear Rules**: Objective entry and exit criteria  
✅ **Risk Management**: Fixed 2% risk per trade with 1:2 RR

## Limitations

⚠️ **Low Frequency**: Conservative filters result in fewer trades (11 in 1.5 years)  
⚠️ **Win Rate**: 45.45% requires excellent RR to be profitable  
⚠️ **Drawdown**: -11.77% max drawdown on limited sample  
⚠️ **Slippage Sensitive**: 1H timeframe may have execution challenges

## Potential Improvements

1. **Multi-Timeframe Analysis**: Confirm on higher timeframe (4H/Daily)
2. **Session Refinement**: Optimize kill zone hours for XAUUSD specifically
3. **Additional Filters**: Add volume profile, premium/discount zones
4. **Dynamic Position Sizing**: Scale based on confidence/confluence
5. **Partial Profits**: Take partial profits at 1:1 to improve win rate

## Disclaimer

This strategy is for educational purposes only. Past performance does not guarantee future results. Always test thoroughly and use proper risk management when trading real capital.

---

**Created**: January 2026  
**Author**: ICT Price Action Strategy Implementation  
**Data Source**: MetaTrader 5 XAUUSD 1H Historical Data
