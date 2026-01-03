# Quick Start - VPS Setup (5 минут)

Самый быстрый способ запустить Stock Screener на VPS.

## 🚀 Быстрая установка (1 команда)

```bash
# Подключиться к VPS
ssh user@your_vps_ip

# Запустить установку
bash <(curl -s https://raw.githubusercontent.com/Muhammed77741/main/claude/simplify-stock-screener-WzlXB/main/stock_smc_trading/scripts/vps_setup.sh)
```

**Или вручную:**

```bash
# 1. Подключиться к VPS
ssh user@your_vps_ip

# 2. Клонировать репозиторий
git clone https://github.com/Muhammed77741/main.git
cd main/main/stock_smc_trading

# 3. Запустить установку
bash scripts/vps_setup.sh
```

---

## ⚡ Еще быстрее (для Ubuntu/Debian)

```bash
# Все в одной команде
ssh user@your_vps_ip 'bash -s' < <(curl -s https://gist.githubusercontent.com/...setup.sh)
```

---

## 📋 Пошаговая инструкция

### Шаг 1: Подключение
```bash
ssh root@your_vps_ip
```

### Шаг 2: Установка базовых пакетов
```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git
```

### Шаг 3: Клонирование репозитория
```bash
cd ~
git clone https://github.com/Muhammed77741/main.git
cd main/main/stock_smc_trading
```

### Шаг 4: Создание виртуального окружения
```bash
python3 -m venv venv
source venv/bin/activate
```

### Шаг 5: Установка зависимостей
```bash
pip install -r requirements.txt
```

### Шаг 6: Тестовый запуск
```bash
# Demo версия (без интернета)
python3 demo_screener.py

# Или с реальными данными (требует yfinance)
python3 real_data_screener.py
```

---

## ⏰ Настройка автозапуска (2 минуты)

### Вариант 1: Автоматически (рекомендуется)
```bash
bash scripts/vps_setup.sh
# Ответьте 'y' когда спросит про cron
```

### Вариант 2: Вручную

#### 1. Сделать скрипт исполняемым
```bash
chmod +x scripts/run_screener.sh
```

#### 2. Протестировать
```bash
./scripts/run_screener.sh
```

#### 3. Добавить в cron
```bash
crontab -e

# Добавить строку (запуск каждый день в 9:00)
0 9 * * * ~/main/main/stock_smc_trading/scripts/run_screener.sh
```

---

## 📊 Просмотр результатов

### Последние результаты
```bash
cat ~/screener_results/latest.csv
```

### Все результаты
```bash
ls -lh ~/screener_results/
```

### Логи
```bash
tail -f ~/screener_logs/screener_*.log
```

---

## 🔄 Обновление

```bash
cd ~/main/main/stock_smc_trading
./scripts/update_repo.sh
```

---

## 📝 Расписание cron (примеры)

```bash
# Каждый день в 9:00
0 9 * * * ~/main/main/stock_smc_trading/scripts/run_screener.sh

# Каждый понедельник в 10:00
0 10 * * 1 ~/main/main/stock_smc_trading/scripts/run_screener.sh

# Каждый будний день в 9:00 и 18:00
0 9,18 * * 1-5 ~/main/main/stock_smc_trading/scripts/run_screener.sh

# Каждые 4 часа
0 */4 * * * ~/main/main/stock_smc_trading/scripts/run_screener.sh
```

---

## 🆘 Troubleshooting

### Проблема: yfinance не устанавливается
```bash
sudo apt install -y python3-dev build-essential
pip install yfinance --no-cache-dir
```

### Проблема: Permission denied
```bash
chmod +x scripts/*.sh
```

### Проблема: Cron не запускается
```bash
sudo systemctl status cron
sudo systemctl restart cron
```

### Проблема: Нет результатов
```bash
# Запустить вручную и посмотреть ошибки
cd ~/main/main/stock_smc_trading
python3 real_data_screener.py
```

---

## ✅ Проверка установки

```bash
# 1. Проверить Python
python3 --version  # Должно быть 3.8+

# 2. Проверить зависимости
pip list | grep yfinance

# 3. Тестовый запуск
python3 demo_screener.py

# 4. Проверить cron
crontab -l

# 5. Проверить логи
ls ~/screener_logs/
```

---

## 🎯 Что дальше?

1. **Посмотрите результаты**: `cat ~/screener_results/latest.csv`
2. **Настройте расписание**: `crontab -e`
3. **Прочитайте полный гайд**: `VPS_DEPLOYMENT.md`
4. **Настройте email уведомления**: См. VPS_DEPLOYMENT.md Шаг 9

---

## 📚 Полезные файлы

- **VPS_DEPLOYMENT.md** - Полная документация
- **DATA_SOURCES.md** - Откуда берутся данные
- **FUNDAMENTAL_GUIDE.md** - Гайд по фундаментальному анализу
- **SCREENER_README.md** - Как работает screener

---

## 💡 Советы

1. **Используйте tmux** для длительных сессий:
   ```bash
   sudo apt install tmux
   tmux new -s screener
   # Ctrl+B, D для выхода
   # tmux attach -t screener для возврата
   ```

2. **Настройте firewall** (если нужен веб-доступ):
   ```bash
   sudo ufw allow 5000/tcp  # Для Flask веб-интерфейса
   ```

3. **Мониторьте ресурсы**:
   ```bash
   htop  # Установить: sudo apt install htop
   ```

4. **Бэкап результатов**:
   ```bash
   rsync -av ~/screener_results/ user@backup-server:/backup/
   ```

---

**Время установки:** ~5 минут
**Сложность:** Легко 🟢
**Нужны права:** sudo (для установки пакетов)
