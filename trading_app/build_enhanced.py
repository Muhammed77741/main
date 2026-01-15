"""
Enhanced Build Script for Trading Bot Manager
Creates optimized Windows .exe with licensing system
"""
import PyInstaller.__main__
import os
import sys
import shutil
from pathlib import Path


def create_icon():
    """Create a basic icon file if it doesn't exist"""
    icon_path = Path(__file__).parent / 'resources' / 'icons' / 'app_icon.ico'
    
    if not icon_path.exists():
        print("⚠️  No icon file found. Will create a placeholder.")
        print(f"   To add a custom icon, place it at: {icon_path}")
        # For now, we'll continue without an icon
        return None
    
    return str(icon_path)


def clean_build_dirs():
    """Clean up previous build directories"""
    script_dir = Path(__file__).parent
    
    dirs_to_clean = ['build', 'dist', '__pycache__']
    
    for dir_name in dirs_to_clean:
        dir_path = script_dir / dir_name
        if dir_path.exists():
            print(f"🧹 Cleaning {dir_name}/...")
            shutil.rmtree(dir_path)


def build_exe():
    """Build .exe using PyInstaller with optimized settings"""
    
    print("=" * 70)
    print("🔨 Building Trading Bot Manager .exe (WITH LICENSING)")
    print("=" * 70)
    
    # Get paths
    script_dir = Path(__file__).parent
    main_script = script_dir / 'main.py'
    trading_bots_dir = script_dir.parent / 'trading_bots'
    
    print(f"\n📁 Main script: {main_script}")
    print(f"📁 Trading bots: {trading_bots_dir}")
    
    # Check if icon exists
    icon_file = create_icon()
    
    # Clean previous builds
    print("\n🧹 Cleaning previous builds...")
    clean_build_dirs()
    
    print("\n⏳ Building... This may take several minutes...\n")
    
    # PyInstaller arguments
    args = [
        str(main_script),
        '--name=TradingBotManager',
        '--onedir',  # One directory (faster startup than onefile)
        '--windowed',  # No console window (GUI mode)
        
        # Add data files
        f'--add-data={trading_bots_dir};trading_bots',
        
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
        '--hidden-import=cryptography',
        '--hidden-import=cryptography.fernet',
        '--hidden-import=cryptography.hazmat',
        '--hidden-import=cryptography.hazmat.primitives',
        '--hidden-import=cryptography.hazmat.primitives.asymmetric',
        '--hidden-import=cryptography.hazmat.primitives.asymmetric.rsa',
        '--hidden-import=cryptography.hazmat.primitives.hashes',
        '--hidden-import=cryptography.hazmat.backends',
        
        # Collect all submodules
        '--collect-all=PySide6',
        '--collect-all=ccxt',
        '--collect-all=cryptography',
        
        # Optimize
        '--strip',  # Strip symbols from binary (smaller size)
        
        # Options
        '--noconfirm',  # Overwrite without asking
        '--clean',  # Clean PyInstaller cache
        
        # Exclude unnecessary modules (reduce size)
        # Note: Only exclude if you're certain they're not needed by dependencies
        # Test thoroughly after excluding any modules
        '--exclude-module=matplotlib',  # Large plotting library (not used)
        '--exclude-module=scipy',  # Scientific computing (not used)
        '--exclude-module=IPython',  # Interactive Python (not used)
        # Note: tkinter excluded as we use PySide6
        '--exclude-module=tkinter',
        
        # Application info
        '--version-file=None',  # Can add version info later
    ]
    
    # Add icon if available
    if icon_file:
        args.append(f'--icon={icon_file}')
        print(f"✅ Using icon: {icon_file}")
    
    # Run PyInstaller
    try:
        PyInstaller.__main__.run(args)
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        return False
    
    return True


