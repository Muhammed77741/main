# Backtest Results - January 5, 2026

## Executive Summary

Backtest был успешно запущен на имеющихся данных XAUUSD (Gold) используя стратегию **V13 - Fibonacci TP Only**.

### Key Highlights
- ✅ **Total PnL**: +40.37% (+1117.5 points)
- ✅ **Win Rate**: 55.3% (173 wins out of 313 trades)
- ✅ **Profit Factor**: 1.32
- 📊 **Data Period**: June 4, 2024 to January 2, 2026 (577 days, 9370 candles)
- 🎯 **Strategy**: V13 Fibonacci TP Only with SMC (Smart Money Concepts)

---

## Data Source

**File**: `XAUUSD_1H_MT5.csv`
- **Size**: 1.24 MB
- **Candles**: 9,370 hourly candles
- **Period**: 2024-06-04 to 2026-01-02
- **Duration**: 577 days (~19 months)
- **Market**: Gold (XAU/USD) hourly timeframe

---

## Strategy Description

**V13: Fibonacci TP Only Strategy**

### Core Concepts:
1. **Entry Signals**: All SMC (Smart Money Concepts) signals accepted
   - Break of Structure (BOS)
   - Order Blocks (OB)
   - Fair Value Gaps (FVG)
   - Volume confirmation

2. **Take Profit Levels**: Dynamic Fibonacci Extensions
   - TP1: 127.2% Fibonacci extension from swing range
   - TP2: 161.8% Fibonacci extension (Golden Ratio)
   - TP3: 200% Fibonacci extension

3. **Position Management**: Partial close strategy
   - 30% closed at TP1
   - 30% closed at TP2
   - 40% closed at TP3

4. **Risk Management**:
   - Trailing Stop Loss: 25/20/13 points (based on regime)
   - Timeout: 60/48/24 hours (based on regime and direction)
   - Maximum 5 concurrent positions

5. **Market Regime Detection**:
   - TREND: Strong directional movement
   - RANGE: Sideways consolidation

---

## Performance Metrics

### Overall Performance
| Metric | Value |
|--------|-------|
| **Total Trades** | 313 |
| **Winning Trades** | 173 (55.3%) |
| **Losing Trades** | 140 (44.7%) |
| **Total PnL** | **+40.37%** |
| **Total Points** | **+1,117.5 points** |
| **Average PnL per Trade** | +0.129% |
| **Average Win** | +0.97% |
| **Average Loss** | -0.90% |
| **Max Win** | +4.62% |
| **Max Loss** | -6.15% |
| **Profit Factor** | **1.32** |

### Duration Metrics
| Metric | Value |
|--------|-------|
| **Average Duration** | 55.2 hours (2.3 days) |
| **Minimum Duration** | 1.0 hour |
| **Maximum Duration** | 111.0 hours (4.6 days) |

---

## Fibonacci Strategy Performance

### Fibonacci TP Usage
- **Fibonacci TP Calculated**: 313 trades (71.6% of all signals)
- **V9 Fallback Used**: 0 trades (0%)
- **Filtered Signals**: 124 (28.4% of total 437 signals)

### TP Hit Rates
| Take Profit Level | Hit Rate | Percentage |
|-------------------|----------|------------|
| **TP1** (Fib 127.2%) | 27/313 | 8.6% |
| **TP2** (Fib 161.8%) | 9/313 | 2.9% |
| **TP3** (Fib 200.0%) | 1/313 | 0.3% |

**Analysis**: Low TP hit rates indicate that most trades exit via timeout or stop loss, suggesting that Fibonacci extension levels might be too ambitious for this market regime.

---

## Exit Analysis

### Exit Type Distribution
| Exit Type | Count | Percentage | Interpretation |
|-----------|-------|------------|----------------|
| **TIMEOUT** | 269 | 85.9% | Most trades hit time limit |
| **STOP LOSS (SL)** | 24 | 7.7% | Initial stop loss hit |
| **TRAILING SL** | 19 | 6.1% | Trailing stop activated after profit |
| **TP3** | 1 | 0.3% | Full target reached |

**Key Insight**: 85.9% of trades exit on timeout, suggesting the strategy needs either:
- Shorter timeout periods
- More realistic TP levels
- Better entry timing

---

## Direction Analysis

### Long vs Short Performance
| Direction | Trades | Win Rate | Total PnL | Avg PnL |
|-----------|--------|----------|-----------|---------|
| **LONG** | 284 | 55.3% | +39.83% | +0.140% |
| **SHORT** | 29 | 55.2% | +0.54% | +0.019% |

**Analysis**: 
- LONG trades dominate (90.7% of all trades)
- Both directions show similar win rates (~55%)
- LONG trades contribute almost all profits
- Strategy appears biased towards long opportunities

---

## Market Regime Analysis

### Trend vs Range Performance
| Regime | Trades | Win Rate | Total PnL | Interpretation |
|--------|--------|----------|-----------|----------------|
| **TREND** | 121 | 50.4% | -7.71% | Underperforming |
| **RANGE** | 192 | 58.3% | +48.08% | **Best performance** |

