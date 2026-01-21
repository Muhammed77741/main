# 🔍 POSITIONS, STATISTICS & NOTIFICATIONS AUDIT

**Date:** 2026-01-21  
**Auditor:** Senior Trading System Engineer  
**Scope:** Full system audit of positions tracking, statistics, and notifications

---

## 📋 EXECUTIVE SUMMARY

### Critical Issues Found: **5**
### High Priority Issues: **3**  
### Medium Priority Issues: **2**

**Status:** ⚠️ **REQUIRES IMMEDIATE FIXES**

---

## 1️⃣ TRAILING STATUS IN STATISTICS & TP_HITS

### ❌ Problem

**Trailing status (`trailing_stop_active`) is NOT displayed in:**
- Statistics dialog (`statistics_dialog.py`)
- TP Hits viewer (`tp_hits_viewer.py`)

### 🔍 Root Cause Analysis

**Location 1: `trading_app/gui/statistics_dialog.py`**
- Line ~180-220: Statistics table does NOT include `trailing_stop_active` column
- Only shows: `Open Time`, `Close Time`, `Type`, `Entry`, `Close`, `SL`, `TP`, `Profit`, `%`, `Status`
- **Missing columns:** `Trailing Active`, `Position #`, `Group`

**Location 2: `trading_app/gui/tp_hits_viewer.py`**  
- Line 84-87: TP hits table does NOT include `trailing_stop_active`
- Only shows: `Timestamp`, `Order ID`, `TP Level`, `Type`, `Amount`, `Entry`, `TP Target`, `Close Price`, `SL`, `Profit $`, `Profit %`
- **Missing columns:** `Trailing Active`, `Position #`, `Group ID`

**Location 3: Data Source**
- Database stores `trailing_stop_active` correctly (line 202-205 in `db_manager.py`)
- Data is retrieved correctly in `get_all_trades()` (line 477-478)
- **But GUI never displays it**

### ✅ Solution

**File: `trading_app/gui/statistics_dialog.py`**

```python
# Line ~180 - Add to column list
self.table.setColumnCount(14)  # Increase from 11
self.table.setHorizontalHeaderLabels([
    'Open Time', 'Close Time', 'Type', 'Entry', 'Close', 'SL', 'TP',
    'Profit', '%', 'Status', 'Pos #', 'Group', 'Trailing', 'Regime'  # ADD THESE 4
])

# Line ~250 - Add when populating rows
row_data = [
    # ... existing columns ...
    str(trade.position_num) if trade.position_num > 0 else '',  # Pos #
    trade.position_group_id[:8] + '...' if trade.position_group_id else '',  # Group (shortened)
    '✅ YES' if trade.trailing_stop_active else '❌ NO',  # Trailing
    trade.market_regime or ''  # Regime
]
```

**File: `trading_app/gui/tp_hits_viewer.py`**

```python
# Line 84 - Add to column list
self.table.setColumnCount(14)  # Increase from 11
self.table.setHorizontalHeaderLabels([
    'Timestamp', 'Order ID', 'TP Level', 'Type', 'Amount',
    'Entry', 'TP Target', 'Close Price', 'SL', 
    'Profit $', 'Profit %', 'Pos #', 'Group', 'Trailing'  # ADD THESE 3
])

# When loading from CSV (line ~150), add:
position_num = row.get('position_num', row.get('Pos #', ''))
group_id = row.get('position_group_id', row.get('Group', ''))
trailing = row.get('trailing_stop_active', row.get('Trailing', 'NO'))
```

---

## 2️⃣ TP / SL / TRAILING EVENTS NOT IN STATISTICS

### ❌ Problem

**Events don't appear because they're never logged:**
- TP hits don't create statistics entries
- SL hits don't create statistics entries  
- Trailing stop activations don't create statistics entries

### 🔍 Root Cause Analysis

**Location: `trading_bots/xauusd_bot/live_bot_mt5_fullauto.py`**

