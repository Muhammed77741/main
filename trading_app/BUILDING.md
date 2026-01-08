# 🏗️ Building Windows Executable

Guide for building the Trading Bot Manager into a standalone Windows `.exe` file.

---

## 📋 Prerequisites

### 1. Install Build Dependencies

```bash
pip install pyinstaller
```

### 2. Verify All Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔨 Build Process

### Method 1: Using Build Script (Recommended)

```bash
python build_exe.py
```

This will:
- Create a single `.exe` file
- Include all dependencies
- Package GUI resources
- No console window (windowed mode)

### Method 2: Manual PyInstaller Command

```bash
pyinstaller --name=TradingBotManager ^
    --onefile ^
    --windowed ^
    --add-data="../trading_bots;trading_bots" ^
    --hidden-import=PySide6 ^
    --hidden-import=ccxt ^
    --hidden-import=MetaTrader5 ^
    main.py
```

---

## 📦 What Gets Built

After building, you'll find in `dist/` folder:

```
dist/
└── TradingBotManager.exe  (~50-100 MB)
```

---

## 🚀 Distribution

### What to Include

For users to run the application, distribute:

1. **TradingBotManager.exe** - The main executable
2. **trading_bots/** - The bot modules (copy from parent directory)

### Folder Structure for End Users

```
TradingBotManager/
├── TradingBotManager.exe
├── trading_bots/
│   ├── xauusd_bot/
│   ├── crypto_bot/
│   └── shared/
└── README.md  (optional)
```

---

## ⚙️ Advanced Build Options

### Add Icon

1. Create or download an icon file (`icon.ico`)
2. Place in `assets/icon.ico`
3. Uncomment icon line in `build_exe.py`
4. Rebuild

### Reduce File Size

Use UPX compression (download UPX first):

```bash
pyinstaller ... --upx-dir=/path/to/upx
```

### Debug Build

For debugging, build with console:

```bash
pyinstaller ... --console  # Instead of --windowed
```

---

## 🧪 Testing the Build

### 1. Test on Build Machine

```bash
cd dist
TradingBotManager.exe
```

### 2. Test on Clean Machine

- Copy to another computer without Python
- Should run without any dependencies
- Verify all bots can start

### 3. Common Issues

**"Module not found" errors:**
- Add missing module to `--hidden-import`
- Rebuild

**"trading_bots not found":**
- Verify `--add-data` path is correct
- Check that trading_bots/ exists

**Large file size:**
- Normal for bundled Python apps (50-150 MB)
- Use `--upx-dir` to compress

---

## 📝 Build Spec File

For more control, use a `.spec` file:

### Create Spec File

```bash
pyi-makespec --onefile --windowed main.py
```

### Edit `main.spec`

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../trading_bots', 'trading_bots'),
    ],
    hiddenimports=[
        'PySide6',
        'ccxt',
        'MetaTrader5',
        'pandas',
        'numpy',
        'telegram',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TradingBotManager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',  # Add icon here
)
```

### Build from Spec

```bash
pyinstaller main.spec
```

---

## 🔐 Code Signing (Optional)

For production, sign the executable:

### Windows Code Signing

```bash
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com TradingBotManager.exe
```

### Benefits
- No "Unknown Publisher" warning
- Builds trust with users
- Required for some antivirus software

---

## 📋 Checklist Before Distribution

- [ ] Tested on build machine
- [ ] Tested on clean Windows 10/11
- [ ] All bots can start
- [ ] Database creation works
- [ ] Settings are saved correctly
- [ ] Logs display correctly
- [ ] No console window appears (windowed mode)
- [ ] Icon displays correctly (if added)
- [ ] File size is reasonable (<150 MB)
- [ ] Antivirus doesn't flag it (may need signing)

---

## 🐛 Troubleshooting

### Build Errors

**"Cannot find module":**
```bash
pip install <module-name>
```

**"Permission denied":**
- Close any running instance
- Run as administrator

**"UPX not found":**
- Remove `--upx-dir` flag
- Or download UPX from https://upx.github.io/

### Runtime Errors

**"DLL not found":**
- Install Visual C++ Redistributable
- Include in installer

**"Database error":**
- Check write permissions
- Run from user directory

---

## 🚀 Creating Installer (Advanced)

### Using Inno Setup

1. Download Inno Setup
2. Create `installer.iss`:

```iss
[Setup]
AppName=Trading Bot Manager
AppVersion=1.0
DefaultDirName={pf}\TradingBotManager
OutputDir=installer_output
OutputBaseFilename=TradingBotManager_Setup

[Files]
Source: "dist\TradingBotManager.exe"; DestDir: "{app}"
Source: "..\trading_bots\*"; DestDir: "{app}\trading_bots"; Flags: recursesubdirs

[Icons]
Name: "{autoprograms}\Trading Bot Manager"; Filename: "{app}\TradingBotManager.exe"
Name: "{autodesktop}\Trading Bot Manager"; Filename: "{app}\TradingBotManager.exe"

[Run]
Filename: "{app}\TradingBotManager.exe"; Description: "Launch Trading Bot Manager"; Flags: postinstall nowait
```

3. Compile with Inno Setup

Result: `TradingBotManager_Setup.exe` installer

---

## 📊 Build Statistics

Typical build outputs:

| Metric | Value |
|--------|-------|
| Build time | 2-5 minutes |
| .exe size | 50-150 MB |
| First run | Creates ~5 MB database |
| RAM usage | 200-500 MB |
| Startup time | 2-5 seconds |

---

**Ready to build!** 🚀

Run `python build_exe.py` to create your Windows executable.
