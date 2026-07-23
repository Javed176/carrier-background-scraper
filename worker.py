import os
import time
import requests
from supabase import create_client, Client

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://vhudqthehrjttbcqluat.supabase.co"
)
SUPABASE_KEY = os.environ.get(
    "SUPABASE_KEY", "sb_publishable_eHNwQ5RLe8oi1uZ7If3ODg_aZR66HJ7"
)
CARRIER_TOKEN = os.environ.get("CARRIER_TOKEN", "3243d1219423e4ea")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_carrier_info(mc_number, token, retries=4):
  url = "https://carrierchk.com/api/carrier"
  params = {"type": "mc", "value": str(mc_number).strip(), "token": token}
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      ),
      "Accept": "application/json",
  }

  for attempt in range(retries):
    try:
      response = requests.get(
          url, params=params, headers=headers, timeout=(4.0, 8.0)
      )
      if response.status_code == 200:
        return response.json()
      elif response.status_code == 429:
        time.sleep(1.0 * (attempt + 1))
        continue
      time.sleep(0.5 * (attempt + 1))
    except requests.exceptions.RequestException:
      time.sleep(1.0 * (attempt + 1))
  return None


def main_loop():
  print("🚀 24/7 Optimized Carrier Background Worker Started...")
  while True:
    try:
      # 1. Check crawler state from database
      res = supabase.table("crawler_state").select("*").eq("id", 1).execute()
      if not res.data:
        time.sleep(3)
        continue

      state = res.data[0]
      is_running = state["is_running"]
      current_mc = int(state["current_mc"])

      if not is_running:
        time.sleep(2)
        continue

      # 2. Fetch global speed config
      cfg_res = supabase.table("system_config").select("*").execute().data
      delay_ms = 100.0
      for row in cfg_res:
        if row["key"] == "throttle_delay_ms":
          delay_ms = float(row["value"])

      print(f"Harvester processing MC-{current_mc}...")
      data = get_carrier_info(str(current_mc), CARRIER_TOKEN)

      if data and isinstance(data, dict):
        carrier_info = data.get("carrier", data)

        carrier_name = carrier_info.get(
            "company_name",
            carrier_info.get("name", f"CARRIER-{current_mc}"),
        )
        operating_status = carrier_info.get(
            "status", carrier_info.get("operating_status", "ACTIVE")
        )
        phone_number = carrier_info.get(
            "phone", carrier_info.get("phone_number", "")
        )
        email_address = carrier_info.get(
            "email", carrier_info.get("email_address", "")
        )

        data_to_insert = {
            "mc_number": f"MC-{current_mc}",
            "carrier_name": carrier_name,
            "operating_status": operating_status,
            "phone_number": phone_number,
            "email_address": email_address,
        }

        # Save directly to the harvested_leads table
        supabase.table("harvested_leads").upsert(
            data_to_insert, on_conflict="mc_number"
        ).execute()
        print(f"Successfully saved: MC-{current_mc} - {carrier_name}")

      # 3. Increment the MC index in Supabase
      next_mc = current_mc + 1
      supabase.table("crawler_state").update({"current_mc": next_mc}).eq(
          "id", 1
      ).execute()

      # 4. Respect throttle delay
      time.sleep(max(0.1, delay_ms / 1000.0))

    except Exception as e:
      print(f"Worker loop exception: {e}")
      time.sleep(3)


if __name__ == "__main__":
  main_loop()
