# Adaptive Backtest V3 - Documentation

## Overview

Adaptive Backtest V3 is an advanced backtesting system that automatically detects market conditions (trend vs. range) and adjusts trading parameters dynamically to optimize performance.

## Features

### 1. Automatic Market Regime Detection

The system uses multiple indicators to classify market conditions:

- **EMA Crossover**: Measures divergence between 20-period and 50-period EMAs
- **ATR (Average True Range)**: Analyzes volatility levels
- **Directional Movement**: Tracks price momentum
- **Candle Sequence**: Identifies patterns of consecutive up/down candles
- **Structural Trends**: Detects higher highs and lower lows

**Decision Logic**: Market is classified as TREND when 3+ out of 5 indicators signal trending conditions.

### 2. Adaptive Trading Parameters

#### TREND MODE (Strong Trending Markets)
- **Take Profit Levels**: 30п / 55п / 90п
- **Trailing Stop**: 18 points
- **Timeout**: 60 hours
- **Strategy**: Aggressive targets to capture large moves

#### RANGE MODE (Sideways Markets)
- **Take Profit Levels**: 20п / 35п / 50п
- **Trailing Stop**: 15 points
- **Timeout**: 48 hours
- **Strategy**: Conservative targets with faster exits

### 3. Partial Position Management

The system uses a partial close strategy:
- **50%** closed at TP1
- **30%** closed at TP2
- **20%** closed at TP3

After TP1, a trailing stop is activated to protect profits.

### 4. Risk Management

- **Max Positions**: 5 simultaneous positions (configurable)
- **Max Trades Per Day**: 10 trades
- **Trading Costs**: 
  - Spread: 2.0 points
  - Commission: 0.5 points per trade
  - Swap: -0.3 points per day

## Files

### 1. `pattern_recognition_strategy.py`

A wrapper strategy that combines SMC (Smart Money Concepts) indicators with Fibonacci-based adjustments.

**Key Features**:
- Uses `SimplifiedSMCStrategy` for signal generation
- Supports multiple Fibonacci modes ('standard', '1.618')
- Returns signals with entry, stop loss, and take profit levels

### 2. `adaptive_backtest_v3.py`

The main backtesting engine that processes historical data and generates trade results.

**Key Methods**:
- `detect_market_regime()`: Classifies market conditions
- `backtest()`: Processes data and executes virtual trades
- `_calculate_pnl_points()`: Calculates profit/loss with costs
- `_print_results()`: Displays comprehensive statistics

### 3. `test_adaptive_backtest_v3.py`

Comprehensive test suite that validates:
- PatternRecognitionStrategy functionality
- Market regime detection accuracy
- Full backtest execution with synthetic data

## Usage

### Basic Usage

```bash
cd smc_trading_strategy
python adaptive_backtest_v3.py --file path/to/data.csv
```

### Data Format

The system accepts CSV files with the following columns:
- `datetime`: Timestamp (supports both `2024-06-04 00:00` and `2024.06.04 00:00` formats)
- `open`: Opening price
- `high`: High price
- `low`: Low price
- `close`: Closing price
- `volume`: Trading volume

### Example Output

```
================================================================================
📊 ADAPTIVE BACKTEST V3 - TREND DETECTOR + RANGE TRADING
================================================================================
   Data: 9371 candles
   Period: 2024-06-04 00:00:00 to 2026-01-02 22:00:00

   🎯 TREND MODE:
   TP: 30п / 55п / 90п
   Trailing: 18п
   Timeout: 60ч

   📊 RANGE MODE:
   TP: 20п / 35п / 50п
   Trailing: 15п
   Timeout: 48ч

================================================================================
📊 MARKET REGIME STATISTICS
================================================================================
   TREND signals: 135 (30.9%)
   RANGE signals: 302 (69.1%)

   TREND trades: 133
     PnL: +3.66%
     Win Rate: 58.6%

   RANGE trades: 299
     PnL: +16.72%
     Win Rate: 62.5%

================================================================================
📊 ADAPTIVE RESULTS
================================================================================

📈 Performance:
   Total trades: 432
   Wins: 265 (61.3%)
   Total PnL: +20.38%
   Total Points: +905.0п
   Avg Win: +0.67%
   Avg Loss: -0.94%
   Profit Factor: 1.13

📉 Risk Metrics:
   Max Drawdown: -20.28%
```

