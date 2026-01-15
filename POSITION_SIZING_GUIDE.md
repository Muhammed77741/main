# 📏 Position Sizing Feature - User Guide

**Branch:** `claude/fix-backtest-and-live-issues-ulnOj`
**Date:** 2026-01-15

---

## ✨ What's New?

You can now choose between **two position sizing modes** in the GUI settings:

### 1. **Auto Mode (Risk-Based)** ⚖️
- Calculates position size dynamically based on **risk percent**
- Automatically adjusts to your account balance
- **Recommended for most users**
- Example: 2% risk with $10,000 = $200 risk per trade

### 2. **Fixed Mode (Fixed Size)** 📌
- Uses a **fixed position size** for every trade
- Size stays the same regardless of account balance
- Useful for:
  - Consistent position sizes
  - Testing strategies with fixed amounts
  - Advanced risk management scenarios

---

## 🎛️ How to Use in GUI

### Step 1: Open Settings
1. Launch the trading app GUI
2. Select a bot (XAUUSD, BTC, or ETH)
3. Click **Settings** button

### Step 2: Configure Position Sizing
In the **Trading Parameters** section:

**Position Size Mode:**
- Select `Auto (Risk %)` or `Fixed Size` from dropdown

**If Auto Mode:**
- Set **Risk per trade**: 0.5% - 10.0% (recommended: 1-2%)
- Position size calculated automatically based on SL distance

**If Fixed Mode:**
- Set **Fixed Position Size**:
  - **XAUUSD**: 0.01 - 100.00 lots
  - **BTC**: 0.001 - 10.000 BTC
  - **ETH**: 0.01 - 100.00 ETH

### Step 3: Save Settings
- Click **Save** to apply changes
- Settings are saved to database automatically

---

## 📊 Position Sizing by Asset

### XAUUSD (Gold) - MT5
- **Unit:** Lots
- **Auto Mode:** Calculates lots based on risk% and SL distance in points
- **Fixed Mode:** Enter lot size directly (e.g., 0.1 lot)
- **Range:** 0.01 - 100 lots
- **Example:**
  ```
  Auto: 2% risk, $10,000 balance, 50 point SL → ~0.20 lot
  Fixed: Always trade 0.1 lot regardless of conditions
  ```

### BTC (Bitcoin) - Binance
- **Unit:** BTC
- **Auto Mode:** Calculates BTC amount based on risk% and SL distance
- **Fixed Mode:** Enter BTC amount directly (e.g., 0.01 BTC)
- **Range:** 0.0001 - 10.0 BTC
- **Example:**
  ```
  Auto: 2% risk, 1000 USDT balance, 2% SL → ~0.01 BTC
  Fixed: Always trade 0.005 BTC (~$450 at $90k BTC)
  ```

### ETH (Ethereum) - Binance
- **Unit:** ETH
- **Auto Mode:** Calculates ETH amount based on risk% and SL distance
- **Fixed Mode:** Enter ETH amount directly (e.g., 0.1 ETH)
- **Range:** 0.001 - 100.0 ETH
- **Example:**
  ```
  Auto: 2% risk, 1000 USDT balance, 2% SL → ~0.15 ETH
  Fixed: Always trade 0.1 ETH (~$330 at $3.3k ETH)
  ```

---

## 🔧 Technical Details

### Auto Mode Calculation (XAUUSD)
```python
# Example:
balance = $10,000
risk_percent = 2.0%
entry_price = 2650.00
sl_price = 2600.00
sl_distance = 50 points

risk_amount = $10,000 × 0.02 = $200
point_value = $1 per point per lot
lot_size = $200 / ($1 × 50) = 4.0 lots

# Clamped to min/max: max(0.01, min(4.0, 100)) = 4.0 lots
```

### Auto Mode Calculation (Crypto)
```python
# Example (BTC):
balance = 1000 USDT
risk_percent = 2.0%
entry_price = $90,000
sl_price = $88,200
sl_distance = $1,800

risk_amount = 1000 × 0.02 = 20 USDT
position_size = 20 / 1800 = 0.011 BTC

# Clamped to min/max: max(0.001, min(0.011, 10)) = 0.011 BTC
```

### Fixed Mode
```python
# Simply uses the configured fixed size:
position_size = fixed_position_size

# Clamped to exchange min/max limits
# XAUUSD: max(0.01, min(position_size, 100))
# BTC: max(0.001, min(position_size, 10))
# ETH: max(0.01, min(position_size, 100))
```

---

## ⚖️ Which Mode Should You Use?

