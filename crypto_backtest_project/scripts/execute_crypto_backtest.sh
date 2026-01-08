#!/bin/bash
# Execute crypto backtest pipeline

echo "================================="
echo "CRYPTO BACKTEST EXECUTION"
echo "================================="

# Step 1: Generate data
echo ""
echo "Step 1: Generating crypto data..."
python generate_crypto_data.py --years 2

# Step 2: Run backtests
echo ""
echo "Step 2: Running BTC backtest..."
python crypto_backtest_v3.py --input BTC_1h_20240107_20260106.csv --output BTC_backtest_v3_results.csv --crypto BTC

echo ""
echo "Step 3: Running ETH backtest..."
python crypto_backtest_v3.py --input ETH_1h_20240107_20260106.csv --output ETH_backtest_v3_results.csv --crypto ETH

# Step 3: Compare results
echo ""
echo "Step 4: Comparing results..."
python compare_crypto_backtests.py

echo ""
echo "================================="
echo "✓ ALL DONE!"
echo "================================="
