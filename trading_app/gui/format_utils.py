"""
Shared constants for position size formats and crypto detection
"""

# Crypto symbol keywords for detection
CRYPTO_KEYWORDS = ['BTC', 'ETH', 'XRP', 'LTC', 'ADA', 'DOT', 'DOGE', 'SOL', 'AVAX', 'MATIC']

# Migration threshold: values above this are considered old format (basis points)
# Old format: 150 (basis points) → New format: 1.5 (percentage)
MIGRATION_THRESHOLD = 10


def is_crypto_symbol(symbol: str) -> bool:
    """
    Check if symbol is cryptocurrency (BTC, ETH, SOL, etc.)
    
    Args:
        symbol: Trading symbol (e.g., 'BTC/USDT', 'BTCUSD', 'XAUUSD')
        
    Returns:
        True if crypto, False if forex/commodities
    """
    if not symbol:
        return False
    symbol_upper = symbol.upper()
    return any(keyword in symbol_upper for keyword in CRYPTO_KEYWORDS)
