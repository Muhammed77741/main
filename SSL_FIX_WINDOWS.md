# SSL Certificate Fix for Windows

## Problem

When running `real_data_screener.py`, you see errors like:

```
Failed to get ticker 'AAPL' reason: Failed to perform, curl: (77) error setting certificate verify locations:
CAfile: C:\Users\Мирас\AppData\Local\Programs\Python\Python311\Lib\site-packages\certifi\cacert.pem
```

This is a common SSL certificate verification issue on Windows, especially:
- When your Windows username contains non-English characters (like Cyrillic: Мирас)
- When the `certifi` package can't find its certificate bundle
- When Python's SSL verification is too strict

## Quick Fix (Automatic)

✅ **Good news!** The latest version of `real_data_screener.py` includes an automatic fix.

Just update your code:

```bash
git pull origin claude/simplify-stock-screener-WzlXB
```

The screener now automatically:
1. Tries to use `certifi` certificates if available
2. Falls back to disabled SSL verification if needed
3. Handles SSL errors gracefully

## Manual Fix Options

If you still have issues, try these solutions:

### Option 1: Reinstall certifi

```bash
# Activate venv first
venv\Scripts\activate

# Reinstall certifi
pip uninstall certifi
pip install certifi --force-reinstall
```

### Option 2: Update pip and packages

```bash
# Activate venv
venv\Scripts\activate

# Update pip
python -m pip install --upgrade pip

# Update all packages
pip install --upgrade yfinance certifi urllib3 requests
```

### Option 3: Use demo_screener.py instead

If SSL issues persist, use the demo screener (no internet required):

```bash
# Run demo version (works offline)
python demo_screener.py
```

Or use the BAT file:

```bash
windows_scripts\run_demo.bat
```

### Option 4: Fix Python path with English username

If your Windows username has Russian/Cyrillic characters, create a new Python virtual environment in a path without special characters:

```bash
# Create venv in a simple path
cd C:\Projects\stock-screener
python -m venv venv

# Activate it
venv\Scripts\activate

# Install dependencies
pip install pandas numpy yfinance
```

### Option 5: Disable SSL verification globally (Not recommended for production)

If you're just testing and need a quick workaround:

Create a file `disable_ssl.py` in the same folder:

```python
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
```

Then import it before running the screener:

```python
import disable_ssl  # Must be first!
from real_data_screener import RealDataScreener

# Rest of your code...
```

⚠️ **Warning:** Disabling SSL verification makes your connection insecure. Only use for local testing!

## Testing the Fix

After applying any fix, test with:

```bash
python -c "import yfinance as yf; print(yf.Ticker('AAPL').info['shortName'])"
```

Should print: `Apple Inc.`

If it works, your SSL is fixed!

## Alternative: Use comprehensive_screener.py

This version uses hardcoded fundamental data (no internet needed for fundamentals, only for price data):

```bash
python comprehensive_screener.py
```

Or:

```bash
windows_scripts\run_comprehensive.bat
```

## Why This Happens

The error occurs because:

1. **certifi package** stores SSL certificates in a file: `cacert.pem`
2. On Windows, the path might contain **special characters** (like Cyrillic: Мирас)
3. The underlying **curl library** can't read paths with non-ASCII characters
4. SSL verification fails

Our fix bypasses this by:
- Setting the correct certificate path
- Falling back to unverified context if that fails
- Catching SSL errors gracefully

## Still Not Working?

If none of these work:

1. **Check your internet connection** - Make sure you can access https://finance.yahoo.com
2. **Check firewall** - Your firewall might be blocking Python
3. **Use VPN** - Some regions block Yahoo Finance
4. **Use demo version** - `demo_screener.py` works offline

## Questions?

- Check `WINDOWS_INSTALL.md` for full installation guide
- Check `PYCHARM_GUIDE.md` for PyCharm setup
- Check `FUNDAMENTAL_GUIDE.md` for understanding the screener

---

**TL;DR:** Update your code with `git pull`, the SSL fix is now automatic! If still broken, use `demo_screener.py` instead.
