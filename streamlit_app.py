import streamlit as st

st.set_page_config(
    page_title="Carrier Scraper Hub",
    page_icon="🚚",
    layout="wide"
)

st.title("🚚 AR Transport Carrier Scraper Hub")
st.write("Welcome to the automated carrier lead generation dashboard.")

st.markdown("""
### Overview
Use the navigation sidebar on the left to access the **Scraper Control Panel** (`scraper`). 
From there, you can configure your batch settings, execute manual runs, and stream new leads directly into your Supabase database.
""")

st.info("👈 Select **scraper** from the sidebar pages to get started.")
