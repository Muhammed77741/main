# 3-Position Multi-TP Feature - Visual Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     SIGNAL GENERATED (e.g., BUY)                        │
│                     Entry: $50,000                                       │
│                     SL: $49,600 (-0.8%)                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                        ┌───────────────────────┐
                        │  3 POSITIONS CREATED  │
                        └───────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌────────────┐  ┌────────────┐  ┌────────────┐
            │ POSITION 1 │  │ POSITION 2 │  │ POSITION 3 │
            └────────────┘  └────────────┘  └────────────┘
            Target: TP1     Target: TP2     Target: TP3
            $50,750 (+1.5%) $51,375 (+2.75%) $52,250 (+4.5%)
            Trailing: ❌     Trailing: ✅     Trailing: ✅
            
                    │               │               │
                    │               │               │
                    ▼               ▼               ▼
                    
            ┌──────────────────────────────────────────────┐
            │         PRICE ACTION TIMELINE                 │
            └──────────────────────────────────────────────┘
            
Bar 1-10:   Price climbs from $50,000 → $50,700
            All positions OPEN 🟢

Bar 11:     Price touches $50,750 (TP1 HIT!)
            ┌─────────────────────────────────────┐
            │ Position 1: CLOSES at TP1 ✅        │
            │   Profit: +1.5%                     │
            │   Close Reason: TP1                 │
            └─────────────────────────────────────┘
            
            Position 2: Still OPEN 🟢
              → Trailing ACTIVATED
              → Trailing Stop: $50,375
            
            Position 3: Still OPEN 🟢
              → Trailing ACTIVATED
              → Trailing Stop: $50,375

Bar 12-15:  Price climbs to $50,950
            Position 2: Still OPEN 🟢
              → Max Price: $50,950
              → Trailing Stop Updates: $50,475
            
            Position 3: Still OPEN 🟢
              → Max Price: $50,950
              → Trailing Stop Updates: $50,475

Bar 16:     Price reverses to $50,500
            Position 2: Still OPEN 🟢
              → Trailing Stop: $50,475 (not hit)
            
            Position 3: Still OPEN 🟢
              → Trailing Stop: $50,475 (not hit)

Bar 17:     Price climbs to $51,400 (TP2 HIT!)
            ┌─────────────────────────────────────┐
            │ Position 2: CLOSES at TP2 ✅        │
            │   Profit: +2.75%                    │
            │   Close Reason: TP2                 │
            └─────────────────────────────────────┘
            
            Position 3: Still OPEN 🟢
              → Max Price: $51,400
              → Trailing Stop Updates: $50,700

Bar 18-20:  Price consolidates around $51,200
            Position 3: Still OPEN 🟢
              → Trailing Stop: $50,700

Bar 21:     Price drops to $50,650
            ┌─────────────────────────────────────┐
            │ Position 3: CLOSES via Trailing ✅   │
            │   Profit: +1.40%                    │
            │   Close Reason: Trailing Stop       │
            └─────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                         FINAL RESULTS                                    │
├──────────┬─────────┬───────────┬──────────────┬───────────────────────┤
│ Position │ Target  │ Outcome   │ Profit %     │ Close Reason          │
├──────────┼─────────┼───────────┼──────────────┼───────────────────────┤
│    1     │  TP1    │  Win ✅   │   +1.50%     │ TP1                   │
│    2     │  TP2    │  Win ✅   │   +2.75%     │ TP2                   │
│    3     │  TP3    │  Win ✅   │   +1.40%     │ Trailing Stop         │
└──────────┴─────────┴───────────┴──────────────┴───────────────────────┘

Average Profit: +1.88%
Total Bars: 21
Group ID: abc123-def456-...
```

## Key Observations

### Position Independence
Each position is completely independent:
- Position 1 closed at bar 11 (TP1)
- Position 2 closed at bar 17 (TP2)
- Position 3 closed at bar 21 (Trailing)

### Trailing Stop Behavior
- **Activation**: Only after TP1 touched (bar 11)
- **Updates**: Moves up as price increases
- **Protection**: Locks in profits above entry
- **Formula**: `stop = max_price - (max_price - entry) × 50%`

### Realistic Simulation
This matches real trading where:
- Some positions close early (conservative)
- Some positions maximize gains (aggressive)
- Trailing stops protect profits after TP1

## Comparison: Single vs 3-Position

### Single-Position Mode (Old)
```
Signal → 1 Row → 1 Outcome → Average of partial closes
Result: +2.15% (weighted average)
```

### 3-Position Mode (New)
```
Signal → 3 Rows → 3 Independent Outcomes
Position 1: +1.50%
Position 2: +2.75%
Position 3: +1.40%
```

**Benefits:**
- ✅ See exact profit per position
- ✅ Compare strategies (TP1 only vs trailing)
- ✅ Understand risk/reward tradeoffs
- ✅ More realistic portfolio simulation

## SL Hit Scenario

What if price dropped immediately?

```
Bar 1:      Price drops to $49,500 (SL HIT!)
            
            All positions close at SL:
            
            Position 1: Loss ❌ (-1.0%)
            Position 2: Loss ❌ (-1.0%)
            Position 3: Loss ❌ (-1.0%)
            
            Close Reason: SL (all positions)
```

## CSV Export Structure

```csv
timestamp,signal,position_group_id,position_num,outcome,profit_pct,tp_levels_hit,bars_held
2025-01-15 10:00,1,abc-123,1,Win ✅,1.50,TP1,11
2025-01-15 10:00,1,abc-123,2,Win ✅,2.75,TP2,17
2025-01-15 10:00,1,abc-123,3,Win ✅,1.40,Trailing,21
```

**Excel Analysis:**
- Filter by `position_group_id` to see all 3 positions for one signal
- Pivot table: Average profit by position_num
- Chart: Position performance over time

## Use Cases

### 1. Conservative Trader
Focus on Position 1 results:
- Always closes at TP1
- No trailing risk
- Consistent, smaller profits

### 2. Balanced Trader
Focus on Position 2 results:
- Aims for TP2
- Trailing protects after TP1
- Good risk/reward balance

### 3. Aggressive Trader
Focus on Position 3 results:
- Aims for TP3
- Maximum potential profit
- Higher risk of trailing stop

### 4. Portfolio Analysis
Compare all 3 positions:
- Which strategy wins most often?
- Which has best average profit?
- Which has best risk-adjusted returns?

## Technical Notes

- Each signal generates exactly 3 positions
- Positions share same entry, SL, and TP levels
- Only difference: trailing behavior and target
- Group ID links positions to original signal
- Trailing activates ONLY after TP1 hit
- Position 1 NEVER uses trailing
- Positions close independently