**Key Findings**:
- **Range markets** generate superior results (58.3% WR, +48.08%)
- **Trend markets** are barely breakeven (50.4% WR, -7.71%)
- 61.3% of trades occur in RANGE regime
- Strategy is optimized for range-bound conditions

---

## Risk/Reward Analysis

### Average Trade Metrics
- **Risk/Reward Ratio**: ~1.08:1 (0.97% avg win / 0.90% avg loss)
- **Win Rate Needed for Breakeven**: ~48.3%
- **Current Win Rate**: 55.3% ✅
- **Edge**: ~7% above breakeven

### Position Sizing Implications
With 2% risk per trade:
- Average winning trade: +0.97% account
- Average losing trade: -0.90% account
- Net expectancy per trade: +0.129% account

---

## Monthly Performance Projection

Based on 313 trades over 577 days:

- **Average trades per day**: 0.54
- **Average trades per month** (30 days): ~16.3 trades
- **Expected monthly PnL**: +2.1% (16.3 trades × 0.129%)
- **Annualized return**: ~28% (assuming similar conditions)

**Note**: This is a historical projection and doesn't account for:
- Market regime changes
- Slippage variations
- Execution quality
- Drawdown periods

---

## Strengths of the Strategy

1. ✅ **Positive Win Rate**: 55.3% is above 50%, providing statistical edge
2. ✅ **Good Profit Factor**: 1.32 shows profitable system
3. ✅ **Range Market Performance**: Excellent in sideways markets (+48.08%)
4. ✅ **Consistent Direction**: Both LONG and SHORT show similar win rates
5. ✅ **Risk Management**: Trailing stops and timeouts prevent catastrophic losses

---

## Areas for Improvement

1. ⚠️ **TP Hit Rates**: Very low (8.6%, 2.9%, 0.3%) suggest targets are too aggressive
2. ⚠️ **Timeout Dependency**: 85.9% of exits via timeout indicates:
   - Fibonacci extensions might be unrealistic
   - Consider more conservative TP levels
3. ⚠️ **Trend Market Performance**: Strategy struggles in trending conditions (-7.71%)
4. ⚠️ **Max Loss**: -6.15% is relatively large compared to average win
5. ⚠️ **Holding Time**: Average 55 hours might be too long for some traders

---

## Recommendations

### Immediate Actions:
1. **Optimize TP Levels**: Consider using more conservative Fibonacci levels
   - Current: 127.2%, 161.8%, 200%
   - Suggested: 100%, 127.2%, 161.8%

2. **Reduce Timeout**: Current 60/48/24h might be too long
   - Test with 36/30/18h to force earlier exits

3. **Trend Filter Enhancement**: Improve trend market performance
   - Consider skipping trend market entries
   - Or use different parameters for trend vs range

4. **Position Sizing**: Adjust for market regime
   - Larger positions in RANGE markets
   - Smaller positions in TREND markets

### Further Testing:
1. Run walk-forward analysis on different time periods
2. Test on other instruments (EURUSD, BTCUSD, etc.)
3. Optimize Fibonacci levels with grid search
4. Compare with V9 (fixed TP) and V12 (Fibonacci entry filtering)

---

## File Outputs

### Generated Files:
1. **`backtest_results_20260105.csv`** - Detailed trade log with 313 trades
   - Columns: entry_time, exit_time, direction, regime, tp_source, swing_range, prices, TP hits, exit_type, PnL, duration

2. **`run_backtest.py`** - Unified backtest runner script
   - Features:
     - Auto-detects data files
     - Handles multiple CSV encodings
     - Comprehensive statistics
     - Easy to use CLI interface

---

## How to Run Again

### List available data files:
```bash
python3 run_backtest.py --list
```

### Run on default (largest) file:
```bash
python3 run_backtest.py
```

### Run on specific file:
```bash
python3 run_backtest.py --file XAUUSD_MT5_20240425_20260102.csv
```

### Specify output file:
```bash
python3 run_backtest.py --output my_results.csv
```

---

## Conclusion

Backtest на имеющихся данных был успешно выполнен! 

**Основные результаты:**
- ✅ Стратегия показывает положительную доходность (+40.37%)
- ✅ Win rate выше 50% (55.3%)
- ✅ Особенно хорошо работает в боковых рынках
- ⚠️ Требует оптимизации для трендовых условий
- ⚠️ Низкие hit rates на TP указывают на необходимость корректировки целей

Стратегия имеет потенциал, но требует дополнительной оптимизации перед использованием в live trading.

---

## Technical Details

### Environment:
- Python 3.12
- pandas 2.3.3
- numpy 2.4.0

### Strategy Parameters:
- Spread: 2.0 points
- Commission: 0.5 points
- Swap: -0.3 points per day
- Max concurrent positions: 5
- SHORT in RANGE: Disabled

### Execution Details:
- Date: January 5, 2026
- Runtime: ~90 seconds
- Total signals detected: 437
- Trades executed: 313 (71.6%)
- Trades filtered: 124 (28.4%)

---

*Report generated by unified backtest runner*
*Strategy: V13 Fibonacci TP Only*
*Data: XAUUSD 1H MT5*
