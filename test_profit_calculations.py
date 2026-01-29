#!/usr/bin/env python3
"""
Test: Verify profit and profit_percent calculations are correct and consistent
"""

def test_profit_calculations():
    """Test all profit calculation scenarios"""
    
    print("=" * 80)
    print("ТЕСТ: Проверка расчета Profit $ и Profit %")
    print("=" * 80)
    print()
    
    # Test helper functions
    def calc_profit_pct(entry, close, trade_type):
        """Calculate profit percentage (price change percentage)"""
        if trade_type == 'BUY':
            return ((close - entry) / entry) * 100
        else:  # SELL
            return ((entry - close) / entry) * 100
    
    def calc_profit_dollars(entry, close, trade_type, volume=0.01):
        """Calculate profit in dollars for XAUUSD"""
        point_value = 100.0  # For XAUUSD, 1 lot = $100 per point
        if trade_type == 'BUY':
            pips = (close - entry) * 10
        else:
            pips = (entry - close) * 10
        return pips / 10 * volume * point_value
    
    # Comprehensive test cases
    test_cases = [
        # (name, entry, close, trade_type, volume)
        ("BUY прибыльная сделка", 2000.0, 2010.0, 'BUY', 0.01),
        ("BUY убыточная сделка", 2000.0, 1990.0, 'BUY', 0.01),
        ("BUY без изменения", 2000.0, 2000.0, 'BUY', 0.01),
        ("SELL прибыльная сделка", 2000.0, 1990.0, 'SELL', 0.01),
        ("SELL убыточная сделка", 2000.0, 2010.0, 'SELL', 0.01),
        ("SELL без изменения", 2000.0, 2000.0, 'SELL', 0.01),
        ("BUY большая прибыль", 2000.0, 2050.0, 'BUY', 0.01),
        ("BUY большой убыток", 2000.0, 1950.0, 'BUY', 0.01),
        ("SELL большая прибыль", 2000.0, 1950.0, 'SELL', 0.01),
        ("SELL большой убыток", 2000.0, 2050.0, 'SELL', 0.01),
    ]
    
    all_passed = True
    
    for name, entry, close, trade_type, volume in test_cases:
        profit_pct = calc_profit_pct(entry, close, trade_type)
        profit_dollars = calc_profit_dollars(entry, close, trade_type, volume)
        
        # Determine expected result
        if trade_type == 'BUY':
            expected_profit = close > entry
            expected_loss = close < entry
        else:  # SELL
            expected_profit = close < entry
            expected_loss = close > entry
        
        # Check if signs match
        signs_match = (profit_pct > 0) == (profit_dollars > 0) and (profit_pct < 0) == (profit_dollars < 0)
        
        # Check if results match expectations
        results_correct = True
        if expected_profit:
            results_correct = profit_dollars > 0 and profit_pct > 0
        elif expected_loss:
            results_correct = profit_dollars < 0 and profit_pct < 0
        else:  # no change
            results_correct = profit_dollars == 0 and profit_pct == 0
        
        status = "✅ PASS" if (signs_match and results_correct) else "❌ FAIL"
        
        if not (signs_match and results_correct):
            all_passed = False
        
        print(f"{status} {name}:")
        print(f"    Вход: ${entry:.2f}, Выход: ${close:.2f}, Тип: {trade_type}, Объем: {volume}")
        print(f"    Profit $: ${profit_dollars:+.2f}")
        print(f"    Profit %: {profit_pct:+.4f}%")
        if not signs_match:
            print(f"    ⚠️  ОШИБКА: Знаки не совпадают!")
        if not results_correct:
            print(f"    ⚠️  ОШИБКА: Результат не соответствует ожиданиям!")
        print()
    
    print("=" * 80)
    if all_passed:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print()
        print("Выводы:")
        print("  ✅ Формулы расчета Profit $ корректны")
        print("  ✅ Формулы расчета Profit % корректны")
        print("  ✅ Знаки всегда совпадают между Profit $ и Profit %")
        print("  ✅ Результаты соответствуют ожиданиям для BUY и SELL сделок")
        return 0
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ!")
        print("Требуется исправление формул расчета.")
        return 1

if __name__ == '__main__':
    import sys
    exit_code = test_profit_calculations()
    sys.exit(exit_code)
