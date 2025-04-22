"""
Encryption Key Generator
======================

Purpose:
--------
Generate a secure encryption key and store it securely.
This script should be run once before setting up credentials.

Dependencies:
------------
- cryptography: For generating Fernet key
"""

import os
import base64
from pathlib import Path
from cryptography.fernet import Fernet

def generate_encryption_key():
    """
    Generate a new Fernet encryption key and save it securely.
    """
    try:
        # Generate new key
        key = Fernet.generate_key()
        
        # Get key file path
        key_path = Path(__file__).parent.parent.parent / 'secure' / 'keys' / 'crypto.key'
        
        # Create directory if not exists
        key_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save key with secure permissions
        key_path.write_bytes(key)
        if os.name != 'nt':  # Skip on Windows
            os.chmod(str(key_path), 0o600)
            os.chmod(str(key_path.parent), 0o700)
        
        print("\n✓ Encryption key generated and saved securely")
        print(f"Key location: {key_path}")
        print("\nYou can now run setup_credentials.py")
        
    except Exception as e:
        print(f"\nError generating encryption key: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(generate_encryption_key()) 