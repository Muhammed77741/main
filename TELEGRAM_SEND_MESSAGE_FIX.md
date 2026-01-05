# TelegramNotifier.send_message() Parameter Fix

## ❌ Error
```
TypeError: TelegramNotifier.send_message() got an unexpected keyword argument 'chat_id'
```

## 🔍 Root Cause

The `TelegramNotifier.send_message()` method signature is:
```python
def send_message(self, text, parse_mode='HTML'):
```

**It does NOT accept `chat_id` parameter** - the chat_id is already stored in `self.chat_id` during initialization.

## ✅ Solution

### Incorrect Code (BEFORE):
```python
self.notifier.send_message(
    chat_id=self.notifier.chat_id,
    text=message,
    parse_mode='Markdown'
)
```

### Correct Code (AFTER):
```python
self.notifier.send_message(message)
```

## 📝 Files Fixed

### Total: **18 instances** across 2 files

### 1. `live_bot_mt5_fullauto.py` - 9 instances
- Line 485: Order entry notification (4-level indent)
- Line 510: Bot startup notification (5-level indent) ⭐ **This was causing your error!**
- Line 584: Signal notification (5-level indent)
- Line 587: Another signal notification (4-level indent)
- Line 677: Position update notification (5-level indent)
- Line 680: Another position update (4-level indent)
- Line 745: TP hit notification (5-level indent)
- Line 748: Another TP notification (4-level indent)

### 2. `live_bot_mt5_semiauto.py` - 9 instances
- Line 486: Order confirmation notification (4-level indent)
- Line 548: Bot startup notification (5-level indent)
- Line 551: Another startup notification (4-level indent)
- Line 634: Signal notification (5-level indent)
- Line 637: Another signal notification (4-level indent)
- Line 740: Position update notification (5-level indent)
- Line 743: Another position update (4-level indent)
- Line 820: TP hit notification (5-level indent)
- Line 823: Another TP notification (4-level indent)

## 🛠️ Why the Error Occurred

The code was calling `send_message()` with keyword arguments:
- `chat_id=self.notifier.chat_id` ❌
- `text=message` ❌
- `parse_mode='Markdown'` ❌

But the method only accepts:
- `text` (positional or keyword)
- `parse_mode` (keyword, default='HTML')

The `chat_id` is already stored in the `self.chat_id` attribute and used internally by the method.

## 📊 Commits

1. **Commit f3567ca**: Fixed 10 instances (4-level indentation)
   - First pass using `replace_all=true`
   - Also fixed f-string formatting errors in telegram_command_handler.py

2. **Commit c262b0d**: Fixed remaining 8 instances (5-level indentation)
   - Caught the instances with deeper nesting that were missed in first pass
   - This commit fixed the error you were seeing on line 510

## ✅ How to Get the Fix

On your Windows machine:
```bash
git fetch origin
git checkout claude/smc-trading-backtest-fixed-SxnaS
git pull origin claude/smc-trading-backtest-fixed-SxnaS
```

Then run your bot again - the error should be completely resolved!

## 📚 Correct Usage Pattern

**For simple text messages:**
```python
self.notifier.send_message("Your message here")
```

**For formatted messages (default is HTML):**
```python
message = "✅ <b>Bold text</b>\n<i>Italic text</i>"
self.notifier.send_message(message)  # Uses HTML by default
```

**For Markdown messages (if needed):**
```python
message = "✅ **Bold text**\n*Italic text*"
self.notifier.send_message(message, parse_mode='Markdown')
```

## 🔍 Note About Indentation

The fix required two separate patterns because the code had two different indentation levels:
- **4-level indentation** (12 spaces): `            self.notifier.send_message(`
- **5-level indentation** (16 spaces): `                self.notifier.send_message(`

Both patterns were fixed using `replace_all=true` to catch all instances at each level.
