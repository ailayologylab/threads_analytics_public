"""
Threads Data Collector
Handles collection and storage of post data
"""
import os
import json
import logging
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
from .client import ThreadsAPIClient
import shutil
import argparse
from dotenv import load_dotenv
import pytz

class ThreadsDataCollector:
    def __init__(self):
        """Initialize collector"""
        # Use absolute path
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.data_dir = os.path.join(base_dir, "data")
        os.makedirs(self.data_dir, exist_ok=True)
        logging.info(f"Data directory set to: {self.data_dir}")
        
        # Initialize API client
        self.client = ThreadsAPIClient()
        
        # Set batch size
        self.batch_size = 50
        
    def collect_posts(self, mode: str = "normal", limit: Optional[int] = None) -> List[Dict]:
        """
        Collect post data
        
        Args:
            mode: Collection mode
                - "force": Force fetch all posts
                - "test": Limit return to specific number of posts for testing
                - "normal": Only update new posts
            limit: Post quantity limit in test mode, defaults to batch_size
            
        Returns:
            List[Dict]: List of posts with complete information
        """
        try:
            # Set default limit
            if mode == "test":
                limit = limit or self.batch_size
                
            # Get posts based on mode
            posts = self._get_posts_with_mode(mode, limit)
            if not posts:
                logging.info("No posts to process")
                return []
                
            logging.info(f"Retrieved {len(posts)} posts")
            
            # Process insights in batches
            post_ids = [post["id"] for post in posts]
            insights_map = self.client.get_post_insights(post_ids)
            
            # Merge data and convert timezone
            processed_posts = []
            for post in posts:
                # Convert UTC time to Taipei time
                post_date = datetime.strptime(post.get("timestamp", ""), '%Y-%m-%dT%H:%M:%S%z')
                taipei_date = post_date.astimezone(pytz.timezone('Asia/Taipei'))
                
                post_data = {
                    "post_id": post["id"],
                    "shortcode": post.get("shortcode", ""),
                    "post_date": taipei_date.strftime('%Y-%m-%dT%H:%M:%S%z'),  # Use Taipei time
                    "content": post.get("text", ""),
                    "is_quote": post.get("is_quote_post", False),
                    "media_type": post.get("media_type", ""),
                    "permalink": post.get("permalink", ""),
                    **insights_map.get(post["id"], {})
                }
                processed_posts.append(post_data)
                
            # Save data
            self._save_posts(processed_posts)
            return processed_posts
            
        except Exception as e:
            logging.error(f"Error occurred while collecting post data: {e}")
            return []
            
    def _get_posts_with_mode(self, mode: str, limit: Optional[int]) -> List[Dict]:
        """
        Get posts based on mode
        
        Args:
            mode: Collection mode
            limit: Quantity limit in test mode
            
        Returns:
            List[Dict]: List of posts matching criteria
        """
        try:
            logging.info(f"Starting _get_posts_with_mode, mode: {mode}, limit: {limit}")
            
            if mode == "test":
                # Test mode: use specified limit or batch_size
                posts = self.client.get_user_posts(limit=limit, is_test_mode=True)
                logging.info(f"Test mode: requesting {limit} posts, actually retrieved {len(posts)} posts")
                return posts
                
            elif mode == "force":
                # Force mode: get all posts
                posts = self.client.get_user_posts(is_test_mode=False)
                logging.info(f"Force mode: getting all posts, {self.batch_size} per batch, actually retrieved {len(posts)} posts")
                return posts
                
            else:  # Normal mode
                logging.info("Executing normal mode logic")
                # 1. Read latest post date from CSV file
                csv_file = os.path.join(self.data_dir, "threads_data.csv")
                logging.info(f"Checking CSV file: {csv_file}")
                
                latest_date = None
                
                if os.path.exists(csv_file):
                    logging.info("CSV file exists")
                    df = pd.read_csv(csv_file)
                    logging.info(f"CSV file content: {df.head()}")
                    logging.info(f"CSV columns: {df.columns.tolist()}")
                    
                    if not df.empty:
                        logging.info("CSV file is not empty")
                        if 'post_date' in df.columns:
                            logging.info("Found post_date column")
                            df['post_date'] = pd.to_datetime(df['post_date'])
                            latest_date = df['post_date'].max()
                            logging.info(f"Original latest date: {latest_date}")
                            # Convert date to YYYY-MM-DD format
                            latest_date = latest_date.strftime('%Y-%m-%d')
                            logging.info(f"Normal mode: Latest post date in CSV is {latest_date}")
                        else:
                            logging.warning("No post_date column in CSV file")
                    else:
                        logging.warning("CSV file is empty")
                else:
                    logging.warning(f"CSV file does not exist: {csv_file}")
                
                # 2. Use since parameter to get new posts
                logging.info(f"Preparing to call get_user_posts with since parameter: {latest_date}")
                posts = self.client.get_user_posts(is_test_mode=False, since=latest_date)
                logging.info(f"Normal mode: Retrieved {len(posts)} new posts")
                return posts
            
        except Exception as e:
            logging.error(f"Error occurred while getting posts: {e}")
            return []
            
    def _save_posts(self, posts: List[Dict]):
        """Save post data to JSON file"""
        try:
            # Only update JSON file
            # Store the latest data from each request
            # For returning to Google Sheets
            # dump usage concept:
            # 1. dump is overwrite mode, clears original content each time
            # 2. Open file in "w" mode (write mode)
            # 3. indent=2 sets JSON indentation format for readability
            with open(os.path.join(self.data_dir, "posts.json"), "w") as f:
                json.dump(posts, f, indent=2)
            logging.info(f"Saved {len(posts)} posts to JSON file")
            
        except Exception as e:
            logging.error(f"Error occurred while saving posts: {e}")
            raise

    def update_csv_backup(self, posts: List[Dict]):
        """Update CSV backup after Google Sheets update"""
        try:
            csv_file = os.path.join(self.data_dir, "threads_data.csv")
            
            # Convert new data to DataFrame
            df_new = pd.DataFrame(posts)
            
            # Read existing CSV file
            if os.path.exists(csv_file):
                df_existing = pd.read_csv(csv_file)
                
                # Merge new and existing data
                df_combined = pd.concat([df_new, df_existing])
                
                # Remove duplicates (using post_id as unique key)
                df_combined = df_combined.drop_duplicates(subset=['post_id'], keep='first')
                
                # Sort by date
                df_combined['post_date'] = pd.to_datetime(df_combined['post_date'])
                df_combined = df_combined.sort_values('post_date', ascending=False)
            else:
                df_combined = df_new
            
            # Save updated complete data
            df_combined.to_csv(csv_file, index=False)
            logging.info(f"CSV backup updated, total {len(df_combined)} posts")
            
        except Exception as e:
            logging.error(f"Error occurred while updating CSV backup: {e}")
            raise

   