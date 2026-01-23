========================================
   STOCK SCREENER - WINDOWS SCRIPTS
========================================

Эти BAT файлы упрощают запуск screener'а на Windows.

ФАЙЛЫ:
------
install.bat          - Установка всех зависимостей
run_demo.bat         - Запуск demo версии (быстро, без интернета)
run_real.bat         - Запуск с реальными данными (требует интернет)
run_comprehensive.bat - Полный анализ (технический + фундаментальный)

ИНСТРУКЦИЯ:
-----------

1. ПЕРВЫЙ ЗАПУСК:

   a) Скопировать все BAT файлы в папку:
      main\main\stock_smc_trading\

   b) Запустить install.bat
      (установит Python пакеты)

   c) Готово!

2. ИСПОЛЬЗОВАНИЕ:

   Двойной клик на:
   - run_demo.bat - для быстрого теста
   - run_real.bat - для реальных данных
   - run_comprehensive.bat - для полного анализа

3. РЕЗУЛЬТАТЫ:

   Открываются автоматически в Excel
   Или найти в папке:
   - demo_top_stocks.csv
   - real_data_screener_results.csv
   - comprehensive_screener_results.csv

ТРЕБОВАНИЯ:
-----------
- Windows 10/11
- Python 3.8+ (установить с python.org)
- При установке Python поставить галочку "Add to PATH"

TROUBLESHOOTING:
----------------

Проблема: "Python не найден"
Решение: Установить Python с галочкой "Add to PATH"

Проблема: "pandas не установлен"
Решение: Запустить install.bat еще раз

Проблема: Русские буквы в пути
Решение: Переместить папку в C:\stock_screener\

========================================
Для помощи: см. WINDOWS_INSTALL.md
========================================
