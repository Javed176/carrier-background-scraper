import streamlit as st
import cloudscraper
import os
from supabase import create_client

st.title("Carrier Scraper Control Panel")
st.write("Enter your starting MC number below and click **Start Scraping** to begin harvesting leads automatically.")

start_mc = st.number_input("Starting MC Number", min_value=1, value=123450, step=1)
max_records = st.slider("Max records to fetch in this batch", min_value=1, max_value=100, value=10)

SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL"))
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY"))
carrier_token = st.secrets.get("CARRIER_TOKEN", "3243d1219423e4ea")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

if st.button("Start Scraping", type="primary"):
    st.info(f"Starting scraper from MC #{start_mc}...")
    
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    url = "https://carrierchk.com/api/carrier"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://carrierchk.com/",
    }

    progress_bar = st.progress(0)
    status_text = st.empty()
    
    current_mc = int(start_mc)
    success_count = 0

    for i in range(max_records):
        params = {"type": "mc", "value": str(current_mc), "token": carrier_token}
        
        try:
            status_text.text(f"Querying MC #{current_mc}...")
            response = scraper.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                carrier_info = data.get("carrier")
                
                if carrier_info and carrier_info.get("legal_name"):
                    city = carrier_info.get("phy_city", "")
                    state = carrier_info.get("phy_state", "")
                    location_str = f"{city}, {state}".strip(", ")

                    record = {
                        "mc_number": str(current_mc),
                        "carrier_name": carrier_info.get("legal_name", "Unknown Carrier"),
                        "operating_status": carrier_info.get("status_code", "Active"),
                        "phone_number": carrier_info.get("phone"),
                        "email_address": carrier_info.get("email_address"),
                        "location": location_str
                    }
                    
                    supabase.table("harvested_leads").upsert(record, on_conflict="mc_number").execute()
                    success_count += 1
                    st.success(f"Saved: MC {current_mc} - {carrier_info.get('legal_name')}")
                else:
                    st.warning(f"No active record for MC {current_mc}")
            
        except Exception as e:
            st.error(f"Error on MC {current_mc}: {str(e)}")
            
        progress_bar.progress((i + 1) / max_records)
        current_mc += 1

    st.success(f"Batch complete! Successfully harvested and saved {success_count} leads.")
