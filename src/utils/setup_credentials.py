"""
Credential Setup Script
=====================

Purpose:
--------
Initialize and securely store encrypted credentials for the application.
Handles user input and file selection for sensitive data.

Execution Flow:
--------------
1. Collect Threads API token
2. Collect Google Spreadsheet ID
3. Select and validate Google service account JSON file
4. Encrypt and store all credentials securely

Dependencies:
------------
- crypto_utils.py: For secure credential storage
- Required environment variables in .env file
"""

import json
import os
import sys
import logging
from pathlib import Path
from typing import List

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
logger = logging.getLogger('setup_credentials')

def list_json_files(directory: Path) -> List[Path]:
    """
    List all JSON files in the specified directory.
    
    Args:
        directory: Directory path to search
        
    Returns:
        List[Path]: List of paths to JSON files
    """
    return list(directory.glob("*.json"))

def setup_credentials() -> None:
    """
    Initialize and encrypt credentials for the application.
    Handles user input and validation of sensitive data.
    """
    try:
        logger.info("Starting credential setup")
        crypto = CryptoManager.from_env()
        
        print("\n=== Threads Data Analytics Credential Setup ===\n")
        
        # Collect credentials
        credentials = {}
        
        # Get Threads API Token
        threads_token = input('Threads API Token: ').strip()
        if not threads_token:
            raise ValueError("Threads API Token cannot be empty")
        credentials['threads_token'] = threads_token
        
        # Get Google Spreadsheet ID
        spreadsheet_id = input('Google Spreadsheet ID: ').strip()
        if not spreadsheet_id:
            raise ValueError("Google Spreadsheet ID cannot be empty")
        credentials['spreadsheet_id'] = spreadsheet_id
        
        logger.info("Basic credentials collected")
        
        # Read Google credentials file
        while True:
            try:
                print("\nSelect Google Credentials JSON file:")
                print("1. Enter full file path")
                print("2. Browse directory for JSON files")
                choice = input("\nSelect option (1/2): ").strip()
                
                if choice == "1":
                    google_creds_path = input('\nEnter full JSON file path: ').strip()
                    creds_path = Path(google_creds_path.strip('"\''))
                
                elif choice == "2":
                    dir_path = input('\nEnter directory path to search: ').strip().strip('"\'')
                    dir_path = Path(dir_path)
                    
                    if not dir_path.is_dir():
                        logger.error(f"Invalid directory path: {dir_path}")
                        print(f"Error: '{dir_path}' is not a valid directory")
                        continue
                    
                    json_files = list_json_files(dir_path)
                    if not json_files:
                        logger.warning(f"No JSON files found in directory: {dir_path}")
                        print(f"No JSON files found in '{dir_path}'")
                        continue
                    
                    print("\nFound JSON files:")
                    for i, file in enumerate(json_files, 1):
                        print(f"{i}. {file.name}")
                    
                    while True:
                        try:
                            file_num = int(input("\nSelect file number: ").strip())
                            if 1 <= file_num <= len(json_files):
                                creds_path = json_files[file_num - 1]
                                break
                            else:
                                print("Invalid selection, please try again")
                        except ValueError:
                            print("Please enter a valid number")
                else:
                    print("Invalid choice, enter 1 or 2")
                    continue
                
                # Validate file
                if not creds_path.is_file():
                    logger.error(f"File not found: {creds_path}")
                    print(f"Error: File '{creds_path}' not found")
                    continue
                    
                if creds_path.suffix.lower() != '.json':
                    logger.error(f"Not a JSON file: {creds_path}")
                    print("Error: Please provide a JSON file")
                    continue
                
                # Read and validate file contents
                logger.info(f"Reading Google credentials file: {creds_path}")
                with open(creds_path, 'r', encoding='utf-8') as f:
                    google_creds = json.load(f)
                
                # Validate required fields
                required_fields = {'type', 'project_id', 'private_key_id', 'private_key', 'client_email'}
                missing_fields = required_fields - set(google_creds.keys())
                if missing_fields:
                    logger.error(f"Missing required fields in credentials: {missing_fields}")
                    print("Error: Invalid Google credentials format")
                    print(f"Missing fields: {', '.join(missing_fields)}")
                    continue
                
                print(f"\nSelected: {creds_path}")
                if input("\nUse this file? (y/n): ").lower().strip() != 'y':
                    continue
                
                credentials['google_credentials'] = google_creds
                logger.info("Google credentials loaded successfully")
                break
                
            except PermissionError:
                logger.error(f"Permission denied: {creds_path}")
                print(f"Error: Cannot access file '{creds_path}', check permissions")
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON format: {creds_path}")
                print("Error: Invalid JSON format")
            except Exception as e:
                logger.error(f"Error reading file: {str(e)}")
                print(f"Error: {str(e)}")
        
        # Verify all required credentials
        required_creds = {'threads_token', 'spreadsheet_id', 'google_credentials'}
        missing_creds = required_creds - set(credentials.keys())
        if missing_creds:
            raise ValueError(f"Missing required credentials: {', '.join(missing_creds)}")
        
        # Encrypt and save credentials
        logger.info("Encrypting and saving credentials")
        crypto.encrypt_credentials(credentials)
        logger.info("Credentials encrypted and saved successfully")
        
        print("\n✓ Credentials encrypted and stored securely")
        print("\nSetup complete! You can now run the main program.")
        
    except CryptoError as e:
        logger.error(f"Encryption error: {str(e)}")
        print(f"\nEncryption error: {str(e)}")
    except Exception as e:
        logger.error(f"Setup error: {str(e)}")
        print(f"\nError: {str(e)}")
    finally:
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    setup_credentials() 