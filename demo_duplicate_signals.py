"""
ДЕМОНСТРАЦИЯ: Обработка дубликатов сигналов

Показывает разницу между Live Bot и Signal Analysis в обработке
повторяющихся сигналов
"""

from datetime import datetime

print("="*80)
print("ВОПРОС: Signal Analysis не перезаписывает уже созданный сигнал?")
print("="*80)

print("""
КОНТЕКСТ:
---------
Live Bot теперь имеет механизм предотвращения дубликатов.
Вопрос: нужен ли такой же механизм в Signal Analysis?


ПРИМЕР СИТУАЦИИ:
================

Допустим, стратегия генерирует сигналы:
""")

signals = [
    (datetime(2024, 1, 15, 0, 0), "LONG", 2500.0),
    (datetime(2024, 1, 15, 1, 0), "LONG", 2500.0),  # Дубликат!
    (datetime(2024, 1, 15, 2, 0), "LONG", 2505.0),  # Другая цена
    (datetime(2024, 1, 15, 3, 0), "LONG", 2500.0),  # Снова дубликат!
]

print("\n📊 СИГНАЛЫ ОТ СТРАТЕГИИ:")
print("-" * 60)
for i, (time, direction, entry) in enumerate(signals, 1):
    signal_id = f"{time.strftime('%Y%m%d%H')}_{1 if direction == 'LONG' else -1}_{entry}"
    print(f"{i}. {time.strftime('%H:%M')} - {direction} @ ${entry:.2f}")
    print(f"   Signal ID: {signal_id}")

# Проверяем дубликаты
print("\n\n🔍 АНАЛИЗ ДУБЛИКАТОВ:")
print("-" * 60)

seen_signals = set()
duplicates = []

for i, (time, direction, entry) in enumerate(signals, 1):
    signal_id = f"{time.strftime('%Y%m%d%H')}_{1 if direction == 'LONG' else -1}_{entry}"
    
    if signal_id in seen_signals:
        duplicates.append(i)
        print(f"Сигнал #{i}: ДУБЛИКАТ (ID уже есть: {signal_id})")
    else:
        seen_signals.add(signal_id)
        print(f"Сигнал #{i}: УНИКАЛЬНЫЙ (ID: {signal_id})")

print(f"\n✓ Уникальных сигналов: {len(seen_signals)}")
print(f"✓ Дубликатов: {len(duplicates)}")
if duplicates:
    print(f"  Дубликаты: сигналы #{', #'.join(map(str, duplicates))}")

# Live Bot поведение
print("\n\n🤖 ПОВЕДЕНИЕ LIVE BOT:")
print("="*60)

print("\nLive Bot работает непрерывно и проверяет каждый час:")
print()

# Симулируем проверки Live Bot
check_times = [
    datetime(2024, 1, 15, 1, 0),
    datetime(2024, 1, 15, 2, 0),
    datetime(2024, 1, 15, 3, 0),
    datetime(2024, 1, 15, 4, 0),
]

opened_signals = set()

for check_time in check_times:
    print(f"\n⏰ Проверка в {check_time.strftime('%H:%M')}:")
    print("-" * 40)
    
    # Ищем сигнал на предыдущем баре
    prev_bar_time = datetime(check_time.year, check_time.month, check_time.day, 
                             check_time.hour - 1, 0)
    
    # Ищем сигнал с этим временем
    found_signal = None
    for time, direction, entry in signals:
        if time == prev_bar_time:
            found_signal = (time, direction, entry)
            break
    
    if found_signal:
        time, direction, entry = found_signal
        signal_id = f"{time.strftime('%Y%m%d%H')}_{1 if direction == 'LONG' else -1}_{entry}"
        
        if signal_id in opened_signals:
            print(f"  Найден сигнал: {direction} @ ${entry:.2f}")
            print(f"  Signal ID: {signal_id}")
            print(f"  ❌ ПРОПУСКАЕМ - уже открыт!")
        else:
            print(f"  Найден сигнал: {direction} @ ${entry:.2f}")
            print(f"  Signal ID: {signal_id}")
            print(f"  ✅ ОТКРЫВАЕМ позицию")
            opened_signals.add(signal_id)
    else:
        print(f"  Нет сигнала на баре {prev_bar_time.strftime('%H:%M')}")

print(f"\n✓ Live Bot открыл {len(opened_signals)} позиций")

# Signal Analysis поведение
print("\n\n📈 ПОВЕДЕНИЕ SIGNAL ANALYSIS (текущее):")
print("="*60)

print("\nSignal Analysis обрабатывает все сигналы ОДИН РАЗ:")
print()

positions_opened = 0
for i, (time, direction, entry) in enumerate(signals, 1):
    print(f"Сигнал #{i} ({time.strftime('%H:%M')}): {direction} @ ${entry:.2f}")
    print(f"  → Обрабатываем и открываем позицию")
    positions_opened += 1

print(f"\n✓ Signal Analysis открыл {positions_opened} позиций")

# Signal Analysis с фильтрацией (предлагаемое)
print("\n\n📈 SIGNAL ANALYSIS С ФИЛЬТРАЦИЕЙ ДУБЛИКАТОВ (предлагаемое):")
print("="*60)

print("\nЕсли добавить фильтрацию, как в Live Bot:")
print()

opened_in_backtest = set()
positions_with_filter = 0

for i, (time, direction, entry) in enumerate(signals, 1):
    signal_id = f"{time.strftime('%Y%m%d%H')}_{1 if direction == 'LONG' else -1}_{entry}"
    
    if signal_id in opened_in_backtest:
        print(f"Сигнал #{i} ({time.strftime('%H:%M')}): {direction} @ ${entry:.2f}")
        print(f"  ❌ ПРОПУСКАЕМ - дубликат (ID: {signal_id})")
    else:
        print(f"Сигнал #{i} ({time.strftime('%H:%M')}): {direction} @ ${entry:.2f}")
        print(f"  ✅ Обрабатываем (ID: {signal_id})")
        opened_in_backtest.add(signal_id)
        positions_with_filter += 1

print(f"\n✓ Signal Analysis с фильтрацией открыл {positions_with_filter} позиций")

# Сравнение
print("\n\n" + "="*80)
print("СРАВНЕНИЕ РЕЗУЛЬТАТОВ:")
print("="*80)

print(f"""
┌────────────────────────────────────┬─────────────────┐
│ Метод                              │ Позиций открыто │
├────────────────────────────────────┼─────────────────┤
│ Live Bot                           │ {len(opened_signals):^15} │
│ Signal Analysis (текущее)          │ {positions_opened:^15} │
│ Signal Analysis (с фильтрацией)    │ {positions_with_filter:^15} │
└────────────────────────────────────┴─────────────────┘

ВЫВОДЫ:
-------
1. Live Bot: {len(opened_signals)} позиций (игнорирует дубликаты)
2. Signal Analysis (текущее): {positions_opened} позиций (обрабатывает все)
3. Signal Analysis (с фильтрацией): {positions_with_filter} позиций (как Live Bot)

РЕКОМЕНДАЦИЯ:
-------------
Если вы хотите, чтобы backtest ТОЧНО соответствовал Live Bot,
нужно добавить фильтрацию дубликатов в Signal Analysis.

Это обеспечит:
✅ Одинаковое количество сделок
✅ Одинаковую логику открытия позиций
✅ Более точное соответствие backtest результатам и live результатам

НО: Если стратегия генерирует РАЗНЫЕ сигналы (разные цены входа),
они все будут обработаны (что правильно).
""")

print("="*80)
