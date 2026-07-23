import os
import cloudscraper
from supabase import create_client, Client

# Initialize Supabase connection
SUPABASE_URL = os.environ.get("SUPABASE_URL") or "YOUR_SUPABASE_URL"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or "YOUR_SUPABASE_KEY"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Use your carrierchk token
CARRIER_TOKEN = os.environ.get("CARRIER_TOKEN") or "3243d121943e4ea"

# Initialize cloudscraper
scraper = cloudscraper.create_scraper()

# Setup headers with your token
headers = {
    "Authorization": f"Bearer {CARRIER_TOKEN}",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

start_mc = 1066434
batch_size = 100

print(f"Starting background scraper for {batch_size} records from MC #{start_mc}...")

for i in range(batch_size):
    target_mc = start_mc + i
    
    try:
        url = f"https://carrierchk.com/api/carrier/{target_mc}"
        response = scraper.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            carrier_name = data.get("company_name", f"COMPANY-{target_mc}")
            operating_status = data.get("status", "ACTIVE")
            phone_number = data.get("phone", "")
            email_address = data.get("email", "")
            
            data_to_insert = {
                "mc_number": f"MC-{target_mc}",
                "carrier_name": carrier_name,
                "operating_status": operating_status,
                "phone_number": phone_number,
                "email_address": email_address
            }
            
            supabase.table("carriers").insert(data_to_insert).execute()
            print(f"Successfully saved: MC-{target_mc} - {carrier_name}")
        else:
            print(f"Failed to fetch MC {target_mc}: Status code {response.status_code}")
            
    except Exception as e:
        print(f"Error processing MC {target_mc}: {e}")

print("Batch scraper run completed successfully!")
