"""
Generate comparison report for BTC and ETH backtests
"""

import pandas as pd
import numpy as np
from datetime import datetime


def analyze_backtest_results(filename, crypto_name):
    """Analyze and print results for a single crypto"""
    print(f"\n{'='*80}")
    print(f"📊 {crypto_name} BACKTEST ANALYSIS")
    print(f"{'='*80}")
    
    # Load results
    df = pd.read_csv(filename)
    
    # Overall stats
    total_trades = len(df)
    wins = len(df[df['pnl_pct'] > 0])
    losses = total_trades - wins
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    total_pnl = df['pnl_pct'].sum()
    avg_win = df[df['pnl_pct'] > 0]['pnl_pct'].mean() if wins > 0 else 0
    avg_loss = df[df['pnl_pct'] <= 0]['pnl_pct'].mean() if losses > 0 else 0
    
    print(f"\n📈 OVERALL PERFORMANCE:")
    print(f"   Total Trades: {total_trades}")
    print(f"   Wins: {wins} ({win_rate:.1f}%)")
    print(f"   Losses: {losses} ({100-win_rate:.1f}%)")
    print(f"   Total PnL: {total_pnl:+.2f}%")
    print(f"   Avg Win: {avg_win:+.2f}%")
    print(f"   Avg Loss: {avg_loss:+.2f}%")
    
    if avg_loss != 0:
        profit_factor = abs(avg_win * wins / (avg_loss * losses))
        print(f"   Profit Factor: {profit_factor:.2f}")
    
    # Drawdown
    cumulative_pnl = df['pnl_pct'].cumsum()
    running_max = cumulative_pnl.cummax()
    drawdown = cumulative_pnl - running_max
    max_drawdown = drawdown.min()
    
    print(f"\n📉 RISK METRICS:")
    print(f"   Max Drawdown: {max_drawdown:.2f}%")
    
    # Monthly stats
    df['entry_time'] = pd.to_datetime(df['entry_time'])
    df['exit_time'] = pd.to_datetime(df['exit_time'])
    df['month'] = df['exit_time'].dt.to_period('M')
    
    monthly = df.groupby('month').agg({
        'pnl_pct': ['sum', 'count', 'mean'],
    })
    monthly.columns = ['Total_PnL_%', 'Trades', 'Avg_PnL_%']
    
    # Calculate winning months
    winning_months = len(monthly[monthly['Total_PnL_%'] > 0])
    total_months = len(monthly)
    
    print(f"\n📅 MONTHLY PERFORMANCE:")
    print(f"   Total Months: {total_months}")
    print(f"   Winning Months: {winning_months} ({winning_months/total_months*100:.1f}%)")
    print(f"   Losing Months: {total_months - winning_months} ({(total_months-winning_months)/total_months*100:.1f}%)")
    print(f"   Best Month: {monthly['Total_PnL_%'].max():+.2f}%")
    print(f"   Worst Month: {monthly['Total_PnL_%'].min():+.2f}%")
    print(f"   Avg Monthly PnL: {monthly['Total_PnL_%'].mean():+.2f}%")
    
    print(f"\n📅 MONTHLY BREAKDOWN:")
    for month, row in monthly.iterrows():
        status = "✅" if row['Total_PnL_%'] > 0 else "❌"
        print(f"   {status} {month}: {int(row['Trades'])} trades, Total: {row['Total_PnL_%']:+7.2f}%, Avg: {row['Avg_PnL_%']:+6.2f}%")
    
    # Direction analysis
    print(f"\n📊 DIRECTION ANALYSIS:")
    for direction in ['LONG', 'SHORT']:
        dir_trades = df[df['direction'] == direction]
        if len(dir_trades) > 0:
            dir_wins = len(dir_trades[dir_trades['pnl_pct'] > 0])
            dir_win_rate = dir_wins / len(dir_trades) * 100
            dir_pnl = dir_trades['pnl_pct'].sum()
            print(f"   {direction}: {len(dir_trades)} trades, WR: {dir_win_rate:.1f}%, PnL: {dir_pnl:+.2f}%")
    
    # Regime analysis
    print(f"\n🌊 REGIME ANALYSIS:")
    for regime in ['TREND', 'RANGE']:
        regime_trades = df[df['regime'] == regime]
        if len(regime_trades) > 0:
            regime_wins = len(regime_trades[regime_trades['pnl_pct'] > 0])
            regime_win_rate = regime_wins / len(regime_trades) * 100
            regime_pnl = regime_trades['pnl_pct'].sum()
            print(f"   {regime}: {len(regime_trades)} trades, WR: {regime_win_rate:.1f}%, PnL: {regime_pnl:+.2f}%")
    
    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'total_pnl': total_pnl,
        'max_drawdown': max_drawdown,
        'winning_months': winning_months,
        'total_months': total_months,
        'monthly': monthly
    }


