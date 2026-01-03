# Запуск Stock Screener на VPS

Пошаговая инструкция по деплою и автоматическому запуску screener'а на VPS.

## 🖥️ Требования к VPS

**Минимальные:**
- Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- 1 GB RAM
- 10 GB диск
- Python 3.8+

**Рекомендуемые провайдеры:**
- DigitalOcean - от $6/месяц
- Linode - от $5/месяц
- Vultr - от $5/месяц
- AWS EC2 - от $3.5/месяц
- Hetzner - от €4/месяц

---

## 📋 Шаг 1: Подключение к VPS

### Через SSH:
```bash
ssh root@your_vps_ip
# или
ssh username@your_vps_ip
```

### Если используете SSH ключ:
```bash
ssh -i ~/.ssh/your_key.pem username@your_vps_ip
```

---

## 🔧 Шаг 2: Установка зависимостей

### Ubuntu/Debian:
```bash
# Обновить систему
sudo apt update && sudo apt upgrade -y

# Установить Python и pip
sudo apt install python3 python3-pip git -y

# Проверить версию Python (должна быть 3.8+)
python3 --version
```

### CentOS/RHEL:
```bash
sudo yum update -y
sudo yum install python3 python3-pip git -y
python3 --version
```

---

## 📦 Шаг 3: Клонирование репозитория

```bash
# Перейти в домашнюю директорию
cd ~

# Клонировать репозиторий
git clone https://github.com/Muhammed77741/main.git

# Перейти в директорию
cd main/main/stock_smc_trading

# Проверить файлы
ls -la
```

---

## 🐍 Шаг 4: Установка Python зависимостей

### Вариант 1: Простая установка
```bash
pip3 install -r requirements.txt
```

### Вариант 2: Виртуальное окружение (рекомендуется)
```bash
# Установить virtualenv
sudo apt install python3-venv -y

# Создать виртуальное окружение
python3 -m venv venv

# Активировать
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Проверить установку
pip list
```

### Если yfinance не устанавливается:
```bash
# Установить build зависимости
sudo apt install python3-dev build-essential -y

# Попробовать снова
pip install yfinance --no-cache-dir
```

---

## 🚀 Шаг 5: Запуск screener'а

### Разовый запуск:

#### 1. Demo screener (без интернета):
```bash
python3 demo_screener.py
```

#### 2. Real data screener (с реальными данными):
```bash
python3 real_data_screener.py
```

#### 3. Comprehensive screener (hardcoded данные):
```bash
python3 comprehensive_screener.py
```

### Проверка результатов:
```bash
# Посмотреть результаты
ls -lh *.csv

# Прочитать CSV
cat comprehensive_screener_results.csv
# или
head -n 10 comprehensive_screener_results.csv
```

---

## ⏰ Шаг 6: Автоматический запуск (Cron)

### Создать скрипт запуска:

```bash
# Создать скрипт
nano ~/run_screener.sh
```

Вставить содержимое:
```bash
#!/bin/bash

# Путь к репозиторию
REPO_DIR="$HOME/main/main/stock_smc_trading"

# Путь к виртуальному окружению (если используется)
VENV_DIR="$REPO_DIR/venv"

# Путь для логов
LOG_DIR="$HOME/screener_logs"
mkdir -p $LOG_DIR

# Дата для имени файла
DATE=$(date +%Y%m%d_%H%M%S)

# Перейти в директорию
cd $REPO_DIR

# Активировать venv (если используется)
if [ -d "$VENV_DIR" ]; then
    source $VENV_DIR/bin/activate
fi

# Запустить screener
echo "=== Stock Screener Run: $(date) ===" >> $LOG_DIR/screener_${DATE}.log
python3 real_data_screener.py >> $LOG_DIR/screener_${DATE}.log 2>&1

# Скопировать результаты
if [ -f "real_data_screener_results.csv" ]; then
    cp real_data_screener_results.csv $LOG_DIR/results_${DATE}.csv
    echo "Results saved to $LOG_DIR/results_${DATE}.csv" >> $LOG_DIR/screener_${DATE}.log
fi

# Отправить email (опционально, требует настройки mail)
# echo "Screener completed" | mail -s "Stock Screener Results" your@email.com

echo "=== Completed: $(date) ===" >> $LOG_DIR/screener_${DATE}.log
```

Сохранить: `Ctrl+X`, затем `Y`, затем `Enter`

