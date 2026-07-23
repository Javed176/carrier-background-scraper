import os
import time
import requests
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vhudqthehrjttbcqluat.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_eHNwQ5RLe8oi1uZ7If3ODg_aZR66HJ7")
CARRIER_TOKEN = os.environ.get("CARRIER_TOKEN", "3243d1219423e4ea")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_carrier_info(mc_number, token, retries=6):
    url = "https://carrierchk.com/api/carrier"
    params = {"type": "mc", "value": str(mc_number).strip(), "token": token}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    for attempt in range(retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=(5.0, 10.0))
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

def main_loop():
    print("🚀 24/7 Carrier Background Worker Started...")
    while True:
        try:
            # 1. Check crawler state from database
            res = supabase.table("crawler_state").select("*").eq("id", 1).execute()
            if not res.data:
                time.sleep(5)
                continue
            
            state = res.data[0]
            is_running = state["is_running"]
            current_mc = int(state["current_mc"])

            if not is_running:
                time.sleep(3)
                continue

            # 2. Fetch global speed config
            cfg_res = supabase.table("system_config").select("*").execute().data
            delay_ms = 250.0
            for row in cfg_res:
                if row["key"] == "throttle_delay_ms":
                    delay_ms = float(row["value"])

            print(f"Harvester processing MC-{current_mc}...")
            raw_info = get_carrier_info(str(current_mc), CARRIER_TOKEN)

            # 3. Increment the MC index in Supabase
            next_mc = current_mc + 1
            supabase.table("crawler_state").update({
                "current_mc": next_mc
            }).eq("id", 1).execute()

            # 4. Respect throttle delay
            time.sleep(max(0.35, delay_ms / 1000.0))

        except Exception as e:
            print(f"Worker loop exception: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main_loop()
