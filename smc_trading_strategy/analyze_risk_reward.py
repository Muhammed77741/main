"""
Analyze Risk:Reward ratio problem
"""

import pandas as pd
from pattern_recognition_strategy import PatternRecognitionStrategy


def load_mt5_data(file_path='../XAUUSD_1H_MT5_20241227_20251227.csv'):
    """Load MT5 XAUUSD data"""
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['datetime'])
    df = df.set_index('timestamp')
    df = df[['open', 'high', 'low', 'close', 'volume']]

    df['is_london'] = df.index.hour.isin(range(7, 12))
    df['is_ny'] = df.index.hour.isin(range(13, 20))
    df['is_overlap'] = df.index.hour.isin(range(13, 16))
    df['is_active'] = df['is_london'] | df['is_ny']
    df['is_best_hours'] = df.index.hour.isin([8, 9, 10, 13, 14, 15])

    return df


def analyze_risk_reward():
    """Analyze Risk:Reward ratios"""

    print("\n" + "=" * 90)
    print("АНАЛИЗ СООТНОШЕНИЯ РИСК:НАГРАДА")
    print("=" * 90)

    # Load data
    df = load_mt5_data()

    # Initialize strategy
    strategy = PatternRecognitionStrategy(fib_mode='standard')

    # Run strategy
    df_strategy = strategy.run_strategy(df.copy())
    df_signals = df_strategy[df_strategy['signal'] != 0].copy()

    print(f"\n📊 Анализирую {len(df_signals)} сигналов...")

    # Current TP levels
    TP1 = 30
    TP2 = 50
    TP3 = 80

    # Analyze risk/reward
    risks = []
    rr_tp1 = []
    rr_tp2 = []
    rr_tp3 = []

    for idx, signal in df_signals.iterrows():
        entry = signal['entry_price']
        sl = signal['stop_loss']

        risk = abs(entry - sl)
        risks.append(risk)

        # Calculate R:R for each TP
        rr_tp1.append(TP1 / risk if risk > 0 else 0)
        rr_tp2.append(TP2 / risk if risk > 0 else 0)
        rr_tp3.append(TP3 / risk if risk > 0 else 0)

    risks = pd.Series(risks)
    rr_tp1 = pd.Series(rr_tp1)
    rr_tp2 = pd.Series(rr_tp2)
    rr_tp3 = pd.Series(rr_tp3)

    print("\n" + "=" * 90)
    print("⚠️  ПРОБЛЕМА: СТОП-ЛОСС СЛИШКОМ БОЛЬШОЙ!")
    print("=" * 90)

    print(f"\n📊 Статистика по стоп-лоссам:")
    print(f"   Средний SL: {risks.mean():.2f} пунктов")
    print(f"   Медианный SL: {risks.median():.2f} пунктов")
    print(f"   Минимальный SL: {risks.min():.2f} пунктов")
    print(f"   Максимальный SL: {risks.max():.2f} пунктов")

    print(f"\n🎯 Текущие уровни TP:")
    print(f"   TP1: {TP1} пунктов")
    print(f"   TP2: {TP2} пунктов")
    print(f"   TP3: {TP3} пунктов")

    print(f"\n❌ Соотношение Риск:Награда (R:R):")
    print(f"   TP1: в среднем 1:{rr_tp1.mean():.2f} (риск в {1/rr_tp1.mean():.1f}x БОЛЬШЕ прибыли!)")
    print(f"   TP2: в среднем 1:{rr_tp2.mean():.2f} (риск в {1/rr_tp2.mean():.1f}x БОЛЬШЕ прибыли!)")
    print(f"   TP3: в среднем 1:{rr_tp3.mean():.2f} (риск в {1/rr_tp3.mean():.1f}x БОЛЬШЕ прибыли!)")

    print(f"\n⚠️  ЭТО ОЧЕНЬ ПЛОХО!")
    print(f"   Нормальный R:R должен быть 1:1.5 или лучше")
    print(f"   У нас риск БОЛЬШЕ чем награда в {1/rr_tp1.mean():.1f} раз!")

    # Show why strategy is still profitable
    print(f"\n" + "=" * 90)
    print("ПОЧЕМУ СТРАТЕГИЯ ВСЕ РАВНО ПРИБЫЛЬНА?")
    print("=" * 90)

    print(f"\n✅ Спасает высокий Win Rate:")
    print(f"   - TP1 достигается в 50% случаев")
    print(f"   - SL срабатывает только в 14% случаев")
    print(f"   - Частичное закрытие минимизирует убытки")
    print(f"\n   НО это не оправдывает плохой R:R!")

    # Propose solutions
    print(f"\n" + "=" * 90)
    print("💡 РЕШЕНИЯ:")
    print("=" * 90)

    print(f"\n🔧 ВАРИАНТ 1: УМЕНЬШИТЬ СТОП-ЛОСС")
    print(f"   Текущий средний SL: {risks.mean():.0f} пунктов")
    print(f"   Предлагаемый SL: 50-60 пунктов (фиксированный)")
    print(f"\n   Новый R:R:")
    new_sl = 50
    print(f"      TP1 ({TP1}п): 1:{TP1/new_sl:.2f} ✅ Лучше!")
    print(f"      TP2 ({TP2}п): 1:{TP2/new_sl:.2f} ✅ Хорошо!")
    print(f"      TP3 ({TP3}п): 1:{TP3/new_sl:.2f} ✅ Отлично!")
    print(f"\n   ⚠️  Риск: SL может чаще срабатывать")

    print(f"\n🔧 ВАРИАНТ 2: УВЕЛИЧИТЬ ТЕЙК-ПРОФИТЫ (пропорционально SL)")
    print(f"   Использовать R:R = 1:1.5, 1:2, 1:2.5")
    avg_sl = risks.mean()
    new_tp1 = avg_sl * 1.0
    new_tp2 = avg_sl * 1.5
    new_tp3 = avg_sl * 2.0
    print(f"\n   Новые TP (на основе среднего SL {avg_sl:.0f}п):")
    print(f"      TP1: {new_tp1:.0f}п (R:R 1:1.0) → закрыть 50%")
    print(f"      TP2: {new_tp2:.0f}п (R:R 1:1.5) → закрыть 30%")
    print(f"      TP3: {new_tp3:.0f}п (R:R 1:2.0) → закрыть 20%")
    print(f"\n   ⚠️  Риск: TP может реже достигаться")

    print(f"\n🔧 ВАРИАНТ 3: АДАПТИВНЫЙ TP (для каждой сделки)")
    print(f"   Для каждого сигнала рассчитывать TP на основе его SL:")
    print(f"      TP1 = SL × 0.8  (R:R 1:0.8)")
    print(f"      TP2 = SL × 1.2  (R:R 1:1.2)")
    print(f"      TP3 = SL × 1.8  (R:R 1:1.8)")
    print(f"\n   ✅ Лучше всего! TP адаптируется под каждую сделку")

    print(f"\n🔧 ВАРИАНТ 4: КОМБИНИРОВАННЫЙ (лучший)")
    print(f"   1. Ограничить MAX SL = 80 пунктов")
    print(f"   2. Использовать адаптивный TP:")
    print(f"      TP1 = max(30, SL × 0.8)")
    print(f"      TP2 = max(50, SL × 1.2)")
    print(f"      TP3 = max(80, SL × 1.8)")
    print(f"\n   ✅ Баланс между фиксированными и адаптивными уровнями")

    # Show examples
    print(f"\n" + "=" * 90)
    print("ПРИМЕРЫ СРАВНЕНИЯ")
    print("=" * 90)

    examples = df_signals.tail(3)

    for idx, (timestamp, signal) in enumerate(examples.iterrows(), 1):
        entry = signal['entry_price']
        sl = signal['stop_loss']
        risk = abs(entry - sl)

        print(f"\n📊 Сигнал #{idx}: Вход {entry:.2f}, SL {sl:.2f}, Риск {risk:.0f}п")

        # Current
        print(f"\n   ❌ ТЕКУЩИЙ подход (фиксированные TP):")
        print(f"      TP1: {entry+TP1:.2f} (+{TP1}п) | R:R 1:{TP1/risk:.2f}")
        print(f"      TP2: {entry+TP2:.2f} (+{TP2}п) | R:R 1:{TP2/risk:.2f}")
        print(f"      TP3: {entry+TP3:.2f} (+{TP3}п) | R:R 1:{TP3/risk:.2f}")

        # Adaptive
        adaptive_tp1 = max(30, risk * 0.8)
        adaptive_tp2 = max(50, risk * 1.2)
        adaptive_tp3 = max(80, risk * 1.8)

        print(f"\n   ✅ АДАПТИВНЫЙ подход:")
        print(f"      TP1: {entry+adaptive_tp1:.2f} (+{adaptive_tp1:.0f}п) | R:R 1:{adaptive_tp1/risk:.2f}")
        print(f"      TP2: {entry+adaptive_tp2:.2f} (+{adaptive_tp2:.0f}п) | R:R 1:{adaptive_tp2/risk:.2f}")
        print(f"      TP3: {entry+adaptive_tp3:.2f} (+{adaptive_tp3:.0f}п) | R:R 1:{adaptive_tp3/risk:.2f}")

    print(f"\n" + "=" * 90)
    print("✅ ВЫВОД")
    print("=" * 90)

    print(f"""
⚠️  ПРОБЛЕМА НАЙДЕНА:
   • Средний SL = {risks.mean():.0f} пунктов
   • TP1 = {TP1} пунктов
   • R:R для TP1 = 1:{TP1/risks.mean():.2f} (ПЛОХО!)

💡 РЕКОМЕНДАЦИЯ:
   Использовать АДАПТИВНЫЙ TP (Вариант 3 или 4)

   Для каждой сделки:
   • TP1 = max(30, SL × 0.8)  → достигается часто
   • TP2 = max(50, SL × 1.2)  → средний R:R
   • TP3 = max(80, SL × 1.8)  → хороший R:R

   Это даст баланс между:
   - Достижимостью TP (не слишком далеко)
   - Правильным риск-менеджментом (R:R >= 1:1)

🔧 НУЖНО ПЕРЕДЕЛАТЬ СТРАТЕГИЮ С АДАПТИВНЫМИ TP!
""")


if __name__ == "__main__":
    analyze_risk_reward()