**Line 390: `_log_tp_hit()` method**
```python
def _log_tp_hit(self, ticket, tp_level, current_price):
    """Log TP hit to CSV file"""
    # ❌ Only writes to CSV file 'bot_tp_hits_log.csv'
    # ❌ Does NOT update trade in database with close reason
    # ❌ Does NOT create statistics entry
```

**Line 970-980: TP hit detection**
```python
# Determines TP level from position_num
# BUT does NOT call any DB update function
# Only calls _log_tp_hit() which writes to CSV
```

**Line 653-662: Trailing stop activation**
```python
# Updates trailing_stop_active in DB ✅ GOOD
# BUT does NOT log this event anywhere for statistics
```

**Missing:** No event logging system for:
- TP1 hit
- TP2 hit
- TP3 hit
- Trailing activation
- Trailing SL hit
- Manual SL hit

### ✅ Solution

**Create new method in `live_bot_mt5_fullauto.py`:**

```python
def _log_trade_event(self, ticket, event_type, details=''):
    """
    Log trade events to database for statistics
    
    Args:
        ticket: Position ticket
        event_type: 'TP1', 'TP2', 'TP3', 'SL', 'TRAILING_ACTIVATED', 'TRAILING_HIT'
        details: Additional info (price, profit, etc)
    """
    try:
        # Get trade from database
        trade = self.db.get_trade_by_order_id(str(ticket))
        if not trade:
            return
        
        # Create event entry in app_logs or new events table
        event_data = {
            'timestamp': datetime.now(),
            'bot_id': self.bot_id,
            'trade_id': trade.trade_id,
            'order_id': str(ticket),
            'event_type': event_type,
            'details': details,
            'position_num': trade.position_num,
            'position_group_id': trade.position_group_id
        }
        
        self.db.save_trade_event(event_data)
        print(f"📊 Event logged: {event_type} for ticket #{ticket}")
        
    except Exception as e:
        print(f"⚠️  Error logging trade event: {e}")
```

**Update `_log_tp_hit()` method (line 390):**

```python
def _log_tp_hit(self, ticket, tp_level, current_price):
    """Log TP hit to CSV file AND database"""
    try:
        # Existing CSV logging code...
        
        # ADD THIS: Log to database for statistics
        self._log_trade_event(
            ticket=ticket,
            event_type=f'TP{tp_level}',
            details=f'Hit at ${current_price:.2f}'
        )
        
    except Exception as e:
        print(f"⚠️  Error logging TP hit: {e}")
```

**Update trailing activation (line 653-662):**

```python
# After updating trailing_stop_active = True
self._log_trade_event(
    ticket=ticket,
    event_type='TRAILING_ACTIVATED',
    details=f'TP1 hit, trailing started from ${new_sl:.2f}'
)
```

**Update trailing SL hit:**

```python
# When position closed by trailing stop
self._log_trade_event(
    ticket=ticket,
    event_type='TRAILING_HIT',
    details=f'Closed at ${close_price:.2f}, protected profit'
)
```

**Create database table for events:**

```sql
CREATE TABLE IF NOT EXISTS trade_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    bot_id TEXT NOT NULL,
    trade_id INTEGER,
    order_id TEXT,
    event_type TEXT NOT NULL,
    details TEXT,
    position_num INTEGER DEFAULT 0,
    position_group_id TEXT,
    FOREIGN KEY (trade_id) REFERENCES trades(trade_id)
)
```

---

## 3️⃣ POS # AND GROUP COLUMNS EMPTY

### ❌ Problem

**Columns `pos #` and `group` in positions monitor are empty**

### 🔍 Root Cause Analysis

**Location 1: `trading_app/gui/positions_monitor.py`**

**Line 102-104:** Data IS retrieved from database:
```python
'position_num': trade.position_num,  # ✅ Retrieved
'position_group_id': trade.position_group_id,  # ✅ Retrieved
'trailing_stop_active': trade.trailing_stop_active  # ✅ Retrieved
```

**BUT...**

**Line 200+: Positions table setup** - Does NOT include these columns!

```python
# Current table setup does NOT define pos # and group columns
# Table only shows: ID, Side, Contracts, Entry, Mark, SL, TP, PnL, etc.
# MISSING: position_num, position_group_id, trailing_stop_active
```

