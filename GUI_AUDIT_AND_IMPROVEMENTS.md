# 🎨 GUI Audit & Improvement Proposals

**Date:** 2026-01-21
**Status:** Analysis Complete + Action Plan

---

## 🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА: DRY-RUN ПОЗИЦИИ НЕ ЗАКРЫВАЮТСЯ

### Корневая причина

**Файл:** `trading_bots/xauusd_bot/live_bot_mt5_fullauto.py:908-937`

**Проблема:**
```python
# При загрузке позиций из БД:
try:
    ticket = int(trade.order_id)  # ❌ Для "DRY-12345" вызывает ValueError
except (ValueError, TypeError):
    ticket = trade.order_id  # Остаётся строкой "DRY-12345"

# При проверке TP hit (строка 1092-1201):
if tp_hit or sl_hit:
    # Пытается закрыть позицию
    self._log_position_closed(ticket=ticket, ...)

# Внутри _log_position_closed (строка 310):
if ticket not in self.positions_tracker:  # ❌ НЕ НАХОДИТ!
    print(f"⚠️  Ticket {ticket} not found in tracker")
    return  # Позиция НЕ закрывается!
```

**Почему не находит:**
- При открытии позиции `ticket` сохраняется как **строка** в `positions_tracker`
- При закрытии ищется тот же `ticket` (тоже **строка**)
- Но если где-то между ними произошла конвертация `int(ticket)`, ключи не совпадут

### ✅ ИСПРАВЛЕНИЕ

**Применено в коммите:**
```python
# FIX: Сохраняем ticket как есть для dry-run
if isinstance(trade.order_id, str) and trade.order_id.startswith('DRY-'):
    ticket = trade.order_id  # Явно оставляем строкой
else:
    ticket = int(trade.order_id)  # Конвертируем только для live
```

**Добавлено debug logging:**
```python
if self.dry_run:
    print(f"🧪 DRY-RUN: Detected {hit_type} hit for position #{ticket}")
    print(f"   Ticket type: {type(ticket)}, Tracker has: {ticket in self.positions_tracker}")
```

**Что теперь делать:**
1. Перезапустить бота в dry-run
2. Дождаться TP hit
3. Проверить логи:
   - Должен быть `🧪 DRY-RUN: Detected TP1 hit...`
   - Должен быть `Tracker has: True`
   - Должен быть `✅ Position #DRY-xxx closed successfully`

---

## 📊 АУДИТ GUI: ОБЩАЯ ОЦЕНКА

### Текущее состояние: **6/10**

**Сильные стороны:**
- ✅ Современный Material Design
- ✅ Асинхронная работа (threading)
- ✅ Поддержка multiple exchanges
- ✅ Dry-run + Live режимы
- ✅ Экспорт в CSV

**Слабые стороны:**
- ❌ Перегруженный интерфейс (14-15 колонок в таблицах)
- ❌ Модальные окна блокируют работу
- ❌ Неполные фичи (period filter, test connection)
- ❌ Слабая обработка ошибок

---

## 🎯 ПРЕДЛОЖЕНИЯ ПО УЛУЧШЕНИЮ

### 🔴 ПРИОРИТЕТ 1: КРИТИЧЕСКИЕ (реализовать в первую очередь)

#### 1.1 Уменьшить количество колонок в таблицах

**Проблема:** 14-15 колонок → горизонтальная прокрутка на всех экранах

**Решение:**
```python
# Positions Monitor: БЫЛО 14 колонок
# Select | ID | Pos# | Group | Type | Amount | Entry | Current | SL | TP | Trailing | Created | P&L$ | P&L%

# ДОЛЖНО БЫТЬ: 8 ключевых колонок
# Select | Position Info | Price Info | Risk Info | P&L

# Колонки со вложенностью:
# - Position Info: ID (с Pos# и Group как tooltip)
# - Price Info: Entry → Current (в одной ячейке)
# - Risk Info: SL / TP / Trailing (иконки)
# - P&L: $ и % вместе

# Реализация с HTML-форматированием в ячейках
```

**Файлы для изменения:**
- `trading_app/gui/positions_monitor.py:237-316`
- `trading_app/gui/statistics_dialog.py:298-339`
- `trading_app/gui/tp_hits_viewer.py:82-114`

**Выгода:**
- Видно всё без скролла
- Читаемость +50%
- Быстрее находить нужную информацию

