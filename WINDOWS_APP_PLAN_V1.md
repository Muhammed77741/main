# 🪟 План создания Windows приложения для торговых ботов - Phase 1 (MVP)

## 📋 Обзор

Windows приложение с графическим интерфейсом для запуска и управления торговыми ботами (XAUUSD, BTC, ETH).

**Phase 1**: Базовый функционал БЕЗ системы лицензирования
**Phase 2**: Добавление лицензий (после успешной реализации Phase 1)

---

## 🎯 Требования Phase 1

### Функциональные требования:
1. ✅ **GUI интерфейс** - удобный графический интерфейс
2. ✅ **Выбор котировки** - BTC/USDT, ETH/USDT, XAUUSD
3. ✅ **Выбор параметров** - risk %, max positions, TP levels, timeframe
4. ✅ **Мониторинг позиций** - в реальном времени
5. ✅ **Отображение статистики** - прибыль, win rate
6. ✅ **Логи в реальном времени** - вывод логов бота
7. ✅ **Telegram интеграция** - настройка уведомлений
8. ✅ **Управление ботами** - start/stop для каждого бота

### Что НЕ входит в Phase 1:
- ❌ Система лицензирования
- ❌ Online activation
- ❌ Code obfuscation
- ❌ Auto-updater
- ❌ Backtesting в GUI (будет в Phase 1.5)

---

## 🏗️ Архитектура приложения

### Технологический стек:

#### Frontend (GUI):
**PySide6** (Qt for Python)

```
Преимущества:
✅ Бесплатная LGPL лицензия
✅ Нативный внешний вид Windows
✅ Высокая производительность
✅ Богатая библиотека компонентов
✅ Поддержка графиков (QtCharts)
✅ Легко упаковать в .exe
```

#### Backend:
- **Python 3.10+**
- **Threading** - для запуска ботов в фоне
- **SQLite** - для хранения настроек и истории сделок
- **Cryptography** - для шифрования API ключей

#### Структура проекта:
```
trading_app/
├── main.py                    # Точка входа
├── gui/
│   ├── main_window.py         # Главное окно
│   ├── bot_panel.py           # Панель управления ботом
│   ├── settings_dialog.py     # Окно настроек
│   ├── positions_monitor.py   # Мониторинг позиций
│   └── logs_viewer.py         # Просмотр логов
├── core/
│   ├── bot_manager.py         # Управление ботами
│   ├── bot_thread.py          # Поток для бота
│   └── database.py            # SQLite операции
├── models/
│   ├── bot_config.py          # Модель конфигурации
│   └── trade_record.py        # Модель сделки
├── utils/
│   ├── logger.py              # Логирование
│   └── crypto.py              # Шифрование
├── assets/
│   ├── icons/                 # Иконки
│   └── styles.qss             # Стили Qt
└── requirements_gui.txt       # Зависимости
```

---

## 🖼️ Дизайн интерфейса

### Главное окно (Main Window)

```
┌─────────────────────────────────────────────────────────────┐
│  Trading Bot Manager                           [_] [□] [X]   │
├─────────────────────────────────────────────────────────────┤
│  ☰ Menu                                                      │
├────────────┬────────────────────────────────────────────────┤
│            │                                                 │
│  Bot List  │              Main Panel                        │
│            │                                                 │
│  🥇 XAUUSD │  ┌─────────────────────────────────────┐      │
│  ○ Stopped │  │  XAUUSD Bot - STOPPED               │      │
│            │  │                                      │      │
│  ₿ BTC     │  │  Configuration:                     │      │
│  ● Running │  │  • Symbol: BTC/USDT                 │      │
│            │  │  • Exchange: Binance Futures        │      │
│  ⟠ ETH     │  │  • Risk: 2.0%                       │      │
│  ○ Stopped │  │  • Max Positions: 3                 │      │
│            │  │  • Mode: V3 Adaptive                │      │
│            │  │                                      │      │
│            │  │  Status:                             │      │
│            │  │  Balance: $10,250.50                │      │
│            │  │  P&L Today: +$250.50 (+2.5%)        │      │
│            │  │  Open Positions: 2/3                │      │
│            │  │  Win Rate: 68%                      │      │
│            │  │                                      │      │
│            │  │  [▶ Start Bot] [⚙ Settings] [📊 Stats] │   │
│            │  └─────────────────────────────────────┘      │
│            │                                                 │
│            │  ┌─────────────────────────────────────┐      │
│            │  │  Live Logs:                         │      │
│            │  │  ────────────────────────────────   │      │
│            │  │  [10:30:45] ✅ Connected to Binance │      │
│            │  │  [10:31:00] 📊 Market: TREND        │      │
│            │  │  [10:31:15] 🎯 Signal: LONG         │      │
│            │  │  [10:31:20] 📈 Position #12345      │      │
│            │  │                                      │      │
│            │  │  [Clear Logs] [Save Logs]           │      │
│            │  └─────────────────────────────────────┘      │
└─────────────┴────────────────────────────────────────────────┘
```

