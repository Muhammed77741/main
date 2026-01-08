"""
Build script for creating Windows .exe
Run: python build_exe.py
"""
import PyInstaller.__main__
import os
import sys

def build_exe():
    """Build .exe using PyInstaller"""

    # Get absolute paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, 'main.py')
    trading_bots_dir = os.path.join(os.path.dirname(script_dir), 'trading_bots')

    # PyInstaller arguments
    args = [
        main_script,
        '--name=TradingBotManager',
        '--onefile',
        '--windowed',  # No console window
        f'--add-data={trading_bots_dir};trading_bots',  # Include trading bots
        '--hidden-import=PySide6',
        '--hidden-import=ccxt',
        '--hidden-import=MetaTrader5',
        '--hidden-import=pandas',
        '--hidden-import=numpy',
        '--hidden-import=telegram',
        '--collect-all=PySide6',
        '--collect-all=ccxt',
        '--noconfirm',  # Overwrite without asking
        # '--icon=assets/icon.ico',  # Uncomment when icon is added
    ]

    # Run PyInstaller
    PyInstaller.__main__.run(args)

    print("\n" + "="*60)
    print("✅ Build complete!")
    print("="*60)
    print(f"\nExecutable created in: {os.path.join(script_dir, 'dist')}")
    print("\nFile: TradingBotManager.exe")
    print("\n⚠️  Note: Copy trading_bots/ folder to the same directory as .exe")
    print("="*60)


if __name__ == '__main__':
    try:
        build_exe()
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        sys.exit(1)
