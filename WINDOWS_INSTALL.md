# Запуск Stock Screener на Windows

Полная инструкция по установке и запуску screener'а на Windows 10/11.

---

## 🎯 Быстрый старт (5 минут)

### Вариант 1: Автоматическая установка (PowerShell)

1. **Открыть PowerShell**
   - Win + X → Windows PowerShell (Admin)

2. **Скопировать и запустить:**
```powershell
# Скачать и запустить установщик
irm https://raw.githubusercontent.com/Muhammed77741/main/claude/simplify-stock-screener-WzlXB/install_windows.ps1 | iex
```

---

### Вариант 2: Ручная установка (рекомендуется для начинающих)

#### Шаг 1: Установить Python

1. **Скачать Python:**
   - Зайти на https://www.python.org/downloads/
   - Скачать Python 3.11+ (кнопка "Download Python")

2. **Установить Python:**
   - Запустить скачанный файл
   - ✅ **ВАЖНО:** Поставить галочку **"Add Python to PATH"**
   - Нажать "Install Now"

3. **Проверить установку:**
   - Win + R → `cmd` → Enter
   - Написать: `python --version`
   - Должно показать: `Python 3.11.x`

---

#### Шаг 2: Скачать код

**Вариант 2.1: Через Git (если установлен)**
```bash
# Открыть командную строку (Win + R → cmd)
cd C:\Users\%USERNAME%\Desktop
git clone https://github.com/Muhammed77741/main.git
cd main\main\stock_smc_trading
```

**Вариант 2.2: Скачать ZIP (проще)**
1. Зайти на https://github.com/Muhammed77741/main
2. Code → Download ZIP
3. Распаковать на Рабочий стол
4. Открыть папку: `main-claude-simplify-stock-screener-WzlXB\main\stock_smc_trading`

---

#### Шаг 3: Установить зависимости

1. **Открыть папку в проводнике**
   - Перейти в `stock_smc_trading`

2. **Открыть командную строку в этой папке**
   - В адресной строке написать `cmd` и нажать Enter
   - Или Shift + ПКМ → "Открыть окно PowerShell здесь"

3. **Создать виртуальное окружение (опционально, но рекомендуется):**
```bash
python -m venv venv
venv\Scripts\activate
```

4. **Установить пакеты:**
```bash
pip install pandas numpy
```

5. **Установить yfinance (для реальных данных):**
```bash
pip install yfinance
```

Если yfinance не устанавливается - не страшно, будет работать demo версия.

---

#### Шаг 4: Запустить screener

**Demo версия (без интернета, быстро):**
```bash
python demo_screener.py
```

**С реальными данными (требует интернет):**
```bash
python real_data_screener.py
```

**Comprehensive (технический + фундаментальный анализ):**
```bash
python comprehensive_screener.py
```

---

#### Шаг 5: Посмотреть результаты

**В командной строке:**
```bash
type demo_top_stocks.csv
# или
type real_data_screener_results.csv
```

**В Excel:**
1. Найти файл `demo_top_stocks.csv` в папке
2. ПКМ → Открыть с помощью → Excel

**В Блокноте:**
```bash
notepad demo_top_stocks.csv
```

---

## 🚀 Пакетные файлы (BAT) для быстрого запуска

Создайте `.bat` файлы для одним кликом запуска:

### 1. `run_demo.bat` - Запуск demo версии
```batch
@echo off
echo ========================================
echo   Stock Screener - Demo Version
echo ========================================
echo.

cd /d "%~dp0"

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

python demo_screener.py

echo.
echo ========================================
echo   Results saved to:
echo   %CD%\demo_top_stocks.csv
echo ========================================
echo.

pause
```

### 2. `run_real.bat` - Запуск с реальными данными
```batch
@echo off
echo ========================================
echo   Stock Screener - Real Data
echo ========================================
echo.

cd /d "%~dp0"

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

python real_data_screener.py

echo.
echo ========================================
echo   Results saved to:
echo   %CD%\real_data_screener_results.csv
echo ========================================
echo.

start excel real_data_screener_results.csv

pause
```

### 3. `run_comprehensive.bat` - Полный анализ
```batch
@echo off
echo ========================================
echo   Stock Screener - Comprehensive
echo ========================================
echo.

cd /d "%~dp0"

if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

python comprehensive_screener.py

echo.
echo Results: comprehensive_screener_results.csv
pause
```

