import streamlit as st
import cloudscraper
import os
import time
from supabase import create_client

st.title("Carrier Scraper Control Panel")
st.write("Enter your starting MC number below and click **Start Scraping** to begin harvesting leads automatically.")

start_mc = st.number_input("Starting MC Number", min_value=1, value=1066434, step=1)
max_records = st.number_input("Max records to fetch in this batch", min_value=1, value=500, step=1)

SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL"))
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY"))
carrier_token = st.secrets.get("CARRIER_TOKEN", "3243d121943e4ea")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

if st.button("Start Scraping", type="primary"):
    st.info(f"Starting scraper from MC #{start_mc} for {max_records} records...")
    
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    url = "https://carrierchk.com/api/carrier"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://carrierchk.com/",
    }

    progress_bar = st.progress(0)
    success_count = 0

    for i in range(max_records):
        current_mc_num = start_mc + i
        # API expects raw string number without prefix
        payload = {"mcNumber": str(current_mc_num), "token": carrier_token}
        
        while True:
            try:
                response = scraper.post(url, json=payload, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if data and "carrier" in data:
                        carrier_info = data["carrier"]
                        supabase.table("harvested_leads").insert(carrier_info).execute()
                        success_count += 1
                        st.success(f"Successfully saved MC #{current_mc_num}")
                    else:
                        st.info(f"MC #{current_mc_num} has no carrier data, skipping.")
                    break  
                elif response.status_code == 404:
                    st.warning(f"MC #{current_mc_num} not found (404), skipping to next...")
                    break  
                elif response.status_code == 429:
                    st.warning(f"Rate limited (429) on MC #{current_mc_num}. Cooling down for 10 seconds...")
                    time.sleep(10)  # Longer cooldown to let rate limit clear
                else:
                    st.warning(f"MC #{current_mc_num}: Server returned status {response.status_code}. Retrying...")
                    time.sleep(3)
            except Exception as e:
                st.error(f"Error on MC #{current_mc_num}: {e}. Retrying...")
                time.sleep(3)
        
        progress_bar.progress((i + 1) / max_records)
        time.sleep(3)  # Safe buffer between requests to prevent hitting 429s

    st.success(f"Scraping completed! Successfully harvested {success_count} records.")
