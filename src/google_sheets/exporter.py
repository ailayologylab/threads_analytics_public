"""
Google Sheets Exporter
Handles data export to Google Sheets
"""
import os
import json
import logging
import pandas as pd
from typing import List, Dict, Tuple
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from .base_sheets import BaseGoogleSheets


class GoogleSheetsExporter(BaseGoogleSheets):
    """Google Sheets Exporter Class"""
    
    def __init__(self):
        """Initialize Google Sheets Exporter"""
        super().__init__()
    
    def _export_to_csv(self, sheet_name: str) -> bool:
        """
        Export worksheet data to CSV file
        
        Args:
            sheet_name: Worksheet name
            
        Returns:
            bool: Export successful
        """
        try:
            # Get worksheet data
            headers, data = self._get_sheet_data(sheet_name)
            
            if not headers:
                logging.warning(f"Worksheet {sheet_name} has no data, cannot export to CSV")
                return False
            
            # Create DataFrame
            df = pd.DataFrame(data, columns=headers)
            
            # Ensure data directory exists
            os.makedirs('data', exist_ok=True)
            
            # Export to CSV
            csv_path = os.path.join('data', f'{sheet_name}.csv')
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            
            logging.info(f"Exported worksheet {sheet_name} to CSV: {csv_path}")
            return True
        except Exception as e:
            logging.error(f"Error exporting to CSV: {e}")
            return False
    
    def export_posts(self, posts: List[Dict]):
        """
        Batch export post data to Google Sheets, import first then process
        
        Args:
            posts: List of posts to export
        """
        if not posts:
            logging.warning("No post data to export")
            return
        
        sheet_name = "threads_data"
        headers = [
            "post_id", "shortcode", "post_date", "content", "is_quote", 
            "media_type", "permalink", "views", "likes", "replies", 
            "reposts", "quotes", "shares", "engagement", "engagement_rate"
        ]
        
        try:
            # 1. Verify connection to Google Sheets API
            success, spreadsheet_info = self._get_sheet_id()
            if not success:
                logging.error("Unable to connect to Google Sheets API")
                return
            
            # 2. Check if worksheet exists, create if not
            success, sheet_id = self._ensure_sheet_exists(sheet_name, spreadsheet_info)
            if not success:
                logging.error(f"Unable to verify or create worksheet: {sheet_name}")
                return
            
            # Check if worksheet has header row
            existing_headers, _ = self._get_sheet_data(sheet_name)
            needs_headers = not existing_headers
            
            # 5. Calculate dynamic batch size
            total_records = len(posts)
            if total_records <= 100:
                batch_size = 50  # For under 100 records, minimum batch size is 50
            else:
                batch_size = max(50, total_records // 2)  # Use 50% of total records as batch size, but not less than 50
            
            logging.info(f"Total records: {total_records}, Batch size: {batch_size}")
            
            # 6. Process new data in batches
            for i in range(0, total_records, batch_size):
                batch_posts = posts[i:i + batch_size]
                new_data = self._prepare_posts_data(batch_posts)
                
                if new_data:
                    # Write new data #Use append mode, don't overwrite existing data
                    self._update_sheet_data(
                        sheet_name,
                        new_data,
                        append_mode=True,
                        headers=headers if needs_headers else None
                    )
                    needs_headers = False  # Headers added, no need for subsequent batches
                    
                    logging.info(f"Processed batch {i//batch_size + 1}/{(total_records + batch_size - 1)//batch_size}, {len(new_data)} records")
            
            # 7. Process all data in Google Sheets
            operations = [
                # Sort by engagement descending first
                {
                    'type': 'sort',
                    'columnIndex': 13,  # engagement column index
                    'ascending': False
                },
                # Remove duplicates, keep records with higher engagement
                {
                    'type': 'removeDuplicates',
                    'range': {
                        'sheetId': sheet_id,
                        'startRowIndex': 1,  # Skip header row
                        'startColumnIndex': 0,
                        'endColumnIndex': 15
                    },
                    'columns': [0, 1, 2]  # post_id, shortcode, post_date
                },
                # Finally sort by post_date descending
                {
                    'type': 'sort',
                    'columnIndex': 2,  # post_date
                    'ascending': False
                },
                # Auto-resize columns
                {
                    'type': 'autoResize'
                }
            ]
            
            self._format_sheet_data(sheet_name, operations, sheet_id)
            
            # 8. Export CSV backup
            self._export_to_csv(sheet_name)
            
            logging.info(f"Post data export completed, processed {total_records} records")
            return True
            
        except Exception as e:
            logging.error(f"Error during batch export of post data: {e}")
            raise
    
    def _prepare_posts_data(self, posts: List[Dict]) -> List[List]:
        """
        Prepare post data
        
        Args:
            posts: List of posts
            
        Returns:
            List[List]: Formatted post data
        """
        data = []
        
        for post in posts:
            # Calculate engagement metrics and rate
            engagement = (
                post.get('likes', 0) +
                post.get('replies', 0) +
                post.get('reposts', 0) +
                post.get('quotes', 0) +
                post.get('shares', 0)
            )
            
            views = post.get('views', 0)
            engagement_rate = round(engagement / views, 2) if views > 0 else 0
            
            row = [
                post.get('post_id', ''),
                post.get('shortcode', ''),
                post.get('post_date', ''),
                post.get('content', ''),
                post.get('is_quote', False),
                post.get('media_type', ''),
                post.get('permalink', ''),
                views,
                post.get('likes', 0),
                post.get('replies', 0),
                post.get('reposts', 0),
                post.get('quotes', 0),
                post.get('shares', 0),
                engagement,
                engagement_rate
            ]
            data.append(row)
        
        return data
    
    