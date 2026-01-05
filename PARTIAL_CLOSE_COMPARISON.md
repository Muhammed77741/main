# Backtest Results Comparison - Partial Close Optimization

## Configuration Change

**Old (V9 default):** 30% / 30% / 40%
**New (User request):** 40% / 30% / 30%

### Rationale:
- TP1 increased from 30% to 40% to capture more profit on the first target
- TP2 kept at 30%
- TP3 reduced from 40% to 30% (closes remaining position)

---

## Results Comparison

### Overall Performance

| Metric | Old (30/30/40) | New (40/30/30) | Difference |
|--------|----------------|----------------|------------|
| **Total PnL** | +40.37% | +40.40% | +0.03% ✅ |
| **Total Points** | +1,117.5п | +1,118.8п | +1.3п ✅ |
| **Win Rate** | 55.3% | 55.3% | 0% ➖ |
| **Total Trades** | 313 | 313 | 0 ➖ |
| **Profit Factor** | 1.32 | 1.32 | 0 ➖ |
| **Average PnL** | +0.129% | +0.129% | 0% ➖ |
| **Average Win** | +0.97% | +0.97% | 0% ➖ |
| **Average Loss** | -0.90% | -0.90% | 0% ➖ |
| **Max Win** | +4.62% | +4.64% | +0.02% ✅ |
| **Max Loss** | -6.15% | -6.15% | 0% ➖ |

### TP Hit Rates

| TP Level | Old (30/30/40) | New (40/30/30) | Impact |
|----------|----------------|----------------|--------|
| **TP1** (127.2%) | 8.6% | 8.6% | Same |
| **TP2** (161.8%) | 2.9% | 2.9% | Same |
| **TP3** (200.0%) | 0.3% | 0.3% | Same |

### Exit Types

| Exit Type | Old (30/30/40) | New (40/30/30) | Change |
|-----------|----------------|----------------|--------|
| **TIMEOUT** | 85.9% | 85.9% | Same |
| **SL** | 7.7% | 7.7% | Same |
| **TRAILING_SL** | 6.1% | 6.1% | Same |
| **TP3** | 0.3% | 0.3% | Same |

### Direction Breakdown

#### LONG Trades
| Metric | Old (30/30/40) | New (40/30/30) | Difference |
|--------|----------------|----------------|------------|
| Win Rate | 55.3% | 55.3% | 0% |
| Total PnL | +39.83% | +39.86% | +0.03% ✅ |

#### SHORT Trades
| Metric | Old (30/30/40) | New (40/30/30) | Difference |
|--------|----------------|----------------|------------|
| Win Rate | 55.2% | 55.2% | 0% |
| Total PnL | +0.54% | +0.54% | 0% |

### Regime Breakdown

#### TREND Markets
| Metric | Old (30/30/40) | New (40/30/30) | Difference |
|--------|----------------|----------------|------------|
| Win Rate | 50.4% | 50.4% | 0% |
| Total PnL | -7.71% | -7.62% | +0.09% ✅ |

#### RANGE Markets
| Metric | Old (30/30/40) | New (40/30/30) | Difference |
|--------|----------------|----------------|------------|
| Win Rate | 58.3% | 58.3% | 0% |
| Total PnL | +48.08% | +48.02% | -0.06% ⚠️ |

---

## Analysis

### Impact of Change

The change from 30/30/40 to 40/30/30 partial close has **minimal impact** on overall performance:

✅ **Positive Changes:**
- Slightly higher total PnL: +40.40% vs +40.37% (+0.03%)
- Slightly better in TREND markets: -7.62% vs -7.71% (+0.09%)
- Marginally higher max win: +4.64% vs +4.62%

⚠️ **Negative Changes:**
- Slightly worse in RANGE markets: +48.02% vs +48.08% (-0.06%)

➖ **No Change:**
- Win rate, profit factor, and trade count remain identical
- TP hit rates unchanged (still very low at 8.6%/2.9%/0.3%)
- Exit type distribution unchanged (still 85.9% timeout)

### Why So Little Difference?

The **minimal impact** (+0.03% PnL difference) is because:

1. **Low TP Hit Rates**: Only 8.6% of trades reach TP1, so the partial close percentages rarely matter
2. **Timeout Dominates**: 85.9% of trades exit on timeout, bypassing TP levels entirely
3. **Same Total**: Both configurations close 100% total (just distributed differently)

### Recommendation

The 40/30/30 configuration is **slightly better** but the difference is negligible. The real issue is:

⚠️ **Core Problem**: Fibonacci TP levels are too aggressive (127.2%/161.8%/200%)
- Consider lowering to more realistic levels (e.g., 100%/127.2%/161.8%)
- This would increase TP hit rates and make partial close percentages more impactful

### User's Concern About TP3

The user asked: "Shouldn't TP3 close 100% instead of 40%?"

**Answer**: Both configurations close 100% total:
- Old: 30% + 30% + 40% = 100%
- New: 40% + 30% + 30% = 100%

The confusion might be about what "40% at TP3" means:
- It means "close 40% of the **original** position size"
- After TP1 (40%) and TP2 (30%), there's 30% remaining
- TP3 closes this remaining 30%, which is 100% of what's left

---

## Conclusion

✅ **Change Implemented**: Partial close changed from 30/30/40 to 40/30/30
✅ **Results**: Minimal improvement (+0.03% PnL)
⚠️ **Real Issue**: TP levels too aggressive (hit rates 8.6%/2.9%/0.3%)

The new configuration is slightly better and aligns with the user's preference for taking more profit at TP1.

---

*Generated: January 5, 2026*
*Strategy: V13 Fibonacci TP Only*
*Data: XAUUSD 1H (9,370 candles, 577 days)*
