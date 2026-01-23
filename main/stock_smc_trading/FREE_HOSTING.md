# Бесплатный запуск Stock Screener

Как запустить screener **полностью бесплатно** - несколько вариантов.

---

## 🎯 Лучшие бесплатные варианты

| Сервис | Бесплатный лимит | Сложность | Рекомендация |
|--------|------------------|-----------|--------------|
| **GitHub Actions** | 2000 минут/месяц | Легко 🟢 | ⭐ Лучший выбор |
| **Oracle Cloud** | Всегда бесплатно | Средне 🟡 | ⭐ Полноценный VPS |
| **Google Colab** | Неограниченно* | Легко 🟢 | Для экспериментов |
| **PythonAnywhere** | 1 app бесплатно | Легко 🟢 | Хорошо для начала |
| **Replit** | Ограничено | Легко 🟢 | Быстрый старт |
| **Railway** | $5 кредитов/месяц | Средне 🟡 | Современный |

---

## ⭐ Вариант 1: GitHub Actions (Рекомендуется)

**Плюсы:**
- ✅ Полностью бесплатно (2000 минут/месяц)
- ✅ Работает автоматически по расписанию
- ✅ Не требует VPS
- ✅ Результаты сохраняются в репозиторий
- ✅ Легко настроить

**Минусы:**
- ⚠️ Ограничение времени выполнения (6 часов макс.)
- ⚠️ Публичный репозиторий (или платный для приватного)

### Настройка:

#### 1. Создать workflow файл:

```bash
mkdir -p .github/workflows
nano .github/workflows/stock_screener.yml
```

#### 2. Вставить конфигурацию:

```yaml
name: Stock Screener

on:
  schedule:
    # Запускать каждый день в 9:00 UTC
    - cron: '0 9 * * *'
  workflow_dispatch:  # Ручной запуск

jobs:
  run-screener:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v3
      with:
        ref: claude/simplify-stock-screener-WzlXB

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        cd main/stock_smc_trading
        pip install -r requirements.txt

    - name: Run screener
      run: |
        cd main/stock_smc_trading
        python3 real_data_screener.py

    - name: Upload results
      uses: actions/upload-artifact@v3
      with:
        name: screener-results
        path: main/stock_smc_trading/real_data_screener_results.csv

    - name: Commit results
      run: |
        cd main/stock_smc_trading
        git config --local user.email "action@github.com"
        git config --local user.name "GitHub Action"
        git add real_data_screener_results.csv || true
        git commit -m "Update screener results $(date +%Y-%m-%d)" || true
        git push || true
```

#### 3. Запушить в GitHub:

```bash
git add .github/workflows/stock_screener.yml
git commit -m "Add GitHub Actions workflow"
git push origin claude/simplify-stock-screener-WzlXB
```

#### 4. Готово!

Screener будет запускаться автоматически каждый день в 9:00 UTC.

**Посмотреть результаты:**
- GitHub → Actions → Stock Screener → Artifacts
- Или в репозитории (если включен commit results)

---

## 🌟 Вариант 2: Oracle Cloud Always Free (Полноценный VPS)

**Плюсы:**
- ✅ **Полностью бесплатно НАВСЕГДА**
- ✅ Полноценный VPS (1-4 OCPU, 1-24 GB RAM)
- ✅ Публичный IP
- ✅ Без ограничений времени
- ✅ 200 GB диска

**Минусы:**
- ⚠️ Нужна банковская карта (не списывают)
- ⚠️ Сложнее настроить

### Настройка:

#### 1. Регистрация:
- Зайти на https://www.oracle.com/cloud/free/
- Создать аккаунт (нужна карта, но не спишут)
- Подтвердить email

#### 2. Создать VM:
```
Compute → Instances → Create Instance
- Image: Ubuntu 22.04
- Shape: VM.Standard.A1.Flex (ARM)
  - OCPU: 1-4 (бесплатно)
  - RAM: 6-24 GB (бесплатно)
- VCN: Create new
```

#### 3. Подключиться:
```bash
ssh -i your_key.pem ubuntu@your_oracle_ip
```