### Окно настроек (Settings Dialog)

```
┌─────────────────────────────────────────┐
│  Bot Settings - BTC                [X]  │
├─────────────────────────────────────────┤
│  ┌─ Exchange ──────────────────────┐    │
│  │ Exchange: [Binance ▼]           │    │
│  │ □ Use Testnet                   │    │
│  │                                  │    │
│  │ API Key:    [***************]   │    │
│  │ API Secret: [***************]   │    │
│  │ [Test Connection]               │    │
│  └─────────────────────────────────┘    │
│                                          │
│  ┌─ Trading Parameters ────────────┐    │
│  │ Symbol: [BTC/USDT ▼]            │    │
│  │ Timeframe: [1h ▼]               │    │
│  │ Risk per trade: [2.0] %         │    │
│  │ Max positions:  [3]             │    │
│  │ □ DRY RUN mode                  │    │
│  └─────────────────────────────────┘    │
│                                          │
│  ┌─ Strategy ──────────────────────┐    │
│  │ Strategy: [V3 Adaptive ▼]       │    │
│  │                                  │    │
│  │ TREND Mode TP:                  │    │
│  │ TP1: [1.5]% TP2: [2.75]% TP3: [4.5]%│
│  │                                  │    │
│  │ RANGE Mode TP:                  │    │
│  │ TP1: [1.0]% TP2: [1.75]% TP3: [2.5]%│
│  └─────────────────────────────────┘    │
│                                          │
│  ┌─ Telegram ──────────────────────┐    │
│  │ □ Enable Notifications          │    │
│  │ Token:   [*****************]    │    │
│  │ Chat ID: [***********]          │    │
│  │ [Test Notification]             │    │
│  └─────────────────────────────────┘    │
│                                          │
│         [Save] [Cancel] [Reset]         │
└─────────────────────────────────────────┘
```

### Окно мониторинга позиций (Positions Monitor)

```
┌─────────────────────────────────────────────────────────┐
│  Open Positions - BTC/USDT                     [X]      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ ID    │ Type │ Amount │ Entry   │ SL     │ TP     │ │
│  ├────────────────────────────────────────────────────┤ │
│  │ 12345 │ LONG │ 0.05   │ 45000   │44500   │45675   │ │
│  │ 12346 │ LONG │ 0.03   │ 45100   │44600   │45775   │ │
│  │                                                     │ │
│  │ Total P&L: +$150.00 (+0.33%)                       │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  Selected Position #12345:                               │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Type: LONG                                        │ │
│  │  Entry: $45,000.00                                 │ │
│  │  Current: $45,150.00                               │ │
│  │  SL: $44,500.00 (-500 points)                     │ │
│  │  TP: $45,675.00 (+675 points)                     │ │
│  │  P&L: +$7.50 (+0.33%)                             │ │
│  │  Duration: 2h 15m                                  │ │
│  │  Regime: TREND                                     │ │
│  │                                                     │ │
│  │  [Close Position] [Modify SL/TP]                   │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  [Refresh] [Close All Positions]                        │
└─────────────────────────────────────────────────────────┘
```

### Окно статистики (Statistics)