**Location 2: MT5 positions (line 119-136)**

```python
# MT5 positions DON'T have position_num or group_id
# These are custom fields stored in database
# But when fetching from MT5, we don't enrich with DB data
```

### ✅ Solution

**File: `trading_app/gui/positions_monitor.py`**

**Step 1: Add columns to table (around line 250):**

```python
# In init_ui() method
self.table.setColumnCount(12)  # Increase from 9
self.table.setHorizontalHeaderLabels([
    'ID', 'Side', 'Contracts', 'Entry', 'Mark', 'SL', 'TP', 
    'P&L', 'Pos #', 'Group', 'Trailing', 'Created'  # ADD THESE 3
])

# Set column widths
self.table.setColumnWidth(8, 60)   # Pos #
self.table.setColumnWidth(9, 100)  # Group (shortened)
self.table.setColumnWidth(10, 80)  # Trailing
```

**Step 2: Populate columns when displaying (around line 300):**

```python
def update_table(self, positions):
    """Update positions table"""
    # ... existing code ...
    
    for row, pos in enumerate(positions):
        # ... existing columns ...
        
        # ADD: Pos # column
        pos_num = pos.get('position_num', 0)
        pos_num_item = QTableWidgetItem(str(pos_num) if pos_num > 0 else '')
        pos_num_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 8, pos_num_item)
        
        # ADD: Group column (shortened UUID)
        group_id = pos.get('position_group_id', '')
        group_display = group_id[:8] + '...' if group_id else ''
        group_item = QTableWidgetItem(group_display)
        group_item.setTextAlignment(Qt.AlignCenter)
        group_item.setToolTip(group_id)  # Full ID on hover
        self.table.setItem(row, 9, group_item)
        
        # ADD: Trailing column
        trailing = pos.get('trailing_stop_active', False)
        trailing_item = QTableWidgetItem('✅ YES' if trailing else '❌ NO')
        trailing_item.setTextAlignment(Qt.AlignCenter)
        if trailing:
            trailing_item.setForeground(QColor(0, 150, 0))  # Green
        self.table.setItem(row, 10, trailing_item)
```

**Step 3: Enrich MT5 positions with database info (line 119-136):**

```python
# In _fetch_positions() when exchange is MT5
if mt5_positions:
    for pos in mt5_positions:
        # ... existing code ...
        
        # Enrich with database info
        pos_data = {
            'id': pos.ticket,
            # ... existing fields ...
        }
        
        # ADD: Get additional info from database
        if self.db_manager:
            try:
                trade = self.db_manager.get_trade_by_order_id(str(pos.ticket))
                if trade:
                    pos_data['position_num'] = trade.position_num
                    pos_data['position_group_id'] = trade.position_group_id
                    pos_data['trailing_stop_active'] = trade.trailing_stop_active
            except Exception as e:
                print(f"⚠️  Could not enrich position {pos.ticket} with DB data: {e}")
        
        positions.append(pos_data)
```

---

## 4️⃣ TELEGRAM NOTIFICATIONS MISSING

### ❌ Problem 1: No Notifications for TP/SL/Trailing

**TP/SL/Trailing events don't send Telegram notifications**

### 🔍 Root Cause Analysis

**Location: `trading_bots/xauusd_bot/live_bot_mt5_fullauto.py`**

**TP Hit (line 970-980):**
```python
# When TP is hit:
# 1. Calls _log_tp_hit() ✅
# 2. Updates database ✅
# 3. ❌ Does NOT call telegram.send_tp_hit()
```

**SL Hit:**
```python
# When SL is hit:
# ❌ No dedicated SL hit detection code
# ❌ No telegram notification
```

**Trailing Activation (line 653-662):**
```python
# When trailing activates:
# 1. Updates trailing_stop_active ✅
# 2. ❌ Does NOT send telegram notification
```

**Missing Methods in `telegram_notifier.py`:**
- `send_tp_hit()` - Send TP hit notification
- `send_sl_hit()` - Send SL hit notification
- `send_trailing_activated()` - Send trailing activation notification
- `send_trailing_hit()` - Send trailing stop hit notification

