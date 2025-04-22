"""
Cryptographic Utilities
======================

Purpose:
--------
Provide secure encryption and decryption functionality for sensitive credentials.
Handles the encryption/decryption of API tokens and other sensitive data.

Execution Flow:
--------------
1. Generate encryption key from environment variable or create new one
2. Encrypt credentials before saving to file
3. Decrypt credentials when needed for verification
4. Ensure secure handling of sensitive data

Dependencies:
------------
- Required environment variables:
  - CREDENTIALS_PATH: Path to encrypted credentials file
  - CRYPTO_KEY_PATH: Path to encryption key file

Security:
---------
- Uses Fernet symmetric encryption (implementation of AES)
- Encryption key stored in environment variables
- Encrypted data stored in files
- Decrypted data only held in memory temporarily
"""

import os
import json
import base64
import logging
from pathlib import Path
from typing import Dict, Any, Union, Optional
from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('crypto_utils')

class CryptoError(Exception):
    """Custom exception for cryptographic operations"""
    pass

class CryptoManager:
    """
    Manages encryption and decryption of sensitive credentials.
    
    Uses Fernet symmetric encryption for secure storage of credentials.
    Handles the encryption key management and file operations.
    """
    
    def __init__(self, key_path: Union[str, Path], credentials_path: str) -> None:
        """
        Initialize the CryptoManager with key path and credentials path.
        
        Args:
            key_path: Path to the encryption key file
            credentials_path: Path to the encrypted credentials file
        """
        try:
            key_path = Path(key_path)
            if not key_path.exists():
                raise CryptoError(f"Encryption key file not found: {key_path}")
                
            encryption_key = key_path.read_bytes()
            self.fernet = Fernet(encryption_key)
            self.credentials_path = Path(credentials_path)
            logger.info("CryptoManager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize CryptoManager: {e}")
            raise CryptoError(f"Initialization failed: {e}")
    
    @classmethod
    def from_env(cls) -> 'CryptoManager':
        """
        Create CryptoManager instance from environment variables.
        
        Returns:
            CryptoManager: Initialized instance
            
        Raises:
            CryptoError: If required environment variables are missing
        """
        load_dotenv()
        
        key_path = os.getenv('CRYPTO_KEY_PATH')
        credentials_path = os.getenv('CREDENTIALS_PATH')
        
        if not key_path:
            raise CryptoError("Missing CRYPTO_KEY_PATH environment variable")
        if not credentials_path:
            raise CryptoError("Missing CREDENTIALS_PATH environment variable")
            
        try:
            # 轉換為絕對路徑
            project_root = Path(__file__).parent.parent.parent
            full_key_path = project_root / key_path
            full_creds_path = project_root / credentials_path
            
            return cls(full_key_path, full_creds_path)
        except Exception as e:
            logger.error(f"Failed to create CryptoManager from environment: {e}")
            raise CryptoError(f"Environment initialization failed: {e}")
    
    def encrypt_credentials(self, credentials: Dict[str, Any]) -> None:
        """
        Encrypt and save credentials to file.
        
        Args:
            credentials: Dictionary of credentials to encrypt
            
        Raises:
            CryptoError: If encryption or file operation fails
        """
        try:
            # Convert credentials to JSON string
            json_data = json.dumps(credentials)
            
            # Encrypt the JSON string
            encrypted_data = self.fernet.encrypt(json_data.encode())
            
            # Save to file with secure permissions
            self.credentials_path.parent.mkdir(parents=True, exist_ok=True)
            if os.name != 'nt':  # Skip on Windows
                os.chmod(str(self.credentials_path.parent), 0o700)
            
            self.credentials_path.write_bytes(encrypted_data)
            if os.name != 'nt':  # Skip on Windows
                os.chmod(str(self.credentials_path), 0o600)
                
            logger.info("Credentials encrypted and saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to encrypt credentials: {e}")
            raise CryptoError(f"Encryption failed: {e}")
    
    def load_credentials(self) -> Dict[str, Any]:
        """
        Load and decrypt credentials from file.
        
        Returns:
            Dict[str, Any]: Decrypted credentials
            
        Raises:
            CryptoError: If decryption or file operation fails
        """
        try:
            if not self.credentials_path.exists():
                logger.error("Credentials file not found")
                raise CryptoError("Credentials file not found")
                
            # Read encrypted data
            encrypted_data = self.credentials_path.read_bytes()
            
            # Decrypt data
            json_data = self.fernet.decrypt(encrypted_data).decode()
            
            # Parse JSON
            credentials = json.loads(json_data)
            logger.info("Credentials loaded and decrypted successfully")
            return credentials
            
        except InvalidToken:
            logger.error("Invalid encryption key or corrupted data")
            raise CryptoError("Invalid encryption key or corrupted data")
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            raise CryptoError(f"Decryption failed: {e}")
    
    def get_single_credential(self, key: str) -> Union[str, Dict[str, Any]]:
        """
        獲取單個憑證值
        
        這個方法可以安全地獲取單個憑證，而不是載入整個憑證字典
        """
        try:
            creds = self.load_credentials()
            if key not in creds:
                raise CryptoError(f"找不到指定的憑證: {key}")
            return creds[key]
        except Exception as e:
            logger.error(f"獲取憑證 '{key}' 時發生錯誤: {e}")
            raise CryptoError(f"獲取憑證 '{key}' 時發生錯誤: {e}") 