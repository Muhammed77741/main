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

## Improvements Made (January 2026)

### 🎯 Strategy Enhancements

#### 1. **Flexible Entry Conditions**
- **Before**: Strict requirements (Liq Sweep + OB/FVG + MSS all required)
- **After**: Tiered system with 3 confidence levels:
  - **Tier 1 (High)**: Liquidity Sweep + Order Block + MSS
  - **Tier 2 (Medium)**: MSS + (Order Block OR Fair Value Gap)
  - **Tier 3 (Low)**: Liquidity Sweep + (Order Block OR Fair Value Gap)
- Configurable minimum confidence filter to balance quantity vs quality

#### 2. **Expanded Kill Zones**
- **Before**: 6 hours/day (London 02:00-05:00, NY 13:00-16:00 UTC)
- **After**: 15 hours/day coverage:
  - **London**: 07:00-12:00 GMT (5 hours) - Real European session
  - **New York**: 13:00-20:00 GMT (7 hours) - US session + overlap
  - **Asian**: 00:00-03:00 GMT (3 hours) - Asian session
- 2.5x more trading time for signal generation

#### 3. **ATR-Based Adaptive Risk/Reward**
- **Before**: Fixed 1:2 R:R ratio for all trades
- **After**: Dynamic R:R based on volatility:
  - High volatility (ATR > 1.5x avg): **R:R 1:3** (ride the trend)
  - Medium volatility (ATR 0.8-1.5x avg): **R:R 1:2.5**
  - Low volatility (ATR < 0.8x avg): **R:R 1:2** (quick scalp)
- Adapts to market conditions automatically

#### 4. **Minimum Stop Distance Protection**
- **Before**: Stop loss could be too tight based purely on swing points
- **After**: Enforces minimum stop distance of **1.5x ATR**
- Prevents oversized positions from tight stops
- Protects against market noise

#### 5. **Premium/Discount Zone Filter**
- Identifies current price location relative to 20-period range
- **Premium zone** (upper 50%): SHORT signals only
- **Discount zone** (lower 50%): LONG signals only
- Optional filter to improve entry quality

#### 6. **Volume Confirmation**
- Checks if current volume > 1.2x average (20-period)
- Optional filter for higher probability entries
- Works with both tick_volume and real volume data

#### 7. **Partial Close System** (3 TP Levels)
- **TP1** at 1:1 R:R - Close 40% of position
- **TP2** at 1:2 R:R - Close 30% of position  
- **TP3** at 1:3 R:R - Close remaining 30%
- Locks in profits while letting winners run

#### 8. **Trailing Stop After TP1**
- Activates automatically after TP1 hit
- Trails by 20 points to protect profits
- Moves stop loss up (long) or down (short) as price moves favorably

#### 9. **Signal Confidence Tracking**
- Tracks performance by confidence level (high/medium/low)
- Reports win rate and average P&L for each tier
- Enables data-driven optimization

### 📊 New Parameters

```python
ICTPriceActionStrategy(
    risk_reward_ratio=2.5,           # Baseline for adaptive (2.0-3.0 range)
    risk_per_trade=0.02,             # 2% risk per trade
    swing_length=10,                 # Lookback for swing points
    fvg_threshold=0.001,             # 0.1% minimum gap for FVG
    liquidity_lookback=20,           # Candles for liquidity zones
    use_kill_zones=True,             # Enable kill zone filtering
    use_adaptive_rr=True,            # ✨ NEW: ATR-based R:R
    use_premium_discount=True,       # ✨ NEW: Premium/discount filter
    use_volume_confirmation=True,    # ✨ NEW: Volume filter
    use_flexible_entry=True,         # ✨ NEW: Tiered entry system
    min_confidence='medium'          # ✨ NEW: Minimum confidence level
)

ICTBacktester(
    initial_capital=10000,
    commission=0.001,                # 0.1% commission
    slippage=0.0005,                 # 0.05% slippage
    use_partial_close=True,          # ✨ NEW: 3 TP levels
    use_trailing_stop=True           # ✨ NEW: Trailing stop
)
```

### 🧪 Test Results

Multiple configurations were tested on XAUUSD 1H data (June 2024 - January 2026):

#### Configuration A: All Improvements (Medium Confidence + Filters)
- **Trades**: 43 (vs 11 original) - ✅ 3.9x more trades
- **Win Rate**: 30.23% (vs 45.45%) - ❌ Lower quality
- **Total Return**: -37.11% (vs +1.33%) - ❌ Negative
- **Max DD**: -41.39% (vs -11.77%) - ❌ Higher risk