### ✅ Solution

**File: `trading_bots/shared/telegram_notifier.py`**

**Add new methods:**

```python
def send_tp_hit(self, tp_data):
    """Send TP hit notification"""
    tp_level = tp_data['tp_level']  # 1, 2, or 3
    order_id = tp_data['order_id']
    direction = tp_data['direction']
    entry_price = tp_data['entry_price']
    close_price = tp_data['close_price']
    profit = tp_data['profit']
    profit_pct = tp_data['profit_pct']
    position_num = tp_data.get('position_num', tp_level)
    timestamp = tp_data.get('timestamp', datetime.now())
    
    timestamp_local = self._convert_to_local_time(timestamp)
    
    emoji = "🎯"
    direction_emoji = "🟢" if direction == "LONG" else "🔴"
    
    message = f"""
{emoji} <b>TAKE PROFIT {tp_level} ДОСТИГНУТ!</b>

📊 <b>Позиция #{position_num}</b>
⏰ <b>Время:</b> {timestamp_local.strftime('%Y-%m-%d %H:%M:%S')}

{direction_emoji} <b>Направление:</b> {direction}
💰 <b>Вход:</b> {entry_price:.2f}
🎯 <b>Выход TP{tp_level}:</b> {close_price:.2f}

✅ <b>Прибыль:</b> ${profit:.2f} ({profit_pct:+.2f}%)

🔔 <b>Ордер:</b> {order_id}
"""
    
    return self.send_message(message)


def send_sl_hit(self, sl_data):
    """Send SL hit notification"""
    order_id = sl_data['order_id']
    direction = sl_data['direction']
    entry_price = sl_data['entry_price']
    sl_price = sl_data['sl_price']
    close_price = sl_data['close_price']
    loss = sl_data['loss']
    loss_pct = sl_data['loss_pct']
    timestamp = sl_data.get('timestamp', datetime.now())
    
    timestamp_local = self._convert_to_local_time(timestamp)
    
    emoji = "🛑"
    direction_emoji = "🟢" if direction == "LONG" else "🔴"
    
    message = f"""
{emoji} <b>STOP LOSS СРАБОТАЛ</b>

⏰ <b>Время:</b> {timestamp_local.strftime('%Y-%m-%d %H:%M:%S')}

{direction_emoji} <b>Направление:</b> {direction}
💰 <b>Вход:</b> {entry_price:.2f}
🛑 <b>Stop Loss:</b> {sl_price:.2f}
❌ <b>Выход:</b> {close_price:.2f}

📉 <b>Убыток:</b> -${abs(loss):.2f} ({loss_pct:.2f}%)

🔔 <b>Ордер:</b> {order_id}

💡 Защита капитала сработала корректно
"""
    
    return self.send_message(message)


def send_trailing_activated(self, trailing_data):
    """Send trailing stop activation notification"""
    order_id = trailing_data['order_id']
    direction = trailing_data['direction']
    entry_price = trailing_data['entry_price']
    tp1_price = trailing_data['tp1_price']
    initial_sl = trailing_data['initial_sl']
    new_sl = trailing_data['new_sl']
    timestamp = trailing_data.get('timestamp', datetime.now())
    
    timestamp_local = self._convert_to_local_time(timestamp)
    
    emoji = "🔄"
    direction_emoji = "🟢" if direction == "LONG" else "🔴"
    
    message = f"""
{emoji} <b>TRAILING STOP АКТИВИРОВАН!</b>

⏰ <b>Время:</b> {timestamp_local.strftime('%Y-%m-%d %H:%M:%S')}

{direction_emoji} <b>Направление:</b> {direction}
💰 <b>Вход:</b> {entry_price:.2f}
🎯 <b>TP1 достигнут:</b> {tp1_price:.2f}

🛡️ <b>Stop Loss обновлён:</b>
   Было: {initial_sl:.2f}
   Стало: {new_sl:.2f} (безубыток)

📊 Позиции TP2 и TP3 теперь под защитой trailing stop
🔒 Гарантированная прибыль зафиксирована

🔔 <b>Ордер:</b> {order_id}
"""
    
    return self.send_message(message)


def send_trailing_hit(self, trailing_data):
    """Send trailing stop hit notification"""
    order_id = trailing_data['order_id']
    direction = trailing_data['direction']
    entry_price = trailing_data['entry_price']
    max_price = trailing_data['max_price']
    close_price = trailing_data['close_price']
    profit = trailing_data['profit']
    profit_pct = trailing_data['profit_pct']
    protected_profit_pct = trailing_data['protected_profit_pct']  # How much profit was protected
    timestamp = trailing_data.get('timestamp', datetime.now())
    
    timestamp_local = self._convert_to_local_time(timestamp)
    
    emoji = "🔒"
    direction_emoji = "🟢" if direction == "LONG" else "🔴"
    
    message = f"""
{emoji} <b>TRAILING STOP ЗАКРЫЛ ПОЗИЦИЮ</b>

⏰ <b>Время:</b> {timestamp_local.strftime('%Y-%m-%d %H:%M:%S')}

{direction_emoji} <b>Направление:</b> {direction}
💰 <b>Вход:</b> {entry_price:.2f}
🚀 <b>Макс. цена:</b> {max_price:.2f}
🔒 <b>Выход (trailing):</b> {close_price:.2f}

✅ <b>Зафиксированная прибыль:</b> ${profit:.2f} ({profit_pct:+.2f}%)
🛡️ <b>Защищено от отката:</b> {protected_profit_pct:.1f}%

🔔 <b>Ордер:</b> {order_id}

💡 Trailing stop защитил вашу прибыль от разворота
"""
    
    return self.send_message(message)
```

