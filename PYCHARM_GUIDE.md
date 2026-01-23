# Запуск Stock Screener через PyCharm

Пошаговая инструкция для PyCharm IDE

---

## 🚀 Быстрый старт

### Шаг 1: Открыть проект в PyCharm

1. **Скачать репозиторий:**
   - Зайти на https://github.com/Muhammed77741/main
   - Code → Download ZIP
   - Распаковать

2. **Открыть в PyCharm:**
   - File → Open
   - Выбрать папку `main/main/stock_smc_trading`
   - Open

---

### Шаг 2: Настроить Python Interpreter

1. **File → Settings** (или Ctrl+Alt+S)

2. **Project: stock_smc_trading → Python Interpreter**

3. **Добавить интерпретатор:**
   - Нажать ⚙️ (шестеренка) → Add...
   - Выбрать **Virtualenv Environment**
   - Location: `venv` (в папке проекта)
   - Base interpreter: Python 3.11+ (выбрать установленный Python)
   - ✅ Create
   - OK

PyCharm создаст виртуальное окружение.

---

### Шаг 3: Установить зависимости

**Вариант 1: Через requirements.txt (автоматически)**

1. PyCharm должен показать уведомление:
   ```
   Package requirements 'requirements.txt' are not satisfied
   ```

2. Нажать **Install requirements**

3. Подождать установки

**Вариант 2: Через Terminal вручную**

1. **View → Tool Windows → Terminal** (или Alt+F12)

2. В терминале PyCharm выполнить:
```bash
pip install -r requirements.txt
```

Или по отдельности:
```bash
pip install pandas numpy
pip install yfinance
```

---

### Шаг 4: Запустить screener

#### **Способ 1: Через кнопку Run ▶️**

1. Открыть файл `demo_screener.py` в редакторе

2. Нажать **▶️ (зеленая стрелка)** справа от:
   ```python
   if __name__ == "__main__":
   ```

3. Или ПКМ на файле → Run 'demo_screener'

4. Результаты появятся в консоли внизу

#### **Способ 2: Через Run Configuration**

1. **Run → Edit Configurations...**

2. **+ (Add New)** → Python

3. **Настройки:**
   - Name: `Demo Screener`
   - Script path: `.../demo_screener.py` (выбрать файл)
   - Working directory: `.../stock_smc_trading`
   - OK

4. **Теперь в меню Run можно выбрать "Demo Screener" и запустить**

#### **Способ 3: Через Terminal**

1. **Alt+F12** (открыть Terminal)

2. Выполнить:
```bash
python demo_screener.py
```

---

## 📊 Запуск разных версий screener'а

### 1. Demo версия (быстро, без интернета):
```python
# Открыть demo_screener.py
# Нажать ▶️ Run
```

### 2. Real data (с реальными данными):
```python
# Открыть real_data_screener.py
# Нажать ▶️ Run
```

### 3. Comprehensive (полный анализ):
```python
# Открыть comprehensive_screener.py
# Нажать ▶️ Run
```

---

## 🔧 Создание Run Configurations для всех версий

1. **Run → Edit Configurations...**

2. **Создать 3 конфигурации:**

### Configuration 1: Demo Screener
```
Name: Demo Screener
Script: demo_screener.py
Working directory: .../stock_smc_trading
Python interpreter: venv
```

### Configuration 2: Real Data Screener
```
Name: Real Data Screener
Script: real_data_screener.py
Working directory: .../stock_smc_trading
Python interpreter: venv
```

### Configuration 3: Comprehensive Screener
```
Name: Comprehensive Screener
Script: comprehensive_screener.py
Working directory: .../stock_smc_trading
Python interpreter: venv
```

3. **Теперь можно переключаться:**
   - В toolbar сверху выбрать нужный screener
   - Нажать ▶️ Run

---

## 📁 Просмотр результатов в PyCharm

### После запуска:

1. **Найти CSV файл** в Project Explorer слева:
   - `demo_top_stocks.csv`
   - `real_data_screener_results.csv`
   - `comprehensive_screener_results.csv`

2. **Открыть файл:**
   - Двойной клик → откроется в редакторе
   - Или ПКМ → Open In → Excel (если установлен)

3. **Посмотреть как таблицу:**
   - Установить плагин: **CSV Plugin**
   - File → Settings → Plugins → Marketplace
   - Найти "CSV" → Install
   - Перезапустить PyCharm
   - Теперь CSV откроется как таблица

---

## 🐛 Debug режим

### Запуск с отладкой:

1. **Поставить breakpoint:**
   - Кликнуть слева от номера строки (появится красная точка)
   - Например, на строке:
   ```python
   results = screener.screen_multiple(universe)
   ```

2. **Запустить в Debug:**
   - Нажать 🐞 (Debug) вместо ▶️ (Run)
   - Или Shift+F9

3. **Отладка:**
   - Программа остановится на breakpoint
   - Можно посмотреть значения переменных внизу
   - F8 - следующая строка
   - F9 - продолжить выполнение

---

## 💡 Полезные функции PyCharm

### 1. Интерактивная консоль Python

После запуска screener'а:

1. **Tools → Python Console**

