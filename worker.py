import time
import requests
from supabase import create_client

SUPABASE_URL = "https://vhudqthehrjttbcqluat.supabase.co"
SUPABASE_KEY = "sb_publishable_eHNwQ5RLe8oi1uZ7If3ODg_aZR66HJ7"
CARRIER_TOKEN = "3243d1219423e4ea"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_carrier_info(mc_number, token):
  url = f"https://carrierchk.com/api/carrier?type=mc&value={mc_number}&token={token}"
  headers = {"User-Agent": "Mozilla/5.0"}
  try:
    response = requests.get(url, headers=headers, timeout=(5.0, 10.0))
    if response.status_code == 200:
      return response.json()
  except Exception as e:
    print(f"API request error for MC-{mc_number}: {e}")
  return None


def main_loop():
  print("🛠️ 24/7 Carrier Background Worker Started...")

  while True:
    current_mc = 1800000
    is_running = False

    try:
      # 1. Fetch live state from Supabase
      state_res = (
          supabase.table("crawler_state").select("*").eq("id", 1).execute()
      )
      if state_res.data:
        current_mc = int(state_res.data[0]["current_mc"])
        is_running = state_res.data[0]["is_running"]

      # 2. If paused from Streamlit, wait and re-check
      if not is_running:
        time.sleep(3)
        continue

      # 3. Fetch system throttle delay
      delay_ms = 250.0
      try:
        cfg_res = supabase.table("system_config").select("*").execute()
        if cfg_res.data:
          for row in cfg_res.data:
            if row["key"] == "throttle_delay_ms":
              delay_ms = float(row["value"])
      except Exception:
        pass

      print(f"Harvester processing MC-{current_mc}...")
      carrier_data = get_carrier_info(str(current_mc), CARRIER_TOKEN)

      # 4. Save to database if data exists
      if carrier_data:
        try:
          supabase.table("harvested_leads").insert({
              "mc_number": str(current_mc),
              "company_name": carrier_data.get("company_name", "N/A"),
              "operating_status": carrier_data.get(
                  "operating_status", "ACTIVE"
              ),
              "email_address": carrier_data.get("email", None),
          }).execute()
        except Exception:
          pass

      # 5. Move counter forward in Supabase
      next_mc = current_mc + 1
      supabase.table("crawler_state").update({"current_mc": next_mc}).eq(
          "id", 1
      ).execute()

      # 6. Respect speed throttle
      time.sleep(max(0.35, delay_ms / 1000.0))

    except Exception as e:
      print(f"Worker loop exception: {e}")
      # Force increment past error so it never gets permanently stuck
      try:
        supabase.table("crawler_state").update(
            {"current_mc": current_mc + 1}
        ).eq("id", 1).execute()
      except Exception:
        pass
      time.sleep(2)


if __name__ == "__main__":
  main_loop()