def create_release_package():
    """Create release package with installer files"""
    script_dir = Path(__file__).parent
    dist_dir = script_dir / 'dist' / 'TradingBotManager'
    release_dir = script_dir / 'release'
    
    if not dist_dir.exists():
        print("❌ Distribution directory not found!")
        return False
    
    print("\n📦 Creating release package...")
    
    # Clean release directory
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir()
    
    # Copy all files from dist
    print(f"   Copying files to {release_dir}...")
    shutil.copytree(dist_dir, release_dir / 'TradingBotManager')
    
    # Create README for release
    readme_content = """# Trading Bot Manager - Professional Edition
Version 1.0.0 with Licensing System

## 🚀 Installation

1. Run the included Setup.exe (if available) or:
2. Copy the entire 'TradingBotManager' folder to your desired location
3. Run TradingBotManager.exe

## 📝 First Run

On first launch, you will see the activation dialog with two options:

### Option 1: Start 7-Day Trial
- Click "Start 7-Day Trial"
- Full functionality for 7 days
- No credit card required

### Option 2: Activate with License Key
- Enter your Hardware ID (shown in the activation window)
- Send the Hardware ID to support to receive your license key
- Enter the license key and click "Activate License"

## ⚙️ Configuration

### For XAUUSD Bot (MetaTrader 5)
1. Install MetaTrader 5
2. Enable "Algo Trading" in MT5 settings
3. Configure bot settings in the application

### For Crypto Bots (Binance)
Create a `.env` file in the application folder:

```
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
BINANCE_TESTNET=true
```

Optional Telegram notifications:
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## 🔑 Licensing

### Trial Version
- 7 days full functionality
- All features enabled
- No limitations

### Licensed Version
- Lifetime or subscription access
- All features unlocked
- Priority support

### Purchase License
Contact: [Your Contact Information]
Website: [Your Website]

## 💻 System Requirements

**Minimum:**
- Windows 10 (64-bit)
- 4 GB RAM
- 500 MB disk space
- Internet connection

**Recommended:**
- Windows 11 (64-bit)
- 8 GB RAM
- 1 GB disk space
- High-speed internet

**Additional Requirements:**
- MetaTrader 5 (for XAUUSD bot)
- Binance Account (for crypto bots)

## 🆘 Troubleshooting

### Application doesn't start
- Run as Administrator
- Check antivirus hasn't blocked it
- Verify Windows 10/11 64-bit

### MT5 connection fails
- Ensure MT5 is running
- Enable "Algo Trading" in MT5
- Check MT5 login credentials

### Binance connection fails
- Verify API keys in .env file
- Check API has Futures trading permission
- Use testnet for testing (BINANCE_TESTNET=true)

### License issues
- Verify you entered the correct license key
- Check Hardware ID matches
- Contact support if problems persist

## ⚠️ Important Notes

**Trial Period:**
- Trial starts on first launch
- Trial data is encrypted and protected
- Changing system time won't extend trial
- Moving to another PC requires new license

**License:**
- License is bound to your Hardware ID
- One license = One PC
- Contact support for transfers
- Keep your license key secure

**Security:**
- API keys are encrypted in the database
- License data is encrypted on disk
- All sensitive data is protected

**Trading:**
- Start with testnet/demo accounts
- Trading involves significant risk
- Test thoroughly before live trading
- Use proper risk management

## 📧 Support

For technical support, license issues, or questions:
- Email: [Your Support Email]
- Website: [Your Website]
- Documentation: [Your Docs URL]

## 📄 License Agreement

By using this software, you agree to the terms and conditions.
See LICENSE.txt for full details.

---

© 2026 Trading Bot Manager. All rights reserved.
"""
    
    readme_path = release_dir / 'README.txt'
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✅ Release package created in: {release_dir}")
    
    return True


