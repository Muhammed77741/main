# Откуда берутся данные?

## 📊 Три версии screener'а

### 1. **demo_screener.py** - Симулированные данные
```python
# Генерирует случайные цены
loader = StockDataLoader(
    ticker='AAPL',
    initial_price=180,
    volatility=0.015,
    trend_strength=0.0005
)
```
**Источник:** Генератор случайных данных (алгоритм)
**Плюсы:** Работает без интернета, быстро
**Минусы:** Не реальные данные
**Использование:** Тестирование, обучение

---

### 2. **comprehensive_screener.py** - Hardcoded данные
```python
profiles = {
    'AAPL': {
        'revenue_growth': 8.5,
        'earnings_growth': 12.3,
        'profit_margin': 25.3,
        'roe': 147.0,
        # ...
    }
}
```
**Источник:** Жестко закодированы в коде (взяты из реальных отчетов Q4 2024)
**Плюсы:** Работает без интернета, реалистичные цифры
**Минусы:** Статичные, не обновляются
**Использование:** Демонстрация, когда нет доступа к API

---

### 3. **real_data_screener.py** - Реальные данные из yfinance ✅
```python
import yfinance as yf

stock = yf.Ticker('AAPL')
info = stock.info

fundamentals = {
    'revenue_growth': info['revenueGrowth'] * 100,
    'earnings_growth': info['earningsGrowth'] * 100,
    'profit_margin': info['profitMargins'] * 100,
    'roe': info['returnOnEquity'] * 100,
    # ...
}
```
**Источник:** Yahoo Finance API (через библиотеку yfinance)
**Плюсы:** Реальные актуальные данные
**Минусы:** Требует интернет, может быть медленным
**Использование:** Реальная торговля

---

## 🔌 Источники данных для реального использования

### 1. **Yahoo Finance (yfinance)** - БЕСПЛАТНО ✅
```bash
pip install yfinance
```

**Что предоставляет:**
- Цены акций (исторические и текущие)
- Фундаментальные данные (P/E, ROE, margins, etc.)
- Финансовые отчеты (income statement, balance sheet)
- Дивиденды, сплиты
- Новости

**Пример использования:**
```python
import yfinance as yf

# Получить данные
stock = yf.Ticker('AAPL')

# Цены
prices = stock.history(period='1y')

# Фундаментальные данные
info = stock.info
print(f"P/E: {info['trailingPE']}")
print(f"Revenue Growth: {info['revenueGrowth']}")
print(f"Profit Margin: {info['profitMargins']}")
print(f"ROE: {info['returnOnEquity']}")
print(f"Debt/Equity: {info['debtToEquity']}")

# Финансовые отчеты
income_stmt = stock.financials  # Income statement
balance = stock.balance_sheet    # Balance sheet
cashflow = stock.cashflow        # Cash flow
```

**Доступные метрики из `stock.info`:**
```python
{
    # Valuation
    'trailingPE': 29.5,           # P/E ratio
    'forwardPE': 27.3,            # Forward P/E
    'priceToBook': 45.2,          # P/B ratio
    'marketCap': 2800000000000,   # Market cap

    # Profitability
    'profitMargins': 0.253,       # Profit margin (25.3%)
    'operatingMargins': 0.297,    # Operating margin
    'returnOnEquity': 1.47,       # ROE (147%)
    'returnOnAssets': 0.285,      # ROA (28.5%)

    # Growth
    'revenueGrowth': 0.085,       # Revenue growth (8.5%)
    'earningsGrowth': 0.123,      # Earnings growth (12.3%)

    # Financial Health
    'debtToEquity': 173.0,        # Debt/Equity
    'currentRatio': 0.98,         # Current ratio
    'quickRatio': 0.88,           # Quick ratio

    # Cash Flow
    'freeCashflow': 99500000000,  # Free cash flow
    'operatingCashflow': 110500000000,

    # Revenue & Earnings
    'totalRevenue': 383300000000,
    'grossProfits': 170800000000,
    'trailingEps': 6.13,          # Earnings per share

    # Dividends
    'dividendRate': 0.96,
    'dividendYield': 0.0053,
}
```

**Плюсы:**
- ✅ Бесплатно
- ✅ Много данных
- ✅ Простой API
- ✅ Активное сообщество

**Минусы:**
- ⚠️ Иногда нестабильно (Yahoo может менять API)
- ⚠️ Лимиты на количество запросов
- ⚠️ Некоторые данные могут отсутствовать

---

### 2. **Alpha Vantage** - БЕСПЛАТНО (с ограничениями)
```bash
pip install alpha_vantage
```

**API Key:** Нужна бесплатная регистрация на https://www.alphavantage.co/

**Пример:**
```python
from alpha_vantage.fundamentaldata import FundamentalData

fd = FundamentalData(key='YOUR_API_KEY')
data, meta = fd.get_company_overview('AAPL')

print(data['PERatio'])
print(data['ProfitMargin'])
print(data['ReturnOnEquityTTM'])
```

