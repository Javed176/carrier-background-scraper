import streamlit as st
import cloudscraper
import os
import time
import pandas as pd
from supabase import create_client

st.title("Carrier Scraper Control Panel")
st.write("Enter your starting MC number below and click **Start Scraping** to begin harvesting leads automatically.")

start_mc = st.number_input("Starting MC Number", min_value=1, value=1066434, step=1)
max_records = st.number_input("Max records to fetch in this batch", min_value=1, value=100, step=1)

SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL"))
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY"))
carrier_token = st.secrets.get("CARRIER_TOKEN", "3243d1219423e4ea")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

if st.button("Start Scraping", type="primary"):
    st.info(f"Starting scraper from MC #{start_mc} for {max_records} records...")
    
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    url = "https://carrierchk.com/api/carrier"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://carrierchk.com/",
    }

    progress_bar = st.progress(0)
    success_count = 0
    current_mc = start_mc

    for i in range(max_records):
        formatted_mc = f"MC-{current_mc}"
        params = {
            "type": "mc",
            "value": str(current_mc),
            "token": carrier_token
        }
        
        while True:
            try:
                response = scraper.get(url, params=params, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    carrier_info = data.get("carrier")
                    
                    if carrier_info and carrier_info.get("legal_name"):
                        city = carrier_info.get("phy_city", "")
                        state = carrier_info.get("phy_state", "")
                        location_str = f"{city}, {state}".strip(", ")

                        raw_status = str(carrier_info.get("status_code", "A")).upper()
                        if raw_status == "A" or "ACTIVE" in raw_status:
                            status_str = "🟢 ACTIVE"
                        else:
                            status_str = f"🔴 {raw_status}"

                        record = {
                            "mc_number": formatted_mc,
                            "carrier_name": carrier_info.get("legal_name", "Unknown Carrier"),
                            "operating_status": status_str,
                            "phone_number": carrier_info.get("phone"),
                            "email_address": carrier_info.get("email_address"),
                            "location": location_str
                        }
                        
                        supabase.table("harvested_leads").upsert(record, on_conflict="mc_number").execute()
                        success_count += 1
                        st.success(f"Saved: {formatted_mc} - {carrier_info.get('legal_name')}")
                    else:
                        st.info(f"No active record found for {formatted_mc}")
                    break  
                    
                elif response.status_code == 429:
                    st.warning(f"Rate limited (429) on {formatted_mc}. Waiting 10s for API to clear...")
                    time.sleep(10)  
                else:
                    st.warning(f"API returned status {response.status_code} for {formatted_mc}. Retrying in 5s...")
                    time.sleep(5)
                    
            except Exception as e:
                st.error(f"Error querying {formatted_mc}: {str(e)}. Retrying in 5s...")
                time.sleep(5)
        
        progress_bar.progress((i + 1) / max_records)
        current_mc += 1
        time.sleep(3)

    st.success(f"Batch completed! Successfully harvested {success_count} records.")

st.markdown("---")

# Navigation Tabs inside the App View
tab1, tab2 = st.tabs(["📋 Complete Master Log", "🎯 Verified Leads (Active Only)"])

with tab1:
    st.subheader("Master History Sheet")
    try:
        response = supabase.table("harvested_leads").select("*").execute()
        data = response.data
        
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
            
            col1, col2 = st.columns(2)
            with col1:
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export Master Sheet to CSV",
                    data=csv_data,
                    file_name="master_carriers.csv",
                    mime="text/csv",
                    type="primary",
                    key="download_master"
                )
            with col2:
                if st.button("🗑️ Clear All Stored Data", type="secondary", key="clear_db"):
                    supabase.table("harvested_leads").delete().neq("mc_number", "NONE").execute()
                    st.success("Database cleared successfully!")
                    st.rerun()
        else:
            st.info("No records found in the database yet.")
    except Exception as e:
        st.error(f"Could not load data: {e}")

with tab2:
    st.subheader("Clean Target Pitch Sheet")
    try:
        response = supabase.table("harvested_leads").select("*").execute()
        data = response.data
        
        if data:
            df = pd.DataFrame(data)
            
            # Filter strictly for ACTIVE status and records that contain a valid email address
            active_df = df[
                df["operating_status"].str.contains("ACTIVE", na=False) & 
                df["email_address"].notnull() & 
                (df["email_address"].str.strip() != "")
            ].copy()
            
            total_records = len(df)
            verified_count = len(active_df)
            
            st.success(f"📊 Total Database Records: **{total_records}** | 🎯 Filtered Active Verified Carrier Targets: **{verified_count}**")
            
            if not active_df.empty:
                st.dataframe(active_df, use_container_width=True)
                
                clean_csv = active_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export Clean Email Pitch Sheet to CSV",
                    data=clean_csv,
                    file_name="verified_active_carriers.csv",
                    mime="text/csv",
                    type="primary",
                    key="download_verified"
                )
            else:
                st.warning("No active carriers with valid email addresses found yet.")
        else:
            st.info("No records found in the database yet.")
    except Exception as e:
        st.error(f"Could not load verified data: {e}")
