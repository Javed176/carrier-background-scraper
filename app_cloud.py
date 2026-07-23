import os
import time
from datetime import datetime, timedelta
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from supabase import Client, create_client

st.set_page_config(page_title="Carrier Automation Portal", layout="wide")

# --- SUPABASE & TOKEN CONFIGURATION ---
SUPABASE_URL = (
    os.environ.get("SUPABASE_URL")
    or st.secrets.get("SUPABASE_URL", "")
    or "https://vhudqthehrjttbcqluat.supabase.co"
)

SUPABASE_KEY = (
    os.environ.get("SUPABASE_KEY")
    or st.secrets.get("SUPABASE_KEY", "")
    or "sb_publishable_eHNwQ5RLe8oi1uZ7If3ODg_aZR66HJ7"
)

if not SUPABASE_URL or not SUPABASE_KEY:
  st.error(
      "🔑 Database configuration missing! Please check your Supabase"
      " credentials."
  )
  st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
CARRIER_TOKEN = os.environ.get("CARRIER_TOKEN") or st.secrets.get(
    "CARRIER_TOKEN", "3243d1219423e4ea"
)


# --- BACKEND DATABASE UTILITIES ---
def log_activity(email, action, detail=""):
  try:
    supabase.table("activity_logs").insert(
        {"email": email, "action": action, "detail": detail}
    ).execute()
  except Exception:
    pass


def get_system_config():
  config = {"throttle_delay_ms": 250.00, "override_global_speed": False}
  try:
    res = supabase.table("system_config").select("*").execute()
    for row in res.data:
      if row["key"] == "throttle_delay_ms":
        config["throttle_delay_ms"] = float(row["value"])
      elif row["key"] == "override_global_speed":
        config["override_global_speed"] = row["value"].upper() == "TRUE"
  except Exception as e:
    print(f"Error fetching system config: {e}")
  return config


def update_global_config(delay_ms, override_bool):
  try:
    supabase.table("system_config").upsert(
        {"key": "throttle_delay_ms", "value": f"{delay_ms:.4f}"},
        on_conflict="key",
    ).execute()
    supabase.table("system_config").upsert(
        {"key": "override_global_speed", "value": str(override_bool).upper()},
        on_conflict="key",
    ).execute()
    return True
  except Exception as e:
    st.error(f"Database error saving global speed config: {e}")
    return False


def get_user_settings(email):
  try:
    res = (
        supabase.table("users")
        .select("delay_ms, session_duration_hours")
        .eq("email", email)
        .execute()
    )
    if res.data:
      delay = float(res.data[0].get("delay_ms", 250.00))
      duration = float(res.data[0].get("session_duration_hours", 3.0))
      return delay, duration
  except Exception as e:
    print(f"Error fetching user settings: {e}")
  return 250.00, 3.0


def get_crawler_state():
  try:
    res = supabase.table("crawler_state").select("*").eq("id", 1).execute()
    if res.data:
      return res.data[0]
  except Exception:
    pass
  return {"current_mc": 1066434, "is_running": False}


def update_crawler_state(current_mc, is_running):
  try:
    supabase.table("crawler_state").upsert({
        "id": 1,
        "current_mc": int(current_mc),
        "is_running": bool(is_running),
    }).execute()
  except Exception as e:
    st.error(f"Failed to update crawler state: {e}")


# --- STATE INITIALIZATIONS ---
if "authenticated" not in st.session_state:
  st.session_state.authenticated = False
if "current_user" not in st.session_state:
  st.session_state.current_user = None
if "is_admin" not in st.session_state:
  st.session_state.is_admin = False
if "login_time" not in st.session_state:
  st.session_state.login_time = None

if "last_db_check" not in st.session_state:
  st.session_state.last_db_check = 0.0
if "cached_delay_ms" not in st.session_state:
  st.session_state.cached_delay_ms = 250.0
if "cached_session_duration" not in st.session_state:
  st.session_state.cached_session_duration = 3.0
if "cached_speed_mode_string" not in st.session_state:
  st.session_state.cached_speed_mode_string = "👤 250.00 ms"


# --- AUTO-LOGOUT HELPER ---
def force_logout(reason="Session Auto-Expired"):
  if st.session_state.authenticated and st.session_state.current_user:
    log_activity(st.session_state.current_user, "logout", reason)
  st.session_state.authenticated = False
  st.session_state.current_user = None
  st.session_state.is_admin = False
  st.session_state.login_time = None
  st.session_state.last_db_check = 0.0