```
┌─────────────────────────────────────────────────────────┐
│  Statistics - BTC Bot                          [X]      │
├─────────────────────────────────────────────────────────┤
│  Period: [Last 30 days ▼]                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─ Summary ──────────────────────────────────────┐    │
│  │ Total Trades: 45                               │    │
│  │ Win Rate: 68.9% (31W / 14L)                    │    │
│  │ Total P&L: +$1,234.56 (+12.3%)                │    │
│  │ Avg Win: $58.23 | Avg Loss: -$32.11           │    │
│  │ Profit Factor: 2.15                            │    │
│  │ Best Trade: +$150.00 | Worst: -$85.00         │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─ By Market Regime ──────────────────────────────┐   │
│  │ TREND: 25 trades | P&L: +$850.00               │   │
│  │ RANGE: 20 trades | P&L: +$384.56               │   │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  ┌─ Trade History ─────────────────────────────────┐   │
│  │ Date       │Type│Entry  │Exit   │P&L      │Rgm │   │
│  ├────────────────────────────────────────────────┤   │
│  │ 2026-01-08 │LONG│45000  │45675  │+$33.75  │T   │   │
│  │ 2026-01-07 │LONG│44800  │44400  │-$20.00  │R   │   │
│  │ 2026-01-07 │SHORT│45200│44800  │+$20.00  │T   │   │
│  │ ...        │... │...    │...    │...      │... │   │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  [Export CSV] [Generate Report]                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 Основные компоненты

### 1. BotManager (core/bot_manager.py)

```python
class BotManager:
    """Управление всеми ботами"""

    def __init__(self):
        self.bots = {}  # {bot_id: BotThread}
        self.configs = {}  # {bot_id: BotConfig}

    def start_bot(self, bot_id: str):
        """Запустить бота в отдельном потоке"""
        config = self.configs[bot_id]
        bot_thread = BotThread(config)
        bot_thread.start()
        self.bots[bot_id] = bot_thread

    def stop_bot(self, bot_id: str):
        """Остановить бота"""
        if bot_id in self.bots:
            self.bots[bot_id].stop()
            del self.bots[bot_id]

    def get_bot_status(self, bot_id: str):
        """Получить статус бота"""
        if bot_id in self.bots:
            return self.bots[bot_id].get_status()
        return {"status": "stopped"}

    def update_config(self, bot_id: str, config: BotConfig):
        """Обновить конфигурацию бота"""
        self.configs[bot_id] = config
        # Сохранить в базу данных
        self.save_config(config)
```

### 2. BotThread (core/bot_thread.py)

```python
class BotThread(QThread):
    """Поток для запуска бота"""

    # Сигналы для обновления GUI
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(dict)
    position_signal = pyqtSignal(dict)

    def __init__(self, config: BotConfig):
        super().__init__()
        self.config = config
        self.running = False
        self.bot = None

    def run(self):
        """Основной цикл бота"""
        self.running = True

        # Инициализировать бота на основе символа
        if self.config.symbol == "XAUUSD":
            from trading_bots.xauusd_bot.live_bot_mt5_fullauto import LiveBotMT5FullAuto
            self.bot = LiveBotMT5FullAuto(
                symbol=self.config.symbol,
                risk_percent=self.config.risk_percent,
                # ... другие параметры
            )
        else:
            from trading_bots.crypto_bot.live_bot_binance_fullauto import LiveBotBinanceFullAuto
            self.bot = LiveBotBinanceFullAuto(
                symbol=self.config.symbol,
                risk_percent=self.config.risk_percent,
                # ... другие параметры
            )

        # Подключить сигналы для логов
        # self.bot.connect_logger(self.log_signal.emit)

        # Запустить бота
        if self.bot.connect_exchange():
            self.bot.run()

    def stop(self):
        """Остановить бота"""
        self.running = False
        if self.bot:
            # Отключить бота gracefully
            pass
