# Stock Screener - Быстрая установка

Три способа установки на ваш VPS (Oracle Cloud, DigitalOcean, и т.д.)

---

## 🚀 Способ 1: One-liner (САМЫЙ БЫСТРЫЙ)

**Скопируйте и вставьте одну команду:**

```bash
bash <(curl -s https://raw.githubusercontent.com/Muhammed77741/main/claude/simplify-stock-screener-WzlXB/install.sh)
```

**Или с wget:**

```bash
bash <(wget -qO- https://raw.githubusercontent.com/Muhammed77741/main/claude/simplify-stock-screener-WzlXB/install.sh)
```

Скрипт автоматически:
- ✅ Обновит систему
- ✅ Установит Python и зависимости
- ✅ Склонирует репозиторий
- ✅ Создаст виртуальное окружение
- ✅ Установит все пакеты
- ✅ Протестирует работу
- ✅ Настроит автозапуск (спросит разрешения)
- ✅ Покажет инструкции

**Время установки:** ~3-5 минут

---

## 📦 Способ 2: Git clone + Install

```bash
# 1. Клонировать репозиторий
git clone https://github.com/Muhammed77741/main.git
cd main

# 2. Запустить установку
bash install.sh
```

---

## 🔧 Способ 3: Ручная установка (если нужен контроль)

```bash
# 1. Обновить систему
sudo apt update && sudo apt upgrade -y

# 2. Установить зависимости
sudo apt install -y python3 python3-pip python3-venv git

# 3. Клонировать репозиторий
cd ~
git clone https://github.com/Muhammed77741/main.git
cd main/main/stock_smc_trading

# 4. Запустить setup скрипт
bash scripts/vps_setup.sh
```

---

## 📺 Пошаговое видео (Oracle Cloud)

### После создания Oracle Cloud VM:

**Шаг 1: Подключиться к VPS**
```bash
ssh -i ~/.ssh/oracle_key ubuntu@YOUR_IP
```

**Шаг 2: Запустить one-liner**
```bash
bash <(curl -s https://raw.githubusercontent.com/Muhammed77741/main/claude/simplify-stock-screener-WzlXB/install.sh)
```

**Шаг 3: Ответить на вопрос**
```
Setup cron? (y/n): y
```

**Готово!** 🎉

---

## 🎯 Что делает install.sh?

### Шаг 1/8: Обновление системы
```
✓ System packages updated
```

### Шаг 2/8: Установка зависимостей
```
✓ Python 3.10+ installed
✓ Git installed
✓ Build tools installed
```

### Шаг 3/8: Клонирование репозитория
```
✓ Repository ready at /home/ubuntu/main
```

### Шаг 4/8: Виртуальное окружение
```
✓ Virtual environment created
```

### Шаг 5/8: Python пакеты
```
✓ pandas and numpy installed
✓ yfinance installed (real data available)
```

### Шаг 6/8: Создание директорий
```
✓ Directories created
  - Logs: /home/ubuntu/screener_logs
  - Results: /home/ubuntu/screener_results
```

### Шаг 7/8: Настройка скриптов
```
✓ Scripts are executable
```

### Шаг 8/8: Тестирование
```
✓ Demo screener works!
```

### Опционально: Cron
```
✓ Cron job added (runs daily at 9:00 AM UTC)
```

---

## ✅ После установки

### Тест ручного запуска:
```bash
cd ~/main/main/stock_smc_trading
./scripts/run_screener.sh
```

### Посмотреть результаты:
```bash
cat ~/screener_results/latest.csv
```

### Посмотреть логи:
```bash
tail -50 ~/screener_logs/screener_*.log | tail -50
```

### Изменить расписание:
```bash
crontab -e

# Примеры:
# Каждый день в 14:00 UTC
0 14 * * * ~/main/main/stock_smc_trading/scripts/run_screener.sh

# Каждый понедельник
0 9 * * 1 ~/main/main/stock_smc_trading/scripts/run_screener.sh
```

---

## 🌐 Полная команда для Oracle Cloud

```bash
# Подключиться
ssh -i ~/.ssh/oracle_key ubuntu@YOUR_ORACLE_IP

# Установить
bash <(curl -s https://raw.githubusercontent.com/Muhammed77741/main/claude/simplify-stock-screener-WzlXB/install.sh)

# Ответить 'y' на вопрос про cron

# Готово! Отключиться
exit
```

Screener будет работать автоматически каждый день!

---

## 🔄 Обновление

```bash
cd ~/main/main/stock_smc_trading
./scripts/update_repo.sh
```

---

## 🆘 Troubleshooting

### Ошибка: "curl: command not found"
```bash
sudo apt install curl
```

### Ошибка: "Permission denied"
```bash
chmod +x install.sh
bash install.sh
```

### Ошибка при установке yfinance
```bash
# Это нормально, будет использоваться demo_screener.py
# Или попробовать:
sudo apt install python3-dev build-essential
```

### Скрипт зависает
```bash
# Нажать Ctrl+C и попробовать:
bash install.sh
```

---

## 📋 Системные требования

**Минимальные:**
- Ubuntu 20.04+ / Debian 11+
- 512 MB RAM
- 5 GB диска
- Python 3.8+

**Рекомендуемые (Oracle Cloud Free):**
- Ubuntu 22.04
- 6-12 GB RAM
- 50 GB диска
- 2 vCPU

---

## 🎁 Что получится после установки

```
~/main/main/stock_smc_trading/
├── venv/                    # Виртуальное окружение
├── scripts/
│   ├── run_screener.sh     # Запуск screener'а
│   ├── update_repo.sh      # Обновление кода
│   └── vps_setup.sh        # Переустановка
├── *_screener.py           # Screener скрипты
└── *.md                    # Документация

~/screener_logs/             # Логи всех запусков
~/screener_results/          # CSV результаты
```

**Автоматический запуск:** Каждый день в 9:00 AM UTC

---

## 💡 Полезные алиасы (опционально)

Добавить в `~/.bashrc`:

```bash
# Stock Screener shortcuts
alias screener='cd ~/main/main/stock_smc_trading && ./scripts/run_screener.sh'
alias screener-results='cat ~/screener_results/latest.csv'
alias screener-logs='tail -f ~/screener_logs/screener_*.log'
alias screener-update='cd ~/main/main/stock_smc_trading && ./scripts/update_repo.sh'
```

Применить:
```bash
source ~/.bashrc
```

Теперь можно просто писать:
```bash
screener          # Запустить
screener-results  # Показать результаты
screener-logs     # Показать логи
screener-update   # Обновить
```

---

## 🌟 Рекомендации

### Для Oracle Cloud:
```bash
# 1. Создать VM (ARM, Ubuntu 22.04, 2 vCPU, 12 GB RAM)
# 2. Подключиться по SSH
# 3. Запустить one-liner
bash <(curl -s https://raw.githubusercontent.com/Muhammed77741/main/claude/simplify-stock-screener-WzlXB/install.sh)
```

### Для других VPS (DigitalOcean, Linode, etc):
```bash
# То же самое!
bash <(curl -s https://raw.githubusercontent.com/Muhammed77741/main/claude/simplify-stock-screener-WzlXB/install.sh)
```

---

## 📞 Поддержка

Если что-то не работает:

1. **Проверить логи установки**
2. **Попробовать ручную установку** (Способ 3)
3. **Проверить версию Python:** `python3 --version` (должна быть 3.8+)
4. **Проверить интернет:** `ping -c 3 google.com`

---

**Время установки:** 3-5 минут
**Сложность:** 🟢 Очень легко (one-liner)
**Стоимость:** $0 (Oracle Cloud Always Free)
