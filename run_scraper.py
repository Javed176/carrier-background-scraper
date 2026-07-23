import os
import time
import requests
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
CARRIER_TOKEN = os.environ.get("CARRIER_TOKEN", "3243d1219423e4ea")

print("Initializing script...")
if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Database configuration missing!")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_carrier_info(mc_number, token):
    url = "https://carrierchk.com/api/carrier"
    params = {
        "type": "mc",
        "value": str(mc_number).strip(),
        "token": token
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    try:
        print(f"Requesting API for MC-{mc_number}...")
        response = requests.get(url, params=params, headers=headers, timeout=5.0)
        print(f"API Response Code: {response.status_code}")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"API request failed: {e}")
    return None

def main():
    print("Starting background harvesting sequence...")
    start_mc = 1066434
    batch_size = 5  # Let's test with a small batch first to verify it flows through instantly
    
    for i in range(batch_size):
        current_mc = start_mc + i
        print(f"Processing index {i}: MC-{current_mc}")
        
        raw_data = get_carrier_info(current_mc, CARRIER_TOKEN)
        if not raw_data or "carrier" not in raw_data:
            print(f"No valid carrier data returned for MC-{current_mc}")
            continue
            
        c = raw_data.get("carrier", {})
        email = c.get("email_address")
        if not email:
            print(f"Skipping MC-{current_mc}: No email found")
            continue
            
        parsed = {
            "mc_number": f"MC-{current_mc}",
            "carrier_name": c.get("dba_name") or c.get("legal_name") or "N/A",
            "operating_status": "🟢 ACTIVE",
            "phone_number": c.get("phone") or "N/A",
            "email_address": email,
            "location": f"{c.get('phy_city', '')}, {c.get('phy_state', '')}".strip(", ")
        }
        
        try:
            print(f"Saving {email} to Supabase...")
            supabase.table("harvested_leads").upsert(parsed, on_conflict="mc_number").execute()
            print("Successfully saved!")
        except Exception as e:
            print(f"Supabase error: {e}")
            
        time.sleep(0.2)

    print("Batch run completed successfully.")

if __name__ == "__main__":
    main()