```

### 3. MainWindow (gui/main_window.py)

```python
class MainWindow(QMainWindow):
    """Главное окно приложения"""

    def __init__(self):
        super().__init__()
        self.bot_manager = BotManager()
        self.init_ui()

    def init_ui(self):
        """Инициализация UI"""
        self.setWindowTitle("Trading Bot Manager")
        self.setGeometry(100, 100, 1200, 800)

        # Создать центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Создать layout
        layout = QHBoxLayout()

        # Левая панель - список ботов
        self.bot_list = self.create_bot_list()
        layout.addWidget(self.bot_list, 1)

        # Правая панель - основная панель
        self.main_panel = self.create_main_panel()
        layout.addWidget(self.main_panel, 3)

        central_widget.setLayout(layout)

    def create_bot_list(self):
        """Создать список ботов"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Кнопки для каждого бота
        self.xauusd_btn = self.create_bot_button("🥇 XAUUSD", "xauusd")
        self.btc_btn = self.create_bot_button("₿ BTC", "btc")
        self.eth_btn = self.create_bot_button("⟠ ETH", "eth")

        layout.addWidget(self.xauusd_btn)
        layout.addWidget(self.btc_btn)
        layout.addWidget(self.eth_btn)
        layout.addStretch()

        widget.setLayout(layout)
        return widget

    def create_bot_button(self, label, bot_id):
        """Создать кнопку бота"""
        btn = QPushButton(label)
        btn.clicked.connect(lambda: self.select_bot(bot_id))
        return btn

    def select_bot(self, bot_id):
        """Выбрать бота для отображения"""
        self.current_bot = bot_id
        self.update_main_panel()
```

### 4. SettingsDialog (gui/settings_dialog.py)

```python
class SettingsDialog(QDialog):
    """Диалог настроек бота"""

    def __init__(self, config: BotConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.init_ui()

    def init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout()

        # Exchange settings
        exchange_group = self.create_exchange_group()
        layout.addWidget(exchange_group)

        # Trading parameters
        trading_group = self.create_trading_group()
        layout.addWidget(trading_group)

        # Strategy settings
        strategy_group = self.create_strategy_group()
        layout.addWidget(strategy_group)

        # Telegram settings
        telegram_group = self.create_telegram_group()
        layout.addWidget(telegram_group)

        # Buttons
        buttons = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

        self.setLayout(layout)

    def save_settings(self):
        """Сохранить настройки"""
        # Собрать данные из полей
        self.config.symbol = self.symbol_combo.currentText()
        self.config.risk_percent = float(self.risk_input.text())
        # ... и т.д.

        # Сохранить в базу данных
        self.accept()
```

---

## 💾 База данных (SQLite)

### Схема базы данных:

```sql
-- Конфигурации ботов
CREATE TABLE bot_configs (
    id INTEGER PRIMARY KEY,
    bot_id TEXT UNIQUE NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    api_key_encrypted TEXT,
    api_secret_encrypted TEXT,
    risk_percent REAL DEFAULT 2.0,
    max_positions INTEGER DEFAULT 3,
    timeframe TEXT DEFAULT '1h',
    strategy TEXT DEFAULT 'v3_adaptive',
    trend_tp1 REAL,
    trend_tp2 REAL,
    trend_tp3 REAL,
    range_tp1 REAL,
    range_tp2 REAL,
    range_tp3 REAL,
    telegram_enabled BOOLEAN DEFAULT 0,
    telegram_token_encrypted TEXT,
    telegram_chat_id_encrypted TEXT,
    dry_run BOOLEAN DEFAULT 1,
    testnet BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- История сделок (импорт из CSV логов)
CREATE TABLE trades (
    id INTEGER PRIMARY KEY,
    bot_id TEXT NOT NULL,
    order_id TEXT,
    open_time TIMESTAMP,
    close_time TIMESTAMP,
    type TEXT,  -- BUY/SELL
    amount REAL,
    entry_price REAL,
    sl REAL,
    tp REAL,
    close_price REAL,
    profit REAL,
    profit_pct REAL,
    market_regime TEXT,  -- TREND/RANGE
    duration_hours REAL,
    status TEXT,  -- OPEN/TP/SL/CLOSED
    comment TEXT,
    FOREIGN KEY (bot_id) REFERENCES bot_configs(bot_id)
);

-- Статус ботов (runtime)
CREATE TABLE bot_status (
    id INTEGER PRIMARY KEY,
    bot_id TEXT UNIQUE NOT NULL,
    status TEXT,  -- stopped/running/error
    balance REAL,
    equity REAL,
    pnl_today REAL,
    open_positions INTEGER,
    last_signal_time TIMESTAMP,
    last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bot_id) REFERENCES bot_configs(bot_id)
);

-- Логи приложения
CREATE TABLE app_logs (
    id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level TEXT,  -- DEBUG/INFO/WARNING/ERROR
    bot_id TEXT,
    message TEXT
);
```

---

## 📦 Упаковка приложения

### PyInstaller

```bash
# Установить PyInstaller
pip install pyinstaller

# Создать .exe
pyinstaller --onefile --windowed \
    --name="TradingBotManager" \
    --icon=assets/icon.ico \
    --add-data "assets;assets" \
    --add-data "trading_bots;trading_bots" \
    --hidden-import=PySide6 \
    --hidden-import=ccxt \
    --hidden-import=MetaTrader5 \
    main.py
```

### Spec файл (для более детальной настройки)

```python
# trading_app.spec
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('trading_bots', 'trading_bots'),
    ],
    hiddenimports=[
        'PySide6',
        'ccxt',
        'MetaTrader5',
        'pandas',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

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
    console=False,  # Без консоли
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)
```

---

## 🚀 План реализации Phase 1 (4-6 недель)

### Неделя 1-2: Основной GUI
- [x] Создать структуру проекта
- [ ] Главное окно с списком ботов
- [ ] Панель управления ботом (start/stop)
- [ ] Базовое отображение статуса

### Неделя 2-3: Интеграция с ботами
- [ ] BotManager для управления ботами
- [ ] BotThread для запуска в фоне
- [ ] Перенаправление логов в GUI
- [ ] Сигналы для обновления статуса

### Неделя 3-4: Настройки и конфигурация
- [ ] Диалог настроек бота
- [ ] Сохранение/загрузка конфигурации
- [ ] Шифрование API ключей
- [ ] База данных (SQLite)

### Неделя 4-5: Мониторинг
- [ ] Отображение открытых позиций
- [ ] Статистика торговли
- [ ] История сделок
- [ ] Графики (опционально)

### Неделя 5-6: Тестирование и упаковка
- [ ] Тестирование всех функций
- [ ] Багфиксинг
- [ ] Упаковка в .exe (PyInstaller)
- [ ] Документация пользователя

---

## 📊 Минимальные системные требования

```
OS: Windows 10/11 (64-bit)
CPU: Intel Core i3 или аналог
RAM: 4 GB
Disk: 500 MB свободного места
Internet: Постоянное подключение

Для XAUUSD бота также требуется:
- MetaTrader 5 установлен
```

---

## 📝 Что будет в Phase 2 (после Phase 1)

- [ ] Система лицензирования
- [ ] Online activation
- [ ] Code obfuscation (PyArmor)
- [ ] Auto-updater
- [ ] Advanced backtesting в GUI
- [ ] Оптимизация параметров
- [ ] Web dashboard (удаленный доступ)
- [ ] Mobile notifications

---

## 🎯 Успех Phase 1

**Критерии успеха:**
1. ✅ Можно запустить/остановить любой бот через GUI
2. ✅ Все логи отображаются в реальном времени
3. ✅ Настройки сохраняются и загружаются
4. ✅ Мониторинг позиций работает
5. ✅ Приложение упаковано в .exe
6. ✅ Стабильно работает 24/7

---

## 📞 Поддержка при разработке

### Используемые технологии:
- **PySide6 Docs**: https://doc.qt.io/qtforpython/
- **SQLite**: https://www.sqlite.org/docs.html
- **PyInstaller**: https://pyinstaller.org/en/stable/

### Полезные ресурсы:
- Qt Designer для визуального дизайна
- Qt Creator для разработки
- Python threading документация

---

**Готовы начать Phase 1!** 🚀

После успешной реализации базового GUI, перейдем к Phase 2 с лицензированием и advanced функциями.
