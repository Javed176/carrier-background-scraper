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

def get_target_endpoint():
    """Define your target URL or endpoint here."""
    # Replace or configure with your actual CarrierChk API or target URL
    return "https://carrierchk.com/api/search" # Update as per your active route

def run_scraper():
    logger.info("Initializing cloudscraper session to bypass bot protection...")
    
    # Create a cloudscraper instance to handle Cloudflare challenges
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    # Optional: If you use session tokens or authorization headers, include them here
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://carrierchk.com/",
    }

    url = get_target_endpoint()
    max_retries = 3
    retry_delay = 5

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Attempt {attempt} of {max_retries}: Fetching data from {url}")
            
            # Make the request using cloudscraper instead of standard requests
            response = scraper.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                logger.info("Successfully fetched data from target.")
                data = response.json()
                
                # Process and store data in Supabase
                process_and_store_data(data)
                return
                
            elif response.status_code == 403 or response.status_code == 429:
                logger.warning(f"Received status {response.status_code}. Possible rate limit or bot block.")
                if attempt < max_retries:
                    logger.info(f"Waiting {retry_delay} seconds before retrying...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("Max retries reached. Request blocked by target server.")
            else:
                logger.error(f"Unexpected status code: {response.status_code} - {response.text}")
                break

        except Exception as e:
            logger.error(f"An error occurred during scraping: {str(e)}")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                logger.error("Failed to complete scraping execution due to persistent errors.")

def process_and_store_data(data):
    """Processes scraped payload and pushes records safely to Supabase."""
    try:
        # Example parsing/insertion logic matching your pipeline
        logger.info("Processing payload for Supabase insertion...")
        
        # Ensure data is structured correctly as a list of records
        records = data if isinstance(data, list) else data.get("results", [])
        
        if not records:
            logger.info("No new records found to insert.")
            return

        for record in records:
            # Upsert or insert logic into your Supabase table
            supabase.table("carrier_leads").upsert(record).execute()
            
        logger.info(f"Successfully processed and stored {len(records)} records.")
        
    except Exception as e:
        logger.error(f"Database insertion error: {str(e)}")

if __name__ == "__main__":
    run_scraper()
