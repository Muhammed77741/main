#!/usr/bin/env python3
"""
Comprehensive Crypto Backtesting Runner
========================================
This script automates the entire crypto backtesting pipeline:
1. Generates crypto data for BTC and ETH (2 years)
2. Runs backtests using crypto_backtest_v3.py
3. Creates detailed result CSV files with monthly breakdown
4. Prints comprehensive statistics

Usage: python run_all_crypto_backtest.py
"""

import os
import sys
import subprocess
import pandas as pd
from datetime import datetime, timedelta
import json

class CryptoBacktestRunner:
    def __init__(self):
        self.data_dir = "crypto_data"
        self.results_dir = "backtest_results"
        self.cryptos = ["BTC", "ETH"]
        self.years = 2
        self.start_date = (datetime.now() - timedelta(days=365*self.years)).strftime("%Y-%m-%d")
        self.end_date = datetime.now().strftime("%Y-%m-%d")
        
        # Create necessary directories
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
    
    def print_header(self, text):
        """Print formatted section header"""
        print("\n" + "="*80)
        print(f" {text}")
        print("="*80 + "\n")
    
    def print_step(self, step_num, text):
        """Print formatted step"""
        print(f"\n{'='*80}")
        print(f"STEP {step_num}: {text}")
        print(f"{'='*80}\n")
    
    def generate_crypto_data(self):
        """Generate crypto data for BTC and ETH"""
        self.print_step(1, "GENERATING CRYPTO DATA")
        
        for crypto in self.cryptos:
            print(f"📊 Generating {crypto} data for {self.years} years...")
            print(f"   Period: {self.start_date} to {self.end_date}")
            
            try:
                # Run generate_crypto_data.py
                cmd = [
                    sys.executable,
                    "generate_crypto_data.py",
                    "--crypto", crypto,
                    "--start", self.start_date,
                    "--end", self.end_date,
                    "--output", f"{self.data_dir}/{crypto}_data.csv"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                print(f"   ✓ {crypto} data generated successfully")
                
                # Verify file was created
                file_path = f"{self.data_dir}/{crypto}_data.csv"
                if os.path.exists(file_path):
                    df = pd.read_csv(file_path)
                    print(f"   → Records: {len(df)} rows")
                    print(f"   → Saved to: {file_path}")
                
            except subprocess.CalledProcessError as e:
                print(f"   ✗ Error generating {crypto} data:")
                print(f"   {e.stderr}")
                return False
            except Exception as e:
                print(f"   ✗ Unexpected error: {str(e)}")
                return False
        
        print("\n✓ All crypto data generated successfully!")
        return True
    
    def run_backtests(self):
        """Run backtests for all cryptocurrencies"""
        self.print_step(2, "RUNNING BACKTESTS")
        
        results = {}
        
        for crypto in self.cryptos:
            print(f"\n{'─'*80}")
            print(f"🔄 Running backtest for {crypto}...")
            print(f"{'─'*80}\n")
            
            try:
                data_file = f"{self.data_dir}/{crypto}_data.csv"
                output_file = f"{self.results_dir}/{crypto}_backtest_results.csv"
                
                # Run crypto_backtest_v3.py
                cmd = [
                    sys.executable,
                    "crypto_backtest_v3.py",
                    "--input", data_file,
                    "--output", output_file,
                    "--crypto", crypto
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                print(result.stdout)
                
                # Store results
                if os.path.exists(output_file):
                    results[crypto] = output_file
                    print(f"\n✓ {crypto} backtest completed successfully")
                    print(f"   → Results saved to: {output_file}")
                
            except subprocess.CalledProcessError as e:
                print(f"\n✗ Error running {crypto} backtest:")
                print(f"   {e.stderr}")
                results[crypto] = None
            except Exception as e:
                print(f"\n✗ Unexpected error: {str(e)}")
                results[crypto] = None
        
        print(f"\n{'─'*80}")
        print("✓ All backtests completed!")
        print(f"{'─'*80}")
        
        return results
    
    def create_monthly_breakdown(self, crypto, results_file):
        """Create monthly breakdown from backtest results"""
        try:
            df = pd.read_csv(results_file)
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['year_month'] = df['timestamp'].dt.to_period('M')
            
            # Calculate monthly statistics
            monthly_stats = df.groupby('year_month').agg({
                'portfolio_value': ['first', 'last', 'min', 'max'],
                'total_return': 'last',
                'realized_pnl': 'sum',
                'position_size': 'mean'
            }).reset_index()
            
            # Flatten column names
            monthly_stats.columns = ['_'.join(col).strip('_') if col[1] else col[0] 
                                    for col in monthly_stats.columns.values]
            
            # Calculate monthly returns
            monthly_stats['monthly_return'] = (
                (monthly_stats['portfolio_value_last'] - monthly_stats['portfolio_value_first']) / 
                monthly_stats['portfolio_value_first'] * 100
            )
            
            # Calculate number of trades per month
            trades_per_month = df.groupby('year_month').size().reset_index(name='num_trades')
            monthly_stats = monthly_stats.merge(trades_per_month, on='year_month')
            
            # Save monthly breakdown
            monthly_file = f"{self.results_dir}/{crypto}_monthly_breakdown.csv"
            monthly_stats.to_csv(monthly_file, index=False)
            
            return monthly_file, monthly_stats
            
        except Exception as e:
            print(f"✗ Error creating monthly breakdown for {crypto}: {str(e)}")
            return None, None
    
    def print_statistics(self, crypto, results_file, monthly_stats):
        """Print comprehensive statistics"""
        try:
            df = pd.read_csv(results_file)
            
            print(f"\n{'='*80}")
            print(f" {crypto} BACKTEST STATISTICS")
            print(f"{'='*80}\n")
            
            # Overall Performance
            print("📈 OVERALL PERFORMANCE")
            print(f"{'─'*80}")
            initial_value = df['portfolio_value'].iloc[0]
            final_value = df['portfolio_value'].iloc[-1]
            total_return = ((final_value - initial_value) / initial_value) * 100
            
            print(f"   Initial Portfolio Value:  ${initial_value:,.2f}")
            print(f"   Final Portfolio Value:    ${final_value:,.2f}")
            print(f"   Total Return:             {total_return:+.2f}%")
            print(f"   Total Realized P&L:       ${df['realized_pnl'].sum():,.2f}")
            
            # Risk Metrics
            print(f"\n💼 RISK METRICS")
            print(f"{'─'*80}")
            returns = df['portfolio_value'].pct_change().dropna()
            volatility = returns.std() * (252 ** 0.5) * 100  # Annualized
            max_drawdown = ((df['portfolio_value'] / df['portfolio_value'].cummax() - 1) * 100).min()
            sharpe = (returns.mean() / returns.std()) * (252 ** 0.5) if returns.std() > 0 else 0
            
            print(f"   Annualized Volatility:    {volatility:.2f}%")
            print(f"   Maximum Drawdown:         {max_drawdown:.2f}%")
            print(f"   Sharpe Ratio:             {sharpe:.2f}")
            
            # Trading Activity
            print(f"\n📊 TRADING ACTIVITY")
            print(f"{'─'*80}")
            total_trades = len(df)
            avg_position = df['position_size'].mean()
            
            # Count position changes (buys/sells)
            position_changes = (df['position_size'].diff() != 0).sum()
            
            print(f"   Total Data Points:        {total_trades:,}")
            print(f"   Position Changes:         {position_changes:,}")
            print(f"   Average Position Size:    {avg_position:.4f} {crypto}")
            
            # Monthly Performance
            if monthly_stats is not None and len(monthly_stats) > 0:
                print(f"\n📅 MONTHLY PERFORMANCE")
                print(f"{'─'*80}")
                avg_monthly_return = monthly_stats['monthly_return'].mean()
                best_month = monthly_stats.loc[monthly_stats['monthly_return'].idxmax()]
                worst_month = monthly_stats.loc[monthly_stats['monthly_return'].idxmin()]
                positive_months = (monthly_stats['monthly_return'] > 0).sum()
                total_months = len(monthly_stats)
                
                print(f"   Average Monthly Return:   {avg_monthly_return:+.2f}%")
                print(f"   Best Month:               {best_month['year_month']} ({best_month['monthly_return']:+.2f}%)")
                print(f"   Worst Month:              {worst_month['year_month']} ({worst_month['monthly_return']:+.2f}%)")
                print(f"   Win Rate:                 {positive_months}/{total_months} ({positive_months/total_months*100:.1f}%)")
            
            # Price Performance
            print(f"\n💰 PRICE PERFORMANCE")
            print(f"{'─'*80}")
            if 'price' in df.columns:
                initial_price = df['price'].iloc[0]
                final_price = df['price'].iloc[-1]
                price_return = ((final_price - initial_price) / initial_price) * 100
                
                print(f"   Initial Price:            ${initial_price:,.2f}")
                print(f"   Final Price:              ${final_price:,.2f}")
                print(f"   Price Return:             {price_return:+.2f}%")
                print(f"   Price Min:                ${df['price'].min():,.2f}")
                print(f"   Price Max:                ${df['price'].max():,.2f}")
            
            print(f"\n{'='*80}\n")
            
        except Exception as e:
            print(f"✗ Error printing statistics for {crypto}: {str(e)}")
    
    def create_summary_report(self, all_results):
        """Create a summary report comparing all cryptocurrencies"""
        self.print_step(3, "CREATING SUMMARY REPORT")
        
        summary_data = []
        
        for crypto, results_file in all_results.items():
            if results_file and os.path.exists(results_file):
                try:
                    df = pd.read_csv(results_file)
                    initial_value = df['portfolio_value'].iloc[0]
                    final_value = df['portfolio_value'].iloc[-1]
                    total_return = ((final_value - initial_value) / initial_value) * 100
                    
                    returns = df['portfolio_value'].pct_change().dropna()
                    volatility = returns.std() * (252 ** 0.5) * 100
                    max_drawdown = ((df['portfolio_value'] / df['portfolio_value'].cummax() - 1) * 100).min()
                    sharpe = (returns.mean() / returns.std()) * (252 ** 0.5) if returns.std() > 0 else 0
                    
                    summary_data.append({
                        'Cryptocurrency': crypto,
                        'Initial Value ($)': initial_value,
                        'Final Value ($)': final_value,
                        'Total Return (%)': total_return,
                        'Volatility (%)': volatility,
                        'Max Drawdown (%)': max_drawdown,
                        'Sharpe Ratio': sharpe,
                        'Total Realized P&L ($)': df['realized_pnl'].sum()
                    })
                    
                except Exception as e:
                    print(f"✗ Error processing {crypto}: {str(e)}")
        
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            summary_file = f"{self.results_dir}/summary_report.csv"
            summary_df.to_csv(summary_file, index=False)
            
            print("📊 COMPARISON SUMMARY")
            print(f"{'─'*80}\n")
            print(summary_df.to_string(index=False))
            print(f"\n✓ Summary report saved to: {summary_file}\n")
            
            return summary_file
        
        return None
    
    def run(self):
        """Execute the complete backtesting pipeline"""
        self.print_header("CRYPTO BACKTESTING PIPELINE - FULL EXECUTION")
        
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📅 Data Period: {self.start_date} to {self.end_date} ({self.years} years)")
        print(f"💰 Cryptocurrencies: {', '.join(self.cryptos)}")
        print(f"📁 Data Directory: {self.data_dir}")
        print(f"📁 Results Directory: {self.results_dir}")
        
        try:
            # Step 1: Generate data
            if not self.generate_crypto_data():
                print("\n✗ Pipeline failed at data generation step")
                return False
            
            # Step 2: Run backtests
            results = self.run_backtests()
            
            # Step 3: Create monthly breakdowns and print statistics
            self.print_step(3, "CREATING MONTHLY BREAKDOWNS & STATISTICS")
            
            for crypto, results_file in results.items():
                if results_file and os.path.exists(results_file):
                    print(f"\n📊 Processing {crypto} results...")
                    monthly_file, monthly_stats = self.create_monthly_breakdown(crypto, results_file)
                    
                    if monthly_file:
                        print(f"   ✓ Monthly breakdown saved to: {monthly_file}")
                    
                    # Print comprehensive statistics
                    self.print_statistics(crypto, results_file, monthly_stats)
            
            # Step 4: Create summary report
            self.create_summary_report(results)
            
            # Final summary
            self.print_header("PIPELINE EXECUTION COMPLETED")
            print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"\n✓ All tasks completed successfully!")
            print(f"\n📁 Results Location: {self.results_dir}/")
            print(f"   - Individual backtest results: {self.results_dir}/*_backtest_results.csv")
            print(f"   - Monthly breakdowns: {self.results_dir}/*_monthly_breakdown.csv")
            print(f"   - Summary report: {self.results_dir}/summary_report.csv")
            print(f"\n{'='*80}\n")
            
            return True
            
        except Exception as e:
            print(f"\n✗ Pipeline failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point"""
    runner = CryptoBacktestRunner()
    success = runner.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
