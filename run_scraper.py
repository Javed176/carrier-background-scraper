import os
import time
import logging
import cloudscraper
from supabase import create_client, Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Supabase Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("Supabase credentials missing from environment variables.")
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def run_scraper():
    logger.info("Initializing cloudscraper session...")
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    # Correct API endpoint and parameters
    url = "https://carrierchk.com/api/carrier"
    
    # Example MC number to query (you can loop through a list of numbers or fetch dynamically)
    params = {
        "type": "mc",
        "value": "123456",  # Replace or expand with your target MC numbers
        "token": "3243d1219423e4ea"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://carrierchk.com/",
    }

    try:
        logger.info(f"Querying carrier data from {url}")
        response = scraper.get(url, params=params, headers=headers, timeout=30)
        
        logger.info(f"Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                process_and_store_data(data)
            except Exception as json_err:
                logger.warning(f"Response is not JSON. Content preview: {response.text[:200]}...")
        else:
            logger.error(f"Failed with status code: {response.status_code}")
            logger.error(f"Response body: {response.text}")

    except Exception as e:
        logger.error(f"An error occurred during scraping: {str(e)}")

def process_and_store_data(data):
    """Processes scraped payload and pushes records safely to Supabase."""
    try:
        logger.info("Processing payload for Supabase insertion...")
        
        # Format records into a list if it's a single dictionary payload
        records = data if isinstance(data, list) else [data]
        
        if not records or not records[0]:
            logger.info("No valid records found to insert.")
            return

        for record in records:
            supabase.table("harvested_leads").upsert(record).execute()
            
        logger.info(f"Successfully processed and stored {len(records)} records.")
        
    except Exception as e:
        logger.error(f"Database insertion error: {str(e)}")

if __name__ == "__main__":
    run_scraper()