## Results File

The backtest generates a CSV file (`backtest_v3_adaptive_results.csv`) with detailed trade information:

- `entry_time`: Trade entry timestamp
- `exit_time`: Trade exit timestamp
- `direction`: LONG or SHORT
- `regime`: TREND or RANGE
- `entry_price`: Entry price
- `exit_price`: Exit price
- `tp1_hit`, `tp2_hit`, `tp3_hit`: Which take profit levels were reached
- `trailing_used`: Whether trailing stop was activated
- `exit_type`: How the trade closed (TP1, TP2, TP3, SL, TRAILING_SL, TIMEOUT)
- `pnl_pct`: Profit/loss percentage
- `pnl_points`: Profit/loss in points
- `duration_hours`: Trade duration
- `month`: Month of trade exit

## Testing

Run the test suite to verify the implementation:

```bash
python test_adaptive_backtest_v3.py
```

This will:
1. Generate synthetic data
2. Test PatternRecognitionStrategy
3. Test market regime detection
4. Run a full backtest simulation

## Performance Metrics

The system tracks:
- **Win Rate**: Percentage of profitable trades
- **Total PnL**: Cumulative profit/loss percentage
- **Profit Factor**: Ratio of gross profit to gross loss
- **Max Drawdown**: Largest peak-to-trough decline
- **Monthly Breakdown**: Performance by calendar month
- **Regime Statistics**: Separate analysis for TREND vs RANGE trades

## Dependencies

```
pandas>=2.0.0
numpy>=1.24.0
```

Install with:
```bash
pip install pandas numpy
```

## Architecture

```
┌─────────────────────────────────┐
│   adaptive_backtest_v3.py       │
│   (Main Backtest Engine)        │
└────────────┬────────────────────┘
             │
             ├─► detect_market_regime()
             │   (TREND/RANGE classifier)
             │
             ├─► pattern_recognition_strategy.py
             │   └─► SimplifiedSMCStrategy
             │       └─► smc_indicators.py
             │       └─► volume_analysis.py
             │
             └─► Trade Management
                 ├─► Partial Closes (50/30/20)
                 ├─► Trailing Stops
                 ├─► Timeouts
                 └─► Cost Calculations
```

## Customization

You can modify parameters in `AdaptiveBacktestV3.__init__()`:

```python
# Trend parameters
self.trend_tp1 = 30
self.trend_tp2 = 55
self.trend_tp3 = 90
self.trend_trailing = 18
self.trend_timeout = 60

# Range parameters
self.range_tp1 = 20
self.range_tp2 = 35
self.range_tp3 = 50
self.range_trailing = 15
self.range_timeout = 48

# Risk limits
self.max_positions = 5
self.max_trades_per_day = 10
```

## Regime Detection Tuning

Adjust regime detection sensitivity in `detect_market_regime()`:

```python
# EMA divergence threshold (default: 0.3%)
ema_trend = ema_diff_pct > 0.3

# Volatility multiplier (default: 1.05)
high_volatility = atr > avg_atr * 1.05

# Directional movement threshold (default: 35%)
strong_direction = directional_move_pct > 0.35

# Trend strength bias (default: 15%)
directional_bias = trend_strength > 0.15

# Structural trend (default: 60% of candles)
structural_trend = (higher_highs > 12) or (lower_lows > 12)

# Number of signals required (default: 3 out of 5)
is_trend = trend_signals >= 3
```

## Known Limitations

1. The strategy requires sufficient historical data (minimum 100 candles) for regime detection
2. No live trading capabilities (backtest only)
3. Does not account for slippage beyond the configured spread
4. Assumes instant order execution at specified prices
5. No consideration for news events or fundamental factors

## Future Enhancements

- [ ] Add volatility-based position sizing
- [ ] Implement dynamic TP/SL based on ATR
- [ ] Add correlation analysis for multi-asset portfolios
- [ ] Include market session filters (London, NY, Asian)
- [ ] Implement Monte Carlo simulation for risk analysis
- [ ] Add walk-forward optimization capabilities

## License

This implementation is part of the SMC Trading Strategy project.

## Support

For issues or questions, please refer to the main repository documentation or create an issue on GitHub.
