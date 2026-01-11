"""
Helper module for Telegram bot imports with proper error handling.

This module provides a safe import mechanism for the python-telegram-bot library
and gives users clear instructions if they have the wrong package installed.
"""


def check_telegram_bot_import():
    """
    Check if python-telegram-bot is correctly installed.
    
    Returns:
        tuple: (success: bool, bot_class or None, error_message or None)
    """
    try:
        from telegram import Bot
        return True, Bot, None
    except ImportError as e:
        error_str = str(e)
        
        # Check if it's the wrong 'telegram' package
        if "cannot import name 'Bot'" in error_str or "'Bot'" in error_str:
            error_message = """
⚠️  TELEGRAM IMPORT ERROR ⚠️

The 'Bot' class cannot be imported from the 'telegram' package.
This usually means you have the wrong 'telegram' package installed.

SOLUTION:
1. Uninstall the wrong package:
   pip uninstall telegram
   
2. Uninstall any existing python-telegram-bot:
   pip uninstall python-telegram-bot
   
3. Install the correct package:
   pip install python-telegram-bot>=20.0
   
4. Verify installation:
   pip show python-telegram-bot
   
IMPORTANT: You need 'python-telegram-bot', NOT 'telegram' (0.0.1)

For more details, see: https://github.com/python-telegram-bot/python-telegram-bot
"""
            return False, None, error_message
        else:
            # Generic import error
            error_message = f"""
⚠️  TELEGRAM MODULE NOT FOUND ⚠️

The python-telegram-bot library is not installed.

SOLUTION:
Install the package:
   pip install python-telegram-bot>=20.0

Error details: {error_str}
"""
            return False, None, error_message
    except Exception as e:
        error_message = f"""
⚠️  UNEXPECTED TELEGRAM ERROR ⚠️

An unexpected error occurred while importing the Telegram bot library.

Error details: {e}

Please try:
1. pip uninstall telegram python-telegram-bot
2. pip install python-telegram-bot>=20.0
"""
        return False, None, error_message


def get_bot_instance(token):
    """
    Safely create a Bot instance with proper error handling.
    
    Args:
        token: Telegram bot token
        
    Returns:
        Bot instance or None if import fails
        
    Raises:
        ImportError with helpful message if package is not installed correctly
    """
    success, Bot, error_msg = check_telegram_bot_import()
    
    if not success:
        raise ImportError(error_msg)
    
    return Bot(token=token)