2. Загрузить результаты:
```python
import pandas as pd
df = pd.read_csv('demo_top_stocks.csv')
print(df)
print(df.describe())
```

### 2. SciView (для визуализации)

```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('demo_top_stocks.csv')

# График
df.plot(x='ticker', y='total_score', kind='bar')
plt.show()  # Откроется в SciView внизу
```

### 3. Data View (просмотр DataFrame)

```python
import pandas as pd
df = pd.read_csv('demo_top_stocks.csv')
# В Debug режиме кликнуть на df → View as DataFrame
```

---

## 📝 Редактирование и тестирование

### Изменить параметры screener'а:

1. **Открыть `demo_screener.py`**

2. **Найти в конце файла:**
```python
if __name__ == "__main__":
    screener = StockScreener(
        lookback_days=180,  # Изменить период
        min_score=60,       # Изменить минимальный балл
        top_n=10            # Изменить количество акций
    )
```

3. **Изменить параметры:**
```python
screener = StockScreener(
    lookback_days=365,  # Анализ за год
    min_score=50,       # Показать больше результатов
    top_n=20            # Топ-20 акций
)
```

4. **Сохранить (Ctrl+S)**

5. **Запустить ▶️**

---

## 🔄 Git интеграция в PyCharm

### Обновление кода:

1. **VCS → Git → Pull**
   - Выбрать ветку `claude/simplify-stock-screener-WzlXB`
   - OK

2. **Или через Terminal:**
```bash
git pull origin claude/simplify-stock-screener-WzlXB
```

---

## ⚙️ Настройки для удобства

### 1. Включить автосохранение

File → Settings → Appearance & Behavior → System Settings
- ✅ Save files automatically

### 2. Показывать номера строк

File → Settings → Editor → General → Appearance
- ✅ Show line numbers

### 3. Настроить Terminal

File → Settings → Tools → Terminal
- Shell path: `cmd.exe` (Windows) или `bash` (Linux/Mac)

### 4. Установить CSV плагин

File → Settings → Plugins
- Marketplace → Поиск "CSV"
- Install "CSV Plugin"

---

## 🎯 Типичный workflow в PyCharm

```
1. Открыть проект
2. Убедиться что venv активирован (внизу справа)
3. Выбрать нужный screener в dropdown (вверху)
4. Нажать ▶️ Run
5. Посмотреть результаты в консоли
6. Открыть CSV файл
7. Анализировать результаты
```

---

## 🆘 Troubleshooting

### Проблема: "No module named 'pandas'"

**Решение:**
1. Проверить что venv активирован (внизу справа должно быть "Python 3.11 (venv)")
2. Terminal → `pip install pandas numpy`
3. Restart Python Console

### Проблема: "Python interpreter not configured"

**Решение:**
1. File → Settings → Project → Python Interpreter
2. Add Interpreter → Virtualenv Environment
3. Выбрать Python 3.11+

### Проблема: Скрипт не запускается

**Решение:**
1. Проверить Working Directory в Run Configuration
2. Должен быть: `.../stock_smc_trading`
3. Run → Edit Configurations → исправить путь

### Проблема: CSV открывается как текст

**Решение:**
1. Установить CSV Plugin
2. ПКМ на CSV → Open As → Data Editor

---

## 📚 Полезные shortcuts PyCharm

```
Ctrl+Alt+S       - Settings
Shift+F10        - Run
Shift+F9         - Debug
Alt+F12          - Terminal
Ctrl+S           - Save
Ctrl+F           - Find
Ctrl+Shift+F     - Find in files
Ctrl+/           - Comment line
Ctrl+D           - Duplicate line
Ctrl+Y           - Delete line
Ctrl+Space       - Autocomplete
```

---

## 🎓 Расширенное использование

### Создать свою версию screener'а:

1. **ПКМ на `demo_screener.py` → Copy**

2. **ПКМ в Project Explorer → Paste**

3. **Назвать: `my_screener.py`**

4. **Изменить код:**
```python
# Добавить свои метрики
# Изменить параметры скоринга
# Добавить новые индикаторы
```

5. **Запустить свою версию**

### Сравнить результаты:

```python
import pandas as pd

demo = pd.read_csv('demo_top_stocks.csv')
real = pd.read_csv('real_data_screener_results.csv')

# Сравнить
print("Demo results:")
print(demo.head())

print("\nReal data results:")
print(real.head())
```

---

## ✅ Checklist

- [ ] PyCharm установлен
- [ ] Проект открыт
- [ ] Python Interpreter настроен (venv)
- [ ] Зависимости установлены (pandas, numpy)
- [ ] Demo screener запускается
- [ ] CSV файлы открываются
- [ ] (Опционально) CSV Plugin установлен
- [ ] (Опционально) Run Configurations созданы

---

## 🎉 Готово!

Теперь вы можете:
- ✅ Запускать screener одной кнопкой ▶️
- ✅ Отлаживать код с breakpoints
- ✅ Визуализировать результаты
- ✅ Редактировать параметры
- ✅ Создавать свои версии

**Время настройки:** 5-10 минут
**Сложность:** 🟢 Легко (если знаком с PyCharm)

---

Нужна помощь? Пишите!
