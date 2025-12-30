"""
Применение MEAN REVERSION SHORT фильтра
К стратегии и боту
"""

# ВАРИАНТ 1: Mean Reversion (строгий) - WR 100%, 2 сделки
MEAN_REVERSION_FILTER_CODE = """
def should_take_short_mean_reversion(self, df, idx):
    '''
    Mean Reversion SHORT filter (строгий)
    SHORT только когда цена ВЫШЕ EMA20 и близко к ней
    
    Результаты: WR 100%, 2 сделки/год, +38.28%
    '''
    
    # Проверяем наличие EMA20
    if 'ema_20' not in df.columns:
        df['ema_20'] = df['close'].ewm(span=20).mean()
    
    close = df['close'].iloc[idx]
    ema_20 = df['ema_20'].iloc[idx]
    
    # 1. Цена должна быть ВЫШЕ EMA20
    if close <= ema_20:
        return False, "Price below EMA20"
    
    # 2. Дистанция от EMA20: 0% до +1% (близко к EMA сверху)
    dist_from_ema = (close - ema_20) / ema_20 * 100
    
    if dist_from_ema > 1.0:
        return False, f"Too far above EMA20 ({dist_from_ema:.2f}%)"
    
    return True, "Mean reversion conditions met"
"""

# ВАРИАНТ 2: Выше EMA50 (либеральный) - WR 50%, 10 сделок
ABOVE_EMA50_FILTER_CODE = """
def should_take_short_above_ema50(self, df, idx):
    '''
    SHORT выше EMA50 (либеральный фильтр)
    
    Результаты: WR 50%, 10 сделок/год, +38.31%
    '''
    
    # Проверяем наличие EMA50
    if 'ema_50' not in df.columns:
        df['ema_50'] = df['close'].ewm(span=50).mean()
    
    close = df['close'].iloc[idx]
    ema_50 = df['ema_50'].iloc[idx]
    
    # Цена должна быть ВЫШЕ EMA50
    if close <= ema_50:
        return False, "Price below EMA50"
    
    return True, "Above EMA50"
"""

# ПРИМЕНЕНИЕ К GOLD_OPTIMIZED_SMC_STRATEGY.PY
INTEGRATION_CODE_STRATEGY = """
# В файле gold_optimized_smc_strategy.py

class GoldOptimizedSMCStrategy(SimplifiedSMCStrategy):
    
    def __init__(self, ...):
        super().__init__(...)
        
        # Добавить опцию
        self.use_mean_reversion_short = True  # ВКЛЮЧИТЬ ФИЛЬТР
    
    
    def should_take_short_mean_reversion(self, df, idx):
        '''Mean Reversion SHORT filter'''
        
        if 'ema_20' not in df.columns:
            df['ema_20'] = df['close'].ewm(span=20).mean()
        
        close = df['close'].iloc[idx]
        ema_20 = df['ema_20'].iloc[idx]
        
        # Цена ВЫШЕ EMA20
        if close <= ema_20:
            return False
        
        # Дистанция 0-1%
        dist = (close - ema_20) / ema_20 * 100
        if dist > 1.0:
            return False
        
        return True
    
    
    def _check_short_setup(self, df, idx):
        '''
        Модифицировать метод для проверки SHORT
        '''
        
        # Оригинальная логика
        is_valid, details = super()._check_short_setup(df, idx)
        
        if not is_valid:
            return False, details
        
        # ДОБАВИТЬ MEAN REVERSION ФИЛЬТР
        if self.use_mean_reversion_short:
            if not self.should_take_short_mean_reversion(df, idx):
                return False, {'reason': 'Mean reversion filter: price not above EMA20'}
        
        return True, details
"""

