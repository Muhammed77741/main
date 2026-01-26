"""
Bot Resilience Helpers
Retry logic, timeout handling, and watchdog for bot stability
"""
import time
import threading
import os
from functools import wraps


class TimeoutException(Exception):
    """Raised when operation times out"""
    pass


def retry_with_timeout(func, max_attempts=3, retry_interval=10, timeout_seconds=30, 
                       description="Operation"):
    """
    Execute function with retries and timeout
    
    Args:
        func: Function to execute
        max_attempts: Maximum attempts (default: 3)
        retry_interval: Interval between attempts in seconds (default: 10)
        timeout_seconds: Timeout for one attempt in seconds (default: 30)
        description: Operation description for logs
    
    Returns:
        Function result or None on failure
    """
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"🔄 {description}: Attempt {attempt}/{max_attempts}...")
            
            # Start time for manual timeout tracking
            start_time = time.time()
            
            # Execute function
            result = func()
            
            # Check if it took too long (manual timeout)
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                raise TimeoutException(f"Operation took {elapsed:.1f}s (timeout: {timeout_seconds}s)")
            
            print(f"✅ {description}: Success on attempt {attempt} ({elapsed:.1f}s)")
            return result
                
        except TimeoutException as e:
            print(f"⏱️  {description}: Timeout on attempt {attempt}: {e}")
            if attempt < max_attempts:
                print(f"   Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
            else:
                print(f"❌ {description}: Failed after {max_attempts} attempts (timeout)")
                return None
                
        except Exception as e:
            print(f"❌ {description}: Error on attempt {attempt}: {e}")
            if attempt < max_attempts:
                print(f"   Retrying in {retry_interval} seconds...")
                time.sleep(retry_interval)
            else:
                print(f"❌ {description}: Failed after {max_attempts} attempts")
                return None
    
    return None


class BotWatchdog:
    """Watchdog for monitoring bot hangs"""
    
    def __init__(self, timeout=300, check_interval=30):
        """
        Args:
            timeout: Time without heartbeat before declaring hang (default: 5 min)
            check_interval: Check interval in seconds (default: 30 sec)
        """
        self.timeout = timeout
        self.check_interval = check_interval
        self.last_heartbeat = time.time()
        self.running = False
        self.watchdog_thread = None
        self._lock = threading.Lock()
    
    def heartbeat(self):
        """Send heartbeat - bot is alive"""
        with self._lock:
            self.last_heartbeat = time.time()
    
    def _watchdog_loop(self):
        """Main watchdog loop"""
        while self.running:
            time.sleep(self.check_interval)
            
            with self._lock:
                elapsed = time.time() - self.last_heartbeat
            
            if elapsed > self.timeout:
                print(f"\n{'='*80}")
                print(f"🚨 WATCHDOG ALERT: Bot appears frozen!")
                print(f"   Last heartbeat: {elapsed:.1f} seconds ago")
                print(f"   Timeout threshold: {self.timeout} seconds")
                print(f"{'='*80}\n")
                
                # Attempt forced restart
                print("🔄 Attempting to restart bot...")
                os._exit(1)  # Hard exit for supervisor restart
    
    def start(self):
        """Start watchdog"""
        self.running = True
        self.last_heartbeat = time.time()
        self.watchdog_thread = threading.Thread(
            target=self._watchdog_loop,
            daemon=True,
            name="BotWatchdog"
        )
        self.watchdog_thread.start()
        print(f"✅ Watchdog started (timeout: {self.timeout}s, check: {self.check_interval}s)")
    
    def stop(self):
        """Stop watchdog"""
        self.running = False
        if self.watchdog_thread:
            self.watchdog_thread.join(timeout=5)
        print("✅ Watchdog stopped")


def interruptible_sleep(seconds, check_func=None, check_interval=1):
    """
    Sleep that can be interrupted by condition
    
    Args:
        seconds: Total seconds to sleep
        check_func: Function that returns False to interrupt sleep
        check_interval: How often to check condition (default: 1 sec)
    
    Returns:
        True if slept full duration, False if interrupted
    """
    start_time = time.time()
    end_time = start_time + seconds
    
    while time.time() < end_time:
        # Check interruption condition
        if check_func and not check_func():
            return False
        
        # Sleep for check_interval or remaining time, whichever is smaller
        remaining = end_time - time.time()
        sleep_time = min(check_interval, remaining)
        
        if sleep_time > 0:
            time.sleep(sleep_time)
    
    return True
