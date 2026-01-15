"""
Build script for creating Windows .exe
Run: python build_exe.py
"""
import PyInstaller.__main__
import os
import sys
import shutil

def build_exe():
    """Build .exe using PyInstaller"""

    # Get absolute paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, 'main.py')
    trading_bots_dir = os.path.join(os.path.dirname(script_dir), 'trading_bots')

    print("="*60)
    print("🔨 Building Trading Bot Manager .exe")
    print("="*60)
    print(f"\nMain script: {main_script}")
    print(f"Trading bots: {trading_bots_dir}")
    print("\n⏳ Building... This may take a few minutes...")

    # PyInstaller arguments
    args = [
        main_script,
        '--name=TradingBotManager',
        '--onefile',  # Single .exe file
        '--windowed',  # No console window (GUI mode)
        f'--add-data={trading_bots_dir};trading_bots',  # Include trading bots

        # Hidden imports for packages
        '--hidden-import=PySide6',
        '--hidden-import=PySide6.QtCore',
        '--hidden-import=PySide6.QtWidgets',
        '--hidden-import=PySide6.QtGui',
        '--hidden-import=ccxt',
        '--hidden-import=MetaTrader5',
        '--hidden-import=pandas',
        '--hidden-import=numpy',
        '--hidden-import=telegram',
        '--hidden-import=python-dotenv',

        # Collect all submodules
        '--collect-all=PySide6',
        '--collect-all=ccxt',

        # Options
        '--noconfirm',  # Overwrite without asking
        '--clean',  # Clean PyInstaller cache

        # Uncomment when you have an icon:
        # '--icon=icon.ico',
    ]

    # Run PyInstaller
    PyInstaller.__main__.run(args)

    # Post-build: Create distribution folder
    dist_dir = os.path.join(script_dir, 'dist')
    release_dir = os.path.join(script_dir, 'release')

    if os.path.exists(release_dir):
        shutil.rmtree(release_dir)
    os.makedirs(release_dir)

    # Copy .exe to release folder
    exe_path = os.path.join(dist_dir, 'TradingBotManager.exe')
    if os.path.exists(exe_path):
        shutil.copy2(exe_path, release_dir)
        print(f"\n✅ Copied .exe to: {release_dir}")

    # Create README for release
    readme_content = """# Trading Bot Manager

## 🚀 How to Run

1. Double-click `TradingBotManager.exe`
2. The application will start automatically

## ⚙️ Configuration

Create a `.env` file in the same folder as the .exe:

```
# For XAUUSD bot (optional - Telegram only)
TELEGRAM_BOT_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id

# For Crypto bots (required)
BINANCE_API_KEY=your_binance_api_key
BINANCE_API_SECRET=your_binance_api_secret
BINANCE_TESTNET=true
```

## 📝 Notes

- First run may take 10-15 seconds to start
- Antivirus may flag the .exe (false positive) - add to exclusions
- Database file `trading_app.db` will be created automatically
- Log files will be created in the same directory

## 🆘 Troubleshooting

**App doesn't start:**
- Right-click .exe → Run as Administrator
- Check antivirus didn't block it

**MT5 connection fails:**
- Make sure MetaTrader 5 is running
- Enable "Algo Trading" in MT5 settings

**Binance connection fails:**
- Check API keys in .env file
- Make sure API has Futures trading permission
- Use BINANCE_TESTNET=true for testing

## ⚠️ Disclaimer

Trading involves significant risk. Test on demo/testnet accounts first.
"""

    readme_path = os.path.join(release_dir, 'README.txt')
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)

    print("\n" + "="*60)
    print("✅ BUILD COMPLETE!")
    print("="*60)
    print(f"\n📁 Release folder: {release_dir}")
    print(f"📦 Executable: TradingBotManager.exe")
    print(f"📄 Readme: README.txt")

    print("\n🎯 Next steps:")
    print("1. Go to 'release' folder")
    print("2. Copy TradingBotManager.exe to any location")
    print("3. Create .env file next to .exe (if needed)")
    print("4. Double-click to run!")

    print("\n⚠️  Note for MT5:")
    print("   MetaTrader 5 must be installed and running")

    print("\n⚠️  Note for Crypto bots:")
    print("   Create .env file with Binance API keys")

    print("\n" + "="*60)


if __name__ == '__main__':
    try:
        build_exe()
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        print("\n💡 Make sure you have installed:")
        print("   pip install pyinstaller")
        import traceback
        traceback.print_exc()
        sys.exit(1)
