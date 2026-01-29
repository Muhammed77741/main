"""
MT5 Connection Manager
Singleton pattern to ensure only one MT5 connection for all bots
"""
import MetaTrader5 as mt5
import threading
import time
from typing import Optional


class MT5Manager:
    """Singleton manager for MT5 connection shared across all bots"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
                    cls._instance._connection_lock = threading.Lock()
                    cls._instance._last_check = 0
        return cls._instance

    def initialize(self) -> bool:
        """Initialize MT5 connection (only once for all bots)"""
        with self._connection_lock:
            if self._initialized:
                # Check if connection is still alive
                if self._is_connected():
                    return True
                else:
                    print("[MT5Manager] Connection lost, reconnecting...")
                    self._initialized = False

            # Try to initialize
            try:
                if mt5.initialize():
                    self._initialized = True
                    print("[MT5Manager] MT5 initialized successfully")
                    return True
                else:
                    error = mt5.last_error()
                    print(f"[MT5Manager] Failed to initialize MT5: {error}")
                    return False
            except Exception as e:
                print(f"[MT5Manager] Exception during initialization: {e}")
                return False

    def _is_connected(self) -> bool:
        """Check if MT5 connection is alive"""
        try:
            # Try a lightweight check
            account_info = mt5.account_info()
            return account_info is not None
        except:
            return False

    def ensure_connection(self) -> bool:
        """Ensure MT5 is connected, reconnect if needed"""
        current_time = time.time()

        # Rate limit connection checks (max once per 5 seconds)
        if current_time - self._last_check < 5:
            return self._initialized

        self._last_check = current_time

        if not self._initialized or not self._is_connected():
            print("[MT5Manager] Connection check failed, reinitializing...")
            return self.initialize()

        return True

    def reconnect(self) -> bool:
        """Force reconnection to MT5"""
        with self._connection_lock:
            print("[MT5Manager] Forcing reconnection...")
            try:
                mt5.shutdown()
                time.sleep(1)
                self._initialized = False
                return self.initialize()
            except Exception as e:
                print(f"[MT5Manager] Reconnection failed: {e}")
                return False

    def shutdown(self):
        """Shutdown MT5 connection (call only when closing entire app)"""
        with self._connection_lock:
            if self._initialized:
                mt5.shutdown()
                self._initialized = False
                print("[MT5Manager] MT5 connection closed")


# Global singleton instance
mt5_manager = MT5Manager()