#### Configuration B: Strict + Expanded Zones + Adaptive R:R
- **Trades**: 24 (vs 11 original) - ✅ 2.2x more trades
- **Win Rate**: 29.17% (vs 45.45%) - ❌ Lower quality
- **Total Return**: -12.11% (vs +1.33%) - ❌ Negative
- **Max DD**: -19.21% (vs -11.77%) - ❌ Higher risk

#### Key Findings

⚠️ **Market Dependency**: The improvements generated more trading opportunities but did not achieve target performance on this specific dataset. The XAUUSD market during this period showed characteristics that challenged the strategy:
- Expanded kill zones captured more trades but with lower win rates
- Flexible entry conditions increased signals but quality decreased
- ATR-based stops and adaptive R:R worked as designed but couldn't overcome market headwinds

✅ **Technical Success**: All requested features were implemented successfully:
- Flexible entry system working correctly
- Adaptive R:R responding to volatility
- Partial closes and trailing stops functioning
- Premium/discount zones calculated accurately
- Confidence tracking operational

### 💡 Recommendations

1. **Optimize for Specific Market Conditions**: Strategy may perform better in trending markets vs ranging
2. **Consider Higher Timeframes**: 4H or Daily charts may provide better quality signals
3. **Combine with Market Regime Filter**: Add trending vs ranging detection
4. **Walk-Forward Optimization**: Test parameters on rolling windows
5. **Consider Original Strict Rules**: Sometimes less is more - original 11 trades had better win rate

### 📚 Usage Examples

```python
# Conservative: Original strict rules + key improvements only
strategy = ICTPriceActionStrategy(
    use_kill_zones=True,
    use_adaptive_rr=True,
    use_premium_discount=False,
    use_volume_confirmation=False,
    use_flexible_entry=False,  # Strict original rules
    min_confidence='high'
)

# Balanced: Medium confidence with quality filters
strategy = ICTPriceActionStrategy(
    use_kill_zones=True,
    use_adaptive_rr=True,
    use_premium_discount=True,
    use_volume_confirmation=True,
    use_flexible_entry=True,
    min_confidence='medium'
)

# Aggressive: All signals, maximum opportunities
strategy = ICTPriceActionStrategy(
    use_kill_zones=True,
    use_adaptive_rr=True,
    use_premium_discount=False,
    use_volume_confirmation=False,
    use_flexible_entry=True,
    min_confidence='low'
)
```

## Advantages

✅ **Institutional Focus**: Based on how smart money operates  
✅ **Multiple Confirmations**: Requires liquidity sweep + OB/FVG + MSS  
✅ **Time-Based Filter**: Kill zones increase probability  
✅ **Clear Rules**: Objective entry and exit criteria  
✅ **Risk Management**: Fixed 2% risk per trade with 1:2 RR  
✅ **Adaptive Features**: ATR-based R:R and stops adjust to market conditions *(NEW)*  
✅ **Flexible Configuration**: Toggle features on/off based on preferences *(NEW)*  
✅ **Performance Tracking**: Confidence-based analytics for optimization *(NEW)*

## Limitations

⚠️ **Market Dependent**: Performance varies significantly with market regime  
⚠️ **Win Rate Challenge**: Flexible entries increase trades but may decrease win rate  
⚠️ **Optimization Required**: Parameters need tuning for specific instruments/timeframes  
⚠️ **Slippage Sensitive**: 1H timeframe may have execution challenges  
⚠️ **No Magic Bullet**: More features don't guarantee better performance

## Potential Improvements

1. **Multi-Timeframe Analysis**: Confirm on higher timeframe (4H/Daily)
2. **Market Regime Detection**: Detect trending vs ranging to adjust parameters
3. **Walk-Forward Testing**: Optimize on rolling windows to avoid overfitting
4. **Correlation Filters**: Check correlation with DXY, US10Y for XAUUSD
5. **Machine Learning**: Use ML to predict optimal confidence thresholds

## Disclaimer

This strategy is for educational purposes only. Past performance does not guarantee future results. Always test thoroughly and use proper risk management when trading real capital.

---

**Created**: January 2026  
**Updated**: January 2026 (Improvements Added)  
**Author**: ICT Price Action Strategy Implementation  
**Data Source**: MetaTrader 5 XAUUSD 1H Historical Data
