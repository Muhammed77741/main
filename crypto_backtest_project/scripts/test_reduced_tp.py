"""
Backtest with REDUCED TP using Simplified SMC Strategy (no gold filters)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backtest_v3_adaptive import AdaptiveBacktestV3
from simplified_smc_strategy import SimplifiedSMCStrategy
import pandas as pd

def run_reduced_tp_backtest():
    print("\n" + "="*80)
    print("🎯 BACKTEST WITH REDUCED TP LEVELS - BTC & ETH")
    print("="*80)
    print("\n📉 TP Reduction: ~30-35% lower")
    print("   TREND: TP1 30→20, TP2 55→35, TP3 90→55, Trail 18→12")
    print("   RANGE: TP1 20→15, TP2 35→25, TP3 50→35, Trail 15→10")
    print("="*80)
    
    results = {}
    
    for symbol, data_file in [('BTC', '../data/BTC_1h_20240107_20260106_real.csv'),
                               ('ETH', '../data/ETH_1h_20240107_20260106_real.csv')]:
        print(f"\n{'='*80}")
        print(f"📊 {symbol} BACKTEST")
        print(f"{'='*80}")
        
        # Load data
        df = pd.read_csv(data_file)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.sort_values('datetime').reset_index(drop=True)
        print(f"✅ Loaded {len(df)} candles: {df['datetime'].iloc[0]} to {df['datetime'].iloc[-1]}")
        
        # Create backtest with REDUCED TPs
        backtest = AdaptiveBacktestV3(spread_points=2.0, commission_points=0.5, swap_per_day=-0.3)
        
        # REDUCE TPs
        backtest.trend_tp1 = 20
        backtest.trend_tp2 = 35  
        backtest.trend_tp3 = 55
        backtest.trend_trailing = 12
        
        backtest.range_tp1 = 15
        backtest.range_tp2 = 25
        backtest.range_tp3 = 35
        backtest.range_trailing = 10
        
        # Use simplified strategy (no gold filters)
        strategy = SimplifiedSMCStrategy(
            risk_reward_ratio=2.0,
            swing_length=10,
            min_candle_quality=50
        )
        
        print(f"\n🚀 Running backtest with Simplified SMC Strategy...")
        
        # Run
        result = backtest.backtest(df, strategy)
        
        if result is None:
            print(f"❌ No result for {symbol}")
            continue
            
        # Parse result
        if isinstance(result, tuple):
            trades_df = result[0]
        else:
            trades_df = result
        
        if trades_df is None or len(trades_df) == 0:
            print(f"❌ No trades for {symbol}")
            continue
        
        # Calculate metrics
        total_trades = len(trades_df)
        wins = len(trades_df[trades_df['total_pnl_%'] > 0])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        total_pnl = trades_df['total_pnl_%'].sum()
        
        # By regime
        trend_mask = trades_df.get('regime', '') == 'TREND'
        range_mask = trades_df.get('regime', '') == 'RANGE'
        trend_trades = trend_mask.sum() if 'regime' in trades_df.columns else 0
        range_trades = range_mask.sum() if 'regime' in trades_df.columns else 0
        trend_pnl = trades_df[trend_mask]['total_pnl_%'].sum() if trend_trades > 0 else 0
        range_pnl = trades_df[range_mask]['total_pnl_%'].sum() if range_trades > 0 else 0
        
        # Drawdown
        cum_pnl = trades_df['total_pnl_%'].cumsum()
        running_max = cum_pnl.cummax()
        dd = cum_pnl - running_max
        max_dd = dd.min()
        
        # Profit factor
        gross_profit = trades_df[trades_df['total_pnl_%'] > 0]['total_pnl_%'].sum()
        gross_loss = abs(trades_df[trades_df['total_pnl_%'] < 0]['total_pnl_%'].sum())
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Erroneous
        err_mask = (trades_df['exit_type'].str.contains('SL', na=False)) & (trades_df['total_pnl_%'] > 0)
        erroneous = err_mask.sum()
        
        print(f"\n✅ {symbol} RESULTS (REDUCED TP):")
        print(f"   📊 Trades: {total_trades}")
        print(f"   🎯 Win Rate: {win_rate:.1f}%")
        print(f"   💰 Total P&L: {total_pnl:+.2f}%")
        print(f"   📉 Max DD: {max_dd:.2f}%")
        print(f"   💎 Profit Factor: {pf:.2f}")
        print(f"   🔥 TREND: {trend_trades} trades ({trend_pnl:+.1f}%)")
        print(f"   📊 RANGE: {range_trades} trades ({range_pnl:+.1f}%)")
        print(f"   ⚠️  Erroneous: {erroneous} ({erroneous/total_trades*100:.1f}%)")
        
        # Save
        output = f"../results/{symbol}_reduced_tp_backtest.csv"
        trades_df.to_csv(output, index=False)
        print(f"   💾 Saved: {output}")
        
        results[symbol] = {
            'trades': total_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'max_dd': max_dd,
            'pf': pf,
            'trend_trades': trend_trades,
            'range_trades': range_trades,
            'trend_pnl': trend_pnl,
            'range_pnl': range_pnl,
            'erroneous': erroneous
        }
    
    # Summary
    if 'BTC' in results and 'ETH' in results:
        print(f"\n{'='*80}")
        print("📊 COMBINED SUMMARY")
        print(f"{'='*80}")
        
        btc = results['BTC']
        eth = results['ETH']
        
        combined_trades = btc['trades'] + eth['trades']
        combined_pnl = btc['total_pnl'] + eth['total_pnl']
        
        print(f"\n🪙 BTC: {btc['trades']} trades, {btc['win_rate']:.1f}% WR, {btc['total_pnl']:+.1f}% P&L")
        print(f"💎 ETH: {eth['trades']} trades, {eth['win_rate']:.1f}% WR, {eth['total_pnl']:+.1f}% P&L")
        print(f"🎯 COMBINED: {combined_trades} trades, {combined_pnl:+.1f}% P&L")
        
        print(f"\n{'='*80}")
        print("📈 COMPARISON WITH ORIGINAL TP")
        print(f"{'='*80}")
        print("\nOriginal TP:")
        print("   BTC: 1,122 trades, +1,335% P&L, 98.0% WR")
        print("   ETH: 1,028 trades, +646% P&L, 86.6% WR")
        print("   Combined: 2,150 trades, +1,981% P&L")
        
        print("\nReduced TP (~30-35% lower):")
        print(f"   BTC: {btc['trades']} trades, {btc['total_pnl']:+.1f}% P&L, {btc['win_rate']:.1f}% WR")
        print(f"   ETH: {eth['trades']} trades, {eth['total_pnl']:+.1f}% P&L, {eth['win_rate']:.1f}% WR")
        print(f"   Combined: {combined_trades} trades, {combined_pnl:+.1f}% P&L")
        
        # Differences
        btc_diff = btc['total_pnl'] - 1335
        eth_diff = eth['total_pnl'] - 646
        comb_diff = combined_pnl - 1981
        
        print(f"\n💹 Difference:")
        print(f"   BTC: {btc_diff:+.1f}% ({btc_diff/1335*100:+.1f}%)")
        print(f"   ETH: {eth_diff:+.1f}% ({eth_diff/646*100:+.1f}%)")
        print(f"   Combined: {comb_diff:+.1f}% ({comb_diff/1981*100:+.1f}%)")
        
        if comb_diff > 0:
            print("\n✅ RESULT: Reduced TP performed BETTER (+{:.1f}%)".format(comb_diff/1981*100))
        elif comb_diff > -100:
            print("\n≈ RESULT: Similar performance")
        else:
            print("\n❌ RESULT: Original TP performed better")
        
        print(f"\n{'='*80}\n")

if __name__ == '__main__':
    try:
        run_reduced_tp_backtest()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