**File: `trading_bots/xauusd_bot/live_bot_mt5_fullauto.py`**

**Update `_log_tp_hit()` to send notification:**

```python
def _log_tp_hit(self, ticket, tp_level, current_price):
    """Log TP hit and send notification"""
    try:
        # Existing CSV logging code...
        
        # Get trade info for notification
        trade = self.db.get_trade_by_order_id(str(ticket))
        if trade and self.telegram:
            tp_data = {
                'tp_level': tp_level,
                'order_id': str(ticket),
                'direction': trade.trade_type,
                'entry_price': trade.entry_price,
                'close_price': current_price,
                'profit': (current_price - trade.entry_price) * trade.amount if trade.trade_type == 'BUY' else (trade.entry_price - current_price) * trade.amount,
                'profit_pct': ((current_price - trade.entry_price) / trade.entry_price * 100) if trade.trade_type == 'BUY' else ((trade.entry_price - current_price) / trade.entry_price * 100),
                'position_num': trade.position_num
            }
            self.telegram.send_tp_hit(tp_data)
        
    except Exception as e:
        print(f"⚠️  Error in _log_tp_hit: {e}")
```

**Add trailing activation notification (line 653-662):**

```python
# After updating trailing_stop_active
if self.telegram:
    trailing_data = {
        'order_id': str(ticket),
        'direction': pos_data['type'],
        'entry_price': pos_data['entry_price'],
        'tp1_price': pos_data['tp'],
        'initial_sl': pos_data['initial_sl'],  # Store this in pos_data
        'new_sl': new_sl
    }
    self.telegram.send_trailing_activated(trailing_data)
```

---

## 5️⃣ TELEGRAM POOL TIMEOUT ERROR

### ❌ Problem

```
Telegram message send error:
Pool timeout: All connections in the connection pool are occupied
```

### 🔍 Root Cause Analysis

**Location: `trading_bots/shared/telegram_notifier.py`**

**Line 52-60: `send_message()` method**

```python
def send_message(self, text, parse_mode='HTML'):
    """Send text message to Telegram"""
    try:
        url = f"{self.base_url}/sendMessage"
        data = {...}
        
        # ❌ Uses requests.post() - synchronous blocking call
        # ❌ No connection pooling configuration
        # ❌ No retry logic
        # ❌ timeout=10 but no pool size limit
        response = requests.post(url, data=data, timeout=10)
```

