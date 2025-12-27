# MTF S/R Retest Strategy - Final Results

## Strategy Comparison (Jan-Nov 2025, 11 months)

### Original Multi-Signal Strategy
- **Total PnL:** +28.53%
- **Win Rate:** 62.0%
- **Total Trades:** 387
- **Avg PnL/Trade:** +0.07%
- **Profitable Months:** 6/11 (55%)
- **Best Months:** Oct (+14.13%), Aug (+7.92%), Jan (+6.49%)

### MTF S/R Retest Strategy
- **Total PnL:** +7.32%
- **Win Rate:** 37.3%
- **Total Trades:** 383
- **Avg PnL/Trade:** +0.02%
- **Profitable Months:** 3/11 (27%)
- **Best Months:** Aug (+17.97%), Apr (+10.48%), Nov (+7.40%)

## Key Findings

### MTF Strategy Parameters (Optimized)
```python
swing_window = 8              # Find swing points
max_zones = 6                 # Keep 6 strongest zones
zone_width_pct = 0.004        # 0.4% zone width
min_touches = 3               # Minimum 3 swing touches
max_touches = 15              # Maximum 15 touches
min_retest_score = 4          # Confluence score 4+
retest_cooldown_hours = 6     # 6h between retests
```

### Performance by Zone Strength
Best performing signal types:
- **resistance_retest_8T:** 50.0% WR, +12.01%
- **support_retest_6T:** 48.9% WR, +9.17%
- **resistance_retest_7T:** 44.4% WR, +7.59%

Worst performing:
- **support_retest_5T:** 25.0% WR, -11.47%
- **support_retest_7T:** 35.3% WR, -5.89%
- **resistance_retest_10T:** 30.6% WR, -5.32%

## Conclusion

**Winner: ORIGINAL MULTI-SIGNAL STRATEGY**

The Original Multi-Signal strategy significantly outperforms the MTF S/R Retest strategy:
- ✅ **21.21% more profit** (+28.53% vs +7.32%)
- ✅ **Higher win rate** (62.0% vs 37.3%)
- ✅ **More consistent** (6 vs 3 profitable months)

### Why MTF Underperforms

1. **Inconsistent Zone Quality:** Zones with similar touch counts (5-10) show vastly different results
2. **Low Overall Win Rate:** 37.3% WR means strategy loses more often than it wins
3. **Poor Monthly Consistency:** Only 3/11 profitable months vs 6/11 for Original
4. **Higher Losses:** Average loss -0.56% vs -0.52% for Original

### Recommendation

**Stick with Original Multi-Signal Strategy** - it provides:
- Higher profitability
- Better consistency
- Lower risk (higher win rate)
- More reliable monthly results

The MTF S/R Retest approach, while theoretically sound, doesn't perform well on 1H gold data. The concept of trading S/R retests works better on higher timeframes (4H, Daily) where zones are more significant and retests are less frequent but higher quality.
