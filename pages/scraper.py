import streamlit as st
import cloudscraper
import os
from supabase import create_client

st.title("Carrier Scraper Control Panel")
st.write("Enter your starting MC number below and click **Start Scraping** to begin harvesting leads automatically.")

start_mc = st.number_input("Starting MC Number", min_value=1, value=1066434, step=1)
# Changed from a slider to a number input allowing you to type custom limits
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
        current_mc = start_mc + i
        payload = {"mcNumber": str(current_mc), "token": carrier_token}
        
        try:
            response = scraper.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data and "carrier" in data:
                    carrier_info = data["carrier"]
                    # Insert into Supabase
                    insert_res = supabase.table("harvested_leads").insert(carrier_info).execute()
                    success_count += 1
            else:
                st.warning(f"Skipping MC {current_mc}: Server returned status {response.status_code}")
        except Exception as e:
            st.error(f"Error on MC {current_mc}: {e}")
        
        progress_bar.progress((i + 1) / max_records)

    st.success(f"Scraping completed! Successfully harvested {success_count} records.")