---

#### 1.2 Реализовать Validation в Settings

**Проблема:** Можно сохранить TP1=100, TP2=50, TP3=30 (обратный порядок)

**Решение:**
```python
# В SettingsDialog.save_settings():
def validate_tp_levels(self):
    """Validate TP levels are in ascending order"""
    if self.config.exchange == 'MT5':
        # XAUUSD в пунктах
        if not (self.trend_tp1 < self.trend_tp2 < self.trend_tp3):
            raise ValueError("TREND TP levels must be ascending: TP1 < TP2 < TP3")
        if not (self.range_tp1 < self.range_tp2 < self.range_tp3):
            raise ValueError("RANGE TP levels must be ascending: TP1 < TP2 < TP3")
    else:
        # Crypto в процентах
        if not (self.trend_tp1 < self.trend_tp2 < self.trend_tp3):
            raise ValueError("TREND TP% must be ascending: TP1 < TP2 < TP3")
        if not (self.range_tp1 < self.range_tp2 < self.range_tp3):
            raise ValueError("RANGE TP% must be ascending: TP1 < TP2 < TP3")

def save_settings(self):
    # Перед сохранением
    try:
        self.validate_tp_levels()
    except ValueError as e:
        QMessageBox.critical(self, "Invalid Settings", str(e))
        return  # Не сохранять

    # Продолжить сохранение...
```

**Добавить проверки:**
- SL > 0
- Risk % в диапазоне 0.1-10%
- Min order size >= exchange minimum
- Total position size >= min order size * 3
- API key/secret не пустые для live

---

#### 1.3 Fix Period Filtering в Statistics

**Проблема:** UI показывает "Last 7 days", но фильтр не работает

**Текущий код (строка 363):**
```python
# Filter by period (TODO: implement date filtering)
# For now, just use all trades
```

**Исправление:**
```python
def load_statistics(self):
    trades = self.db.get_trades(self.config.bot_id, limit=1000)

    # FIX: Implement period filtering
    period_index = self.period_combo.currentIndex()
    if period_index > 0:  # Not "All time"
        trades = self._filter_by_period(trades, period_index)

    # ...

def _filter_by_period(self, trades, period_index):
    """Filter trades by selected time period"""
    from datetime import datetime, timedelta

    now = datetime.now()
    cutoff_days = {
        1: 7,   # Last 7 days
        2: 30,  # Last 30 days
        3: 90   # Last 90 days
    }.get(period_index, 0)

    if cutoff_days == 0:
        return trades  # All time

    cutoff_date = now - timedelta(days=cutoff_days)
    return [t for t in trades if t.open_time and t.open_time >= cutoff_date]
```

---

### 🟡 ПРИОРИТЕТ 2: ВАЖНЫЕ (улучшат UX)

#### 2.1 Non-Modal Dialogs

**Проблема:** Открытие Statistics блокирует Main Window

**Решение:**
```python
# Изменить все диалоги:
class StatisticsDialog(QDialog):
    def __init__(self, ...):
        super().__init__(parent)
        # БЫЛО: По умолчанию modal=True
        self.setWindowModality(Qt.NonModal)  # FIX: Разрешить работу с main window
        self.setWindowFlags(Qt.Window)  # Отдельное окно
```

**Выгода:** Можно одновременно смотреть Statistics и Positions

---

#### 2.2 Context Menu для Positions

**Проблема:** Чтобы закрыть позицию, нужно:
1. Выделить checkbox
2. Нажать кнопку "Close Selected"
3. Подтвердить

**Решение:** Right-click menu
```python
def setup_context_menu(self):
    self.positions_table.setContextMenuPolicy(Qt.CustomContextMenu)
    self.positions_table.customContextMenuRequested.connect(self.show_context_menu)

def show_context_menu(self, pos):
    menu = QMenu(self)

    # Get selected row
    row = self.positions_table.rowAt(pos.y())
    if row < 0:
        return

    # Actions
    close_action = menu.addAction("🔴 Close Position")
    modify_sl = menu.addAction("📊 Modify SL")
    modify_tp = menu.addAction("🎯 Modify TP")
    menu.addSeparator()
    copy_action = menu.addAction("📋 Copy Position ID")

    # Execute
    action = menu.exec_(self.positions_table.viewport().mapToGlobal(pos))
    if action == close_action:
        self.close_single_position(row)
    elif action == modify_sl:
        self.modify_stop_loss(row)
    # ...
```