### Use **Auto Mode** if:
- ✅ You want consistent **risk per trade** (recommended)
- ✅ Your account balance changes over time
- ✅ You want automatic position scaling
- ✅ You're following proper risk management (1-2% risk)
- ✅ You're a beginner or intermediate trader

### Use **Fixed Mode** if:
- ✅ You want **consistent position sizes**
- ✅ You're testing a strategy with fixed amounts
- ✅ You have a specific dollar amount per trade in mind
- ✅ You're doing advanced risk management
- ✅ You understand the implications of fixed sizing

---

## ⚠️ Important Notes

### 1. Risk Management
- **Auto mode** is generally safer as it adjusts to your account
- **Fixed mode** can lead to over-leveraging if account shrinks
- Always monitor your account equity

### 2. Validation
- All position sizes are validated before saving:
  - TP levels must be in ascending order
  - Position size must be within allowed range
  - Mode must be 'auto' or 'fixed'
- Invalid configs will show error message

### 3. Exchange Limits
- Position sizes are automatically clamped to exchange min/max:
  - MT5 XAUUSD: 0.01 - 100 lots
  - Binance BTC: 0.001 - 10 BTC (market-dependent)
  - Binance ETH: 0.01 - 100 ETH (market-dependent)

### 4. Default Settings
- **Default mode**: Auto (risk-based)
- **Default fixed sizes**:
  - XAUUSD: 0.1 lot
  - BTC: 0.01 BTC (~$900 at $90k)
  - ETH: 0.1 ETH (~$330 at $3.3k)

---

## 📝 Example Configurations

### Conservative XAUUSD Trader (Auto)
```
Mode: Auto (Risk %)
Risk per trade: 1.0%
Max positions: 3
→ Each trade risks 1% of account
→ Position size adjusts automatically
```

### Aggressive BTC Trader (Auto)
```
Mode: Auto (Risk %)
Risk per trade: 3.0%
Max positions: 1
→ Single position risks 3% of account
→ High risk, high reward
```

### Fixed Size XAUUSD Trader
```
Mode: Fixed Size
Fixed position size: 0.5 lot
Max positions: 3
→ Always trades 0.5 lot per position
→ Total exposure: 1.5 lots across 3 positions
```

### Fixed Size BTC Trader
```
Mode: Fixed Size
Fixed position size: 0.005 BTC
Max positions: 1
→ Always trades $450 worth (at $90k BTC)
→ Risk depends on SL distance
```

---

## 🔍 Testing Recommendations

### Before Going Live:
1. **Test in DRY RUN mode first**
   - Verify position sizes are calculated correctly
   - Check that fixed mode uses your configured size
   - Ensure auto mode respects risk percent

2. **Test on DEMO account**
   - Run for 30-60 days minimum
   - Compare actual position sizes with expected
   - Monitor if sizing matches your strategy

3. **Start with Auto Mode**
   - Safer for most traders
   - Automatic risk management
   - Easier to understand

4. **Use Low Risk Initially**
   - Start with 0.5-1% risk
   - Increase only after proven profitable
   - Never risk more than you can afford to lose

---

## 🆘 Troubleshooting

### Problem: "Position size must be positive"
**Solution:** Ensure fixed_position_size > 0 in settings

### Problem: "Position size outside allowed range"
**Solution:** Check the range for your asset:
- XAUUSD: 0.01-100 lots
- BTC: 0.0001-10 BTC
- ETH: 0.001-100 ETH

### Problem: Fixed mode not working
**Solution:**
1. Check mode is set to "Fixed Size" in settings
2. Verify bot was restarted after changing settings
3. Check logs for position size output

### Problem: Auto mode calculates wrong size
**Solution:**
1. Verify risk_percent is correct (1-10%)
2. Check SL distance is reasonable
3. Ensure account balance is fetched correctly
4. Check bot logs for calculation details

---

## 📞 Support

If you encounter issues with position sizing:
1. Check bot logs for position size calculations
2. Verify settings are saved correctly in database
3. Test in DRY RUN mode first
4. Ensure exchange connection is working
5. Check that account balance is available

---

## 🎯 Summary

- **Two modes:** Auto (risk-based) and Fixed (fixed size)
- **Asset-specific:** Different units for XAUUSD/BTC/ETH
- **Validation:** Automatic checks prevent invalid configs
- **GUI integration:** Easy configuration in settings dialog
- **Backward compatible:** Existing configs default to Auto mode

**Recommendation:** Use **Auto mode with 1-2% risk** for most trading scenarios.

---

**Version:** 2.0.0-position-sizing
**Last Updated:** 2026-01-15
**Status:** ✅ Ready for Testing