### 4. `install.bat` - Установка зависимостей
```batch
@echo off
echo ========================================
echo   Installing Dependencies
echo ========================================
echo.

python -m venv venv
call venv\Scripts\activate.bat

pip install --upgrade pip
pip install pandas numpy

echo.
echo Trying to install yfinance (for real data)...
pip install yfinance

echo.
echo ========================================
echo   Installation Complete!
echo ========================================
echo.
pause
```

**Использование:**
1. Создать текстовый файл
2. Скопировать код
3. Сохранить как `run_demo.bat` (не `.txt`!)
4. Двойной клик для запуска

---

## ⏰ Автоматический запуск (Task Scheduler)

### Настройка ежедневного запуска в Windows:

#### Шаг 1: Создать PowerShell скрипт

**Создать файл `run_screener.ps1`:**
```powershell
# Перейти в директорию
Set-Location "C:\Users\YourUsername\Desktop\main\main\stock_smc_trading"

# Активировать venv (если есть)
if (Test-Path "venv\Scripts\Activate.ps1") {
    .\venv\Scripts\Activate.ps1
}

# Запустить screener
python real_data_screener.py

# Скопировать результаты с датой
$date = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item "real_data_screener_results.csv" "results_$date.csv"

# Логирование
$log = "Screener completed at $(Get-Date)"
Add-Content -Path "screener.log" -Value $log
```

#### Шаг 2: Открыть Task Scheduler

1. Win + R → `taskschd.msc` → Enter
2. Action → Create Basic Task
3. Name: `Stock Screener Daily`
4. Trigger: Daily (выбрать время, например 9:00)
5. Action: Start a program
   - Program: `powershell.exe`
   - Arguments: `-ExecutionPolicy Bypass -File "C:\Users\YourUsername\Desktop\main\main\stock_smc_trading\run_screener.ps1"`
6. Finish

#### Шаг 3: Протестировать

1. Найти созданную задачу в Task Scheduler
2. ПКМ → Run
3. Проверить результаты

---

## 📁 Структура папок

```
C:\Users\YourUsername\Desktop\main\main\stock_smc_trading\
│
├── venv\                          # Виртуальное окружение (если создано)
│
├── demo_screener.py               # Demo версия
├── real_data_screener.py          # С реальными данными
├── comprehensive_screener.py      # Полный анализ
│
├── run_demo.bat                   # Быстрый запуск demo
├── run_real.bat                   # Быстрый запуск real
├── install.bat                    # Установка зависимостей
│
├── demo_top_stocks.csv            # Результаты demo
├── real_data_screener_results.csv # Результаты real
└── comprehensive_screener_results.csv # Результаты comprehensive
```

---

## 🎨 GUI версия (для тех кто не любит командную строку)

Создайте простой GUI с помощью Python:

**`gui_launcher.py`:**
```python
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os

class ScreenerGUI:
    def __init__(self, root):
        self.root = root
        root.title("Stock Screener Launcher")
        root.geometry("400x300")

        # Title
        title = ttk.Label(root, text="📊 Stock Screener", font=('Arial', 16, 'bold'))
        title.pack(pady=20)

        # Buttons
        btn_demo = ttk.Button(root, text="Run Demo Screener", command=self.run_demo, width=30)
        btn_demo.pack(pady=10)

        btn_real = ttk.Button(root, text="Run Real Data Screener", command=self.run_real, width=30)
        btn_real.pack(pady=10)

        btn_comprehensive = ttk.Button(root, text="Run Comprehensive Screener", command=self.run_comprehensive, width=30)
        btn_comprehensive.pack(pady=10)

        btn_results = ttk.Button(root, text="Open Results in Excel", command=self.open_results, width=30)
        btn_results.pack(pady=10)

        # Status
        self.status = ttk.Label(root, text="Ready", relief=tk.SUNKEN)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    def run_demo(self):
        self.status.config(text="Running demo screener...")
        self.root.update()
        subprocess.run(["python", "demo_screener.py"], shell=True)
        self.status.config(text="Demo complete! Results saved.")
        messagebox.showinfo("Complete", "Demo screener finished!\nResults: demo_top_stocks.csv")

    def run_real(self):
        self.status.config(text="Running real data screener...")
        self.root.update()
        subprocess.run(["python", "real_data_screener.py"], shell=True)
        self.status.config(text="Real data complete! Results saved.")
        messagebox.showinfo("Complete", "Real data screener finished!\nResults: real_data_screener_results.csv")

    def run_comprehensive(self):
        self.status.config(text="Running comprehensive screener...")
        self.root.update()
        subprocess.run(["python", "comprehensive_screener.py"], shell=True)
        self.status.config(text="Comprehensive complete! Results saved.")
        messagebox.showinfo("Complete", "Comprehensive screener finished!")

    def open_results(self):
        if os.path.exists("real_data_screener_results.csv"):
            os.startfile("real_data_screener_results.csv")
        elif os.path.exists("demo_top_stocks.csv"):
            os.startfile("demo_top_stocks.csv")
        else:
            messagebox.showwarning("Not Found", "No results found. Run screener first.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ScreenerGUI(root)
    root.mainloop()
```

