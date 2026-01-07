"""
Анализ: что можно добавить из Patterns Only в SHORT Optimized

Сравнение двух стратегий:
1. Patterns Only: 78.1% WR, +60.71% PnL (чистые паттерны)
2. SHORT Optimized: 77.3% WR, +325.70% PnL (SMC + асимметричные параметры)

ВОПРОС: Что из Patterns Only можно добавить в SHORT Optimized?
"""

import pandas as pd
import numpy as np


def main():
    print("\n" + "="*80)
    print("🔍 АНАЛИЗ: Patterns Only vs SHORT Optimized")
    print("="*80)

    # Load results
    patterns_df = pd.read_csv('smc_trading_strategy/backtest_patterns_only_results.csv')
    short_opt_df = pd.read_csv('smc_trading_strategy/backtest_v3_short_optimized_results.csv')

    print(f"\n📊 ОСНОВНАЯ СТАТИСТИКА:")
    print(f"\n   Patterns Only:")
    print(f"   - Сделок: {len(patterns_df)}")
    print(f"   - Win Rate: {len(patterns_df[patterns_df['pnl_pct'] > 0]) / len(patterns_df) * 100:.1f}%")
    print(f"   - Total PnL: {patterns_df['pnl_pct'].sum():+.2f}%")
    print(f"   - Avg Win: {patterns_df[patterns_df['pnl_pct'] > 0]['pnl_pct'].mean():+.2f}%")
    print(f"   - Avg Loss: {patterns_df[patterns_df['pnl_pct'] <= 0]['pnl_pct'].mean():.2f}%")

    print(f"\n   SHORT Optimized:")
    print(f"   - Сделок: {len(short_opt_df)}")
    print(f"   - Win Rate: {len(short_opt_df[short_opt_df['pnl_pct'] > 0]) / len(short_opt_df) * 100:.1f}%")
    print(f"   - Total PnL: {short_opt_df['pnl_pct'].sum():+.2f}%")
    print(f"   - Avg Win: {short_opt_df[short_opt_df['pnl_pct'] > 0]['pnl_pct'].mean():+.2f}%")
    print(f"   - Avg Loss: {short_opt_df[short_opt_df['pnl_pct'] <= 0]['pnl_pct'].mean():.2f}%")

    print(f"\n{'='*80}")
    print(f"1️⃣  ЧТО PATTERNS ONLY ДЕЛАЕТ ЛУЧШЕ?")
    print(f"{'='*80}")

    patterns_wr = len(patterns_df[patterns_df['pnl_pct'] > 0]) / len(patterns_df) * 100
    short_opt_wr = len(short_opt_df[short_opt_df['pnl_pct'] > 0]) / len(short_opt_df) * 100

    print(f"\n✅ Win Rate: {patterns_wr:.1f}% vs {short_opt_wr:.1f}%")
    print(f"   Patterns Only имеет на {patterns_wr - short_opt_wr:+.1f}% ВЫШЕ винрейт!")
    print(f"   → Это значит что паттерны ОТФИЛЬТРОВЫВАЮТ плохие сделки")

    # Check trade selectivity
    print(f"\n📊 Селективность:")
    print(f"   Patterns Only: {len(patterns_df)} сделок")
    print(f"   SHORT Optimized: {len(short_opt_df)} сделок")
    print(f"   Разница: {len(short_opt_df) - len(patterns_df)} сделок ({(len(short_opt_df) - len(patterns_df)) / len(patterns_df) * 100:+.1f}%)")
    print(f"\n   → Patterns Only более селективная (меньше сделок, выше винрейт)")
    print(f"   → SHORT Optimized берет больше сделок, но с ниже винрейтом")

    # Best patterns from Patterns Only
    print(f"\n{'='*80}")
    print(f"2️⃣  ЛУЧШИЕ ПАТТЕРНЫ ИЗ PATTERNS ONLY")
    print(f"{'='*80}")

    # From compare_strategies.md:
    best_patterns = [
        {'name': 'Ascending Triangle', 'trades': 160, 'wr': 81.2, 'pnl': 44.70},
        {'name': 'Falling Wedge', 'trades': 20, 'wr': 100.0, 'pnl': 8.14},
        {'name': 'Symmetrical Triangle', 'trades': 25, 'wr': 76.0, 'pnl': 7.91},
    ]

    worst_patterns = [
        {'name': 'Descending Triangle', 'trades': 27, 'wr': 70.4, 'pnl': -0.95},
        {'name': 'Rising Wedge', 'trades': 13, 'wr': 61.5, 'pnl': -0.02},
    ]

    print(f"\n✅ ОТЛИЧНЫЕ паттерны (стоит добавить как BOOST):")
    for p in best_patterns:
        print(f"   - {p['name']}: {p['trades']} сделок, {p['wr']}% WR, {p['pnl']:+.2f}% PnL")

    print(f"\n❌ ПЛОХИЕ паттерны (стоит ФИЛЬТРОВАТЬ):")
    for p in worst_patterns:
        print(f"   - {p['name']}: {p['trades']} сделок, {p['wr']}% WR, {p['pnl']:+.2f}% PnL")

    print(f"\n{'='*80}")
    print(f"3️⃣  ЧТО МОЖНО ДОБАВИТЬ В SHORT OPTIMIZED?")
    print(f"{'='*80}")

    recommendations = []

    # Recommendation 1: Pattern filtering
    recommendations.append({
        'title': 'PATTERN FILTERING (Фильтрация плохих паттернов)',
        'description': 'Перед открытием сделки проверять наличие плохих паттернов',
        'implementation': [
            '1. Добавить функцию detect_pattern() в ShortOptimizedBacktestV3',
            '2. Перед открытием позиции проверять паттерн',
            '3. Если паттерн = Descending Triangle или Rising Wedge → SKIP',
            '4. Ожидаемый эффект: меньше убыточных сделок, выше винрейт'
        ],
        'expected': 'Win Rate может вырасти с 77.3% до 78-79%',
        'risk': 'Может уменьшить количество сделок на 5-10%'
    })

    # Recommendation 2: Pattern boost
    recommendations.append({
        'title': 'PATTERN BOOST (Усиление отличных паттернов)',
        'description': 'Увеличивать TP для сигналов с отличными паттернами',
        'implementation': [
            '1. Если паттерн = Ascending Triangle → TP увеличить на 20%',
            '2. Если паттерн = Falling Wedge → TP увеличить на 20%',
            '3. Пример: LONG TREND TP 30/55/90п → 36/66/108п',
            '4. Ожидаемый эффект: больше прибыли с лучших сетапов'
        ],
        'expected': 'Avg Win может вырасти на 10-15%',
        'risk': 'TP3 может стать слишком далеким (достижение < 20%)'
    })

    # Recommendation 3: Hybrid signal confirmation
    recommendations.append({
        'title': 'SIGNAL CONFIRMATION (Подтверждение сигналов)',
        'description': 'Требовать совпадения SMC + Pattern для входа',
        'implementation': [
            '1. SMC дает сигнал LONG',
            '2. Проверяем наличие бычьего паттерна (Ascending Triangle, Falling Wedge, Symmetrical)',
            '3. Если паттерн есть → сигнал УСИЛЕННЫЙ (можно увеличить size или TP)',
            '4. Если паттерна нет → обычная сделка',
            '5. Ожидаемый эффект: более качественные сигналы'
        ],
        'expected': 'Win Rate может вырасти до 80%+',
        'risk': 'Количество сделок может упасть на 30-40%'
    })

    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['title']}")
        print(f"   {rec['description']}\n")
        print(f"   Реализация:")
        for step in rec['implementation']:
            print(f"      {step}")
        print(f"\n   ✅ Ожидаемый эффект: {rec['expected']}")
        print(f"   ⚠️  Риск: {rec['risk']}")

    print(f"\n{'='*80}")
    print(f"4️⃣  РЕКОМЕНДАЦИЯ")
    print(f"{'='*80}")

    print(f"\n🎯 ОПТИМАЛЬНЫЙ ПОДХОД: Pattern Filtering (вариант 1)")
    print(f"\n   Почему:")
    print(f"   1. SHORT Optimized уже показывает ОТЛИЧНЫЕ результаты (+325.70%)")
    print(f"   2. Patterns Only подтверждает, что некоторые паттерны дают убытки")
    print(f"   3. Добавление фильтрации плохих паттернов:")
    print(f"      - Минимальные изменения в код")
    print(f"      - Не уменьшает количество сделок значительно")
    print(f"      - Может повысить винрейт с 77.3% до 78-79%")
    print(f"      - Ожидаемый PnL: +330-340% (вместо +325.70%)")

    print(f"\n   📝 Реализация:")
    print(f"   1. Создать backtest_v3_pattern_filtered.py")
    print(f"   2. Скопировать логику из SHORT Optimized")
    print(f"   3. Добавить detect_pattern() для каждого сигнала")
    print(f"   4. SKIP сигналы с Descending Triangle / Rising Wedge")
    print(f"   5. Запустить backtest и сравнить результаты")

    print(f"\n   💡 Pattern Boost (вариант 2) - можно попробовать ПОСЛЕ")
    print(f"      Если фильтрация сработает хорошо, добавить бусты для лучших паттернов")

    print(f"\n{'='*80}")
    print(f"5️⃣  КЛЮЧЕВОЙ ИНСАЙТ")
    print(f"{'='*80}")

    print(f"\n   🔑 Patterns Only НЕ ЛУЧШЕ SHORT Optimized!")
    print(f"   ✅ SHORT Optimized дает в 5 раз больше прибыли (+325.70% vs +60.71%)")
    print(f"   ✅ SMC сигналы + адаптивность + асимметричные параметры = МОЩНАЯ комбинация")
    print(f"\n   НО:")
    print(f"   📊 Patterns Only показывает КАКИЕ паттерны работают/не работают")
    print(f"   💡 Эту информацию можно использовать как ФИЛЬТР для SHORT Optimized")
    print(f"\n   ВЫВОД:")
    print(f"   Не заменять SHORT Optimized на Patterns,")
    print(f"   а УЛУЧШИТЬ SHORT Optimized, добавив фильтрацию паттернов!")

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    main()