#### 4. Установить screener:
```bash
sudo apt update && sudo apt install -y python3 python3-pip git
git clone https://github.com/Muhammed77741/main.git
cd main/main/stock_smc_trading
bash scripts/vps_setup.sh
```

**Готово!** У вас полноценный бесплатный VPS навсегда.

---

## 📊 Вариант 3: Google Colab (Для экспериментов)

**Плюсы:**
- ✅ Полностью бесплатно
- ✅ Jupyter notebooks
- ✅ GPU доступ (не нужен для screener'а)
- ✅ Не требует настройки

**Минусы:**
- ⚠️ Сессия умирает через 12 часов
- ⚠️ Нужно запускать вручную
- ⚠️ Нет автоматизации

### Использование:

#### 1. Создать notebook:
Открыть https://colab.research.google.com/

#### 2. Вставить код:

```python
# Установка
!git clone https://github.com/Muhammed77741/main.git
%cd main/main/stock_smc_trading
!pip install -q -r requirements.txt

# Запуск
!python3 real_data_screener.py

# Показать результаты
import pandas as pd
df = pd.read_csv('real_data_screener_results.csv')
display(df)
```

#### 3. Запустить все ячейки

Результаты появятся прямо в notebook.

**Скачать результаты:**
```python
from google.colab import files
files.download('real_data_screener_results.csv')
```

---

## 🐍 Вариант 4: PythonAnywhere

**Плюсы:**
- ✅ Бесплатный план
- ✅ Легко настроить
- ✅ Веб-интерфейс
- ✅ Scheduled tasks (1 задача бесплатно)

**Минусы:**
- ⚠️ Ограничения на внешние запросы (whitelist)
- ⚠️ Только 1 scheduled task

### Настройка:

#### 1. Регистрация:
https://www.pythonanywhere.com/registration/register/beginner/

#### 2. Загрузить код:
```bash
# В консоли PythonAnywhere
git clone https://github.com/Muhammed77741/main.git
cd main/main/stock_smc_trading
pip3 install --user -r requirements.txt
```

#### 3. Создать scheduled task:
```
Tasks → Add a new scheduled task
Command: python3 /home/username/main/main/stock_smc_trading/real_data_screener.py
Time: 09:00 UTC
```

**Ограничение:** Yahoo Finance может быть заблокирован. Используйте demo_screener.py

---

## 🔄 Вариант 5: Replit

**Плюсы:**
- ✅ Бесплатно
- ✅ Онлайн IDE
- ✅ Быстрый старт
- ✅ Веб-интерфейс

**Минусы:**
- ⚠️ Repl засыпает без активности
- ⚠️ Ограниченные ресурсы

### Использование:

#### 1. Создать Repl:
https://replit.com/

#### 2. Import from GitHub:
```
Import from GitHub → Muhammed77741/main
Branch: claude/simplify-stock-screener-WzlXB
```

#### 3. Запустить:
```bash
cd main/stock_smc_trading
python3 real_data_screener.py
```

#### 4. Keep alive (чтобы не засыпал):
Использовать UptimeRobot для пинга Repl каждые 5 минут.

---

## 💰 Вариант 6: Railway (Ограниченно бесплатно)

**Плюсы:**
- ✅ $5 бесплатных кредитов/месяц
- ✅ Современный интерфейс
- ✅ Auto-deploy из GitHub
- ✅ Легко настроить

**Минусы:**
- ⚠️ Ограниченные бесплатные кредиты
- ⚠️ Может не хватить на месяц

### Настройка:

#### 1. Регистрация:
https://railway.app/

#### 2. New Project → Deploy from GitHub

#### 3. Создать railway.json:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "cd main/stock_smc_trading && python3 real_data_screener.py",
    "restartPolicyType": "ON_FAILURE"
  }
}
```

#### 4. Добавить cron (через другой сервис или GitHub Actions)

---

## 🌐 Сравнение бесплатных вариантов

| Критерий | GitHub Actions | Oracle Cloud | Google Colab | PythonAnywhere |
|----------|---------------|--------------|--------------|----------------|
| **Стоимость** | Бесплатно | Бесплатно | Бесплатно | Бесплатно |
| **Лимиты** | 2000 мин/мес | Без лимитов | 12ч сессия | 1 задача |
| **Автозапуск** | ✅ Cron | ✅ Cron | ❌ Вручную | ✅ 1 задача |
| **Настройка** | Легко | Сложнее | Легко | Легко |
| **VPS** | ❌ Нет | ✅ Да | ❌ Нет | ❌ Нет |
| **Публичный IP** | ❌ Нет | ✅ Да | ❌ Нет | ❌ Нет |

---

## ⭐ Мои рекомендации

### Для начинающих:
**GitHub Actions** - самый простой способ
```yaml
# Один файл .github/workflows/stock_screener.yml
# И все работает автоматически!
```

### Для серьезного использования:
**Oracle Cloud Always Free** - полноценный VPS бесплатно
```bash
# Настоящий VPS с публичным IP
# Можно делать что угодно
# Навсегда бесплатно
```

### Для экспериментов:
**Google Colab** - быстро протестировать
```python
# Jupyter notebook в браузере
# Не требует установки
```

---

## 🚀 Быстрый старт: GitHub Actions (5 минут)

### 1. Создать файл:
```bash
mkdir -p .github/workflows
cat > .github/workflows/screener.yml << 'EOF'
name: Daily Stock Screener