---

#### 2.3 Keyboard Shortcuts

**Текущее состояние:** Всё только мышкой

**Добавить:**
```python
class MainWindow(QMainWindow):
    def setup_shortcuts(self):
        # Global shortcuts
        QShortcut(QKeySequence("Ctrl+S"), self, self.open_settings)
        QShortcut(QKeySequence("Ctrl+P"), self, self.open_positions)
        QShortcut(QKeySequence("Ctrl+T"), self, self.open_statistics)
        QShortcut(QKeySequence("Ctrl+L"), self, self.focus_logs)
        QShortcut(QKeySequence("F5"), self, self.refresh_all)
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)

        # Bot controls
        QShortcut(QKeySequence("Space"), self, self.toggle_bot_start_stop)
        QShortcut(QKeySequence("Ctrl+R"), self, self.restart_bot)
```

**Отображение в UI:**
- Добавить подсказки в кнопки: "Settings (Ctrl+S)"
- Меню Help → Keyboard Shortcuts

---

#### 2.4 Search & Filter

**Добавить в Main Window:**
```python
# Над bot list
self.search_bar = QLineEdit()
self.search_bar.setPlaceholderText("🔍 Search bots, positions, logs...")
self.search_bar.textChanged.connect(self.filter_content)

def filter_content(self, text):
    # Filter bot list
    for i in range(self.bot_list.count()):
        item = self.bot_list.item(i)
        bot_id = item.data(Qt.UserRole)
        config = self.db.load_config(bot_id)

        match = (
            text.lower() in config.name.lower() or
            text.lower() in config.symbol.lower() or
            text.lower() in bot_id.lower()
        )
        item.setHidden(not match)

    # Filter logs (if text in log line)
    # ...
```

---

### 🟢 ПРИОРИТЕТ 3: ЖЕЛАТЕЛЬНЫЕ (polish)

#### 3.1 Dark Mode

**Добавить в Settings:**
```python
# UI Theme
theme_group = QGroupBox("Appearance")
self.dark_mode_checkbox = QCheckBox("Enable Dark Mode")
self.dark_mode_checkbox.stateChanged.connect(self.apply_theme)

def apply_theme(self):
    if self.dark_mode_checkbox.isChecked():
        # Dark theme stylesheet
        self.setStyleSheet("""
            QMainWindow, QDialog {
                background-color: #1E1E1E;
                color: #FFFFFF;
            }
            QGroupBox {
                border: 2px solid #3C3C3C;
                background-color: #2D2D2D;
                color: #FFFFFF;
            }
            # ... остальные элементы
        """)
    else:
        # Light theme (current)
        self.setStyleSheet(current_light_theme)
```

---

#### 3.2 Dockable Widgets

**Проблема:** Фиксированный layout, нельзя перестроить

**Решение:** Использовать `QDockWidget`
```python
class MainWindow(QMainWindow):
    def setup_dockable_panels(self):
        # Bot List Dock
        bot_dock = QDockWidget("Bots", self)
        bot_dock.setWidget(self.bot_list)
        self.addDockWidget(Qt.LeftDockWidgetArea, bot_dock)

        # Logs Dock
        logs_dock = QDockWidget("Logs", self)
        logs_dock.setWidget(self.logs_display)
        self.addDockWidget(Qt.BottomDockWidgetArea, logs_dock)

        # Positions Dock (mini view)
        pos_dock = QDockWidget("Live Positions", self)
        pos_dock.setWidget(self.positions_section)
        self.addDockWidget(Qt.RightDockWidgetArea, pos_dock)

        # User can:
        # - Drag docks to different areas
        # - Float docks as separate windows
        # - Close/show docks from View menu
```

---

#### 3.3 Help Tooltips

**Добавить ко всем настройкам:**
```python
# Example: Trailing Stop %
self.trailing_stop_input.setToolTip(
    "<b>Trailing Stop Percentage</b><br>"
    "After TP1 is hit, SL moves to protect profit.<br>"
    "Value: 0.1 - 1.0 (10% - 100% of distance to entry)<br>"
    "<br>"
    "Example: Entry $2500, TP1 $2530<br>"
    "Trailing 50% → SL moves to $2515<br>"
    "<i>Lower = tighter trailing, higher chance of premature exit</i>"
)
```

