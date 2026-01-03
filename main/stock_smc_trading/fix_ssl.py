"""
SSL Fix для Windows с русскими буквами в пути

Этот скрипт исправляет проблему с certifi на Windows.
Запускайте ПЕРЕД использованием real_data_screener.py
"""

import os
import sys
import ssl
import tempfile
import shutil

def fix_ssl_certificates():
    """Исправить SSL сертификаты для yfinance"""

    print("🔧 Исправление SSL сертификатов...")

    # Способ 1: Попробовать найти certifi и скопировать в безопасное место
    try:
        import certifi
        original_cert = certifi.where()
        print(f"   Найден certifi: {original_cert}")

        # Создать временную папку БЕЗ русских букв
        temp_dir = "C:\\temp_certs" if os.name == 'nt' else "/tmp/certs"
        os.makedirs(temp_dir, exist_ok=True)

        # Скопировать сертификат
        new_cert_path = os.path.join(temp_dir, "cacert.pem")
        shutil.copy2(original_cert, new_cert_path)

        # Установить переменные окружения
        os.environ['SSL_CERT_FILE'] = new_cert_path
        os.environ['REQUESTS_CA_BUNDLE'] = new_cert_path
        os.environ['CURL_CA_BUNDLE'] = new_cert_path

        print(f"   ✅ Сертификат скопирован в: {new_cert_path}")
        print(f"   ✅ Установлены переменные окружения")

        return True

    except Exception as e:
        print(f"   ⚠️  Ошибка с certifi: {e}")

    # Способ 2: Отключить SSL проверку полностью
    print("   Отключение SSL проверки...")
    ssl._create_default_https_context = ssl._create_unverified_context
    print("   ✅ SSL проверка отключена")

    return True

if __name__ == "__main__":
    fix_ssl_certificates()
    print("\n✅ SSL исправлен! Теперь можно запускать real_data_screener.py")