**Лимиты (бесплатный план):**
- 25 API запросов в день
- 5 запросов в минуту

**Плюсы:**
- ✅ Официальный API
- ✅ Стабильный
- ✅ Много метрик

**Минусы:**
- ❌ Жесткие лимиты на бесплатном плане
- ❌ Платный план $49/месяц

---

### 3. **Financial Modeling Prep** - БЕСПЛАТНО (250 запросов/день)
```bash
pip install financialmodelingprep
```

**API Key:** https://financialmodelingprep.com/developer/docs/

**Пример:**
```python
import requests

API_KEY = 'your_api_key'
ticker = 'AAPL'

# Получить финансовые метрики
url = f'https://financialmodelingprep.com/api/v3/key-metrics/{ticker}?apikey={API_KEY}'
response = requests.get(url)
data = response.json()

print(data[0]['peRatio'])
print(data[0]['priceToBookRatio'])
print(data[0]['roeTTM'])
```

**Плюсы:**
- ✅ 250 запросов/день (достаточно для большинства)
- ✅ Много данных
- ✅ API качественный

**Минусы:**
- ⚠️ Требует регистрацию

---

### 4. **IEX Cloud** - ПЛАТНО
https://iexcloud.io/

**Цена:** От $9/месяц

**Плюсы:**
- ✅ Очень надежный
- ✅ Реал-тайм данные
- ✅ Отличная документация

**Минусы:**
- ❌ Платный

---

### 5. **Polygon.io** - ПЛАТНО
https://polygon.io/

**Цена:** От $29/месяц (бесплатный план - 5 запросов/минуту)

**Плюсы:**
- ✅ Профессиональный API
- ✅ Много данных
- ✅ WebSocket поддержка

---

## 📝 Рекомендация

### Для начала: **yfinance** ✅
```bash
pip install yfinance
```

**Почему:**
1. Бесплатно
2. Не требует регистрацию
3. Достаточно данных для большинства задач
4. Простой в использовании

**Используйте:** `real_data_screener.py`

---

## 🔄 Сравнение версий screener'а

| Версия | Данные | Интернет | Скорость | Точность | Использование |
|--------|--------|----------|----------|----------|---------------|
| `demo_screener.py` | Симуляция | ❌ Нет | 🚀 Быстро | ⚠️ Низкая | Тестирование |
| `comprehensive_screener.py` | Hardcoded | ❌ Нет | 🚀 Быстро | ⚠️ Средняя | Демо |
| `real_data_screener.py` | Yahoo Finance | ✅ Да | 🐌 Медленно | ✅ Высокая | Реальная торговля |

---

## 💡 Как перейти на реальные данные

### Шаг 1: Установить yfinance
```bash
pip install yfinance
```

### Шаг 2: Использовать real_data_screener.py
```bash
python3 real_data_screener.py
```

### Шаг 3: Проверить результаты
```python
# Результаты сохраняются в CSV
real_data_screener_results.csv
```

---

## 🛠️ Кастомизация источника данных

Если хотите использовать другой API (Alpha Vantage, FMP, etc.), просто измените класс `RealFundamentalData`:

```python
class RealFundamentalData:
    @staticmethod
    def get_fundamentals(ticker: str) -> Optional[Dict]:
        # Замените на ваш API
        # Пример с Alpha Vantage:
        from alpha_vantage.fundamentaldata import FundamentalData
        fd = FundamentalData(key='YOUR_KEY')
        data, _ = fd.get_company_overview(ticker)

        return {
            'revenue_growth': float(data.get('QuarterlyRevenueGrowthYOY', 0)) * 100,
            'profit_margin': float(data.get('ProfitMargin', 0)) * 100,
            'roe': float(data.get('ReturnOnEquityTTM', 0)) * 100,
            # ... и т.д.
        }
```

---

## ⚠️ Важные замечания

1. **Лимиты API**: Не делайте слишком много запросов
   ```python
   import time
   for ticker in tickers:
       screen_stock(ticker)
       time.sleep(0.5)  # Пауза между запросами
   ```

2. **Обработка ошибок**: API могут возвращать None
   ```python
   fundamentals = get_fundamentals(ticker)
   if fundamentals is None:
       continue  # Пропустить акцию
   ```

3. **Кэширование**: Сохраняйте данные локально
   ```python
   # Сохранить результаты
   results.to_csv('cached_data.csv')

   # Использовать кэш
   if os.path.exists('cached_data.csv'):
       results = pd.read_csv('cached_data.csv')
   ```

4. **Актуальность**: Финансовые данные обновляются раз в квартал
   - Не нужно скачивать каждый день
   - Обновляйте раз в неделю/месяц

---

## 📚 Дополнительные ресурсы

- **yfinance docs**: https://github.com/ranaroussi/yfinance
- **Alpha Vantage**: https://www.alphavantage.co/documentation/
- **FMP**: https://financialmodelingprep.com/developer/docs/
- **Pandas datareader**: https://pandas-datareader.readthedocs.io/