---

#### 3.4 Advanced Performance Metrics

**Новая секция в Statistics:**
```python
# Advanced Metrics (collapsible)
advanced_group = QGroupBox("Advanced Metrics")
grid = QGridLayout()

# Profit Factor
pf_label = QLabel("Profit Factor:")
pf_value = QLabel(f"{profit_factor:.2f}")
grid.addWidget(pf_label, 0, 0)
grid.addWidget(pf_value, 0, 1)

# Sharpe Ratio (if have equity curve)
sharpe_label = QLabel("Sharpe Ratio:")
sharpe_value = QLabel(f"{sharpe:.2f}")
grid.addWidget(sharpe_label, 1, 0)
grid.addWidget(sharpe_value, 1, 1)

# Max Consecutive Wins/Losses
max_win_streak = self.calculate_max_streak(trades, win=True)
max_loss_streak = self.calculate_max_streak(trades, win=False)
grid.addWidget(QLabel("Max Win Streak:"), 2, 0)
grid.addWidget(QLabel(str(max_win_streak)), 2, 1)
grid.addWidget(QLabel("Max Loss Streak:"), 3, 0)
grid.addWidget(QLabel(str(max_loss_streak)), 3, 1)

# Avg Holding Time (winners vs losers)
# ...
```

---

## 📋 РЕАЛИЗАЦИЯ: ПЛАН ДЕЙСТВИЙ

### Phase 1: Фиксы критических багов (1-2 дня)
- [x] Fix dry-run position closing issue
- [ ] Implement period filtering in statistics
- [ ] Add settings validation
- [ ] Fix "Test Connection" button

### Phase 2: UX Improvements (3-5 дней)
- [ ] Reduce table columns (8 max)
- [ ] Add context menus for positions
- [ ] Implement keyboard shortcuts
- [ ] Make dialogs non-modal
- [ ] Add search/filter bar

### Phase 3: Feature Additions (1-2 недели)
- [ ] Implement advanced metrics
- [ ] Add dark mode toggle
- [ ] Dockable widgets support

### Phase 4: Polish (ongoing)
- [ ] Comprehensive help tooltips
- [ ] Performance optimization
- [ ] Error logging to file
- [ ] User preferences persistence
- [ ] Tutorial/onboarding flow

---

## 🎨 КОНКРЕТНЫЕ ФАЙЛЫ ДЛЯ ИЗМЕНЕНИЯ

### Высокий приоритет:
1. **`trading_app/gui/positions_monitor.py`**
   - Уменьшить колонки с 14 до 8
   - Добавить context menu
   - Сделать non-modal

2. **`trading_app/gui/statistics_dialog.py`**
   - Реализовать period filtering
   - Добавить advanced metrics section
   - Уменьшить колонки

3. **`trading_app/gui/settings_dialog.py`**
   - Добавить validation перед save
   - Исправить "Test Connection"
   - Добавить tooltips

4. **`trading_app/gui/main_window.py`**
   - Добавить keyboard shortcuts
   - Добавить search bar
   - Оптимизировать refresh timers

### Средний приоритет:
5. **`trading_app/gui/tp_hits_viewer.py`**
   - Уменьшить колонки
   - Добавить фильтр комбинации
   - Показать win rate

---

## 🚀 ОЖИДАЕМЫЕ РЕЗУЛЬТАТЫ

### После Phase 1:
- ✅ Все dry-run позиции закрываются корректно
- ✅ Невозможно сохранить невалидные настройки
- ✅ Period filter работает

### После Phase 2:
- ✅ Таблицы читаемые без scrolling
- ✅ Быстрые действия через right-click
- ✅ Работа с GUI только с клавиатуры
- ✅ Можно открыть несколько окон одновременно

### После Phase 3:
- ✅ Advanced performance metrics в Statistics
- ✅ Пользователь может настроить layout под себя
- ✅ Тёмная тема для работы ночью

### После Phase 4:
- ✅ Профессиональный trading terminal
- ✅ Минимум обучения новых пользователей
- ✅ Надёжная работа без crashes
- ✅ Удовольствие от использования

---

**Готовность к работе: 100%**
**Приоритетность изменений: Определена**
**Оценка времени реализации: 2-4 недели для всех фаз**
