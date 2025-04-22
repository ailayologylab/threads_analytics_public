"""
Credential Verification Script
============================

Purpose:
--------
Verify the existence and validity of encrypted credentials with minimal API requests.
Ensures security of sensitive data during verification process.

Execution Flow:
--------------
1. Verify encryption key and file existence
2. Verify each credential with minimal API calls
3. Return verification results

Dependencies:
------------
- crypto_utils.py: For secure credential handling
- Required environment variables in .env file
"""

import sys
import json
import logging
import requests
from pathlib import Path
from typing import Dict, Any, Tuple
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.utils.crypto_utils import CryptoManager, CryptoError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('verify_credentials')

def verify_threads_token(crypto_manager: CryptoManager) -> bool:
    """
    Verify Threads API token with a single API call.
    
    Args:
        crypto_manager: Instance of CryptoManager
        
    Returns:
        bool: True if token is valid
    """
    try:
        threads_token = crypto_manager.get_single_credential('threads_token')
        if not threads_token:
            logger.error("Threads token not found in credentials")
            return False
            
       #Setting the correct API
        headers = {
            "Authorization": f"Bearer {threads_token}",
            "Content-Type": "application/json"
        }
        
        #setting the correct API endpoint
        response = requests.get(
            'https://graph.threads.net/v1.0/me',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info("Threads token verified successfully")
            return True
        else:
            logger.error(f"Threads API returned status code: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Threads token verification failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during Threads token verification: {e}")
        return False

def verify_google_credentials(crypto_manager: CryptoManager) -> Tuple[bool, bool]:
    """
    Verify Google credentials and spreadsheet access with a single API call.
    
    Args:
        crypto_manager: Instance of CryptoManager
        
    Returns:
        Tuple[bool, bool]: (google_credentials_valid, spreadsheet_id_valid)
    """
    try:
        # Get credentials individually to minimize decryption operations
        google_creds = crypto_manager.get_single_credential('google_credentials')
        spreadsheet_id = crypto_manager.get_single_credential('spreadsheet_id')
        
        if not (google_creds and spreadsheet_id):
            return False, False
            
        # Single API call to verify both credentials
        credentials = service_account.Credentials.from_service_account_info(
            google_creds,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        service = build('sheets', 'v4', credentials=credentials)
        service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        
        return True, True
    except Exception as e:
        logger.error(f"Google credentials verification failed: {e}")
        return False, False

def verify_credentials() -> Dict[str, bool]:
    """
    Verify all credentials with minimal API calls and secure handling.
    
    Returns:
        Dict[str, bool]: Verification results for each credential
    """
    results = {
        'threads_token': False,
        'spreadsheet_id': False,
        'google_credentials': False
    }
    
    try:
        logger.info("Starting credential verification...")
        crypto_manager = CryptoManager.from_env()
        
        # Verify Threads token
        results['threads_token'] = verify_threads_token(crypto_manager)
        
        # Verify Google credentials and spreadsheet with a single call
        google_valid, spreadsheet_valid = verify_google_credentials(crypto_manager)
        results['google_credentials'] = google_valid
        results['spreadsheet_id'] = spreadsheet_valid
        
        return results
    except Exception as e:
        logger.error(f"Verification process failed: {e}")
        return results

def main() -> int:
    """
    Main execution function.
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    try:
        logger.info("Starting verification process...")
        results = verify_credentials()
        
        print("\nVerification Results:")
        print("-" * 30)
        
        all_valid = True
        for key, is_valid in results.items():
            status = "✓ Valid" if is_valid else "✗ Invalid"
            print(f"{key}: {status}")
            all_valid = all_valid and is_valid
        
        print("-" * 30)
        if all_valid:
            logger.info("All credentials are valid")
            print("\n✓ All credentials are valid and ready to use")
            return 0
        else:
            logger.warning("Some credentials are invalid")
            print("\n✗ Some credentials are invalid")
            print("Please run setup_credentials.py to configure missing credentials")
            return 1
            
    except Exception as e:
        logger.error(f"Verification error: {e}")
        print(f"Error during verification: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 