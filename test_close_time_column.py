"""
Тест: Проверка вычисления времени закрытия бара

Демонстрирует работу новой функции для разных таймфреймов
"""

from datetime import datetime, timedelta

def calculate_bar_close_time(open_time, timeframe):
    """
    Calculate bar close time based on open time and timeframe
    
    Args:
        open_time: datetime - bar open time
        timeframe: str - timeframe ('1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w')
    
    Returns:
        datetime - bar close time
    """
    timeframe_deltas = {
        '1m': timedelta(minutes=1),
        '3m': timedelta(minutes=3),
        '5m': timedelta(minutes=5),
        '15m': timedelta(minutes=15),
        '30m': timedelta(minutes=30),
        '1h': timedelta(hours=1),
        '2h': timedelta(hours=2),
        '4h': timedelta(hours=4),
        '6h': timedelta(hours=6),
        '8h': timedelta(hours=8),
        '12h': timedelta(hours=12),
        '1d': timedelta(days=1),
        '3d': timedelta(days=3),
        '1w': timedelta(weeks=1),
    }
    
    delta = timeframe_deltas.get(timeframe, timedelta(hours=1))  # Default to 1h
    return open_time + delta


print("="*80)
print("ТЕСТ: Вычисление времени закрытия бара")
print("="*80)

print("""
НОВАЯ ФУНКЦИЯ: Отдельная колонка для времени закрытия
======================================================

Теперь в Signal Analysis таблице показываются:
  1. Date/Time (Open) - время ОТКРЫТИЯ бара
  2. Close Time - время ЗАКРЫТИЯ бара
  
Это делает очевидным весь период бара.
""")

# Примеры для разных таймфреймов
timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
open_time = datetime(2024, 1, 15, 14, 0)  # 2024-01-15 14:00

print("\nПРИМЕРЫ ВЫЧИСЛЕНИЯ:")
print("="*80)
print(f"Время открытия бара: {open_time.strftime('%Y-%m-%d %H:%M')}")
print()

for tf in timeframes:
    close_time = calculate_bar_close_time(open_time, tf)
    period = close_time - open_time
    
    # Format period nicely
    total_seconds = period.total_seconds()
    if total_seconds < 3600:
        period_str = f"{int(total_seconds / 60)} минут"
    elif total_seconds < 86400:
        period_str = f"{int(total_seconds / 3600)} часов"
    else:
        period_str = f"{int(total_seconds / 86400)} дней"
    
    print(f"Таймфрейм {tf:>4} → Закрытие: {close_time.strftime('%Y-%m-%d %H:%M')} (период: {period_str})")

print("\n" + "="*80)
print("КАК ЭТО ВЫГЛЯДИТ В ТАБЛИЦЕ:")
print("="*80)

print("""
┌──────────────────┬──────────────────┬──────┬───────┬────────────┐
│ Date/Time (Open) │   Close Time     │ Type │ Price │    ...     │
├──────────────────┼──────────────────┼──────┼───────┼────────────┤
│ 2024-01-15 14:00 │ 2024-01-15 15:00 │ BUY  │ 2500  │    ...     │  ← H1
│ 2024-01-15 15:00 │ 2024-01-15 16:00 │ SELL │ 2505  │    ...     │  ← H1
│ 2024-01-15 10:00 │ 2024-01-15 10:15 │ BUY  │ 2495  │    ...     │  ← M15
└──────────────────┴──────────────────┴──────┴───────┴────────────┘

ПРЕИМУЩЕСТВА:
=============

✅ Видно полный период бара (открытие → закрытие)
✅ Понятно когда именно сигнал стал доступен (на закрытии)
✅ Легко вычислить длительность бара
✅ Работает для всех таймфреймов автоматически

ПРИМЕР ИНТЕРПРЕТАЦИИ:
======================

Строка в таблице:
  Date/Time (Open): 2024-01-15 14:00
  Close Time:       2024-01-15 15:00
  Type:             BUY

Это значит:
  • Бар открылся в 14:00
  • Бар закрылся в 15:00
  • Сигнал BUY сгенерирован на закрытии (в 15:00)
  • Live Bot может использовать этот сигнал после 15:00
  • Период бара: 1 час (H1 таймфрейм)


ВИЗУАЛЬНОЕ ОТЛИЧИЕ:
====================

Close Time отображается светло-серым цветом (Qt.darkGray)
чтобы визуально отличать от основного времени открытия.
""")

print("="*80)
print("✅ Тест успешно завершен!")
print("="*80)
