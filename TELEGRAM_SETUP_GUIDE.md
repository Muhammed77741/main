# 📱 Telegram Setup Guide & Troubleshooting

This guide helps you set up Telegram notifications for the trading bots and fix common issues.

## 🚀 Quick Setup

### 1. Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Follow the instructions to create your bot
4. Copy the **Bot Token** (looks like: `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`)

### 2. Get Your Chat ID

**Option A: Use @userinfobot**
1. Search for **@userinfobot** in Telegram
2. Send `/start`
3. Copy your **Chat ID** (looks like: `123456789` or `-100123456789` for channels)

**Option B: Use @getidsbot**
1. Search for **@getidsbot** in Telegram
2. Send `/start`
3. Copy your **Chat ID**

### 3. Add Credentials to Your Bot

**For Command-Line Bots:**

Create or edit `.env` file in the project root:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

**For GUI Application:**

1. Open the trading app
2. Select your bot (XAUUSD, BTC, or ETH)
3. Click "⚙ Settings"
4. Enable "Enable Telegram notifications"
5. Enter your Bot Token and Chat ID
6. Click "Save"

### 4. Test the Connection

**Command-Line:**
```bash
python run_xauusd_bot.py --dry-run
# or
python run_crypto_bot.py BTC --dry-run
```

**GUI Application:**
- Start the bot and check if you receive a startup notification in Telegram

---

## ⚠️ Common Issue: Cannot Import 'Bot' from 'telegram'

### The Problem

You may see this error:
```
⚠️  Telegram init failed: cannot import name 'Bot' from 'telegram'
```

Or in Windows:
```
cannot import name 'Bot' from 'telegram' (C:\Users\...\Python\...\Lib\site-packages\telegram\__init__.py)
```

### The Cause

There are **TWO different packages** with similar names:
1. ❌ **`telegram`** (version 0.0.1) - Wrong package, doesn't have Bot class
2. ✅ **`python-telegram-bot`** (version 20+) - Correct package for bot development

If you installed the wrong `telegram` package, Python will try to import from it and fail.

### The Solution

**Step 1: Uninstall both packages**
```bash
pip uninstall telegram
pip uninstall python-telegram-bot
```

**Step 2: Check for leftover files**

Look in your Python's site-packages directory and remove any `telegram` folders if they exist:
- Windows: `C:\Users\YourName\AppData\Local\Programs\Python\Python3XX\Lib\site-packages\telegram`
- Linux/Mac: `~/.local/lib/python3.XX/site-packages/telegram`

**Step 3: Install the correct package**
```bash
pip install python-telegram-bot>=20.0
```

**Step 4: Verify installation**
```bash
pip show python-telegram-bot
```

You should see:
```
Name: python-telegram-bot
Version: 20.x or higher
```

**Step 5: Test the import**
```bash
python -c "from telegram import Bot; print('Success!')"
```

If you see "Success!", you're all set!

### Alternative Fix (Virtual Environment)

If the above doesn't work, try using a clean virtual environment:

```bash
# Create a new virtual environment
python -m venv telegram_env

# Activate it
# Windows:
telegram_env\Scripts\activate
# Linux/Mac:
source telegram_env/bin/activate

# Install the correct package
pip install python-telegram-bot>=20.0

# Install other dependencies
pip install -r trading_bots/requirements.txt
```

---

## 🔍 Other Telegram Issues

### Bot Token Invalid

**Error:** `Unauthorized` or `Invalid token`

**Solution:**
- Double-check your token from @BotFather
- Make sure there are no extra spaces
- Regenerate the token if needed

### Wrong Chat ID

**Error:** `Chat not found` or messages not arriving

**Solution:**
- Verify your Chat ID
- If using a channel, make sure to add the bot as an admin
- For channels, Chat ID starts with `-100`
- For private chats, Chat ID is a positive number

### Timeout Errors

**Error:** `Read timed out`

**Solution:**
- Check your internet connection
- Try again - Telegram servers might be temporarily slow
- Increase timeout in code if persistent

### Messages Not Arriving

**Checklist:**
- ✅ Bot token is correct
- ✅ Chat ID is correct
- ✅ You've sent `/start` to the bot first
- ✅ Bot is not blocked by you
- ✅ Internet connection is working
- ✅ Check Telegram for messages (might be in "Archived" or "Spam")

---

## 📝 Testing Your Setup

Run this simple test script:

```python
import asyncio
from telegram import Bot

async def test():
    bot = Bot(token="YOUR_TOKEN_HERE")
    
    # Test connection
    me = await bot.get_me()
    print(f"✅ Connected as: @{me.username}")
    
    # Send test message
    await bot.send_message(
        chat_id="YOUR_CHAT_ID_HERE",
        text="🎉 <b>Test successful!</b>\n\nTelegram notifications are working!",
        parse_mode='HTML'
    )
    print("✅ Message sent!")

# Run the test
asyncio.run(test())
```

Save as `test_telegram.py` and run:
```bash
python test_telegram.py
```

---

## 🔐 Security Notes

- **Never share your Bot Token** - it's like a password
- **Never commit tokens to Git** - use `.env` files (which are in `.gitignore`)
- **Regenerate token if exposed** - use @BotFather to create a new one
- **Be careful with Chat IDs** - don't send messages to wrong chats

---

## 📚 Additional Resources

- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [BotFather Commands](https://core.telegram.org/bots#6-botfather)

---

## ✅ Checklist

Before reporting an issue, make sure:

- [ ] I installed `python-telegram-bot`, NOT `telegram`
- [ ] I can run `python -c "from telegram import Bot"`
- [ ] My Bot Token is correct (from @BotFather)
- [ ] My Chat ID is correct (from @userinfobot)
- [ ] I sent `/start` to my bot
- [ ] I tested with the test script above
- [ ] My internet connection is working
- [ ] My firewall allows Python to access the internet

---

**Still having issues?** Check the bot logs for detailed error messages or review the main README troubleshooting section.
