"""
Hardware ID generation for machine binding
"""
import uuid
import platform
import hashlib
import subprocess


def get_hardware_id() -> str:
    """
    Generate unique hardware ID based on machine characteristics
    
    Returns:
        str: SHA256 hash of hardware identifiers
    """
    components = []
    
    # MAC address (most stable identifier)
    mac = uuid.getnode()
    components.append(str(mac))
    
    # System information
    components.append(platform.system())
    components.append(platform.machine())
    
    # CPU info (Windows-specific)
    try:
        if platform.system() == 'Windows':
            # Get CPU ID from WMIC
            result = subprocess.run(
                ['wmic', 'cpu', 'get', 'ProcessorId'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                cpu_id = result.stdout.strip().split('\n')[-1].strip()
                if cpu_id:
                    components.append(cpu_id)
            
            # Get motherboard serial
            result = subprocess.run(
                ['wmic', 'baseboard', 'get', 'SerialNumber'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                mb_serial = result.stdout.strip().split('\n')[-1].strip()
                if mb_serial and mb_serial != 'SerialNumber':
                    components.append(mb_serial)
    except Exception:
        # Fallback if WMIC fails
        pass
    
    # Combine all components
    hw_string = '-'.join(components)
    
    # Generate SHA256 hash
    hw_hash = hashlib.sha256(hw_string.encode('utf-8')).hexdigest()
    
    return hw_hash.upper()


def get_hardware_id_short() -> str:
    """
    Get shortened version of hardware ID (first 16 characters)
    
    Returns:
        str: Shortened hardware ID
    """
    return get_hardware_id()[:16]


if __name__ == '__main__':
    # Test hardware ID generation
    print(f"Full Hardware ID: {get_hardware_id()}")
    print(f"Short Hardware ID: {get_hardware_id_short()}")
