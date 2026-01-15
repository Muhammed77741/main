# ⚡ Quick Start - 3 Simple Steps

## 📦 Step 1: Build (2 minutes)

```bash
cd trading_app
python build_enhanced.py
```

**What happens:**
- ✅ Cleans previous builds
- ✅ Builds optimized .exe
- ✅ Creates release package
- ✅ Generates installer script
- ✅ Shows completion message with instructions

**Output location:**
```
trading_app/release/TradingBotManager/
├── TradingBotManager.exe    ← Main application
├── _internal/                ← Libraries (don't distribute separately)
└── ...
```

---

## 🧪 Step 2: Test (5 minutes)

### Test A: Trial System
```bash
cd release/TradingBotManager
./TradingBotManager.exe
```

**What to expect:**
1. Activation dialog appears
2. Shows your Hardware ID
3. Two buttons: "Start 7-Day Trial" or "Activate License"
4. Click "Start 7-Day Trial"
5. Application starts
6. Top bar shows: "ℹ Trial: 7 days remaining"

### Test B: License Activation
```bash
# In another terminal:
cd trading_app
python tools/keygen_tool.py
```

**What to do:**
1. Copy Hardware ID from activation dialog
2. Paste in key generator
3. Select: "365 days (1 year)" + "ALL (Full Access)"
4. Click "Generate License Key"
5. Copy the generated key
6. Enter in activation dialog
7. Click "Activate License"
8. Should show: "✓ Licensed: 365 days remaining"

---

## 🎁 Step 3: Distribute (1 minute)

### Option A: Folder (Quick)
```bash
# Zip the folder
cd trading_app/release
zip -r TradingBotManager.zip TradingBotManager/

# Or on Windows:
# Right-click TradingBotManager folder → Send to → Compressed folder
```

Send `TradingBotManager.zip` to customers with `README.txt`

### Option B: Installer (Professional)
```bash
# 1. Install Inno Setup from:
#    https://jrsoftware.org/isinfo.php

# 2. Open in Inno Setup:
cd trading_app/resources/installer
# Open setup.iss

# 3. Click "Compile"

# 4. Installer created at:
#    Output/TradingBotManager_Setup_v1.0.0.exe
```

Send the setup.exe to customers

---

## 🔑 Managing Customers

### When customer contacts you:

**Customer:** "I want to try the application"
**You:** 
- Send them TradingBotManager.zip or Setup.exe
- Tell them: "Start 7-day trial when you run it"

**Customer:** "My trial expired, I want to buy"
**You:**
1. Ask for Hardware ID (shown in activation dialog)
2. Run: `python tools/keygen_tool.py`
3. Enter their Hardware ID
4. Select duration and features
5. Generate key
6. Send key to customer
7. Customer enters in app
8. Done! ✓

**Customer:** "I got a new computer"
**You:**
- Get new Hardware ID
- Generate new key for new Hardware ID
- Optional: Deactivate old key (keep track in spreadsheet)

---

## 📋 Simple License Tracking

Create a spreadsheet with:

| Date | Customer Email | Hardware ID | Key | Duration | Expires | Status |
|------|---------------|-------------|-----|----------|---------|--------|
| 2026-01-15 | john@example.com | ABC123... | XXXXX-... | 1 year | 2027-01-15 | Active |
| 2026-01-16 | jane@example.com | DEF456... | YYYYY-... | Lifetime | - | Active |

---

## 🐛 Common Issues

### "Python not found"
```bash
# Install Python 3.10+ from python.org
```

### "Module not found"
```bash
pip install -r requirements.txt
```

### "Build failed"
```bash
# Clear cache and try again
rm -rf build dist __pycache__
python build_enhanced.py
```

### Customer: "License invalid"
- Check Hardware ID matches
- Regenerate key if needed
- Verify no typos in key entry

### Customer: "Trial reset"
- This is normal behavior - trial can't be reset
- Only way forward is license key
- This is the security feature working correctly

---

## 💰 Pricing Suggestions

### Simple Model:
- **Trial**: 7 days free
- **Monthly**: $29/month
- **Yearly**: $299/year (save $49)
- **Lifetime**: $999 (one-time)

### Features Model:
- **Single Bot**: $199/year (BTC, ETH, or XAUUSD)
- **All Bots**: $299/year
- **Lifetime All**: $999

---

## 📞 Customer Support Template

**Email template for new customers:**

```
Subject: Trading Bot Manager - Activation Instructions

Hi [Customer Name],

Thank you for purchasing Trading Bot Manager!

STEP 1: Install
- Download: [link to TradingBotManager.zip or Setup.exe]
- Extract/Install and run TradingBotManager.exe

STEP 2: Get Hardware ID
- When activation dialog appears, copy the Hardware ID
- Reply to this email with your Hardware ID

STEP 3: Activate
- I'll send you your license key within 24 hours
- Enter the key in the activation dialog
- Click "Activate License"
- Done!

CONFIGURATION:
For crypto bots (BTC/ETH), create .env file next to exe:
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
BINANCE_TESTNET=true

For XAUUSD bot, install MetaTrader 5.

Support: [your email]
Documentation: See README.txt in application folder

Best regards,
[Your Name]
```

---

## ✅ Checklist Before First Customer

- [ ] Application builds successfully
- [ ] Trial works (tested)
- [ ] License activation works (tested)
- [ ] README.txt is clear
- [ ] You can generate keys with keygen_tool
- [ ] You have spreadsheet for tracking licenses
- [ ] You have support email set up
- [ ] Pricing is decided
- [ ] Payment method is ready (PayPal, Stripe, etc.)

---

## 🎯 Your Files Overview

```
trading_app/
├── 📘 IMPLEMENTATION_SUMMARY.md      ← Technical details
├── 📗 WINDOWS_APP_GUIDE.md           ← Complete guide (English)
├── 📙 WINDOWS_APP_GUIDE_RU.md        ← Complete guide (Russian)
├── 📕 QUICKSTART.md                  ← This file (simplest)
│
├── 🔧 build_enhanced.py              ← Run this to build
├── 🔑 tools/keygen_tool.py           ← Run this to generate keys
│
├── 💻 main.py                        ← Application entry point
├── 🎨 gui/                           ← User interface
├── 🔐 licensing/                     ← Trial + License system
└── 📦 resources/                     ← Icons, installer
```

**Read in order:**
1. This file (QUICKSTART.md) - Get started fast
2. WINDOWS_APP_GUIDE.md - Learn everything
3. IMPLEMENTATION_SUMMARY.md - Technical reference

---

## 🎉 You're Ready!

**In 10 minutes you can:**
1. Build application
2. Test trial
3. Generate license key
4. Distribute to first customer

**Questions?** Check the full guides or contact support.

**Good luck with your sales! 🚀💰**