**Problems:**
1. **No Session object** - Creates new connection for each message
2. **No connection pool settings** - Default pool size is too small
3. **Synchronous calls** - Blocks execution
4. **No rate limiting** - Can overwhelm Telegram API
5. **No queue** - Multiple messages sent simultaneously
6. **No retry with backoff** - Single attempt only

**When does pool timeout occur:**
- Multiple TP hits at same time (3 positions closing together)
- Entry signal + TP hits happening rapidly
- Restart recovery sending multiple notifications
- Main thread blocked waiting for Telegram response

### ✅ Solution

**File: `trading_bots/shared/telegram_notifier.py`**

**Complete rewrite with async queue and connection pool:**

```python
"""
Telegram notification module with connection pooling and async queue
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
from datetime import datetime, timedelta
import queue
import threading
import time


class TelegramNotifier:
    """Send trading alerts to Telegram with connection pooling and async queue"""

    def __init__(self, bot_token, chat_id, timezone_offset=5, max_pool_connections=10):
        """
        Initialize Telegram notifier with connection pool
        
        Args:
            bot_token: Telegram bot token
            chat_id: Chat ID or channel username
            timezone_offset: Timezone offset in hours from UTC
            max_pool_connections: Maximum connections in pool (default: 10)
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timezone_offset = timezone_offset
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
        # Create session with connection pooling
        self.session = self._create_session(max_pool_connections)
        
        # Message queue for async sending
        self.message_queue = queue.Queue()
        self.queue_thread = None
        self.running = False
        
        # Rate limiting
        self.last_send_time = 0
        self.min_interval = 0.5  # Min 0.5 seconds between messages
        
        # Start queue processor
        self._start_queue_processor()
    
    def _create_session(self, max_connections):
        """Create requests session with connection pooling and retry"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,  # 3 retry attempts
            backoff_factor=1,  # 1, 2, 4 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP codes
            method_whitelist=["POST"]
        )
        
        # Configure adapter with connection pool
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=max_connections,  # Connection pool size
            pool_maxsize=max_connections * 2,  # Max connections per host
            pool_block=False  # Don't block if pool is full, raise error instead
        )
        
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        return session
    
    def _start_queue_processor(self):
        """Start background thread to process message queue"""
        if self.queue_thread and self.queue_thread.is_alive():
            return  # Already running
        
        self.running = True
        self.queue_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.queue_thread.start()
    
    def _process_queue(self):
        """Process messages from queue in background thread"""
        while self.running:
            try:
                # Get message from queue with timeout
                try:
                    message_data = self.message_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Rate limiting
                time_since_last = time.time() - self.last_send_time
                if time_since_last < self.min_interval:
                    time.sleep(self.min_interval - time_since_last)
                
                # Send message
                self._send_message_direct(message_data['text'], message_data['parse_mode'])
                self.last_send_time = time.time()
                
                # Mark task as done
                self.message_queue.task_done()
                
            except Exception as e:
                print(f"⚠️  Error in Telegram queue processor: {e}")
    
    def _send_message_direct(self, text, parse_mode='HTML'):
        """Send message directly (called by queue processor)"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }

            response = self.session.post(url, data=data, timeout=10)

            if response.status_code == 200:
                return True
            else:
                print(f"❌ Telegram error: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.ConnectionError as e:
            print(f"❌ Telegram connection error: {e}")
            return False
        except requests.exceptions.Timeout as e:
            print(f"❌ Telegram timeout: {e}")
            return False
        except Exception as e:
            print(f"❌ Failed to send Telegram message: {e}")
            return False
    
    def send_message(self, text, parse_mode='HTML', async_send=True):
        """
        Send text message to Telegram
        
        Args:
            text: Message text
            parse_mode: HTML or Markdown
            async_send: If True, queue message for async sending. If False, send immediately.
        
        Returns:
            True if queued/sent successfully
        """
        try:
            if async_send:
                # Add to queue for async sending
                self.message_queue.put({
                    'text': text,
                    'parse_mode': parse_mode
                })
                return True
            else:
                # Send immediately (blocking)
                return self._send_message_direct(text, parse_mode)
                
        except Exception as e:
            print(f"❌ Failed to queue Telegram message: {e}")
            return False
    
    def wait_for_queue(self, timeout=5):
        """Wait for all queued messages to be sent (useful for shutdown)"""
        try:
            self.message_queue.join()  # Wait for queue to empty
        except Exception as e:
            print(f"⚠️  Error waiting for Telegram queue: {e}")
    
    def shutdown(self):
        """Shutdown Telegram notifier gracefully"""
        print("📱 Shutting down Telegram notifier...")
        
        # Wait for queue to empty (with timeout)
        try:
            self.message_queue.join()  # This will block until queue is empty
        except:
            pass
        
        # Stop queue processor
        self.running = False
        if self.queue_thread:
            self.queue_thread.join(timeout=3)
        
        # Close session
        self.session.close()
        
        print("✅ Telegram notifier shut down")
    
    # ... keep all other methods (send_entry_signal, send_exit_signal, etc) ...
```

