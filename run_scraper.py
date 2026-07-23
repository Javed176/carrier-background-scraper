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
    
    url = "https://carrierchk.com/api/carrier"
    params = {
        "type": "mc",
        "value": "123456",  # Update or loop through target MC numbers as needed
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
                logger.info(f"API Response Payload: {data}")
                process_and_store_data(data)
            except Exception as json_err:
                logger.warning(f"Response is not JSON. Content preview: {response.text[:200]}...")
        else:
            logger.error(f"Failed with status code: {response.status_code}")
            logger.error(f"Response body: {response.text}")

    except Exception as e:
        logger.error(f"An error occurred during scraping: {str(e)}")

def process_and_store_data(data):
    """Maps and pushes records safely to Supabase."""
    try:
        logger.info("Processing payload for Supabase insertion...")
        
        items = data if isinstance(data, list) else [data]
        
        if not items or not items[0]:
            logger.info("No valid records found to insert.")
            return

        for item in items:
            # Explicitly map JSON fields to your Supabase columns
            record = {
                "mc_number": str(item.get("mc_number") or item.get("mc") or "123456"),
                "carrier_name": item.get("carrier_name") or item.get("name") or "Unknown Carrier",
                "operating_status": item.get("operating_status") or item.get("status") or "Active"
            }
            
            result = supabase.table("harvested_leads").upsert(record).execute()
            logger.info(f"Inserted record: {record}")
            
        logger.info(f"Successfully processed and stored {len(items)} records.")
        
    except Exception as e:
        logger.error(f"Database insertion error: {str(e)}")

if __name__ == "__main__":
    run_scraper()