# ПРИМЕНЕНИЕ К PAPER_TRADING_IMPROVED.PY
INTEGRATION_CODE_BOT = """
# В файле paper_trading_improved.py

class PaperTradingBot:
    
    def __init__(self, ...):
        ...
        # Добавить опцию
        self.use_mean_reversion_short = True
    
    
    def check_and_open_position(self):
        '''Check for signals and open positions'''
        
        # ... existing code до открытия позиции ...
        
        # ДОБАВИТЬ ПРОВЕРКУ ДЛЯ SHORT
        if signal_data['direction'] == 'SHORT':
            
            # Mean Reversion фильтр
            if self.use_mean_reversion_short:
                
                # Получить текущую цену и EMA20
                current_price = self.get_current_price(self.symbol)
                
                if current_price is None:
                    return
                
                # Получить EMA20 (можно из стратегии или рассчитать)
                # Вариант 1: Запросить историю и рассчитать
                bars = mt5.copy_rates_from_pos(self.symbol, mt5.TIMEFRAME_H1, 0, 21)
                
                if bars is not None and len(bars) >= 20:
                    df_bars = pd.DataFrame(bars)
                    df_bars['ema_20'] = df_bars['close'].ewm(span=20).mean()
                    
                    current_close = current_price['bid']  # Для SHORT используем bid
                    ema_20 = df_bars['ema_20'].iloc[-1]
                    
                    # Проверка фильтра
                    if current_close <= ema_20:
                        print(f"⚠️  SHORT пропущен: цена {current_close:.2f} <= EMA20 {ema_20:.2f}")
                        return
                    
                    dist = (current_close - ema_20) / ema_20 * 100
                    
                    if dist > 1.0:
                        print(f"⚠️  SHORT пропущен: слишком далеко от EMA20 ({dist:.2f}%)")
                        return
                    
                    print(f"✅ SHORT прошел Mean Reversion фильтр (dist: {dist:.2f}%)")
        
        # ... продолжить с открытием позиции ...
"""

def main():
    print("\n" + "="*100)
    print("📋 ИНСТРУКЦИЯ: ПРИМЕНЕНИЕ MEAN REVERSION SHORT ФИЛЬТРА")
    print("="*100)
    
    print("\n🎯 ЦЕЛЬ:")
    print("   Применить фильтр чтобы SHORT работал с WR 100% вместо 31%")
    
    print("\n📊 РЕЗУЛЬТАТЫ ФИЛЬТРА:")
    print("   - SHORT сделок: 100 → 2")
    print("   - Win Rate: 31% → 100%")
    print("   - Total PnL: +349% → +387.30%")
    print("   - Улучшение: +38.28%")
    
    print("\n" + "="*100)
    print("ШАГ 1: ВЫБРАТЬ ВАРИАНТ ФИЛЬТРА")
    print("="*100)
    
    print("\n✅ ВАРИАНТ 1: MEAN REVERSION (рекомендуется)")
    print("   Правило: SHORT когда цена выше EMA20, дистанция 0-1%")
    print("   Результат: 2 сделки, WR 100%, +38.28%")
    print("\n   Код:")
    print(MEAN_REVERSION_FILTER_CODE)
    
    print("\n⚠️  ВАРИАНТ 2: ВЫШЕ EMA50")
    print("   Правило: SHORT когда цена выше EMA50")
    print("   Результат: 10 сделок, WR 50%, +38.31%")
    print("\n   Код:")
    print(ABOVE_EMA50_FILTER_CODE)
    
    print("\n" + "="*100)
    print("ШАГ 2: ПРИМЕНИТЬ К СТРАТЕГИИ")
    print("="*100)
    
    print("\nФайл: gold_optimized_smc_strategy.py")
    print(INTEGRATION_CODE_STRATEGY)
    
    print("\n" + "="*100)
    print("ШАГ 3: ПРИМЕНИТЬ К БОТУ")
    print("="*100)
    
    print("\nФайл: paper_trading_improved.py")
    print(INTEGRATION_CODE_BOT)
    
    print("\n" + "="*100)
    print("ШАГ 4: ПРОТЕСТИРОВАТЬ")
    print("="*100)
    
    print("\n1. Запустить backtest:")
    print("   cd smc_trading_strategy")
    print("   python3 test_mean_reversion_short.py")
    
    print("\n2. Проверить результаты:")
    print("   - SHORT сделок: ~2-10")
    print("   - SHORT WR: 50-100%")
    print("   - Total PnL: ~+387%")
    
    print("\n3. Если OK, запустить бота:")
    print("   python3 paper_trading_improved.py")
    
    print("\n" + "="*100)
    print("✅ ГОТОВО!")
    print("="*100)
    
    print("\n💡 РЕКОМЕНДАЦИЯ:")
    print("   Использовать ВАРИАНТ 1 (Mean Reversion)")
    print("   Лучшее соотношение качества и результата")


if __name__ == "__main__":
    main()