**Usage in bot:**

```python
# At bot initialization
self.telegram = TelegramNotifier(
    bot_token=TELEGRAM_BOT_TOKEN,
    chat_id=TELEGRAM_CHAT_ID,
    max_pool_connections=20  # Increase pool size
)

# Send messages (non-blocking)
self.telegram.send_message("Test message", async_send=True)  # Queued

# At bot shutdown
self.telegram.shutdown()  # Wait for queue and cleanup
```

**Benefits:**
- ✅ Connection pool prevents "pool timeout" errors
- ✅ Async queue prevents blocking main thread
- ✅ Rate limiting prevents Telegram API spam
- ✅ Automatic retry on failures
- ✅ Graceful shutdown waits for pending messages
- ✅ Thread-safe implementation

---

## 📊 SUMMARY OF FIXES

### Priority 1: Critical (Fix Immediately)

| # | Issue | File | Lines | Effort |
|---|-------|------|-------|--------|
| 1 | Pos # and Group empty in positions | `positions_monitor.py` | 250, 300, 119-136 | 2h |
| 2 | Telegram pool timeout | `telegram_notifier.py` | Complete rewrite | 4h |
| 3 | Missing TP/SL notifications | `telegram_notifier.py` + bot | New methods | 3h |

### Priority 2: High (Fix This Week)

| # | Issue | File | Lines | Effort |
|---|-------|------|-------|--------|
| 4 | Trailing status not in statistics | `statistics_dialog.py` | ~180, ~250 | 1h |
| 5 | Trailing status not in TP hits | `tp_hits_viewer.py` | 84, ~150 | 1h |

### Priority 3: Medium (Fix This Sprint)

| # | Issue | File | Lines | Effort |
|---|-------|------|-------|--------|
| 6 | TP/SL/Trailing events not logged | `live_bot_mt5_fullauto.py` | New method | 2h |
| 7 | Create trade_events table | `db_manager.py` | New table | 1h |

### Total Estimated Effort: **14 hours**

---

## 🔧 IMPLEMENTATION CHECKLIST

