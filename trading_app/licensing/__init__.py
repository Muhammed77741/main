"""
Licensing module for Trading Bot Manager
Handles trial version and license key activation
"""

from .license_manager import LicenseManager
from .trial_manager import TrialManager
from .hwid import get_hardware_id
from .keygen import generate_license_key, validate_license_key

__all__ = [
    'LicenseManager',
    'TrialManager',
    'get_hardware_id',
    'generate_license_key',
    'validate_license_key',
]