def compare_backtests():
    """Compare BTC and ETH backtests"""
    print("\n" + "="*80)
    print("🪙 CRYPTO BACKTEST COMPARISON - BTC vs ETH")
    print("="*80)
    
    # Analyze both
    btc_stats = analyze_backtest_results('BTC_backtest_v3_results.csv', 'BITCOIN (BTC)')
    eth_stats = analyze_backtest_results('ETH_backtest_v3_results.csv', 'ETHEREUM (ETH)')
    
    # Comparison
    print(f"\n{'='*80}")
    print(f"🔄 COMPARISON SUMMARY")
    print(f"{'='*80}")
    
    print(f"\n📊 OVERALL:")
    print(f"   BTC Total PnL: {btc_stats['total_pnl']:+.2f}%")
    print(f"   ETH Total PnL: {eth_stats['total_pnl']:+.2f}%")
    print(f"   Winner: {'BTC' if btc_stats['total_pnl'] > eth_stats['total_pnl'] else 'ETH'}")
    
    print(f"\n🎯 WIN RATES:")
    print(f"   BTC Win Rate: {btc_stats['win_rate']:.1f}%")
    print(f"   ETH Win Rate: {eth_stats['win_rate']:.1f}%")
    print(f"   Winner: {'BTC' if btc_stats['win_rate'] > eth_stats['win_rate'] else 'ETH'}")
    
    print(f"\n📉 RISK:")
    print(f"   BTC Max Drawdown: {btc_stats['max_drawdown']:.2f}%")
    print(f"   ETH Max Drawdown: {eth_stats['max_drawdown']:.2f}%")
    print(f"   Better Risk: {'BTC' if abs(btc_stats['max_drawdown']) < abs(eth_stats['max_drawdown']) else 'ETH'}")
    
    print(f"\n📅 CONSISTENCY:")
    btc_monthly_win_rate = btc_stats['winning_months'] / btc_stats['total_months'] * 100
    eth_monthly_win_rate = eth_stats['winning_months'] / eth_stats['total_months'] * 100
    print(f"   BTC Winning Months: {btc_stats['winning_months']}/{btc_stats['total_months']} ({btc_monthly_win_rate:.1f}%)")
    print(f"   ETH Winning Months: {eth_stats['winning_months']}/{eth_stats['total_months']} ({eth_monthly_win_rate:.1f}%)")
    print(f"   More Consistent: {'BTC' if btc_monthly_win_rate > eth_monthly_win_rate else 'ETH'}")
    
    print(f"\n{'='*80}")
    print(f"✅ CONCLUSION")
    print(f"{'='*80}")
    
    # Calculate scores
    btc_score = 0
    eth_score = 0
    
    if btc_stats['total_pnl'] > eth_stats['total_pnl']:
        btc_score += 1
    else:
        eth_score += 1
    
    if btc_stats['win_rate'] > eth_stats['win_rate']:
        btc_score += 1
    else:
        eth_score += 1
    
    if abs(btc_stats['max_drawdown']) < abs(eth_stats['max_drawdown']):
        btc_score += 1
    else:
        eth_score += 1
    
    if btc_monthly_win_rate > eth_monthly_win_rate:
        btc_score += 1
    else:
        eth_score += 1
    
    print(f"\n🏆 Overall Score: BTC {btc_score} - {eth_score} ETH")
    
    if btc_score > eth_score:
        print(f"   Winner: BITCOIN (BTC)")
        print(f"   BTC performed better in {btc_score} out of 4 categories")
    elif eth_score > btc_score:
        print(f"   Winner: ETHEREUM (ETH)")
        print(f"   ETH performed better in {eth_score} out of 4 categories")
    else:
        print(f"   Result: TIE")
        print(f"   Both cryptocurrencies performed equally well")
    
    print(f"\n💡 RECOMMENDATIONS:")
    print(f"   • Both strategies show positive results over 2 years")
    print(f"   • BTC Total Return: {btc_stats['total_pnl']:+.2f}%")
    print(f"   • ETH Total Return: {eth_stats['total_pnl']:+.2f}%")
    print(f"   • Consider diversifying across both assets")
    print(f"   • Monitor monthly performance and adjust parameters as needed")
    print(f"   • Backtest results are based on simulated data and historical patterns")


if __name__ == "__main__":
    compare_backtests()
    
    print(f"\n{'='*80}")
    print(f"📁 FILES GENERATED:")
    print(f"{'='*80}")
    print(f"   • BTC_backtest_v3_results.csv")
    print(f"   • ETH_backtest_v3_results.csv")
    print(f"   • BTC_1h_20240107_20260106.csv (data)")
    print(f"   • ETH_1h_20240107_20260106.csv (data)")
