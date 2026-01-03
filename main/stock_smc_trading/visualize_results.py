"""
Visualize Stock Screener Results
Compare Buy & Hold vs Trading
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from stock_screener import StockScreener, create_stock_universe


def compare_strategies():
    """
    Visual comparison: Buy & Hold vs Active Trading
    """
    
    # Historical results from our testing
    stocks = ['NVDA', 'AAPL', 'MSFT', 'TSLA', 'GOOGL']
    
    buy_hold = [788.81, 77.43, 83.78, 141.75, 23.93]  # % returns
    trading = [-4.35, -4.62, -10.96, -5.23, -2.14]    # % returns
    
    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Stock Strategy Comparison: Buy & Hold vs Active Trading\n(2023-2026, 3 years)', 
                 fontsize=16, fontweight='bold')
    
    # Plot 1: Bar chart comparison
    ax1 = axes[0, 0]
    x = np.arange(len(stocks))
    width = 0.35
    
    bars1 = ax1.bar(x - width/2, buy_hold, width, label='Buy & Hold', color='green', alpha=0.7)
    bars2 = ax1.bar(x + width/2, trading, width, label='Active Trading', color='red', alpha=0.7)
    
    ax1.set_xlabel('Stock')
    ax1.set_ylabel('Return (%)')
    ax1.set_title('Returns Comparison')
    ax1.set_xticks(x)
    ax1.set_xticklabels(stocks)
    ax1.legend()
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax1.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%',
                    ha='center', va='bottom' if height > 0 else 'top',
                    fontsize=9)
    
    # Plot 2: $10,000 investment growth
    ax2 = axes[0, 1]
    
    initial = 10000
    bh_values = [initial * (1 + r/100) for r in buy_hold]
    tr_values = [initial * (1 + r/100) for r in trading]
    
    ax2.plot(stocks, bh_values, marker='o', linewidth=3, markersize=10, 
             label='Buy & Hold', color='green')
    ax2.plot(stocks, tr_values, marker='o', linewidth=3, markersize=10,
             label='Active Trading', color='red')
    ax2.axhline(y=initial, color='black', linestyle='--', label='Initial $10k')
    
    ax2.set_xlabel('Stock')
    ax2.set_ylabel('Portfolio Value ($)')
    ax2.set_title('$10,000 Investment Growth')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Format y-axis as currency
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    # Plot 3: Win Rate comparison
    ax3 = axes[1, 0]
    
    # Trading stats from our tests
    strategies = ['Pattern\nRecognition', 'Adaptive\nTREND/RANGE', 
                  'Stock\nOptimized', 'Balanced\nApproach', 'Simple\nTrend']
    win_rates = [65, 64, 67, 65, 63]
    profit_factors = [0.65, 0.71, 0.82, 0.84, 0.91]
    final_returns = [-62, -60, -10, -47, -5]
    
    x = np.arange(len(strategies))
    
    # Create bars colored by final return
    colors = ['red' if r < 0 else 'green' for r in final_returns]
    bars = ax3.bar(x, win_rates, color=colors, alpha=0.6)
    
    ax3.set_xlabel('Strategy')
    ax3.set_ylabel('Win Rate (%)')
    ax3.set_title('Trading Strategies: High Win Rate ≠ Profit!')
    ax3.set_xticks(x)
    ax3.set_xticklabels(strategies, fontsize=9)
    ax3.axhline(y=50, color='gray', linestyle='--', label='50% baseline')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # Add profit factor as text
    for i, (wr, pf, ret) in enumerate(zip(win_rates, profit_factors, final_returns)):
        ax3.text(i, wr + 1, f'WR:{wr}%\nPF:{pf:.2f}\nRet:{ret}%',
                ha='center', va='bottom', fontsize=8)
    
    # Plot 4: Expected returns from screener
    ax4 = axes[1, 1]
    
    # Top 4 from screener
    screened_stocks = ['LRCX', 'MU', 'TSM', 'ASML']
    returns_6m = [81.3, 159.7, 33.7, 50.0]
    scores = [67, 65, 52, 50]
    
    # Create bar chart with gradient
    bars = ax4.bar(screened_stocks, returns_6m, color=plt.cm.RdYlGn(np.array(scores)/100))
    
    ax4.set_xlabel('Stock (From Screener)')
    ax4.set_ylabel('6-Month Return (%)')
    ax4.set_title('Stock Screener Top Picks Performance')
    ax4.grid(True, alpha=0.3)
    
    # Add score and return labels
    for i, (stock, ret, score) in enumerate(zip(screened_stocks, returns_6m, scores)):
        ax4.text(i, ret + 5, f'{ret:.1f}%\nScore:{score}',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # Add average line
    avg = np.mean(returns_6m)
    ax4.axhline(y=avg, color='blue', linestyle='--', linewidth=2, 
                label=f'Average: {avg:.1f}%')
    ax4.legend()
    
    plt.tight_layout()
    plt.savefig('stock_strategy_comparison.png', dpi=300, bbox_inches='tight')
    print("📊 Chart saved: stock_strategy_comparison.png")
    plt.close()


def plot_screener_results():
    """
    Visualize stock screener scoring breakdown
    """
    
    # Top 4 stocks scoring
    stocks = ['LRCX', 'MU', 'TSM', 'ASML']
    
    # Score components
    momentum = [15, 15, 12, 10]
    rel_strength = [25, 25, 15, 15]
    trend_quality = [12, 8, 15, 15]
    volume = [5, 7, 0, 0]
    risk_reward = [10, 10, 10, 10]
    
    # Create stacked bar chart
    fig, ax = plt.subplots(figsize=(12, 8))
    
    width = 0.6
    x = np.arange(len(stocks))
    
    # Stack bars
    p1 = ax.bar(x, momentum, width, label='Momentum (30)', color='#FF6B6B')
    p2 = ax.bar(x, rel_strength, width, bottom=momentum, label='Rel Strength (25)', color='#4ECDC4')
    p3 = ax.bar(x, trend_quality, width, bottom=np.array(momentum)+np.array(rel_strength), 
                label='Trend Quality (20)', color='#45B7D1')
    p4 = ax.bar(x, volume, width, 
                bottom=np.array(momentum)+np.array(rel_strength)+np.array(trend_quality),
                label='Volume (15)', color='#FFA07A')
    p5 = ax.bar(x, risk_reward, width,
                bottom=np.array(momentum)+np.array(rel_strength)+np.array(trend_quality)+np.array(volume),
                label='Risk/Reward (10)', color='#98D8C8')
    
    ax.set_ylabel('Score')
    ax.set_xlabel('Stock')
    ax.set_title('Stock Screener - Scoring Breakdown (Top 4)', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(stocks)
    ax.legend(loc='upper right')
    
    # Add total scores on top
    totals = [sum(x) for x in zip(momentum, rel_strength, trend_quality, volume, risk_reward)]
    for i, total in enumerate(totals):
        ax.text(i, total + 2, f'{total}/100', ha='center', va='bottom', 
                fontsize=12, fontweight='bold')
    
    ax.axhline(y=50, color='red', linestyle='--', linewidth=1, alpha=0.5, label='Min Score (50)')
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('screener_scoring_breakdown.png', dpi=300, bbox_inches='tight')
    print("📊 Chart saved: screener_scoring_breakdown.png")
    plt.close()


def plot_portfolio_simulation():
    """
    Simulate $10k portfolio growth over 6 months
    """
    
    # Simulate portfolio
    months = ['Month 0', 'Month 1', 'Month 2', 'Month 3', 'Month 4', 'Month 5', 'Month 6']
    
    # Top 3 equal weight portfolio (LRCX, MU, TSM)
    # Assume linear growth (simplified)
    target_return = 91.5  # % over 6 months
    monthly_return = target_return / 6
    
    portfolio_values = [10000]
    for i in range(1, 7):
        portfolio_values.append(portfolio_values[-1] * (1 + monthly_return/100))
    
    # Buy & Hold comparison (average of top stocks)
    bh_target = 200  # Average of NVDA, MSFT, etc
    bh_monthly = bh_target / 36  # Over 3 years = 36 months, but show 6 months
    bh_values = [10000]
    for i in range(1, 7):
        bh_values.append(bh_values[-1] * (1 + bh_monthly/100))
    
    # Trading (loses money)
    trading_target = -30  # Average loss
    trading_monthly = trading_target / 6
    trading_values = [10000]
    for i in range(1, 7):
        trading_values.append(trading_values[-1] * (1 + trading_monthly/100))
    
    # Plot
    fig, ax = plt.subplots(figsize=(12, 8))
    
    ax.plot(months, portfolio_values, marker='o', linewidth=3, markersize=10,
            label='Screener Portfolio (Top 3)', color='green', linestyle='-')
    ax.plot(months, bh_values, marker='s', linewidth=2, markersize=8,
            label='Buy & Hold (Avg)', color='blue', linestyle='--')
    ax.plot(months, trading_values, marker='x', linewidth=2, markersize=8,
            label='Active Trading', color='red', linestyle=':')
    
    ax.axhline(y=10000, color='black', linestyle='-', linewidth=1, alpha=0.3)
    
    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Portfolio Value ($)', fontsize=12)
    ax.set_title('$10,000 Portfolio Growth Comparison\n(Screener vs Buy & Hold vs Trading)', 
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    
    # Format y-axis as currency
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    # Add final values
    final_screener = portfolio_values[-1]
    final_bh = bh_values[-1]
    final_trading = trading_values[-1]
    
    ax.text(6, final_screener + 300, f'${final_screener:,.0f}\n+{((final_screener/10000)-1)*100:.1f}%',
            ha='right', va='bottom', fontsize=10, fontweight='bold', color='green')
    ax.text(6, final_bh + 300, f'${final_bh:,.0f}\n+{((final_bh/10000)-1)*100:.1f}%',
            ha='right', va='bottom', fontsize=10, fontweight='bold', color='blue')
    ax.text(6, final_trading - 300, f'${final_trading:,.0f}\n{((final_trading/10000)-1)*100:.1f}%',
            ha='right', va='top', fontsize=10, fontweight='bold', color='red')
    
    plt.tight_layout()
    plt.savefig('portfolio_growth_simulation.png', dpi=300, bbox_inches='tight')
    print("📊 Chart saved: portfolio_growth_simulation.png")
    plt.close()


if __name__ == "__main__":
    print("\n📊 Creating visualizations...\n")
    
    # Generate all charts
    compare_strategies()
    plot_screener_results()
    plot_portfolio_simulation()
    
    print("\n✅ All visualizations created!")
    print("\nGenerated files:")
    print("  1. stock_strategy_comparison.png")
    print("  2. screener_scoring_breakdown.png")
    print("  3. portfolio_growth_simulation.png")
