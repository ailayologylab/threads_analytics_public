"""
Main Program Entry Point
"""
import os
import json
import logging
import argparse
from dotenv import load_dotenv
from threads_api.collector import ThreadsDataCollector
from datetime import datetime

def main():
    # Parse command line arguments
    #threads only   
    parser = argparse.ArgumentParser(description="Threads Data Collection and Export Tool")
    parser.add_argument("--mode", choices=["test", "force", "normal"], default="normal",
                      help="Run mode: test(testing), force(force update), normal(update new posts only)")
    parser.add_argument("--limit", type=int, help="Post quantity limit in test mode")
    parser.add_argument("--threads-only", action="store_true", 
                      help="Execute Threads API process only, skip Google Sheets export")
    
    #google sheets only
    parser.add_argument("--sheets-only", action="store_true",
                      help="Execute Google Sheets data import only, skip Threads API process")
    parser.add_argument("--json-file", type=str,
                      help="When using --sheets-only, specify the JSON file path to import")
    parser.add_argument("--debug", action="store_true",
                      help="Enable debug mode, show detailed logs")
    args = parser.parse_args()
    
    # Set log level and format
    logging_level = logging.DEBUG if args.debug else logging.INFO
    
    # Set log format
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Set console handler - show all logs
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    console_handler.setLevel(logging_level)  # Set level based on debug parameter
    
    # Set root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging_level)
    root_logger.addHandler(console_handler)
    
    # Custom error handler, create file only when error occurs
    class ErrorFileHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.has_error = False
            self.log_file = None
            
        def emit(self, record):
            if record.levelno >= logging.ERROR:
                if not self.has_error:
                    self.has_error = True
                    # Ensure logs directory exists
                    os.makedirs('logs', exist_ok=True)
                    # Create file handler
                    self.log_file = os.path.join('logs', f'threads_data_{datetime.now().strftime("%Y%m%d")}.log')
                    file_handler = logging.FileHandler(self.log_file, mode='w', encoding='utf-8')
                    file_handler.setFormatter(logging.Formatter(log_format, date_format))
                    file_handler.setLevel(logging.ERROR)
                    root_logger.addHandler(file_handler)
                    logging.info(f"Error detected, log file created: {self.log_file}")
    
    # Add custom error handler
    error_handler = ErrorFileHandler()
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)
    
    logging.info("Starting Threads data collection...")
    
    # Load environment variables
    load_dotenv()
    
    # Check parameter conflicts
    if args.threads_only and args.sheets_only:
        logging.error("Error: --threads-only and --sheets-only cannot be used together")
        return
        
    if args.sheets_only and not args.json_file:
        logging.error("Error: --json-file must be specified when using --sheets-only")
        return
    
    # Execute Google Sheets data import only
    if args.sheets_only:
        try:
            # Read JSON file
            logging.info(f"Starting to read JSON file: {args.json_file}")
            with open(args.json_file, 'r', encoding='utf-8') as f:
                posts = json.load(f)
            
            from google_sheets.exporter import GoogleSheetsExporter
            
            logging.info(f"Starting to import data from {args.json_file} to Google Sheets...")
            exporter = GoogleSheetsExporter()
            if exporter.export_posts(posts):
                logging.info("✓ Data export completed")
            else:
                logging.error("✗ Data export failed")
            return
            
        except FileNotFoundError:
            logging.error(f"✗ Specified JSON file not found: {args.json_file}")
            return
        except json.JSONDecodeError:
            logging.error(f"✗ Invalid JSON file format: {args.json_file}")
            return
        except Exception as e:
            logging.error(f"✗ Error processing JSON file: {str(e)}")
            if args.debug:
                logging.exception("Detailed error information:")
            return
    
    # Initialize collector - no user_id needed
    collector = ThreadsDataCollector()
    
    # Collect post data
    print("Starting to collect Threads post data...")
    posts = collector.collect_posts(mode=args.mode, limit=args.limit)
    print(f"Successfully collected {len(posts)} posts")
    
    # If threads-only is specified, skip Google Sheets export
    if not args.threads_only:
        from google_sheets.exporter import GoogleSheetsExporter
        
        try:
            logging.info("Starting to export data to Google Sheets...")
            exporter = GoogleSheetsExporter()
            if exporter.export_posts(posts):
                logging.info("✓ Data export completed")
            else:
                logging.error("✗ Data export failed")
        except Exception as e:
            logging.error(f"✗ Error occurred during Google Sheets export: {str(e)}")
            if args.debug:
                logging.exception("Detailed error information:")
    else:
        print("Skipped Google Sheets export step")

if __name__ == "__main__":
    main() 