**Запуск GUI:**
```bash
python gui_launcher.py
```

**Создать ярлык:**
1. ПКМ на Рабочем столе → Создать → Ярлык
2. Расположение: `C:\Users\YourUsername\Desktop\main\main\stock_smc_trading\gui_launcher.py`
3. Назвать: "Stock Screener"
4. Готово! Теперь можно запускать двойным кликом

---

## 🔍 Troubleshooting

### Python не найден
```
'python' is not recognized as an internal or external command
```
**Решение:**
1. Переустановить Python с галочкой "Add to PATH"
2. Или использовать `py` вместо `python`:
```bash
py demo_screener.py
```

### Ошибка импорта pandas
```
ModuleNotFoundError: No module named 'pandas'
```
**Решение:**
```bash
pip install pandas numpy
```

### yfinance не устанавливается
```
ERROR: Failed building wheel for multitasking
```
**Решение:**
Используйте demo_screener.py (работает без yfinance)

### Русские буквы в пути
Если в пути к файлу есть русские буквы, могут быть проблемы.

**Решение:**
Переместить папку в `C:\stock_screener\`

---

## 💡 Полезные советы

### 1. Создать desktop shortcut для quick access:

**Ярлык для demo screener:**
```
Target: C:\Windows\System32\cmd.exe /k "cd /d C:\Users\YourName\Desktop\main\main\stock_smc_trading && python demo_screener.py"
```

### 2. Открывать результаты в Excel автоматически:

Добавить в конец BAT файла:
```batch
start excel demo_top_stocks.csv
```

### 3. Создать папку для результатов:

```batch
if not exist "results" mkdir results
copy /y demo_top_stocks.csv results\results_%date%.csv
```

### 4. Notifications:

Добавить уведомление Windows:
```powershell
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.MessageBox]::Show("Screener completed!")
```

---

## 📊 Просмотр результатов

### В Excel:
1. Открыть файл CSV
2. Data → Text to Columns → Delimited → Comma

### В Python (анализ):
```python
import pandas as pd

# Загрузить результаты
df = pd.read_csv('demo_top_stocks.csv')

# Показать топ-5
print(df.head())

# Фильтровать по баллу
high_score = df[df['total_score'] > 70]
print(high_score)

# Построить график
import matplotlib.pyplot as plt
df.plot(x='ticker', y='total_score', kind='bar')
plt.show()
```

---

## ✅ Checklist

- [ ] Python установлен (с галочкой Add to PATH)
- [ ] Код скачан (git clone или ZIP)
- [ ] Зависимости установлены (pip install)
- [ ] Demo screener работает
- [ ] BAT файлы созданы (опционально)
- [ ] Task Scheduler настроен (опционально)
- [ ] Результаты открываются в Excel

---

## 🎯 Рекомендуемая настройка для Windows:

```
1. Установить Python 3.11+ (с Add to PATH)
2. Скачать ZIP с GitHub
3. Распаковать на Desktop
4. Создать install.bat и запустить
5. Создать run_demo.bat и run_real.bat
6. Двойной клик на run_demo.bat для запуска
7. Открыть результаты в Excel
```

**Время настройки:** 10-15 минут
**Сложность:** 🟢 Легко (с картинками)
**Автозапуск:** Через Task Scheduler

---

**Если нужны скриншоты или видео - дайте знать!**
