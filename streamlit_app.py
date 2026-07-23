import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os
import cloudscraper

# Initialize connection to Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Carrier Scraper Dashboard", layout="wide")

st.title("Carrier Scraper Control Panel")
st.write("Enter your starting MC number below and click **Start Scraping** to begin harvesting leads automatically.")

# Initialize session state for running status
if "is_running" not in st.session_state:
    st.session_state.is_running = False

# Control Panel Form Layout
col1, col2 = st.columns(2)

with col1:
    current_mc = st.number_input("Current MC", value=1066434, step=1)

with col2:
    max_records = st.number_input("Max records to fetch in this batch", value=100, step=10)

# Start and Stop Scraping buttons side-by-side
b_col1, b_col2, _ = st.columns([1, 1, 4])

with b_col1:
    if st.button("Start Scraping", type="primary", use_container_width=True):
        st.session_state.is_running = True
        st.rerun()

with b_col2:
    if st.button("Stop Scraping", use_container_width=True):
        st.session_state.is_running = False
        st.rerun()

# Status display & Scraping Loop
if st.session_state.is_running:
    st.info(f"Starting scraper from MC #{current_mc} for {max_records} records...")
    
    scraper = cloudscraper.create_scraper()
    
    for i in range(max_records):
        if not st.session_state.is_running:
            st.warning("Scraping stopped by user.")
            break
            
        target_mc = current_mc + i
        
        try:
            # 1. Make your actual request using cloudscraper
            # Replace with your actual target URL endpoint
            url = f"https://your-target-website.com/api/carrier/{target_mc}"
            response = scraper.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                # 2. Extract real values from the response
                company_name = data.get("company_name", "Unknown")
                status = data.get("status", "Active")
                
                # 3. Save the real data to Supabase
                data_to_insert = {
                    "mc_number": str(target_mc),
                    "company_name": company_name,
                    "status": status
                }
                supabase.table("carriers").insert(data_to_insert).execute()
                
                st.success(f"Saved: MC-{target_mc} - {company_name}")
            else:
                st.warning(f"MC {target_mc} not found or blocked.")
                
        except Exception as e:
            st.error(f"Error fetching MC {target_mc}: {e}")
            
    # Reset running state when batch completes
    st.session_state.is_running = False
else:
    st.warning("Scraper is currently stopped.")

st.divider()

# Master History Sheet / Database Viewer Section
st.subheader("Master History Sheet")
try:
    response = supabase.table("carriers").select("*").execute()
    data = response.data
    if data:
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No records found in the database yet.")
except Exception as e:
    st.error(f"Error loading data from Supabase: {e}")
