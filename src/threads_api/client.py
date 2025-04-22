"""
Threads API Client
Handles communication with Threads API
"""
import os
import json
import time
import logging
from typing import Dict, List, Optional, Union, Tuple
import requests
from dotenv import load_dotenv
from utils.crypto_utils import CryptoManager
from concurrent.futures import ThreadPoolExecutor

class ThreadsAPIClient:
    def __init__(self):
        load_dotenv()
        self.base_url = "https://graph.threads.net/v1.0"
        
        # Read encrypted file path from environment variables
        credentials_path = os.getenv("CREDENTIALS_PATH")
        if not credentials_path:
            raise ValueError("CREDENTIALS_PATH environment variable not set")
            
        # Use CryptoManager to decrypt and get token
        try:
            crypto_manager = CryptoManager.from_env()
            # Name can be obtained from the creds dictionary in verify_credentials.py
            token = crypto_manager.get_single_credential("threads_token")
            if not token:
                raise ValueError("Unable to obtain access token")
                
            # Set headers
            self._headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            # Clear sensitive data
            del token
            
        except Exception as e:
            # Ensure sensitive data is cleaned up even when error occurs
            if 'token' in locals():
                del token
            if 'crypto_manager' in locals():
                del crypto_manager
            logging.error("Error occurred during initialization")
            raise
            
        # Basic settings
        self.batch_size = 100  # API batch size
        self.insights_batch_size = 10  # Insights API batch size
        self.api_delay = 0.5  # API request interval
        
        # Basic post fields
        self.basic_fields = [
            'id', 'shortcode', 'timestamp', 
            'text', 'is_quote_post', 'media_type', 'permalink'
        ]
        
        self.metrics = ['views', 'likes', 'replies', 'reposts', 'quotes', 'shares']
        
        # Cache related settings
        self._insights_cache = {}  # Cache dictionary
        self.cache_duration = 3600  # Cache duration (seconds)
        
    def __del__(self):
        """Ensure cleanup of sensitive information"""
        if hasattr(self, '_headers'):
            self._headers['Authorization'] = None
            self._headers['Content-Type'] = None
            del self._headers
            
    def _make_api_request(self, endpoint: str, params: Dict) -> requests.Response:
        """Unified API request method, handles rate limiting and errors"""
        try:
            logging.info(f"Preparing to send API request to endpoint: {endpoint}")
            logging.info(f"Request parameters: {params}")
            logging.info(f"Request URL: {self.base_url}/{endpoint}")
            
            response = requests.get(
                f"{self.base_url}/{endpoint}",
                headers=self._headers,
                params=params
            )
            
            logging.info(f"API response status code: {response.status_code}")
            if response.status_code != 200:
                logging.error(f"API response content: {response.text}")
                
            response.raise_for_status()
            logging.info("API request successful, waiting for rate limit...")
            time.sleep(self.api_delay)  # Basic rate limiting
            logging.info("Rate limit wait completed")
            return response
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {e}")
            raise
        
    def get_user_posts(self, limit: int = 100, is_test_mode: bool = False, since: Optional[str] = None) -> List[Dict]:
        """
        Get posts of the currently authorized user, supports pagination
        
        Args:
            limit: Post quantity limit, can be used to test with fewer posts
            is_test_mode: Whether in test mode, determines if post quantity should be limited
            since: Start date, format is ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)
            
        Returns:
            List of posts
        """
        all_posts = []
        next_page = 'me/threads'
        
        logging.info(f"Starting to fetch posts, limit: {limit}, test mode: {is_test_mode}, start date: {since}")
        
        while next_page:
            try:
                if is_test_mode and len(all_posts) >= limit:
                    break
                    
                current_batch = self.batch_size
                if is_test_mode:
                    remaining = limit - len(all_posts)
                    current_batch = min(remaining, self.batch_size)
                
                # Prepare API parameters
                params = {
                    "fields": ",".join(self.basic_fields),
                    "limit": current_batch
                }
                
                # Add since parameter to request if provided
                if since:
                    params["since"] = since
                
                logging.info(f"Request endpoint: {next_page}, parameters: {params}")
                response = self._make_api_request(
                    endpoint=next_page,
                    params=params
                )
                
                data = response.json()
                posts = data.get("data", [])
                logging.info(f"Retrieved {len(posts)} posts in this request")
                all_posts.extend(posts)
                
                next_page = data.get("paging", {}).get("next")
                if next_page:
                    next_page = next_page.split(self.base_url + "/")[-1]
                    logging.info(f"Found next page: {next_page}")
                    
            except Exception as e:
                logging.error(f"Error occurred while fetching posts: {e}")
                break
                
        logging.info(f"Total posts retrieved: {len(all_posts)}")
        return all_posts
            
    def _should_update_cache(self, post_id: str) -> bool:
        """Check if cache needs to be updated"""
        if post_id not in self._insights_cache:
            return True
        return time.time() - self._insights_cache[post_id]['timestamp'] > self.cache_duration

    def _update_cache(self, post_id: str, insights: Dict) -> None:
        """Update cache"""
        self._insights_cache[post_id] = {
            'data': insights,
            'timestamp': time.time()
        }

    def _process_single_insight(self, post_id: str) -> Tuple[str, Dict]:
        """Process insights for a single post"""
        try:
            endpoint = f"{post_id}/insights"
            params = {"metric": ",".join(self.metrics)}
            response = self._make_api_request(endpoint, params)
            data = response.json()
            
            if data and 'data' in data:
                insights = {metric: 0 for metric in self.metrics}
                for metric in data['data']:
                    if metric.get('values') and metric['values']:
                        insights[metric['name']] = metric['values'][0].get('value', 0)
                    elif metric.get('total_value'):
                        insights[metric['name']] = metric['total_value'].get('value', 0)
            else:
                insights = {metric: 0 for metric in self.metrics}
                
            return post_id, insights
            
        except Exception as e:
            logging.error(f"Error processing post {post_id}: {e}")
            return post_id, {metric: 0 for metric in self.metrics}

    def get_post_insights(self, post_ids: Union[str, List[str]], use_cache: bool = True) -> Dict[str, Dict]:
        """
        Get post insights data using batch parallel processing
        
        Args:
            post_ids: Single post ID or list of post IDs
            use_cache: Whether to use cache, defaults to True
            
        Returns:
            Dict[str, Dict]: {post_id: insights_data}
        """
        # Standardize input format
        if isinstance(post_ids, str):
            post_ids = [post_ids]
        
        insights_map = {}
        total_posts = len(post_ids)
        processed_posts = 0
        
        # Check cache in advance
        if use_cache:
            cached_posts = {post_id: self._insights_cache[post_id]['data'] for post_id in post_ids if post_id in self._insights_cache}
            insights_map.update(cached_posts)
            post_ids = [post_id for post_id in post_ids if post_id not in cached_posts]
            processed_posts += len(cached_posts)
        
        # Process uncached posts in batches
        for i in range(0, len(post_ids), self.insights_batch_size):
            batch = post_ids[i:i + self.insights_batch_size]
            logging.info(f"Starting to process batch {i//self.insights_batch_size + 1}, containing {len(batch)} posts")
            
            # Use ThreadPoolExecutor for parallel processing of this batch
            with ThreadPoolExecutor(max_workers=self.insights_batch_size) as executor:
                # Submit all tasks
                future_to_post = {
                    executor.submit(self._process_single_insight, post_id): post_id 
                    for post_id in batch
                }
                
                # Collect results
                for future in future_to_post:
                    try:
                        post_id, insights = future.result()
                        insights_map[post_id] = insights
                        
                        # Update cache
                        if use_cache:
                            self._update_cache(post_id, insights)
                            
                        processed_posts += 1
                        logging.info(f"Processing progress: {processed_posts}/{total_posts} posts")
                        
                    except Exception as e:
                        post_id = future_to_post[future]
                        logging.error(f"Error processing post {post_id}: {e}")
                        insights_map[post_id] = {metric: 0 for metric in self.metrics}
                        processed_posts += 1
            
            logging.info(f"Completed processing batch {i//self.insights_batch_size + 1}")
        
        logging.info(f"Post insights data retrieval completed, processed {processed_posts}/{total_posts} posts")
        return insights_map
            
   