"""
Main License Manager
Integrates trial and license key functionality
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
from cryptography.fernet import Fernet
import base64
import hashlib

from .trial_manager import TrialManager
from .keygen import validate_license_key
from .hwid import get_hardware_id


class LicenseManager:
    """Main license manager for the application"""
    
    def __init__(self):
        """Initialize license manager"""
        self.trial_manager = TrialManager()
        
        # License storage location (same as trial)
        if os.name == 'nt':
            program_data = os.environ.get('PROGRAMDATA', 'C:\\ProgramData')
            self.license_dir = Path(program_data) / 'TradingBotManager' / '.config'
        else:
            self.license_dir = Path.home() / '.tradingbotmanager'
        
        self.license_dir.mkdir(parents=True, exist_ok=True)
        self.license_file = self.license_dir / '.lic.dat'
        
        # Encryption key
        self._encryption_key = self._generate_encryption_key()
    
    def _generate_encryption_key(self) -> bytes:
        """Generate encryption key from hardware ID"""
        hw_id = get_hardware_id()
        salt = "TradingBotManager_License_2026"
        key_material = f"{hw_id}{salt}".encode('utf-8')
        key_hash = hashlib.sha256(key_material).digest()
        return base64.urlsafe_b64encode(key_hash)
    
    def _encrypt_data(self, data: dict) -> bytes:
        """Encrypt license data"""
        f = Fernet(self._encryption_key)
        json_data = json.dumps(data).encode('utf-8')
        return f.encrypt(json_data)
    
    def _decrypt_data(self, encrypted_data: bytes) -> Optional[dict]:
        """Decrypt license data"""
        try:
            f = Fernet(self._encryption_key)
            decrypted = f.decrypt(encrypted_data)
            return json.loads(decrypted.decode('utf-8'))
        except Exception:
            return None
    
    def _save_license_data(self, data: dict):
        """Save encrypted license data"""
        encrypted = self._encrypt_data(data)
        with open(self.license_file, 'wb') as f:
            f.write(encrypted)
        
        # Set as hidden on Windows
        if os.name == 'nt':
            try:
                import ctypes
                ctypes.windll.kernel32.SetFileAttributesW(str(self.license_file), 0x02)
            except Exception:
                pass
    
    def _load_license_data(self) -> Optional[dict]:
        """Load encrypted license data"""
        if not self.license_file.exists():
            return None
        
        try:
            with open(self.license_file, 'rb') as f:
                encrypted = f.read()
            return self._decrypt_data(encrypted)
        except Exception:
            return None
    
    def activate_license(self, license_key: str) -> Dict[str, any]:
        """
        Activate application with license key
        
        Args:
            license_key: License key to activate
            
        Returns:
            dict: Activation result with keys:
                - success: bool
                - message: str
                - license_info: dict or None
        """
        hwid = get_hardware_id()
        
        # Validate license key
        is_valid, message, license_info = validate_license_key(license_key, hwid)
        
        if not is_valid:
            return {
                'success': False,
                'message': message,
                'license_info': None,
            }
        
        # Save license data
        license_data = {
            'key': license_key,
            'hwid': hwid,
            'activated_at': datetime.now().isoformat(),
            'license_info': license_info,
        }
        
        self._save_license_data(license_data)
        
        return {
            'success': True,
            'message': 'License activated successfully',
            'license_info': license_info,
        }
    
    def check_license(self) -> Dict[str, any]:
        """
        Check current license status
        
        Returns:
            dict: License status with keys:
                - is_licensed: bool
                - is_trial: bool
                - is_valid: bool
                - message: str
                - days_remaining: int or None
                - features: list
                - requires_activation: bool
        """
        hwid = get_hardware_id()
        
        # First, check if there's an activated license
        license_data = self._load_license_data()
        
        if license_data:
            # Verify hardware ID
            if license_data.get('hwid') != hwid:
                # License moved to different machine
                return {
                    'is_licensed': False,
                    'is_trial': False,
                    'is_valid': False,
                    'message': 'License is for different machine',
                    'days_remaining': None,
                    'features': [],
                    'requires_activation': True,
                }
            
            # Re-validate license key
            license_key = license_data.get('key')
            is_valid, message, license_info = validate_license_key(license_key, hwid)
            
            if is_valid:
                days_remaining = None
                if license_info and license_info.get('expires'):
                    days_remaining = license_info.get('days_remaining')
                
                return {
                    'is_licensed': True,
                    'is_trial': False,
                    'is_valid': True,
                    'message': message,
                    'days_remaining': days_remaining,
                    'features': license_info.get('features', ['ALL']) if license_info else ['ALL'],
                    'requires_activation': False,
                    'license_type': license_info.get('type', 'lifetime') if license_info else 'lifetime',
                }
            else:
                # License invalid (expired or tampered)
                return {
                    'is_licensed': False,
                    'is_trial': False,
                    'is_valid': False,
                    'message': message,
                    'days_remaining': None,
                    'features': [],
                    'requires_activation': True,
                }
        
        # No license, check trial
        trial_status = self.trial_manager.check_trial()
        
        if trial_status['is_first_run']:
            # First run - need to start trial
            return {
                'is_licensed': False,
                'is_trial': True,
                'is_valid': True,
                'message': f'Trial available: {self.trial_manager.TRIAL_DAYS} days',
                'days_remaining': self.trial_manager.TRIAL_DAYS,
                'features': ['ALL'],
                'requires_activation': False,
                'is_first_run': True,
            }
        
        if trial_status['is_valid']:
            # Trial active
            return {
                'is_licensed': False,
                'is_trial': True,
                'is_valid': True,
                'message': trial_status['message'],
                'days_remaining': trial_status['days_remaining'],
                'features': ['ALL'],
                'requires_activation': False,
            }
        else:
            # Trial expired - need activation
            return {
                'is_licensed': False,
                'is_trial': False,
                'is_valid': False,
                'message': trial_status['message'],
                'days_remaining': 0,
                'features': [],
                'requires_activation': True,
            }
    
    def start_trial(self) -> Dict[str, any]:
        """
        Start trial period
        
        Returns:
            dict: Trial information
        """
        return self.trial_manager.start_trial()
    
    def get_hardware_id(self) -> str:
        """
        Get hardware ID for this machine
        
        Returns:
            str: Hardware ID
        """
        return get_hardware_id()
    
    def is_feature_available(self, feature: str) -> bool:
        """
        Check if a feature is available
        
        Args:
            feature: Feature name (BTC, ETH, XAUUSD, or ALL)
            
        Returns:
            bool: True if feature is available
        """
        status = self.check_license()
        
        if not status['is_valid']:
            return False
        
        features = status['features']
        
        # 'ALL' gives access to everything
        if 'ALL' in features:
            return True
        
        # Check specific feature
        return feature.upper() in [f.upper() for f in features]
    
    def get_status_message(self) -> str:
        """
        Get human-readable status message
        
        Returns:
            str: Status message
        """
        status = self.check_license()
        
        if status.get('is_first_run'):
            return f"Welcome! {self.trial_manager.TRIAL_DAYS}-day trial available"
        
        if status['is_licensed']:
            if status['license_type'] == 'lifetime':
                return "Licensed: Lifetime"
            else:
                days = status['days_remaining']
                return f"Licensed: {days} days remaining"
        
        if status['is_trial'] and status['is_valid']:
            days = status['days_remaining']
            return f"Trial: {days} days remaining"
        
        if status['requires_activation']:
            return "Activation required"
        
        return "Unknown status"
    
    def remove_license(self):
        """Remove license data (for testing)"""
        if self.license_file.exists():
            self.license_file.unlink()


if __name__ == '__main__':
    # Test license manager
    lm = LicenseManager()
    
    print("=" * 60)
    print("License Manager Test")
    print("=" * 60)
    
    # Get hardware ID
    hwid = lm.get_hardware_id()
    print(f"\nHardware ID: {hwid}")
    
    # Check license status
    status = lm.check_license()
    print(f"\nLicense Status:")
    print(json.dumps(status, indent=2))
    
    # Get status message
    print(f"\nStatus Message: {lm.get_status_message()}")
    
    # Check feature availability
    print(f"\nFeature Availability:")
    print(f"  BTC: {lm.is_feature_available('BTC')}")
    print(f"  ETH: {lm.is_feature_available('ETH')}")
    print(f"  XAUUSD: {lm.is_feature_available('XAUUSD')}")
