# 📦 Trading Bot Manager - Windows Application Package

Complete Windows application with professional licensing system.

## 📋 Overview

This is a complete, production-ready Windows application with:
- ✅ **7-day trial system** (encrypted, anti-tamper)
- ✅ **License key activation** (HWID-bound, algorithmic validation)
- ✅ **Professional .exe build** (PyInstaller, optimized)
- ✅ **Windows installer** (Inno Setup script included)
- ✅ **Desktop & Start Menu shortcuts**
- ✅ **Security features** (encryption, anti-bypass)

## 🏗️ Project Structure

```
trading_app/
├── main.py                      # Main entry point with licensing
├── gui/
│   ├── main_window.py           # Main UI (updated for licensing)
│   ├── activation_dialog.py     # License activation UI
│   └── ...                      # Other UI components
├── licensing/                   # 🆕 Licensing system
│   ├── __init__.py
│   ├── license_manager.py       # Main license manager
│   ├── trial_manager.py         # 7-day trial handling
│   ├── keygen.py                # License key generation/validation
│   └── hwid.py                  # Hardware ID generation
├── tools/                       # 🆕 Utility tools
│   └── keygen_tool.py           # GUI tool for generating keys
├── resources/                   # 🆕 Resources for packaging
│   ├── icons/                   # Application icons
│   └── installer/               # Installer scripts
│       └── setup.iss            # Inno Setup script
├── build_enhanced.py            # 🆕 Enhanced build script
├── requirements.txt             # Updated dependencies
└── README.md                    # This file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd trading_app
pip install -r requirements.txt
```

### 2. Build Application

```bash
python build_enhanced.py
```

This will:
- Build optimized .exe
- Create release package
- Generate installer script
- Provide complete instructions

### 3. Test Application

```bash
cd release/TradingBotManager
./TradingBotManager.exe
```

## 🔑 Licensing System

### Trial Version (7 Days)

**How it works:**
1. On first launch, user sees activation dialog
2. User can choose "Start 7-Day Trial"
3. Trial data is encrypted and stored in `%PROGRAMDATA%\TradingBotManager\.config\`
4. Trial countdown shows in main window
5. After 7 days, activation required

**Security features:**
- ✅ Encrypted storage (Fernet encryption)
- ✅ HWID binding (can't copy to another PC)
- ✅ System time manipulation detection
- ✅ Multiple backup locations
- ✅ Hidden files (Windows attributes)

### License Key Activation

**How it works:**
1. User gets their Hardware ID from activation dialog
2. You generate license key using `keygen_tool.py`
3. User enters license key
4. Key is validated locally (no server needed)
5. License is saved encrypted

**License Key Format:**
```
XXXXX-XXXXX-XXXXX-XXXXX-XXXXX
Example: AB12C-34DE5-6FG78-9HIJ0-12K3L
```

**Features:**
- ✅ HWID-bound (one license = one PC)
- ✅ Algorithmic validation (no server needed)
- ✅ Lifetime or time-limited licenses
- ✅ Feature-based licenses (ALL, BTC, ETH, XAUUSD)
- ✅ RSA-based security

## 🛠️ Generating License Keys

### Method 1: GUI Tool (Recommended)

```bash
cd trading_app
python tools/keygen_tool.py
```

This opens a GUI where you can:
- Enter customer's Hardware ID
- Select duration (7 days to Lifetime)
- Select features (ALL, BTC, ETH, XAUUSD)
- Generate and copy license key

### Method 2: Python Script

```python
from licensing import generate_license_key, get_hardware_id

# Get Hardware ID
hwid = get_hardware_id()
print(f"Hardware ID: {hwid}")

# Generate 1-year license with all features
license_key = generate_license_key(hwid, days=365, features="ALL")
print(f"License Key: {license_key}")