# --- LOGIN GATEWAY ---
if not st.session_state.authenticated:
  st.title("🔒 Security Access Required")
  st.write(
      "This engine is locked. Enter your assigned email and password to begin."
  )

  col_l1, col_l2 = st.columns(2)
  with col_l1:
    email_input = (
        st.text_input("Email Address:", placeholder="user@domain.com")
        .strip()
        .lower()
    )
  with col_l2:
    password_input = st.text_input(
        "Password:", type="password", placeholder="••••••••"
    )

  if st.button("Verify & Unlock Engine", use_container_width=True):
    response = (
        supabase.table("users").select("*").eq("email", email_input).execute()
    )
    user_records = response.data

    if user_records and user_records[0]["password"] == password_input:
      st.session_state.authenticated = True
      st.session_state.current_user = email_input
      st.session_state.is_admin = user_records[0].get("is_admin", False)
      st.session_state.login_time = time.time()
      st.session_state.last_db_check = 0.0

      log_activity(email_input, "login", "Logged in successfully")
      st.success(f"Access Granted! Welcome, {email_input}.")
      st.rerun()
    else:
      st.error("Access denied: Invalid credentials.")
  st.stop()

# --- THROTTLED CONFIG RETRIEVAL ---
now = time.time()
if now - st.session_state.last_db_check > 10.0:
  sys_cfg = get_system_config()
  if sys_cfg["override_global_speed"]:
    st.session_state.cached_delay_ms = sys_cfg["throttle_delay_ms"]
    st.session_state.cached_speed_mode_string = (
        f"🚨 Forced Global Override ({st.session_state.cached_delay_ms:.2f} ms)"
    )
    _, st.session_state.cached_session_duration = get_user_settings(
        st.session_state.current_user
    )
  else:
    (
        st.session_state.cached_delay_ms,
        st.session_state.cached_session_duration,
    ) = get_user_settings(st.session_state.current_user)
    st.session_state.cached_speed_mode_string = (
        f"👤 {st.session_state.cached_delay_ms:.2f} ms"
    )
    st.session_state.last_db_check = now

live_session_duration = st.session_state.cached_session_duration
speed_mode_string = st.session_state.cached_speed_mode_string

# --- AUTO-LOCK CHECK ---
if st.session_state.login_time:
  session_timeout_seconds = live_session_duration * 3600
  elapsed_time = time.time() - st.session_state.login_time
  if elapsed_time >= session_timeout_seconds:
    force_logout("Session Auto-Expired")
    st.warning(
        "⏱️ Session Expired: Your custom session has ended. Please log in"
        " again."
    )
    st.rerun()

# --- SIDEBAR USER CARD & TIMER ---
st.sidebar.markdown("### 👤 Logged In As:")
st.sidebar.info(st.session_state.current_user)

session_timeout_seconds = live_session_duration * 3600
elapsed_time = time.time() - st.session_state.login_time
remaining_seconds = max(0, int(session_timeout_seconds - elapsed_time))

st.sidebar.markdown("### ⏱️ Session Security Lockout")
timer_html = f"""
<div style="font-family: monospace; font-size: 16px; font-weight: bold; color: #ff4b4b; background-color: #0e1117; padding: 10px; border-radius: 5px; text-align: center; border: 1px solid #30363d; margin-bottom: 10px;">
    Auto-Locks In: <span id="clock">--h --m --s</span>
</div>
<script>
    let remaining = {remaining_seconds};
    const clockSpan = document.getElementById('clock');
    function updateClock() {{
        if (remaining <= 0) {{
            clockSpan.textContent = "EXPIRED";
            window.parent.location.reload();
            return;
        }}
        let hours = Math.floor(remaining / 3600);
        let minutes = Math.floor((remaining % 3600) / 60);
        let seconds = remaining % 60;
        clockSpan.textContent = (hours < 10 ? "0" + hours : hours) + "h " + (minutes < 10 ? "0" + minutes : minutes) + "m " + (seconds < 10 ? "0" + seconds : seconds) + "s";
        remaining--;
    }}
    updateClock();
    setInterval(updateClock, 1000);
</script>
"""
with st.sidebar:
  components.html(timer_html, height=65)

