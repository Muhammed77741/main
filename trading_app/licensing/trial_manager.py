"""
Trial version manager
Handles 7-day trial period with encrypted storage
"""
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from cryptography.fernet import Fernet
import base64
import hashlib


class TrialManager:
    """Manages trial period for the application"""
    
    TRIAL_DAYS = 7
    
    def __init__(self):
        """Initialize trial manager"""
        # Store trial data in ProgramData (Windows)
        if os.name == 'nt':  # Windows
            program_data = os.environ.get('PROGRAMDATA', 'C:\\ProgramData')
            self.trial_dir = Path(program_data) / 'TradingBotManager' / '.config'
        else:
            # Fallback for non-Windows systems
            self.trial_dir = Path.home() / '.tradingbotmanager'
        
        self.trial_dir.mkdir(parents=True, exist_ok=True)
        self.trial_file = self.trial_dir / '.trial.dat'
        self.backup_file = self.trial_dir / '.tbm.cfg'  # Backup location
        
        # Generate encryption key from machine-specific data
        self._encryption_key = self._generate_encryption_key()
    
    def _generate_encryption_key(self) -> bytes:
        """
        Generate encryption key from machine-specific data
        
        Returns:
            bytes: Fernet encryption key
        """
        from .hwid import get_hardware_id
        
        # Use hardware ID as basis for encryption key
        hw_id = get_hardware_id()
        
        # Add some salt
        salt = "TradingBotManager_2026_Trial_System"
        
        # Combine and hash
        key_material = f"{hw_id}{salt}".encode('utf-8')
        key_hash = hashlib.sha256(key_material).digest()
        
        # Convert to Fernet-compatible key (base64 encoded 32 bytes)
        fernet_key = base64.urlsafe_b64encode(key_hash)
        
        return fernet_key
    
    def _encrypt_data(self, data: dict) -> bytes:
        """
        Encrypt trial data
        
        Args:
            data: Dictionary to encrypt
            
        Returns:
            bytes: Encrypted data
        """
        f = Fernet(self._encryption_key)
        json_data = json.dumps(data).encode('utf-8')
        encrypted = f.encrypt(json_data)
        return encrypted
    
    def _decrypt_data(self, encrypted_data: bytes) -> dict:
        """
        Decrypt trial data
        
        Args:
            encrypted_data: Encrypted bytes
            
        Returns:
            dict: Decrypted data
        """
        try:
            f = Fernet(self._encryption_key)
            decrypted = f.decrypt(encrypted_data)
            data = json.loads(decrypted.decode('utf-8'))
            return data
        except Exception:
            return None
    
    def _save_trial_data(self, data: dict):
        """Save encrypted trial data to multiple locations"""
        encrypted = self._encrypt_data(data)
        
        # Save to primary location
        with open(self.trial_file, 'wb') as f:
            f.write(encrypted)
        
        # Save to backup location
        with open(self.backup_file, 'wb') as f:
            f.write(encrypted)
        
        # Set files as hidden on Windows
        if os.name == 'nt':
            try:
                import ctypes
                # FILE_ATTRIBUTE_HIDDEN = 0x02
                ctypes.windll.kernel32.SetFileAttributesW(str(self.trial_file), 0x02)
                ctypes.windll.kernel32.SetFileAttributesW(str(self.backup_file), 0x02)
            except Exception:
                pass
    
    def _load_trial_data(self) -> dict:
        """Load encrypted trial data"""
        # Try primary location
        if self.trial_file.exists():
            try:
                with open(self.trial_file, 'rb') as f:
                    encrypted = f.read()
                data = self._decrypt_data(encrypted)
                if data:
                    return data
            except Exception:
                pass
        
        # Try backup location
        if self.backup_file.exists():
            try:
                with open(self.backup_file, 'rb') as f:
                    encrypted = f.read()
                data = self._decrypt_data(encrypted)
                if data:
                    # Restore primary file
                    self._save_trial_data(data)
                    return data
            except Exception:
                pass
        
        return None
    
    def start_trial(self) -> dict:
        """
        Start trial period
        
        Returns:
            dict: Trial information
        """
        from .hwid import get_hardware_id
        
        now = datetime.now()
        end_date = now + timedelta(days=self.TRIAL_DAYS)
        
        trial_data = {
            'started_at': now.isoformat(),
            'expires_at': end_date.isoformat(),
            'hwid': get_hardware_id(),
            'version': '1.0.0',
        }
        
        self._save_trial_data(trial_data)
        
        return {
            'started_at': now,
            'expires_at': end_date,
            'days_remaining': self.TRIAL_DAYS,
        }
    
    def check_trial(self) -> dict:
        """
        Check trial status
        
        Returns:
            dict: Trial status with keys:
                - is_valid: bool
                - is_expired: bool
                - days_remaining: int
                - expires_at: datetime or None
                - message: str
        """
        from .hwid import get_hardware_id
        
        # Check if trial exists
        trial_data = self._load_trial_data()
        
        if not trial_data:
            # No trial found, start new trial
            return {
                'is_valid': False,
                'is_expired': False,
                'is_first_run': True,
                'days_remaining': self.TRIAL_DAYS,
                'expires_at': None,
                'message': 'First run - trial not started yet',
            }
        
        # Verify hardware ID (anti-tampering)
        if trial_data.get('hwid') != get_hardware_id():
            return {
                'is_valid': False,
                'is_expired': True,
                'days_remaining': 0,
                'expires_at': None,
                'message': 'Trial data tampered or moved to different machine',
            }
        
        # Check expiration
        try:
            started_at = datetime.fromisoformat(trial_data['started_at'])
            expires_at = datetime.fromisoformat(trial_data['expires_at'])
        except (KeyError, ValueError):
            # Invalid data
            return {
                'is_valid': False,
                'is_expired': True,
                'days_remaining': 0,
                'expires_at': None,
                'message': 'Trial data corrupted',
            }
        
        now = datetime.now()
        
        # Check for system time manipulation
        if now < started_at:
            return {
                'is_valid': False,
                'is_expired': True,
                'days_remaining': 0,
                'expires_at': expires_at,
                'message': 'System time manipulation detected',
            }
        
        # Calculate remaining days
        time_remaining = expires_at - now
        days_remaining = max(0, time_remaining.days)
        
        is_expired = now >= expires_at
        
        return {
            'is_valid': not is_expired,
            'is_expired': is_expired,
            'is_first_run': False,
            'days_remaining': days_remaining,
            'started_at': started_at,
            'expires_at': expires_at,
            'message': f'{days_remaining} days remaining' if not is_expired else 'Trial expired',
        }
    
    def get_trial_info(self) -> str:
        """
        Get human-readable trial information
        
        Returns:
            str: Trial information message
        """
        status = self.check_trial()
        
        if status['is_first_run']:
            return f"Trial: {self.TRIAL_DAYS} days available"
        elif status['is_valid']:
            return f"Trial: {status['days_remaining']} days remaining"
        else:
            return "Trial: Expired"


if __name__ == '__main__':
    # Test trial manager
    tm = TrialManager()
    
    # Check trial status
    status = tm.check_trial()
    print("Trial Status:")
    print(json.dumps(status, indent=2, default=str))
    
    # Get trial info
    print(f"\n{tm.get_trial_info()}")