# Generate lifetime license
license_key_lifetime = generate_license_key(hwid, days=0, features="ALL")
print(f"Lifetime Key: {license_key_lifetime}")
```

### License Types

**Duration:**
- `days=7` - 7-day trial
- `days=30` - 1 month
- `days=365` - 1 year
- `days=0` - Lifetime

**Features:**
- `"ALL"` - Full access to all bots
- `"BTC"` - Bitcoin bot only
- `"ETH"` - Ethereum bot only
- `"XAUUSD"` - Gold bot only

## 📦 Building & Distribution

### Step 1: Build Application

```bash
python build_enhanced.py
```

**Output:**
- `dist/TradingBotManager/` - Application files
- `release/TradingBotManager/` - Distribution package
- `release/README.txt` - User documentation

### Step 2: Create Installer (Optional)

1. Install Inno Setup from https://jrsoftware.org/isinfo.php
2. Open `resources/installer/setup.iss` in Inno Setup
3. Click "Compile"
4. Installer will be in `resources/installer/Output/`

**Installer features:**
- Desktop shortcut
- Start Menu shortcut
- Proper uninstaller
- Windows 10/11 compatibility check
- Admin privileges when needed

### Step 3: Distribute

**Option A - Folder Distribution:**
- Share the entire `release/TradingBotManager/` folder
- Include `README.txt`
- User runs `TradingBotManager.exe`

**Option B - Installer Distribution:**
- Share the `TradingBotManager_Setup_v1.0.0.exe`
- User runs installer
- Application installed to Program Files
- Shortcuts created automatically

## 🔒 Security Features

### Anti-Tampering
- ✅ Encrypted trial and license data
- ✅ Hardware ID validation
- ✅ System time manipulation detection
- ✅ Multiple data storage locations
- ✅ Data integrity checks

### What's Protected
- Trial start/end dates
- License activation data
- Hardware binding
- Feature access

### Bypass Prevention
- ❌ Can't delete files to reset trial (encrypted, hidden, backed up)
- ❌ Can't change system time (detection built-in)
- ❌ Can't copy to another PC (HWID-bound)
- ❌ Can't modify license files (encrypted with HWID-based key)

### Additional Security (Optional)
For even more security, you could add:
- Code obfuscation with PyArmor
- Online license validation
- Periodic re-validation
- Usage analytics

## 🧪 Testing

### Test Trial System

```bash
# Run application
python main.py

# First run - should show activation dialog
# Click "Start 7-Day Trial"
# Application should start and show trial status

# Check trial files (hidden in ProgramData)
# Windows: %PROGRAMDATA%\TradingBotManager\.config\
```

### Test License Activation

```bash
# 1. Get Hardware ID from activation dialog
# 2. Generate license key:
python tools/keygen_tool.py

# 3. Enter license key in application
# 4. Should activate successfully
```

### Test HWID Binding

```bash
# Try to copy .lic.dat file to different machine
# Should fail validation due to HWID mismatch
```

## 📋 Requirements

### Development
- Python 3.10+
- Windows 10/11 (64-bit)
- PyInstaller 6.0+
- PySide6 6.6+
- cryptography 41.0+

### End User
- Windows 10/11 (64-bit)
- 4 GB RAM (minimum)
- 500 MB disk space
- Internet connection
- MetaTrader 5 (for XAUUSD bot)
- Binance API keys (for crypto bots)

## 📝 Configuration

### Environment Variables (.env)

Create `.env` file next to the executable:

```bash
# Binance API (for crypto bots)
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
BINANCE_TESTNET=true

# Telegram (optional notifications)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## 🐛 Troubleshooting

### Build Issues

**"PyInstaller not found"**
```bash
pip install pyinstaller
```

**"Module not found" during build**
```bash
pip install -r requirements.txt
```

### Runtime Issues

**"License validation failed"**
- Check Hardware ID matches
- Verify license key was entered correctly
- Ensure not copied from another machine

**"Trial expired immediately"**
- Check system date/time is correct
- Don't manipulate system time
- Contact support if issue persists

**Application doesn't start**
- Run as Administrator
- Check antivirus hasn't blocked it
- Verify Windows 10/11 64-bit

## 🔄 Updates & Maintenance

### Updating the Application

1. Update code
2. Increment version in `main.py` and `build_enhanced.py`
3. Rebuild: `python build_enhanced.py`
4. Update installer script version
5. Recompile installer
6. Distribute new version

### License Key Management

**Best practices:**
- Keep private key secure (in `keygen.py`)
- Log all generated licenses
- Track which Hardware IDs have licenses
- Provide license transfer process
- Set up support system for license issues

## 📞 Support

### For Developers
- Check `licensing/` modules for implementation details
- See `gui/activation_dialog.py` for UI
- Review `main.py` for integration

### For Users
Include in your distribution:
- README.txt with setup instructions
- Support contact information
- FAQ for common issues
- License agreement

## 📄 License

This application and its licensing system are proprietary software.
Modify the licensing system as needed for your use case.

## 🎯 Next Steps

1. ✅ Build application: `python build_enhanced.py`
2. ✅ Test trial system
3. ✅ Test license activation
4. ✅ Create installer (Inno Setup)
5. ✅ Test on clean Windows machine
6. ✅ Set up license key generation process
7. ✅ Prepare distribution materials
8. ✅ Set up support system

## ⚡ Advanced Customization

### Changing Trial Period

Edit `licensing/trial_manager.py`:
```python
TRIAL_DAYS = 7  # Change to desired days
```

### Changing License Key Format

Edit `licensing/keygen.py`:
- Modify key generation algorithm
- Update validation logic
- Keep public/private key pair secure

### Adding Features

Edit `licensing/license_manager.py`:
```python
def is_feature_available(self, feature: str) -> bool:
    # Add your custom feature checks
```

---

**Built with ❤️ for professional Windows distribution**