on:
  schedule:
    - cron: '0 9 * * *'  # 9:00 UTC каждый день
  workflow_dispatch:

jobs:
  screen:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          ref: claude/simplify-stock-screener-WzlXB

      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install & Run
        run: |
          cd main/stock_smc_trading
          pip install -r requirements.txt
          python3 real_data_screener.py

      - uses: actions/upload-artifact@v3
        with:
          name: results
          path: main/stock_smc_trading/*.csv
EOF
```

### 2. Запушить:
```bash
git add .github/workflows/screener.yml
git commit -m "Add daily screener"
git push
```

### 3. Готово!
Зайти на GitHub → Actions → Увидите результаты

---

## 💡 Советы по экономии

### 1. Кэширование зависимостей (GitHub Actions):
```yaml
- uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

### 2. Запускать реже:
```yaml
# Раз в неделю вместо каждый день
- cron: '0 9 * * 1'  # Только понедельник
```

### 3. Использовать demo_screener.py:
```python
# Не требует интернета для yfinance
# Быстрее работает
python3 demo_screener.py
```

---

## 🔧 Troubleshooting

### GitHub Actions не запускается:
1. Проверить Actions включены: Settings → Actions → Allow all actions
2. Проверить cron синтаксис: https://crontab.guru/
3. Запустить вручную: Actions → Run workflow

### Oracle Cloud не дает создать VM:
- Попробовать другой регион
- Выбрать ARM (A1.Flex) вместо AMD
- Подождать 24 часа после регистрации

### PythonAnywhere блокирует yfinance:
```python
# Использовать demo_screener.py
# Или comprehensive_screener.py (hardcoded данные)
```

---

## 📊 Итоговые рекомендации

### Начните с GitHub Actions:
```bash
# 1. Создать .github/workflows/screener.yml
# 2. Запушить
# 3. Profit!
```

### Если нужен VPS - Oracle Cloud:
```bash
# Бесплатный VPS навсегда
# 1-4 CPU, до 24GB RAM
# Полный контроль
```

### Комбо подход (лучшее):
```
GitHub Actions - ежедневный скрининг
Oracle Cloud - хранение результатов, веб-интерфейс
Colab - эксперименты с новыми стратегиями
```

---

## ✅ Что выбрать?

**Хочу просто чтобы работало:**
→ GitHub Actions

**Нужен настоящий VPS:**
→ Oracle Cloud Always Free

**Хочу поэкспериментировать:**
→ Google Colab

**Нужен веб-интерфейс:**
→ PythonAnywhere или Railway

---

**Стоимость всех вариантов: $0/месяц** 🎉
