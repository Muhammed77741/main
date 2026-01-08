"""
Run backtest with REDUCED TP levels - Simple version
Modifies TP parameters and runs with existing SMC strategy setup
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest_v3_adaptive import AdaptiveBacktestV3
from pattern_recognition_strategy import PatternRecognitionStrategy
import pandas as pd

def run_backtest_reduced_tp(symbol, data_path):
    """Run single backtest with reduced TP"""
    print(f"\n{'='*80}")
    print(f"🔄 {symbol} BACKTEST WITH REDUCED TP LEVELS")
    print(f"{'='*80}")
    
    # Load data
    df = pd.read_csv(data_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    print(f"📊 Loaded {len(df)} candles from {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")
    
    # Create backtest with REDUCED TPs
    backtest = AdaptiveBacktestV3(spread_points=2.0, commission_points=0.5, swap_per_day=-0.3)
    
    # REDUCE TP levels by ~30-35%
    print("\n🎯 TP Configuration (REDUCED):")
    print(f"   TREND: TP1={backtest.trend_tp1} → 20, TP2={backtest.trend_tp2} → 35, TP3={backtest.trend_tp3} → 55, Trail={backtest.trend_trailing} → 12")
    backtest.trend_tp1 = 20      # was 30
    backtest.trend_tp2 = 35      # was 55  
    backtest.trend_tp3 = 55      # was 90
    backtest.trend_trailing = 12  # was 18
    
    print(f"   RANGE: TP1={backtest.range_tp1} → 15, TP2={backtest.range_tp2} → 25, TP3={backtest.range_tp3} → 35, Trail={backtest.range_trailing} → 10")
    backtest.range_tp1 = 15      # was 20
    backtest.range_tp2 = 25      # was 35
    backtest.range_tp3 = 35      # was 50
    backtest.range_trailing = 10  # was 15
    
    # Create strategy
    strategy = PatternRecognitionStrategy()
    
    # Run backtest
    print("\n🚀 Running backtest...")
    result = backtest.backtest(df, strategy)
    
    if result is None or len(result) == 0:
        print("❌ No result returned from backtest")
        return None
        
    # Get results (could be tuple or just dataframe)
    if isinstance(result, tuple):
        trades_df = result[0]
        if len(result) > 1:
            metrics = result[1]
        else:
            metrics = None
        if len(result) > 2:
            monthly = result[2]
        else:
            monthly = None
    else:
        trades_df = result
        metrics = None
        monthly = None
    
    # Calculate metrics if not provided
    if trades_df is not None and len(trades_df) > 0:
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['total_pnl_%'] > 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        total_pnl = trades_df['total_pnl_%'].sum()
        
        # Count by regime
        trend_trades = len(trades_df[trades_df.get('regime', '') == 'TREND'])
        range_trades = len(trades_df[trades_df.get('regime', '') == 'RANGE'])
        trend_pnl = trades_df[trades_df.get('regime', '') == 'TREND']['total_pnl_%'].sum() if 'regime' in trades_df.columns else 0
        range_pnl = trades_df[trades_df.get('regime', '') == 'RANGE']['total_pnl_%'].sum() if 'regime' in trades_df.columns else 0
        
        #  Drawdown
        cumulative_pnl = trades_df['total_pnl_%'].cumsum()
        running_max = cumulative_pnl.cummax()
        drawdown = cumulative_pnl - running_max
        max_dd = drawdown.min()
        
        # Profit factor
        gross_profit = trades_df[trades_df['total_pnl_%'] > 0]['total_pnl_%'].sum()
        gross_loss = abs(trades_df[trades_df['total_pnl_%'] < 0]['total_pnl_%'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Erroneous trades
        erroneous = len(trades_df[(trades_df['exit_type'].str.contains('SL')) & (trades_df['total_pnl_%'] > 0)])
        
        print(f"\n✅ {symbol} RESULTS:")
        print(f"   📊 Trades: {total_trades}")
        print(f"   🎯 Win Rate: {win_rate:.1f}%")
        print(f"   💰 Total P&L: {total_pnl:+.2f}%")
        print(f"   📉 Max DD: {max_dd:.2f}%")
        print(f"   💎 Profit Factor: {profit_factor:.2f}")
        print(f"   🔥 TREND: {trend_trades} trades ({trend_pnl:+.1f}%)")
        print(f"   📊 RANGE: {range_trades} trades ({range_pnl:+.1f}%)")
        print(f"   ⚠️  Erroneous: {erroneous} ({erroneous/total_trades*100:.1f}%)")
        
        # Save
        output_file = f"../results/{symbol}_reduced_tp_backtest.csv"
        trades_df.to_csv(output_file, index=False)
        print(f"   💾 Saved: {output_file}")
        
        return {
            'trades': total_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'max_dd': max_dd,
            'profit_factor': profit_factor,
            'trend_trades': trend_trades,
            'range_trades': range_trades,
            'trend_pnl': trend_pnl,
            'range_pnl': range_pnl,
            'erroneous': erroneous
        }
    
    return None

def main():
    print("\n" + "="*80)
    print("🎯 BACKTEST WITH REDUCED TP LEVELS FOR BTC & ETH")
    print("="*80)
    print("\n📝 Reducing all TP levels by ~30-35%:")
    print("   TREND: TP1 30→20, TP2 55→35, TP3 90→55, Trail 18→12")
    print("   RANGE: TP1 20→15, TP2 35→25, TP3 50→35, Trail 15→10")
    print("="*80)
    
    # Run BTC
    btc_result = run_backtest_reduced_tp('BTC', '../data/BTC_1h_20240107_20260106_real.csv')
    
    # Run ETH
    eth_result = run_backtest_reduced_tp('ETH', '../data/ETH_1h_20240107_20260106_real.csv')
    
    # Summary
    if btc_result and eth_result:
        print(f"\n{'='*80}")
        print("📊 COMBINED SUMMARY - REDUCED TP")
        print(f"{'='*80}")
        
        combined_trades = btc_result['trades'] + eth_result['trades']
        combined_pnl = btc_result['total_pnl'] + eth_result['total_pnl']
        
        print(f"\n🪙 BTC: {btc_result['trades']} trades, {btc_result['win_rate']:.1f}% WR, {btc_result['total_pnl']:+.1f}% P&L")
        print(f"💎 ETH: {eth_result['trades']} trades, {eth_result['win_rate']:.1f}% WR, {eth_result['total_pnl']:+.1f}% P&L")
        print(f"🎯 COMBINED: {combined_trades} trades, {combined_pnl:+.1f}% P&L")
        
        print(f"\n{'='*80}")
        print("📈 COMPARISON WITH ORIGINAL")
        print(f"{'='*80}")
        print("\nOriginal TP levels:")
        print("   BTC: 1,122 trades, +1,335% P&L, 98.0% WR")
        print("   ETH: 1,028 trades, +646% P&L, 86.6% WR")
        print("   Combined: 2,150 trades, +1,981% P&L")
        
        print("\nReduced TP levels:")
        print(f"   BTC: {btc_result['trades']} trades, {btc_result['total_pnl']:+.1f}% P&L, {btc_result['win_rate']:.1f}% WR")
        print(f"   ETH: {eth_result['trades']} trades, {eth_result['total_pnl']:+.1f}% P&L, {eth_result['win_rate']:.1f}% WR")
        print(f"   Combined: {combined_trades} trades, {combined_pnl:+.1f}% P&L")
        
        # Difference
        btc_diff = btc_result['total_pnl'] - 1335
        eth_diff = eth_result['total_pnl'] - 646
        combined_diff = combined_pnl - 1981
        
        print(f"\n💹 Difference:")
        print(f"   BTC: {btc_diff:+.1f}% ({btc_diff/1335*100:+.1f}%)")
        print(f"   ETH: {eth_diff:+.1f}% ({eth_diff/646*100:+.1f}%)")
        print(f"   Combined: {combined_diff:+.1f}% ({combined_diff/1981*100:+.1f}%)")
        
        if combined_diff > 0:
            print("\n✅ RESULT: Reduced TP performed BETTER!")
        elif combined_diff > -100:
            print("\n≈ RESULT: Similar performance")
        else:
            print("\n❌ RESULT: Original TP performed better")
        
        print(f"\n{'='*80}\n")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
