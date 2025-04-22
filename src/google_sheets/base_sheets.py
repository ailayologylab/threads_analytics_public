"""
Google Sheets Base Operation Class
Provides basic Google Sheets operation functionality
"""
import os
import json
import logging
from typing import List, Dict, Tuple, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from utils.crypto_utils import CryptoManager
import sys

# Use os.path to handle paths
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
utils_dir = os.path.join(base_dir, "src", "utils")
if utils_dir not in sys.path:
    sys.path.append(utils_dir)


class BaseGoogleSheets:
    """Google Sheets Base Operation Class"""
    
    def __init__(self):
        """Initialize Google Sheets Base Operation Class"""
        load_dotenv()
        
        # Read encrypted file path from environment variables
        credentials_path = os.getenv("CREDENTIALS_PATH")
        if not credentials_path:
            raise ValueError("CREDENTIALS_PATH environment variable not set")
            
        # Use CryptoManager to decrypt and get credentials
        try:
            crypto_manager = CryptoManager.from_env()
            
            # Get Google credentials and spreadsheet ID from encrypted file
            credentials = crypto_manager.get_single_credential("google_credentials")
            self._spreadsheet_id = crypto_manager.get_single_credential("spreadsheet_id")
            
            if not credentials:
                raise ValueError("Unable to obtain Google credentials")
            if not self._spreadsheet_id:
                raise ValueError("Unable to obtain spreadsheet ID")
                
            # Create credentials object
            try:
                # If it's a string (encrypted credentials), try to parse as JSON
                if isinstance(credentials, str):
                    credentials = json.loads(credentials)
                
                creds = service_account.Credentials.from_service_account_info(
                    credentials,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
            except Exception as e:
                logging.error(f"Error processing Google credentials: {e}")
                raise
            
            # Initialize service
            self._service = build('sheets', 'v4', credentials=creds)
            
            # Clean up sensitive information
            del credentials
            del creds
            del crypto_manager
            
        except Exception as e:
            # Ensure sensitive data is cleaned up even when error occurs
            if 'credentials' in locals():
                del credentials
            if 'creds' in locals():
                del creds
            if 'crypto_manager' in locals():
                del crypto_manager
            logging.error(f"Error initializing Google Sheets Base Operation Class: {e}")
            raise
    
    def __del__(self):
        """Ensure cleanup of sensitive information"""
        try:
            if hasattr(self, '_service'):
                self._service = None
            if hasattr(self, '_spreadsheet_id'):
                self._spreadsheet_id = None
        except Exception as e:
            logging.warning(f"Error occurred while cleaning up resources: {e}")
    
    def _get_sheet_id(self) -> Tuple[bool, Dict]:
        """
        Verify connection to Google Sheets API and access to spreadsheet
        
        Returns:
            Tuple[bool, Dict]: (Connection successful, Spreadsheet information)
        """
        try:
            # Check if API service is initialized
            if not self._service:
                logging.error("Google Sheets API service not initialized")
                return False, None
                
            # Check if spreadsheet_id is valid
            if not self._spreadsheet_id:
                logging.error("spreadsheet_id not set")
                return False, None
                
            # Try to access spreadsheet
            spreadsheet_info = self._service.spreadsheets().get(
                spreadsheetId=self._spreadsheet_id
            ).execute()
            
            logging.info("Successfully connected to Google Sheets API")
            return True, spreadsheet_info
            
        except Exception as e:
            logging.error(f"Error connecting to Google Sheets API: {e}")
            return False, None
    
    def _ensure_sheet_exists(self, sheet_name: str, spreadsheet_info: Dict) -> Tuple[bool, int]:
        """
        Ensure worksheet exists, create if not exists
        
        Args:
            sheet_name: Worksheet name
            spreadsheet_info: Spreadsheet information (must be provided)
            
        Returns:
            Tuple[bool, int]: (Worksheet exists or created, Worksheet ID)
        """
        try:
            if spreadsheet_info is None:
                logging.error("Spreadsheet information must be provided")
                return False, None
            
            # Find worksheet ID
            sheet_id = None
            for sheet in spreadsheet_info.get('sheets', []):
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    logging.info(f"Found existing worksheet: {sheet_name}, ID: {sheet_id}")
                    break
            
            # Create worksheet if it doesn't exist
            if sheet_id is None:
                body = {
                    'requests': [{
                        'addSheet': {
                            'properties': {
                                'title': sheet_name
                            }
                        }
                    }]
                }
                response = self._service.spreadsheets().batchUpdate(
                    spreadsheetId=self._spreadsheet_id,
                    body=body
                ).execute()
                
                # Get newly created worksheet ID from response
                sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
                logging.info(f"Created worksheet: {sheet_name}, ID: {sheet_id}")
            
            return True, sheet_id
        except Exception as e:
            logging.error(f"Error checking/creating worksheet: {e}")
            return False, None
    
    def _get_sheet_data(self, sheet_name: str) -> Tuple[List[str], List[List]]:
        """
        Get worksheet data
        
        Args:
            sheet_name: Worksheet name
            
        Returns:
            Tuple[List[str], List[List]]: (Header row, Data rows)
        """
        try:
            result = self._service.spreadsheets().values().get(
                spreadsheetId=self._spreadsheet_id,
                range=f"{sheet_name}!A:Z"
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                return [], []
            
            headers = values[0]
            data = values[1:] if len(values) > 1 else []
            
            return headers, data
        except Exception as e:
            logging.error(f"Error getting worksheet data: {e}")
            return [], []
    
    def _update_sheet_data(self, sheet_name: str, data: List[List], 
                          start_cell: str = "A1", append_mode: bool = True, 
                          headers: List[str] = None) -> bool:
        """
        Update worksheet data
        
        Args:
            sheet_name: Worksheet name
            data: Data rows
            start_cell: Starting cell (not needed in append mode)
            append_mode: Whether to use append mode (defaults to True)
            headers: Header row, if provided will be added before data
            
        Returns:
            bool: Update successful
        """
        try:
            # Prepare data, determine if header row needs to be added
            values = [headers] + data if headers else data
            
            body = {"values": values}
            
            # Append data to worksheet #requires append api
            result = self._service.spreadsheets().values().append(
                spreadsheetId=self._spreadsheet_id,
                range=f"{sheet_name}!A1",  # Use fixed starting position in append mode
                valueInputOption="USER_ENTERED",  # Use USER_ENTERED instead of RAW to let Google Sheets auto-parse datetime
                insertDataOption="INSERT_ROWS",
                body=body
            ).execute()
            
            if headers:
                logging.info(f"Added header row and {len(data)} rows of data to worksheet {sheet_name}")
            else:
                logging.info(f"Appended {len(data)} rows of data to worksheet {sheet_name}")
            return True
            
        except Exception as e:
            logging.error(f"Error updating worksheet data: {e}")
            return False
    
    def _format_sheet_data(self, sheet_name: str, operations: List[Dict[str, Any]], sheet_id: int) -> bool:
        """
        Format worksheet data, execute multiple formatting operations
        
        Args:
            sheet_name: Worksheet name
            operations: List of operations
            sheet_id: Worksheet ID, must be provided
            
        Returns:
            bool: Operation successful
        """
        try:
            # sheet_id must be provided
            if sheet_id is None:
                logging.error(f"Worksheet ID must be provided to execute formatting operations")
                return False
            
            requests = []
            
            for op in operations:
                if op['type'] == 'sort':
                    requests.append({
                        'sortRange': {
                            'range': {
                                'sheetId': sheet_id,
                                'startRowIndex': op.get('startRowIndex', 1),
                                'startColumnIndex': op.get('startColumnIndex', 0),
                                'endColumnIndex': op.get('endColumnIndex', 26)
                            },
                            'sortSpecs': [{
                                'dimensionIndex': op['columnIndex'],
                                'sortOrder': 'ASCENDING' if op.get('ascending', False) else 'DESCENDING'
                            }]
                        }
                    })
                elif op['type'] == 'autoResize':
                    requests.append({
                        'autoResizeDimensions': {
                            'dimensions': {
                                'sheetId': sheet_id,
                                'dimension': 'COLUMNS',
                                'startIndex': 0,
                                'endIndex': op.get('endIndex', 26)
                            }
                        }
                    })
                elif op['type'] == 'removeDuplicates':
                    requests.append({
                        'deleteDuplicates': {
                            'range': op.get('range', {
                                'sheetId': sheet_id,
                                'startRowIndex': 1,
                                'startColumnIndex': 0,
                                'endColumnIndex': 26
                            }),
                            'comparisonColumns': [
                                {
                                    'sheetId': sheet_id,
                                    'dimension': 'COLUMNS',
                                    'startIndex': col_index,
                                    'endIndex': col_index + 1
                                }
                                for col_index in op.get('columns', [])
                            ]
                        }
                    })
                elif op['type'] == 'formatPercent':
                    requests.append({
                        'repeatCell': {
                            'range': {
                                'sheetId': sheet_id,
                                'startRowIndex': 1,
                                'startColumnIndex': op['columnIndex'],
                                'endColumnIndex': op['columnIndex'] + 1
                            },
                            'cell': {
                                'userEnteredFormat': {
                                    'numberFormat': {
                                        'type': 'PERCENT',
                                        'pattern': op.get('pattern', '0.00%')
                                    }
                                }
                            },
                            'fields': 'userEnteredFormat.numberFormat'
                        }
                    })
            
            if requests:
                self._service.spreadsheets().batchUpdate(
                    spreadsheetId=self._spreadsheet_id,
                    body={'requests': requests}
                ).execute()
                logging.info(f"Completed formatting operations for worksheet {sheet_name}")
            
            return True
        except Exception as e:
            logging.error(f"Error formatting worksheet: {e}")
            return False
    
    