### Phase 1: Critical Fixes (Day 1-2)
- [ ] Fix positions monitor columns (Pos #, Group, Trailing)
- [ ] Enrich MT5 positions with DB data
- [ ] Rewrite Telegram notifier with connection pool
- [ ] Add async message queue
- [ ] Test connection pool under load

### Phase 2: Notifications (Day 3-4)
- [ ] Add `send_tp_hit()` to telegram_notifier
- [ ] Add `send_sl_hit()` to telegram_notifier
- [ ] Add `send_trailing_activated()` to telegram_notifier
- [ ] Add `send_trailing_hit()` to telegram_notifier
- [ ] Update `_log_tp_hit()` to send notifications
- [ ] Add trailing activation notification
- [ ] Test all notification types

### Phase 3: Statistics & Events (Day 5-6)
- [ ] Add columns to statistics dialog
- [ ] Add columns to TP hits viewer
- [ ] Create `trade_events` table
- [ ] Implement `_log_trade_event()` method
- [ ] Log TP1/TP2/TP3 events
- [ ] Log trailing activation events
- [ ] Log SL hit events
- [ ] Test event logging

### Phase 4: Testing (Day 7)
- [ ] Full integration test
- [ ] Test with 3-position group
- [ ] Test TP hits send notifications
- [ ] Test trailing activation sends notification
- [ ] Test SL hit sends notification
- [ ] Test Telegram under high load (20+ messages)
- [ ] Test positions monitor shows all fields
- [ ] Test statistics shows all fields
- [ ] Verify no pool timeout errors

---

## 🎯 EXPECTED OUTCOMES

### After Fixes:

**Positions Monitor:**
```
| ID     | Side | Contracts | Entry   | Mark    | SL      | TP      | P&L    | Pos # | Group      | Trailing | Created     |
|--------|------|-----------|---------|---------|---------|---------|--------|-------|------------|----------|-------------|
| 123456 | buy  | 0.1       | 2870.00 | 2920.00 | 2850.00 | 2930.00 | +50.00 | 1     | e19ada... | ❌ NO    | 10:30:45    |
| 123457 | buy  | 0.1       | 2870.00 | 2920.00 | 2870.00 | 2960.00 | +50.00 | 2     | e19ada... | ✅ YES   | 10:30:45    |
| 123458 | buy  | 0.1       | 2870.00 | 2920.00 | 2870.00 | 2990.00 | +50.00 | 3     | e19ada... | ✅ YES   | 10:30:45    |
```

**Statistics:**
```
| Open Time | Close Time | Type | Entry   | Close   | SL      | TP      | Profit | %     | Pos # | Group      | Trailing | Status |
|-----------|------------|------|---------|---------|---------|---------|--------|-------|-------|------------|----------|--------|
| 10:30     | 11:45      | BUY  | 2870.00 | 2930.00 | 2850.00 | 2930.00 | +60.00 | +2.1% | 1     | e19ada... | ❌ NO    | CLOSED |
| 10:30     | 12:30      | BUY  | 2870.00 | 2950.00 | 2870.00 | 2960.00 | +80.00 | +2.8% | 2     | e19ada... | ✅ YES   | CLOSED |
```

**Telegram Notifications (Example):**
```
🎯 TAKE PROFIT 1 ДОСТИГНУТ!

📊 Позиция #1
⏰ Время: 2026-01-21 11:45:23

🟢 Направление: LONG
💰 Вход: 2870.00
🎯 Выход TP1: 2930.00

✅ Прибыль: $60.00 (+2.09%)

🔔 Ордер: 123456
```

```
🔄 TRAILING STOP АКТИВИРОВАН!

⏰ Время: 2026-01-21 11:45:25

🟢 Направление: LONG
💰 Вход: 2870.00
🎯 TP1 достигнут: 2930.00

🛡️ Stop Loss обновлён:
   Было: 2850.00
   Стало: 2870.00 (безубыток)

📊 Позиции TP2 и TP3 теперь под защитой trailing stop
🔒 Гарантированная прибыль зафиксирована
```

**No More Errors:**
- ✅ No "Pool timeout" errors
- ✅ No missing columns
- ✅ No empty Pos # or Group fields
- ✅ All events logged and visible

---

## 📚 REFERENCES

**Files Analyzed:**
- `trading_app/models/trade_record.py` - Data model ✅
- `trading_app/gui/statistics_dialog.py` - Statistics UI ⚠️
- `trading_app/gui/tp_hits_viewer.py` - TP hits UI ⚠️
- `trading_app/gui/positions_monitor.py` - Positions UI ⚠️
- `trading_bots/shared/telegram_notifier.py` - Telegram ❌
- `trading_bots/xauusd_bot/live_bot_mt5_fullauto.py` - Bot logic ⚠️
- `trading_app/database/db_manager.py` - Database ✅

**Legend:**
- ✅ Working correctly
- ⚠️ Needs improvements
- ❌ Critical issues

---

**END OF AUDIT REPORT**

*Generated: 2026-01-21*  
*Auditor: Senior Trading System Engineer*
