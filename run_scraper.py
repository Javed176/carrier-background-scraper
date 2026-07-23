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

def run_continuous_scraper():
    logger.info("Initializing cloudscraper session...")
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    url = "https://carrierchk.com/api/carrier"
    token = "3243d1219423e4ea" # Or use os.environ.get("CARRIER_TOKEN")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://carrierchk.com/",
    }

    # Starting MC number (you can adjust this starting point)
    start_mc = 123450 
    max_consecutive_misses = 10  # Stops if it hits 10 empty numbers in a row
    consecutive_misses = 0

    logger.info(f"Starting continuous scraping loop from MC: {start_mc}")

    current_mc = start_mc
    while True:
        params = {
            "type": "mc",
            "value": str(current_mc),
            "token": token
        }
        
        try:
            logger.info(f"Querying MC #{current_mc}...")
            response = scraper.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                carrier_info = data.get("carrier")
                
                if carrier_info and carrier_info.get("legal_name"):
                    # Valid carrier found, save to Supabase
                    record = {
                        "mc_number": str(current_mc),
                        "carrier_name": carrier_info.get("legal_name", "Unknown Carrier"),
                        "operating_status": carrier_info.get("status_code", "Active")
                    }
                    supabase.table("harvested_leads").upsert(record).execute()
                    logger.info(f"Saved: MC {current_mc} - {carrier_info.get('legal_name')}")
                    consecutive_misses = 0 # Reset miss counter
                else:
                    logger.info(f"No active record found for MC {current_mc}")
                    consecutive_misses += 1
            else:
                logger.warning(f"API returned status code {response.status_code} for MC {current_mc}")
                consecutive_misses += 1

            # Safety break if it runs through too many missing/invalid numbers consecutively
            if consecutive_misses >= max_consecutive_misses:
                logger.info(f"Reached {max_consecutive_misses} empty results in a row. Pausing loop.")
                break

        except Exception as e:
            logger.error(f"Error querying MC {current_mc}: {str(e)}")
        
        # Increment to the next MC number
        current_mc += 1
        
        # Short polite delay between requests to avoid triggering rate limits
        time.sleep(1.5)

if __name__ == "__main__":
    run_continuous_scraper()