### Сделать скрипт исполняемым:
```bash
chmod +x ~/run_screener.sh
```

### Протестировать скрипт:
```bash
~/run_screener.sh

# Проверить логи
ls -lh ~/screener_logs/
cat ~/screener_logs/screener_*.log
```

---

## 📅 Шаг 7: Настройка Cron

### Открыть crontab:
```bash
crontab -e
```

### Выбрать редактор (если спрашивает):
Выберите `nano` (обычно вариант 1)

### Добавить задания:

```bash
# Запускать каждый день в 9:00 утра
0 9 * * * /home/username/run_screener.sh

# Запускать каждый понедельник в 10:00
0 10 * * 1 /home/username/run_screener.sh

# Запускать каждый час
0 * * * * /home/username/run_screener.sh

# Запускать каждые 4 часа
0 */4 * * * /home/username/run_screener.sh

# Запускать каждый будний день в 9:00 и 18:00
0 9,18 * * 1-5 /home/username/run_screener.sh
```

### Формат cron:
```
* * * * * команда
│ │ │ │ │
│ │ │ │ └─── День недели (0-7, 0 и 7 = воскресенье)
│ │ │ └───── Месяц (1-12)
│ │ └─────── День месяца (1-31)
│ └───────── Час (0-23)
└─────────── Минута (0-59)
```

### Примеры расписаний:

```bash
# Ежедневно в 9:00 утра
0 9 * * *

# Каждый понедельник в 10:00
0 10 * * 1

# Каждый час
0 * * * *

# Каждые 30 минут
*/30 * * * *

# По будням в 9:00
0 9 * * 1-5

# В 9:00, 12:00, 18:00 каждый день
0 9,12,18 * * *
```

### Сохранить и выйти:
`Ctrl+X`, `Y`, `Enter`

### Проверить crontab:
```bash
crontab -l
```

---

## 📊 Шаг 8: Мониторинг и логи

### Просмотр логов cron:
```bash
# Системные логи cron
sudo tail -f /var/log/syslog | grep CRON
# или
sudo tail -f /var/log/cron
```

### Просмотр логов screener'а:
```bash
# Последний запуск
ls -lt ~/screener_logs/screener_*.log | head -1 | xargs cat

# Все логи
ls ~/screener_logs/

# Последние 50 строк последнего лога
ls -lt ~/screener_logs/screener_*.log | head -1 | xargs tail -50
```

### Очистка старых логов:
```bash
# Удалить логи старше 7 дней
find ~/screener_logs -name "*.log" -mtime +7 -delete
find ~/screener_logs -name "*.csv" -mtime +7 -delete
```

### Добавить в cron автоматическую очистку:
```bash
crontab -e

# Добавить строку (очистка каждый понедельник в 00:00)
0 0 * * 1 find ~/screener_logs -name "*.log" -mtime +7 -delete
```

---

## 📧 Шаг 9: Отправка результатов по email (опционально)

### Установить mail:
```bash
sudo apt install mailutils -y
```

### Настроить SMTP (Gmail пример):
```bash
# Создать файл конфигурации
sudo nano /etc/ssmtp/ssmtp.conf
```

Вставить:
```
root=your-email@gmail.com
mailhub=smtp.gmail.com:587
AuthUser=your-email@gmail.com
AuthPass=your-app-password
UseSTARTTLS=YES
```

### Изменить скрипт для отправки email:
```bash
nano ~/run_screener.sh
```

Добавить в конец:
```bash
# Отправить результаты на email
if [ -f "real_data_screener_results.csv" ]; then
    echo "Stock screener results attached" | \
    mail -s "Stock Screener - $(date +%Y-%m-%d)" \
         -A real_data_screener_results.csv \
         your@email.com
fi
```

---

## 🔄 Шаг 10: Автоматическое обновление репозитория

### Создать скрипт обновления:
```bash
nano ~/update_repo.sh
```

Вставить:
```bash
#!/bin/bash

REPO_DIR="$HOME/main"
LOG_FILE="$HOME/screener_logs/update_$(date +%Y%m%d).log"

cd $REPO_DIR

echo "=== Update started: $(date) ===" >> $LOG_FILE

# Обновить репозиторий
git fetch origin >> $LOG_FILE 2>&1
git pull origin claude/simplify-stock-screener-WzlXB >> $LOG_FILE 2>&1

echo "=== Update completed: $(date) ===" >> $LOG_FILE
```