def create_installer_script():
    """Create Inno Setup script for Windows installer"""
    script_dir = Path(__file__).parent
    installer_dir = script_dir / 'resources' / 'installer'
    installer_dir.mkdir(parents=True, exist_ok=True)
    
    inno_script = """
; Trading Bot Manager - Inno Setup Script
; Creates Windows installer with desktop and start menu shortcuts

#define MyAppName "Trading Bot Manager"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "TradingBots"
#define MyAppURL "https://your-website.com"
#define MyAppExeName "TradingBotManager.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-4789-A012-3456789ABCDE}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\\..\\LICENSE.txt
OutputDir=Output
OutputBaseFilename=TradingBotManager_Setup_v{#MyAppVersion}
SetupIconFile=..\\icons\\app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "Create a &Quick Launch icon"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\\..\\release\\TradingBotManager\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"
Name: "{group}\\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\\Microsoft\\Internet Explorer\\Quick Launch\\{#MyAppName}"; Filename: "{app}\\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  if not IsWin64 then begin
    MsgBox('This application requires 64-bit Windows 10 or later.', mbError, MB_OK);
    Result := False;
  end;
end;
"""
    
    script_path = installer_dir / 'setup.iss'
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(inno_script)
    
    print(f"\n✅ Inno Setup script created: {script_path}")
    print("\n📝 To create installer:")
    print("   1. Install Inno Setup from https://jrsoftware.org/isinfo.php")
    print("   2. Open the setup.iss file in Inno Setup")
    print("   3. Click 'Compile' to create the installer")
    print("   4. Installer will be in resources/installer/Output/")
    
    return True


def print_final_instructions():
    """Print final build instructions"""
    script_dir = Path(__file__).parent
    release_dir = script_dir / 'release'
    
    print("\n" + "=" * 70)
    print("✅ BUILD COMPLETE!")
    print("=" * 70)
    
    print(f"\n📁 Release folder: {release_dir}")
    print(f"📦 Application: TradingBotManager/TradingBotManager.exe")
    print(f"📄 README: README.txt")
    
    print("\n🎯 Next Steps:")
    print("\n1️⃣  Test the application:")
    print(f"   - Go to: {release_dir / 'TradingBotManager'}")
    print("   - Run: TradingBotManager.exe")
    print("   - Test trial and licensing features")
    
    print("\n2️⃣  Create installer (optional):")
    print("   - Install Inno Setup")
    print("   - Compile resources/installer/setup.iss")
    print("   - Get setup.exe from resources/installer/Output/")
    
    print("\n3️⃣  Generate license keys:")
    print("   - Run: python tools/keygen_tool.py")
    print("   - Enter customer Hardware ID")
    print("   - Generate and provide license key")
    
    print("\n4️⃣  Distribute:")
    print("   - Option A: Share the entire 'TradingBotManager' folder")
    print("   - Option B: Share the installer.exe created by Inno Setup")
    print("   - Include README.txt with instructions")
    
    print("\n⚠️  Important Notes:")
    print("   - MetaTrader 5 must be installed for XAUUSD bot")
    print("   - Binance API keys needed for crypto bots")
    print("   - First run will show activation dialog")
    print("   - 7-day trial available without license")
    print("   - Generate license keys using tools/keygen_tool.py")
    
    print("\n📊 Build Statistics:")
    if (script_dir / 'dist' / 'TradingBotManager').exists():
        size_mb = sum(f.stat().st_size for f in (script_dir / 'dist' / 'TradingBotManager').rglob('*') if f.is_file()) / (1024 * 1024)
        print(f"   - Application size: ~{size_mb:.1f} MB")
    
    print("\n" + "=" * 70)


def main():
    """Main build process"""
    try:
        # Step 1: Build .exe
        if not build_exe():
            print("\n❌ Build failed!")
            sys.exit(1)
        
        # Step 2: Create release package
        if not create_release_package():
            print("\n❌ Release package creation failed!")
            sys.exit(1)
        
        # Step 3: Create installer script
        create_installer_script()
        
        # Step 4: Print instructions
        print_final_instructions()
        
        print("\n✅ All done! Application is ready for distribution.")
        
    except Exception as e:
        print(f"\n❌ Build process failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
