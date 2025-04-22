# Threads Data Analytics Tool

## Project Structure

```
threads-data-analytics/
├── src/
│   ├── threads_api/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── collector.py
│   ├── google_sheets/
│   │   ├── __init__.py
│   │   ├── base_sheets.py
│   │   └── exporter.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── crypto_utils.py
│   │   ├── verify_credentials.py
│   │   ├── generate_key.py
│   │   └── setup_credentials.py
│   └── main.py
├── data/
│   ├── posts.json
│   └── threads_data.csv
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

This tool is designed to collect post data from the Threads platform and export it to Google Sheets.

## Workflow Overview

1. **Encrypt Credentials**: Securely encrypt API and Google Sheets credentials using `CryptoManager`.
2. **Data Collection**: Use Threads API to collect post data.
3. **JSON Storage**: Store the latest fetched data in `posts.json` for Google Sheets upload.
4. **Google Sheets Export**: Export data to Google Sheets.
5. **CSV Backup**: Save a local CSV backup of the complete dataset from Google Sheets.

## Features

- Fetch post data from Threads API
- Supports three operation modes:
  - Test Mode: Fetch a small number of posts for testing
  - Force Mode: Fetch all posts
  - Normal Mode: Fetch only new posts
- Automatically export data to Google Sheets
- Secure credential management with encryption
- Local CSV backup
- Credential verification system

## Installation

1. Clone the repository:
```bash
git clone [repository_url]
cd threads_analytics_public
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set environment variables:
```bash
cp .env.example .env
```
Edit the `.env` file and fill in the necessary configuration information.

## First Time Setup

The following steps are only required when setting up the application for the first time:
These scripts will:
- Generate a secure encryption key
- Guide you through entering your credentials
- Encrypt and store your credentials securely
- Verify that all credentials are properly set up

1. Generate encryption key:
```bash
python src/utils/generate_key.py
```

2. Setup credentials:
```bash
python src/utils/setup_credentials.py
```

3. Verify credentials:
```bash
python src/utils/verify_credentials.py
```
The verification process checks:
- Threads API token:
  - Makes a test API call to verify token validity
  - Checks API response status code
- Google credentials:
  - Verifies service account credentials format
  - Tests Google Sheets API access
  - Validates spreadsheet ID access

## Usage

1. Test Mode (fetch posts with custom limit):
```bash
python src/main.py --mode test --limit <number>
```
- Fetches a specified number of posts for testing
- Use `--limit` parameter to set the number of posts (e.g., `--limit 5` for 5 posts)
- Useful for testing API connectivity and data format

2. Force Mode (fetch all posts):
```bash
python src/main.py --mode force
```
- Fetches all available posts from the Threads API
- No limit on the number of posts
- Useful for initial data collection or full data refresh

3. Normal Mode (fetch only new posts):
```bash
python src/main.py --mode normal
```
- Fetches only posts newer than the latest post in the CSV file
- Compares post dates to avoid duplicates
- Ideal for regular updates and incremental data collection

4. Threads API Only:
```bash
python src/main.py --threads-only
```
- Only fetches posts from Threads API
- Does not update Google Sheets
- Useful for testing API functionality

5. Google Sheets Only:
```bash
python src/main.py --sheets-only --json-file data/posts.json
```
- Only updates Google Sheets with existing JSON data
- Requires specifying the JSON file path
- Useful for manual data updates

## Google Sheets Columns

- post_id
- shortcode
- post_date
- content
- is_quote
- media_type
- permalink
- views
- likes
- replies
- reposts
- quotes
- shares
- engagement 
- engagement_rate 

## Notes

1. Ensure secure storage of encryption keys and credential files
2. Avoid exceeding Threads API request limits
3. Regularly back up local data files


## Required Tokens and Credentials

- **Threads API Access Token**: Required to access Threads API. Obtain it from your Threads developer account.
- **Google Service Account Credentials**: Required for Google Sheets API access. Follow the [Google Consule ](https://console.cloud.google.com/) to set up a service account and download the credentials JSON file.
- **Google Sheets Spreadsheet ID**: Required to specify the target spreadsheet for data export. You can find this ID in the URL of your Google Sheets document. For example, in the URL `https://docs.google.com/spreadsheets/d/1A2B3C4D5E6F7G8H9I0J/edit`, the ID is `1A2B3C4D5E6F7G8H9I0J`.

## API Documentation Links

- [Threads API Documentation](https://developers.facebook.com/docs/threads)
- [Google Sheets API Documentation](https://developers.google.com/sheets/api) 
