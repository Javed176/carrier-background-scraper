import os
import time
import requests
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
CARRIER_TOKEN = os.environ.get("CARRIER_TOKEN", "3243d1219423e4ea")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("🔑 Database configuration missing!")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_carrier_info(mc_number, token, retries=6):
    url = "https://carrierchk.com/api/carrier"
    params = {
        "type": "mc",
        "value": str(mc_number).strip(),
        "token": token
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict) and ("carrier" in data or "error" in data):
                    return data
            elif response.status_code == 429:
                time.sleep(2.0 * (attempt + 1))
                continue
            time.sleep(1.0 * (attempt + 1))
        except requests.exceptions.RequestException:
            time.sleep(1.5 * (attempt + 1))
    return "API_ERROR"

def parse_carrier_data(mc_number, raw_data):
    if raw_data == "API_ERROR" or not raw_data or not isinstance(raw_data, dict) or "carrier" not in raw_data or not raw_data["carrier"]:
        return None
    
    c = raw_data.get("carrier", {})
    status_code = str(c.get("status_code", "")).upper()
    allowed = str(c.get("allowed_to_operate", "")).upper()
    
    is_active = (status_code == "A" or allowed == "Y")
    status = "🟢 ACTIVE" if is_active else "🔴 INACTIVE"
    
    phone = c.get("phone") or c.get("cell_phone") or "N/A"
    email = c.get("email_address")
    if not email or str(email).strip() == "":
        return None
        
    city = c.get("phy_city", "").strip()
    state = c.get("phy_state", "").strip()
    location = f"{city}, {state}".strip(", ") if city or state else "N/A"
    
    return {
        "mc_number": f"MC-{mc_number}",
        "carrier_name": c.get("dba_name") or c.get("legal_name") or "N/A",
        "operating_status": status,
        "phone_number": phone,
        "email_address": email,
        "location": location
    }

def main():
    print("Starting background harvesting sequence...")
    start_mc = 1066434
    batch_size = 50
    
    for i in range(batch_size):
        current_mc = start_mc + i
        print(f"Checking MC-{current_mc}...")
        
        raw_data = get_carrier_info(current_mc, CARRIER_TOKEN)
        parsed = parse_carrier_data(current_mc, raw_data)
        
        if parsed:
            try:
                supabase.table("harvested_leads").upsert(parsed, on_conflict="mc_number").execute()
                print(f"Successfully saved lead: {parsed['email_address']}")
            except Exception as e:
                print(f"Database insert error: {e}")
                
        time.sleep(0.3)

    print("Batch run completed successfully.")

if __name__ == "__main__":
    main()
