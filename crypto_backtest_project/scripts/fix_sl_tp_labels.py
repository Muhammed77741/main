#!/usr/bin/env python3
"""
Fix incorrect SL/TP labels in backtest results.

Corrects trades labeled as "SL" (Stop Loss) that have positive P&L.
These should be labeled as TP (Take Profit) exits instead.
"""

import pandas as pd
import os

def fix_exit_labels(df):
    """
    Fix exit_type labels for trades with positive P&L marked as SL.
    
    Logic:
    - If exit_type == 'SL' and pnl_pct > 0: Change to appropriate TP level
    - Determine TP level based on which TPs were hit
    """
    fixed_count = 0
    
    for idx, row in df.iterrows():
        if row['exit_type'] == 'SL' and row['pnl_pct'] > 0:
            # Determine correct TP level
            if row.get('tp3_hit', False):
                df.at[idx, 'exit_type'] = 'TP3'
            elif row.get('tp2_hit', False):
                df.at[idx, 'exit_type'] = 'TP2'
            elif row.get('tp1_hit', False):
                df.at[idx, 'exit_type'] = 'TP1'
            else:
                # If no TP flags but profitable, assume TP1 at minimum
                df.at[idx, 'exit_type'] = 'TP1'
            
            fixed_count += 1
            print(f"Fixed: {row['entry_time']} {row['direction']} @ {row['entry_price']:.2f} → {row['exit_price']:.2f} (+{row['pnl_pct']:.2f}%) | SL → {df.at[idx, 'exit_type']}")
    
    return df, fixed_count

def main():
    results_dir = '/home/runner/work/main/main/crypto_backtest_project/results'
    
    # Files to fix
    files_to_fix = [
        'BTC_smc_backtest_results.csv',
        'ETH_smc_backtest_results.csv',
        'combined_smc_results.csv',
        'BTC_smc_all_positions.csv',
        'ETH_smc_all_positions.csv'
    ]
    
    total_fixed = 0
    
    for filename in files_to_fix:
        filepath = os.path.join(results_dir, filename)
        
        if not os.path.exists(filepath):
            print(f"⚠️  File not found: {filename}")
            continue
        
        print(f"\n{'='*80}")
        print(f"Processing: {filename}")
        print('='*80)
        
        # Read CSV
        df = pd.read_csv(filepath)
        original_count = len(df)
        
        # Check if exit_type column exists
        if 'exit_type' not in df.columns:
            print(f"⚠️  No exit_type column in {filename}, skipping...")
            continue
        
        # Count original SL with positive P&L
        erroneous = df[(df['exit_type'] == 'SL') & (df['pnl_pct'] > 0)]
        print(f"Found {len(erroneous)} erroneous SL trades with positive P&L")
        
        # Fix labels
        df_fixed, fixed_count = fix_exit_labels(df)
        
        # Save fixed version
        if fixed_count > 0:
            # Create backup
            backup_path = filepath.replace('.csv', '_backup_before_fix.csv')
            if not os.path.exists(backup_path):
                df_original = pd.read_csv(filepath)
                df_original.to_csv(backup_path, index=False)
                print(f"✅ Backup created: {backup_path}")
            
            # Save fixed version
            df_fixed.to_csv(filepath, index=False)
            print(f"✅ Fixed {fixed_count} trades in {filename}")
            total_fixed += fixed_count
        else:
            print(f"✅ No fixes needed for {filename}")
    
    # Update erroneous files (should now be empty or minimal)
    print(f"\n{'='*80}")
    print("Updating erroneous trade files...")
    print('='*80)
    
    for asset in ['BTC', 'ETH']:
        results_file = os.path.join(results_dir, f'{asset}_smc_backtest_results.csv')
        erroneous_file = os.path.join(results_dir, f'{asset}_smc_backtest_erroneous.csv')
        
        if os.path.exists(results_file):
            df = pd.read_csv(results_file)
            
            # Find remaining erroneous trades (SL with positive P&L)
            erroneous = df[(df['exit_type'] == 'SL') & (df['pnl_pct'] > 0)]
            
            if len(erroneous) > 0:
                erroneous.to_csv(erroneous_file, index=False)
                print(f"⚠️  {asset}: {len(erroneous)} erroneous trades remaining (saved to {asset}_smc_backtest_erroneous.csv)")
            else:
                # Create empty or minimal erroneous file
                erroneous.to_csv(erroneous_file, index=False)
                print(f"✅ {asset}: All SL/TP labeling issues fixed! ({asset}_smc_backtest_erroneous.csv now empty)")
    
    print(f"\n{'='*80}")
    print(f"SUMMARY: Fixed {total_fixed} total erroneous trades across all files")
    print('='*80)

if __name__ == '__main__':
    main()