if st.sidebar.button("🔓 Manual Log Out", use_container_width=True):
  force_logout("Manual Logout")
  st.rerun()

show_admin_panel = False
if st.session_state.is_admin:
  st.sidebar.markdown("---")
  show_admin_panel = st.sidebar.checkbox(
      "🛡️ Open Admin Dashboard", value=False
  )

# --- ADMIN PANEL ---
if show_admin_panel and st.session_state.is_admin:
  st.title("🛡️ Super Admin Control Dashboard")
  adm_tab1, adm_tab2, adm_tab3 = st.tabs(
      ["👥 User Management", "📊 Activity Logs", "⚙️ System Configuration"]
  )
  with adm_tab3:
    sys_config = get_system_config()
    override_switch = st.checkbox(
        "⚠️ Activate Global Speed Override",
        value=sys_config["override_global_speed"],
    )
    global_speed_slider = st.number_input(
        "Default Global Speed Limit (ms):",
        min_value=0.01,
        max_value=2000.0,
        value=float(sys_config["throttle_delay_ms"]),
        step=0.1,
        format="%.2f",
    )
    if st.button("💾 Save Global Settings", use_container_width=True):
      if update_global_config(float(global_speed_slider), override_switch):
        st.success("Successfully updated system configurations!")
        st.rerun()

# --- MAIN HARVESTER CONTROLLER ---
if not show_admin_panel:
  st.title("🚚 Automated Carrier Harvester (24/7 Cloud Mode)")
  st.write(
      "Control the cloud background crawler. Once started, it runs"
      " independently on the server 24/7 even if you shut down your PC."
  )

  state = get_crawler_state()
  is_running = state["is_running"]
  current_mc_val = state["current_mc"]

  col_st1, col_st2 = st.columns(2)
  with col_st1:
    if is_running:
      st.success(
          f"🟢 Cloud Crawler is ACTIVE (Currently processing MC-{current_mc_val})"
      )
    else:
      st.warning("🔴 Cloud Crawler is STOPPED")
  with col_st2:
    st.metric("Enforced Speed Limit", speed_mode_string)

  new_mc_input = st.text_input(
      "Set / Reset Starting MC Number:", value=str(current_mc_val)
  )

  col_btn1, col_btn2 = st.columns(2)
  if col_btn1.button("🚀 Start 24/7 Cloud Sequence", use_container_width=True):
    if new_mc_input.isdigit():
      update_crawler_state(int(new_mc_input), True)
      log_activity(
          st.session_state.current_user,
          "start_cloud_crawler",
          f"Resumed/Started at MC-{new_mc_input}",
      )
      st.success("Cloud worker signal sent! Harvester is now running 24/7.")
      st.rerun()

  if col_btn2.button("🛑 STOP Cloud Sequence", use_container_width=True):
    update_crawler_state(current_mc_val, False)
    log_activity(
        st.session_state.current_user,
        "stop_cloud_crawler",
        f"Paused at MC-{current_mc_val}",
    )
    st.success("Cloud worker paused.")
    st.rerun()

  st.markdown("---")

  # --- DATABASE MAINTENANCE ---
  st.subheader("🗑️ Database Maintenance")
  st.write("Clear out old historical data or logs from your database.")

  col_m1, col_m2 = st.columns(2)
  with col_m1:
    if st.button("🗑️ Clear Activity Logs", type="secondary"):
      try:
        supabase.table("activity_logs").delete().neq("id", 0).execute()
        st.success("Activity logs cleared!")
        st.rerun()
      except Exception as e:
        st.error(f"Error: {e}")

  with col_m2:
    if st.button("🗑️ Clear Harvested Leads Table", type="primary"):
      try:
        supabase.table("harvested_leads").delete().neq("id", 0).execute()
        st.success("Harvested leads table cleared successfully!")
        st.rerun()
      except Exception as e:
        st.error(f"Error clearing table: {e}")

  st.markdown("---")
  st.subheader("📋 Master History Sheet (Harvested Carriers)")

  try:
    carriers_res = (
        supabase.table("harvested_leads")
        .select("*")
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    if carriers_res.data:
      st.dataframe(pd.DataFrame(carriers_res.data), use_container_width=True)
    else:
      st.info(
          "No carrier records found yet. Start the scraper to harvest data."
      )
  except Exception as e:
    st.info(
        "Could not load harvested_leads table. Make sure your table name"
        " matches."
    )