### Сделать исполняемым:
```bash
chmod +x ~/update_repo.sh
```

### Добавить в cron (каждый день в 8:00):
```bash
crontab -e

# Добавить
0 8 * * * /home/username/update_repo.sh
```

---

## 🔐 Шаг 11: Безопасность

### 1. Создать отдельного пользователя:
```bash
# Создать пользователя
sudo adduser screener

# Переключиться на пользователя
sudo su - screener

# Повторить шаги 3-7
```

### 2. Ограничить доступ к логам:
```bash
chmod 700 ~/screener_logs
```

### 3. Не хранить API ключи в коде:
```bash
# Создать .env файл
nano ~/.env
```

Вставить:
```
ALPHA_VANTAGE_KEY=your_api_key
FMP_KEY=your_fmp_key
```

Загрузить в скрипте:
```bash
# В run_screener.sh добавить
export $(cat ~/.env | xargs)
```

---

## 📱 Шаг 12: Веб-интерфейс (опционально)

### Создать простой веб-сервер для просмотра результатов:

```bash
# Установить Flask
pip3 install flask

# Создать web.py
nano ~/main/main/stock_smc_trading/web.py
```

Вставить:
```python
from flask import Flask, send_file, render_template_string
import pandas as pd
import os

app = Flask(__name__)

@app.route('/')
def index():
    csv_file = 'real_data_screener_results.csv'
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
        html = df.to_html(classes='table table-striped')
        return render_template_string('''
        <html>
        <head>
            <title>Stock Screener Results</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5/dist/css/bootstrap.min.css">
        </head>
        <body>
            <div class="container mt-5">
                <h1>Stock Screener Results</h1>
                <p>Last updated: {{ updated }}</p>
                {{ table|safe }}
            </div>
        </body>
        </html>
        ''', table=html, updated=pd.Timestamp.now())
    return "No results yet"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### Запустить веб-сервер:
```bash
python3 web.py
```

Открыть в браузере: `http://your_vps_ip:5000`

---

## 🐳 Бонус: Docker деплой

### Создать Dockerfile:
```bash
nano ~/main/main/stock_smc_trading/Dockerfile
```

Вставить:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "real_data_screener.py"]
```

### Создать docker-compose.yml:
```yaml
version: '3.8'
services:
  screener:
    build: .
    volumes:
      - ./results:/app/results
    environment:
      - TZ=Europe/Moscow
```

### Запустить:
```bash
docker-compose up -d
```

---

## ✅ Проверочный список

- [ ] VPS подключен
- [ ] Python 3.8+ установлен
- [ ] Репозиторий склонирован
- [ ] Зависимости установлены
- [ ] Screener запускается вручную
- [ ] Скрипт run_screener.sh создан
- [ ] Cron настроен
- [ ] Логи работают
- [ ] Результаты сохраняются

---

## 🆘 Troubleshooting

### Проблема: "Permission denied"
```bash
chmod +x ~/run_screener.sh
```

### Проблема: "Module not found"
```bash
# Проверить где установлены пакеты
pip3 list

# Переустановить
pip3 install -r requirements.txt --force-reinstall
```

### Проблема: Cron не запускается
```bash
# Проверить статус cron
sudo systemctl status cron

# Перезапустить
sudo systemctl restart cron

# Проверить логи
sudo tail -f /var/log/syslog | grep CRON
```

### Проблема: yfinance не работает
```bash
# Проверить интернет
ping -c 3 google.com

# Проверить прокси
echo $http_proxy

# Попробовать другой источник
pip3 install yfinance --index-url https://pypi.org/simple/
```

### Проблема: Мало места на диске
```bash
# Проверить использование диска
df -h

# Очистить логи
find ~/screener_logs -name "*.log" -mtime +7 -delete

# Очистить apt cache
sudo apt clean
```

---

## 📚 Полезные команды

```bash
# Проверить запущен ли процесс
ps aux | grep python3

# Убить процесс
pkill -f real_data_screener.py

# Посмотреть использование ресурсов
top
htop

# Проверить логи системы
journalctl -f

# Перезагрузить VPS
sudo reboot
```

---

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте логи: `~/screener_logs/`
2. Проверьте cron логи: `/var/log/syslog`
3. Запустите вручную: `python3 real_data_screener.py`
4. Проверьте версию Python: `python3 --version`
5. Проверьте зависимости: `pip3 list`
