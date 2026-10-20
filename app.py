import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, timezone, timedelta
import random
import requests
import base64
import html
from google.oauth2 import service_account

# ==========================================
# 1. PAGE CONFIG & MOBILE-FIRST CSS OVERHAUL
# ==========================================
st.set_page_config(
    page_title="Task Pro",
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Embedded SVG/PNG Data URIs matching your uploaded Paperclip & Blue Recycle Bin icons
ICON_PAPERCLIP = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23111827' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'><path d='M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48'/></svg>"
ICON_TRASH = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%232563EB'><path d='M9 3h6a1 1 0 0 1 1 1v1h4a1 1 0 1 1 0 2h-1l-1 13a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 7H3a1 1 0 1 1 0-2h4V4a1 1 0 0 1 1-1zm1 2h4V4h-4v1zm-1 5a1 1 0 0 0-1 1v6a1 1 0 1 0 2 0v-6a1 1 0 0 0-1-1zm6 0a1 1 0 0 0-1 1v6a1 1 0 1 0 2 0v-6a1 1 0 0 0-1-1z'/></svg>"

st.markdown("""
    <style>
        /* Remove wasted top/side blank space on mobile phones */
        .block-container {
            padding-top: 1.0rem !important;
            padding-bottom: 3.0rem !important;
            padding-left: 0.6rem !important;
            padding-right: 0.6rem !important;
            max-width: 720px !important;
        }

        /* Make all text sharper, darker, and thicker for mobile readability */
        body, p, div, span, label {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            color: #111827;
        }

        /* Prominent Top-Level & Sub-Level Tabs */
        div[data-baseweb="tab-list"] {
            gap: 6px !important;
            background-color: #F1F5F9;
            padding: 6px;
            border-radius: 10px;
        }
        button[data-baseweb="tab"] {
            font-size: 15px !important;
            font-weight: 700 !important;
            padding: 10px 12px !important;
            border-radius: 8px !important;
            background-color: transparent !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            background-color: #1E3A8A !important;
            color: #FFFFFF !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.15);
        }
        button[data-baseweb="tab"][aria-selected="true"] p {
            color: #FFFFFF !important;
            font-weight: 800 !important;
        }

        /* High-visibility input boxes */
        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
            font-size: 16px !important;
            font-weight: 500 !important;
            border-radius: 8px !important;
        }

        /* Enlarge Voice Note Recorder on Mobile */
        [data-testid="stAudioInput"] {
            border: 2px dashed #2563EB !important;
            border-radius: 12px !important;
            padding: 10px !important;
            background-color: #EFF6FF !important;
        }
        [data-testid="stAudioInput"] button {
            transform: scale(1.25);
            margin: 4px 8px !important;
        }

        /* All standard buttons bold and thumb-friendly */
        .stButton > button {
            border-radius: 8px !important;
            font-weight: 700 !important;
            font-size: 14px !important;
            min-height: 42px !important;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12) !important;
        }

        /* Blue Paperclip Attachment Button */
        div[class*="st-key-att_"] button {
            background-color: #DBEAFE !important;
            color: #1D4ED8 !important;
            border: 1.5px solid #3B82F6 !important;
            font-weight: 800 !important;
        }

        /* Red Recycle Bin Delete Button */
        div[class*="st-key-del_"] button {
            background-color: #FEE2E2 !important;
            color: #DC2626 !important;
            border: 1.5px solid #EF4444 !important;
            font-weight: 800 !important;
        }

        /* Task Card Custom Styling */
        .task-card-header {
            font-size: 18px;
            font-weight: 800;
            color: #0F172A;
            line-height: 1.3;
            margin-bottom: 4px;
        }
        .task-id-chip {
            font-size: 11px;
            font-weight: 700;
            color: #475569;
            background: #F1F5F9;
            padding: 2px 6px;
            border-radius: 4px;
            margin-left: 6px;
        }
        .route-banner {
            font-size: 14px;
            font-weight: 700;
            color: #1E3A8A;
            background-color: #EFF6FF;
            padding: 6px 10px;
            border-radius: 6px;
            margin: 6px 0;
            border-left: 4px solid #2563EB;
        }
        .task-desc-box {
            font-size: 15px;
            font-weight: 500;
            color: #1F2937;
            background-color: #FAFAFA;
            padding: 8px 10px;
            border-radius: 6px;
            border: 1px solid #E5E7EB;
            margin: 6px 0;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .meta-grid {
            font-size: 13.5px;
            font-weight: 600;
            line-height: 1.6;
            margin-top: 6px;
        }
        .att-pill {
            display: inline-block;
            margin-top: 8px;
            padding: 6px 10px;
            background-color: #DBEAFE;
            color: #1E40AF;
            border-radius: 6px;
            font-size: 13.5px;
            font-weight: 700;
            border: 1px solid #93C5FD;
        }
        .thread-container {
            margin-top: 10px;
            padding: 10px;
            background-color: #F8FAFC;
            border: 1px solid #CBD5E1;
            border-left: 5px solid #1E3A8A;
            border-radius: 6px;
            max-height: 220px;
            overflow-y: auto;
        }
        .thread-msg {
            font-size: 14.5px;
            font-weight: 500;
            color: #111827;
            padding: 7px 9px;
            margin-bottom: 6px;
            background: #FFFFFF;
            border-radius: 6px;
            border: 1px solid #E2E8F0;
            word-wrap: break-word;
            white-space: pre-wrap;
            line-height: 1.4;
        }
        .stats-strip {
            display: flex;
            justify-content: space-between;
            background: linear-gradient(90deg, #1E3A8A 0%, #2563EB 100%);
            color: white;
            padding: 10px 14px;
            border-radius: 10px;
            margin-bottom: 12px;
            font-weight: 700;
            font-size: 14px;
            box-shadow: 0 2px 6px rgba(30, 58, 138, 0.2);
        }
        .stats-item {
            color: #FFFFFF !important;
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONSTANTS & CREDENTIALS
# ==========================================
SHEET_ID = st.secrets.get("SHEET_ID", "1oKei6r42q5zH4g-014bNEZfMRkzdm-MoOUwU5GUbsZk")
FOLDER_ID = st.secrets.get("FOLDER_ID", "1-p5zcpZa8vXtpPLMx7y4JoMsGEOYSEaR")
TELEGRAM_BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "8644417421:AAEyHCjujQU30YP_wpbXFlitXH82M7dm4Ws")
GAS_WEBAPP_URL = st.secrets.get(
    "GAS_WEBAPP_URL",
    "https://script.google.com/macros/s/AKfycbwTAf2WeIGGNBlDdtRq4pjHYNf9_KxU-3Pji5Ejg8TkTesrHJUxyZSoFkTfhPQJ9GSx/exec"
)

IST = timezone(timedelta(hours=5, minutes=30))

def now_ist():
    return datetime.now(IST).replace(tzinfo=None)

@st.cache_resource
def get_gcp_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )
    return gspread.authorize(creds)

gs_client = get_gcp_client()

# ==========================================
# 3. GOOGLE SHEETS & DRIVE BRIDGE FUNCTIONS
# ==========================================
REQUIRED_TASK_HEADERS = [
    "Task ID", "Title", "Description", "Assigned By", "Assigned Dept",
    "Assigned To", "Created", "Deadline", "Status", "Attachments",
    "Review Notes", "Priority", "ItemType", "Submitted At"
]

@st.cache_data(ttl=30)
def fetch_data(sheet_name):
    sheet = gs_client.open_by_key(SHEET_ID).worksheet(sheet_name)
    all_values = sheet.get_all_values()
    if not all_values:
        if sheet_name == "Tasks":
            sheet.append_row(REQUIRED_TASK_HEADERS)
            return pd.DataFrame(columns=REQUIRED_TASK_HEADERS)
        return pd.DataFrame()

    headers = [str(h).strip() for h in all_values[0]]
    rows = all_values[1:]
    df = pd.DataFrame(rows, columns=headers) if rows else pd.DataFrame(columns=headers)

    if sheet_name == "Tasks":
        if "Created" not in df.columns and "Created Date" in df.columns:
            df["Created"] = df["Created Date"]

        defaults = {
            "Task ID": "",
            "Title": "",
            "Description": "",
            "Assigned By": "",
            "Assigned Dept": "",
            "Assigned To": "",
            "Created": "",
            "Deadline": "",
            "Status": "Assigned",
            "Attachments": "",
            "Review Notes": "",
            "Priority": "🟢 Regular",
            "ItemType": "Task",
            "Submitted At": ""
        }
        for col, default_val in defaults.items():
            if col not in df.columns:
                df[col] = default_val
            else:
                df[col] = df[col].fillna(default_val).replace("", default_val if col in ["Priority", "ItemType"] else "")

    return df

def ensure_sheet_headers():
    sheet = gs_client.open_by_key(SHEET_ID).worksheet("Tasks")
    current_headers = [str(h).strip() for h in sheet.row_values(1)]
    if not current_headers:
        sheet.append_row(REQUIRED_TASK_HEADERS)
        return REQUIRED_TASK_HEADERS
    updated = False
    for col in REQUIRED_TASK_HEADERS:
        if col not in current_headers:
            current_headers.append(col)
            updated = True
    if updated:
        sheet.update("A1", [current_headers])
    return current_headers

def append_task(task_dict):
    sheet = gs_client.open_by_key(SHEET_ID).worksheet("Tasks")
    headers = ensure_sheet_headers()
    row_to_append = [str(task_dict.get(col, "")) for col in headers]
    sheet.append_row(row_to_append)

def update_task_fields(task_id, updates_dict):
    sheet = gs_client.open_by_key(SHEET_ID).worksheet("Tasks")
    headers = ensure_sheet_headers()
    cell = sheet.find(str(task_id), in_column=1)
    if cell:
        row_idx = cell.row
        for col_name, val in updates_dict.items():
            if col_name in headers:
                col_idx = headers.index(col_name) + 1
                sheet.update_cell(row_idx, col_idx, str(val))

def delete_task_from_sheet(task_id):
    sheet = gs_client.open_by_key(SHEET_ID).worksheet("Tasks")
    cell = sheet.find(str(task_id), in_column=1)
    if cell:
        sheet.delete_rows(cell.row)
    if GAS_WEBAPP_URL.startswith("http"):
        try:
            requests.post(GAS_WEBAPP_URL, json={"action": "delete", "taskId": task_id}, timeout=15)
        except Exception:
            pass

def clear_all_completed_tasks(owner_name, role):
    sheet = gs_client.open_by_key(SHEET_ID).worksheet("Tasks")
    records = sheet.get_all_records()
    for idx in range(len(records) - 1, -1, -1):
        status_val = str(records[idx].get("Status", "")).strip()
        assigned_by_val = str(records[idx].get("Assigned By", "")).strip().upper()
        if status_val == "Completed":
            if role in ["CEO", "GM"] and assigned_by_val != owner_name.upper():
                continue
            task_id = records[idx].get("Task ID")
            sheet.delete_rows(idx + 2)
            if task_id and GAS_WEBAPP_URL.startswith("http"):
                try:
                    requests.post(GAS_WEBAPP_URL, json={"action": "delete", "taskId": task_id}, timeout=10)
                except Exception:
                    pass

def upload_bytes_to_drive(file_bytes, filename, mimetype):
    if not GAS_WEBAPP_URL.startswith("http"):
        st.error("⚠️ Please configure your Google Apps Script Web App URL.")
        st.stop()
    payload = {
        "action": "upload",
        "filename": filename,
        "mimeType": mimetype,
        "bytes": base64.b64encode(file_bytes).decode("utf-8")
    }
    resp = requests.post(GAS_WEBAPP_URL, json=payload, timeout=60)
    try:
        res_json = resp.json()
    except Exception:
        st.error("Drive Bridge Error: Make sure Apps Script access is set to 'Anyone'.")
        st.stop()

    if res_json.get("status") != "success":
        st.error(f"Drive Upload Error: {res_json.get('message')}")
        st.stop()
    return res_json.get("id")

@st.cache_data(ttl=120)
def fetch_attachments_from_drive(task_id):
    if not GAS_WEBAPP_URL.startswith("http"):
        return []
    try:
        resp = requests.post(GAS_WEBAPP_URL, json={"action": "list", "taskId": task_id}, timeout=30)
        res_json = resp.json()
        if res_json.get("status") == "success":
            return res_json.get("files", [])
    except Exception:
        pass
    return []

def parse_dt(dt_str):
    if not dt_str or pd.isna(dt_str):
        return None
    s = str(dt_str).strip()
    for fmt in [
        "%d/%m/%Y, %I:%M:%S %p",
        "%d/%m/%Y, %I:%M %p",
        "%m/%d/%Y, %I:%M:%S %p",
        "%Y-%m-%d %H:%M:%S"
    ]:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None

# ==========================================
# 4. EXACT TELEGRAM NOTIFICATION TEMPLATE
# ==========================================
def send_telegram_alert(
    chat_id,
    task_title,
    assigned_by,
    deadline,
    description,
    priority="🟢 Regular",
    assignee_name="STAFF",
    assignee_dept="General",
    attachment_summary=""
):
    if not chat_id:
        return
    details_text = description if str(description).strip() else "No additional text."
    if attachment_summary:
        details_text = f"{details_text}\n📎 Attachments from {assigned_by}: {attachment_summary}"

    # Exact template structure requested by user
    message = (
        f"🚨Title: {task_title}\n"
        f"🏢 From: {assigned_by}\n"
        f"👤 For: {assignee_name.upper()} ({assignee_dept} Dept)\n"
        f"📌 Priority: {priority}\n"
        f"📅 Deadline: {deadline}\n\n"
        f"📝 Details:\n{details_text}"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": str(chat_id).strip(),
        "text": message
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass

# ==========================================
# 5. SESSION STATE MANAGEMENT
# ==========================================
if "user" not in st.session_state:
    st.session_state.user = None
if "form_key" not in st.session_state:
    st.session_state.form_key = 0
if "open_attachments" not in st.session_state:
    st.session_state.open_attachments = {}

# ==========================================
# 6. LOGIN SCREEN
# ==========================================
if st.session_state.user is None:
    st.markdown(
        "<h1 style='text-align: center; color: #1E3A8A; font-weight: 900; margin-bottom: 0px;'>📋 Task Pro</h1>"
        "<p style='text-align: center; color: #475569; font-weight: 600; margin-top: 4px;'>Factory & Department Task Portal</p>",
        unsafe_allow_html=True
    )
    st.write("")

    with st.container(border=True):
        username = st.text_input("👤 Employee Name").strip().upper()
        password = st.text_input("🔑 Password", type="password")

        if st.button("🚀 Secure Login", use_container_width=True, type="primary"):
            users_df = fetch_data("User_list")
            if not users_df.empty:
                user_match = users_df[
                    (users_df["NAME"].astype(str).str.strip().str.upper() == username) &
                    (users_df["PASSWORD"].astype(str).str.strip() == str(password).strip())
                ]
                if not user_match.empty:
                    user_info = user_match.iloc[0]
                    st.session_state.user = {
                        "name": str(user_info["NAME"]).strip().upper(),
                        "dept": str(user_info["DEPARTMENT"]).strip(),
                        "role": str(user_info["ROLE"]).strip().upper()
                    }
                    st.rerun()
                else:
                    st.error("❌ Invalid Employee Name or Password")
            else:
                st.error("⚠️ User_list sheet is empty.")

# ==========================================
# 7. MAIN APPLICATION DASHBOARD
# ==========================================
else:
    user = st.session_state.user
    fk = st.session_state.form_key

    # Compact Mobile Top User Bar (No need to open sidebar on phone)
    top_c1, top_c2, top_c3 = st.columns([0.56, 0.22, 0.22])
    with top_c1:
        st.markdown(
            f"<div style='font-size:16px; font-weight:800; color:#1E3A8A;'>👤 {user['name']} "
            f"<span style='font-size:13px; font-weight:600; color:#475569;'>({user['role']} | {user['dept']})</span></div>",
            unsafe_allow_html=True
        )
    with top_c2:
        if st.button("🔄 Refresh", use_container_width=True):
            fetch_data.clear()
            fetch_attachments_from_drive.clear()
            st.rerun()
    with top_c3:
        if st.button("🚪 Logout", key="top_logout", use_container_width=True):
            st.session_state.user = None
            st.rerun()

    # Sidebar for Bulk Maintenance
    with st.sidebar:
        st.markdown(f"### 👤 {user['name']}")
        st.caption(f"**{user['role']}** | {user['dept']}")
        st.divider()
        st.markdown(
            f"<div style='margin-bottom:6px; font-weight:800; color:#1E3A8A;'>"
            f"<img src=\"{ICON_TRASH}\" style='width:18px; vertical-align:middle; margin-right:6px;'/>"
            f"Maintenance</div>",
            unsafe_allow_html=True
        )
        if st.button("🗑️ Clear Completed Tasks", use_container_width=True):
            with st.spinner("Cleaning up completed tasks..."):
                clear_all_completed_tasks(user["name"], user["role"])
                fetch_data.clear()
            st.toast("Completed tasks cleared!", icon="🧹")
            st.rerun()

    # --- TOP-LEVEL NAVIGATION TABS ---
    main_tab1, main_tab2, main_tab3 = st.tabs([
        "📋 Task Pro",
        "➕ Create Task",
        "⏰ Set Reminder"
    ])

    # ==========================================
    # TAB 1: TASK PRO (WORKSPACE)
    # ==========================================
    with main_tab1:
        all_df = fetch_data("Tasks")

        if all_df.empty:
            st.info("No tasks or reminders in the system yet. Use '➕ Create Task' to assign one.")
        else:
            # Prominent Switcher: Operational Tasks vs. Reminders
            view_mode = st.radio(
                "Select View:",
                ["📋 Operational Tasks", "⏰ Routine Reminders"],
                horizontal=True,
                label_visibility="collapsed"
            )

            if view_mode == "📋 Operational Tasks":
                tasks_df = all_df[all_df["ItemType"].astype(str).str.strip().isin(["Task", "", "None"])].copy()
            else:
                tasks_df = all_df[all_df["ItemType"].astype(str).str.strip() == "Reminder"].copy()

            # STRICT PRIVACY & VISIBILITY LOGIC:
            # Every user strictly sees tasks THEY assigned OR tasks assigned TO them.
            # Sujen only sees tasks Sujen assigned (or assigned to Sujen), never internal tasks Sudeep assigned to Sudeep.
            tasks_df = tasks_df[
                (tasks_df["Assigned By"].astype(str).str.strip().str.upper() == user["name"]) |
                (tasks_df["Assigned To"].astype(str).str.strip().str.upper() == user["name"])
            ].copy()

            if tasks_df.empty:
                st.info(f"No items found under {view_mode} for {user['name']}.")
            else:
                current_time = now_ist()

                def check_is_overdue(row):
                    status_str = str(row.get("Status", "")).strip()
                    if status_str == "Completed":
                        return False
                    dt = parse_dt(row.get("Deadline", ""))
                    return (dt is not None) and (dt < current_time)

                tasks_df["is_overdue"] = tasks_df.apply(check_is_overdue, axis=1)

                active_df = tasks_df[tasks_df["Status"].astype(str).str.strip() == "Assigned"]
                overdue_df = tasks_df[tasks_df["is_overdue"] == True]
                review_df = tasks_df[tasks_df["Status"].astype(str).str.strip().isin(["Under Review", "Marked Complete"])]
                done_df = tasks_df[tasks_df["Status"].astype(str).str.strip() == "Completed"]

                # Minimalist Mobile Quick-Stats Strip
                st.markdown(f"""
                    <div class='stats-strip'>
                        <div class='stats-item'>📌 Active: {len(active_df)}</div>
                        <div class='stats-item'>🚨 Overdue: {len(overdue_df)}</div>
                        <div class='stats-item'>⏳ Review: {len(review_df)}</div>
                        <div class='stats-item'>✅ Done: {len(done_df)}</div>
                    </div>
                """, unsafe_allow_html=True)

                sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
                    f"📌 Active ({len(active_df)})",
                    f"🚨 Overdue ({len(overdue_df)})",
                    f"⏳ Review ({len(review_df)})",
                    f"✅ Done ({len(done_df)})"
                ])

                def sort_by_priority(df_subset):
                    if df_subset.empty:
                        return df_subset
                    df_copy = df_subset.copy()
                    p_order = {"🔴 High Priority": 0, "🔴 High": 0, "🟢 Regular": 1}
                    df_copy["p_rank"] = df_copy["Priority"].map(lambda x: p_order.get(str(x).strip(), 1))
                    return df_copy.sort_values(by="p_rank", ascending=True)

                def render_task_card(row, tab_prefix):
                    task_id = str(row.get("Task ID", "")).strip()
                    title_txt = html.escape(str(row.get("Title", "")))
                    desc_txt = html.escape(str(row.get("Description", "")))
                    assigned_by = str(row.get("Assigned By", "")).strip().upper()
                    assigned_to = str(row.get("Assigned To", "")).strip().upper()
                    assigned_dept = html.escape(str(row.get("Assigned Dept", "")).strip())
                    created_at = str(row.get("Created", "")).strip()
                    deadline_at = str(row.get("Deadline", "")).strip()
                    submitted_at = str(row.get("Submitted At", "")).strip()
                    status = str(row.get("Status", "Assigned")).strip()
                    priority = str(row.get("Priority", "🟢 Regular")).strip()
                    att_summary = str(row.get("Attachments", "")).strip()
                    review_notes = str(row.get("Review Notes", "")).strip()
                    is_overdue = bool(row.get("is_overdue", False))

                    # Priority Badge
                    if "High" in priority:
                        prio_badge = "<span style='background:#FEE2E2; color:#DC2626; padding:3px 8px; border-radius:6px; font-size:12px; font-weight:800; margin-left:6px; border:1px solid #FCA5A5;'>🔴 HIGH PRIORITY</span>"
                    else:
                        prio_badge = "<span style='background:#DCFCE7; color:#15803D; padding:3px 8px; border-radius:6px; font-size:12px; font-weight:800; margin-left:6px; border:1px solid #86EFAC;'>🟢 Regular</span>"

                    # Overdue / Status Badge
                    overdue_badge = ""
                    if is_overdue:
                        overdue_badge = "<span style='background:#DC2626; color:#FFFFFF; padding:3px 8px; border-radius:6px; font-size:12px; font-weight:800; margin-left:6px;'>🚨 OVERDUE</span>"
                    elif status == "Marked Complete":
                        overdue_badge = "<span style='background:#FEF3C7; color:#B45309; padding:3px 8px; border-radius:6px; font-size:12px; font-weight:800; margin-left:6px;'>✔️ Marked Complete by Assignee</span>"
                    elif status == "Under Review":
                        overdue_badge = "<span style='background:#E0E7FF; color:#1D4ED8; padding:3px 8px; border-radius:6px; font-size:12px; font-weight:800; margin-left:6px;'>⏳ Waiting Review</span>"

                    # Timeliness check (Submitted At vs Deadline)
                    submitted_html = ""
                    if submitted_at:
                        dl_dt = parse_dt(deadline_at)
                        sub_dt = parse_dt(submitted_at)
                        if dl_dt and sub_dt:
                            if sub_dt <= dl_dt:
                                time_tag = "<span style='color:#15803D; font-weight:800;'>(✅ Within Deadline)</span>"
                            else:
                                time_tag = "<span style='color:#DC2626; font-weight:800;'>(⚠️ Submitted Late)</span>"
                        else:
                            time_tag = ""
                        submitted_html = f"<div>📤 <b>Submitted / Actioned At:</b> {html.escape(submitted_at)} {time_tag}</div>"

                    # Instant Attachment Indicator (Explicitly specifies Assigner sent them)
                    att_indicator_html = ""
                    if att_summary:
                        att_indicator_html = (
                            f"<div class='att-pill'>"
                            f"<img src=\"{ICON_PAPERCLIP}\" style='width:15px; vertical-align:middle; margin-right:5px;'/>"
                            f"Sent by {html.escape(assigned_by)}: {html.escape(att_summary)} (Tap 📎 to open)</div>"
                        )

                    # Clean Multi-Line Conversation Thread (No broken raw HTML tags!)
                    thread_html = ""
                    if review_notes:
                        # Clean any legacy <br> or <b> tags if an older row had them
                        cleaned_notes = review_notes.replace("<br>", " ").replace("<b>", "").replace("</b>", "")
                        entries = [e.strip() for e in cleaned_notes.split(" | ") if e.strip()]
                        bubbles = "".join([f"<div class='thread-msg'>💬 {html.escape(entry)}</div>" for entry in entries])
                        thread_html = (
                            f"<div class='thread-container'>"
                            f"<div style='font-size:13px; font-weight:800; color:#1E3A8A; margin-bottom:6px;'>📋 Remarks & Review Thread ({len(entries)}):</div>"
                            f"{bubbles}</div>"
                        )

                    with st.container(border=True):
                        can_delete = (assigned_by == user["name"]) or (user["role"] in ["CEO", "GM"])
                        if can_delete:
                            c1, c2, c3 = st.columns([0.68, 0.16, 0.16])
                        else:
                            c1, c2 = st.columns([0.80, 0.20])
                            c3 = None

                        with c1:
                            created_line = f"<div>🕒 <b>Assigned On:</b> {html.escape(created_at)}</div>" if created_at else ""
                            deadline_color = "#DC2626" if is_overdue else "#B45309"

                            card_html = (
                                f"<div class='task-card-header'>{title_txt}"
                                f"<span class='task-id-chip'>{html.escape(task_id)}</span>"
                                f"{prio_badge}{overdue_badge}</div>"
                                f"<div class='route-banner'>🏢 From: {html.escape(assigned_by)} &nbsp;➡️&nbsp; 👷 To: {html.escape(assigned_to)} ({assigned_dept})</div>"
                                f"<div class='task-desc-box'>{desc_txt if desc_txt else 'No extra details provided.'}</div>"
                                f"<div class='meta-grid'>"
                                f"{created_line}"
                                f"<div style='color:{deadline_color};'>📅 <b>Deadline:</b> {html.escape(deadline_at)}</div>"
                                f"{submitted_html}"
                                f"</div>"
                                f"{att_indicator_html}"
                                f"{thread_html}"
                            )
                            st.markdown(card_html, unsafe_allow_html=True)

                        # Blue Paperclip Button
                        with c2:
                            st.markdown(
                                f"<div style='text-align:center; margin-bottom:2px;'>"
                                f"<img src=\"{ICON_PAPERCLIP}\" style='width:18px;'/></div>",
                                unsafe_allow_html=True
                            )
                            toggle_key = f"{tab_prefix}_{task_id}"
                            if st.button("📎", key=f"att_{toggle_key}", help="Open Assigner's Files & Voice Notes", use_container_width=True):
                                st.session_state.open_attachments[toggle_key] = not st.session_state.open_attachments.get(toggle_key, False)

                        # Red Recycle Bin Delete Button
                        if can_delete and c3 is not None:
                            with c3:
                                st.markdown(
                                    f"<div style='text-align:center; margin-bottom:2px;'>"
                                    f"<img src=\"{ICON_TRASH}\" style='width:18px;'/></div>",
                                    unsafe_allow_html=True
                                )
                                if st.button("🗑️", key=f"del_{tab_prefix}_{task_id}", help="Delete Task Permanently", use_container_width=True):
                                    with st.spinner("Deleting task..."):
                                        delete_task_from_sheet(task_id)
                                        fetch_data.clear()
                                    st.toast(f"Deleted {task_id}", icon="🗑️")
                                    st.rerun()

                        # Display Attachments Inline When Toggled
                        if st.session_state.open_attachments.get(f"{tab_prefix}_{task_id}", False):
                            with st.spinner("Loading attachments from Drive..."):
                                items = fetch_attachments_from_drive(task_id)
                                if not items:
                                    st.info(f"ℹ️ No voice notes or files were attached by {assigned_by}.")
                                else:
                                    st.markdown(f"**📂 Original Attachments Sent by {assigned_by}:**")
                                    for item in items:
                                        mime = item.get("mimeType", "")
                                        raw_bytes = base64.b64decode(item["b64"]) if "b64" in item else None
                                        if "audio" in mime and raw_bytes:
                                            st.caption(f"🎙️ **Voice Note from {assigned_by}:** `{item['name']}`")
                                            st.audio(raw_bytes, format="audio/wav")
                                        elif "image" in mime and raw_bytes:
                                            st.caption(f"🖼️ **Photo from {assigned_by}:** `{item['name']}`")
                                            st.image(raw_bytes, use_container_width=True)
                                        else:
                                            st.markdown(f"📄 [{item['name']}]({item.get('url', '#')})")

                        # ==========================================
                        # WORKFLOW ACTION BUTTONS (ASSIGNEE VS ASSIGNER)
                        # ==========================================
                        # 1. Assignee Actions when task is Assigned
                        if status == "Assigned" and user["name"] == assigned_to:
                            st.divider()
                            user_msg = st.text_input(
                                f"✍️ Write Remark to {assigned_by} (e.g., Done, will complete by tomorrow):",
                                key=f"msg_{tab_prefix}_{task_id}",
                                placeholder="Type your remark before submitting..."
                            )
                            act_col1, act_col2 = st.columns(2)
                            with act_col1:
                                if st.button("📤 Submit for Review", key=f"sub_{tab_prefix}_{task_id}", use_container_width=True):
                                    current_str = now_ist().strftime("%d/%m/%Y, %I:%M:%S %p")
                                    remark_text = user_msg.strip() if user_msg.strip() else "Submitted for review."
                                    new_entry = f"[{user['name']} Submitted for Review at {current_str}]: {remark_text}"
                                    updated_notes = f"{review_notes} | {new_entry}" if review_notes else new_entry

                                    update_task_fields(task_id, {
                                        "Status": "Under Review",
                                        "Review Notes": updated_notes,
                                        "Submitted At": current_str
                                    })
                                    fetch_data.clear()
                                    st.toast("Submitted for review!", icon="📤")
                                    st.rerun()

                            with act_col2:
                                if st.button("✅ Mark Completed", key=f"direct_done_{tab_prefix}_{task_id}", use_container_width=True, type="primary"):
                                    current_str = now_ist().strftime("%d/%m/%Y, %I:%M:%S %p")
                                    remark_text = user_msg.strip() if user_msg.strip() else "Marked as completed."
                                    new_entry = f"[{user['name']} Marked Completed at {current_str}]: {remark_text}"
                                    updated_notes = f"{review_notes} | {new_entry}" if review_notes else new_entry

                                    update_task_fields(task_id, {
                                        "Status": "Marked Complete",
                                        "Review Notes": updated_notes,
                                        "Submitted At": current_str
                                    })
                                    fetch_data.clear()
                                    st.toast(f"Marked completed! Sent to {assigned_by} for verification.", icon="✅")
                                    st.rerun()

                        # 2. Assigner (Sujen) Review & Close Loop
                        elif status in ["Under Review", "Marked Complete"]:
                            if user["name"] == assigned_by:
                                st.divider()
                                st.caption(f"🔔 **{assigned_to}** submitted this task with a text remark above. Verify and close, or send back:")
                                manager_reply = st.text_input(
                                    f"💬 Reply to {assigned_to} (required if sending back):",
                                    key=f"reply_{tab_prefix}_{task_id}",
                                    placeholder="Write feedback or closing note..."
                                )
                                b1, b2 = st.columns(2)
                                with b1:
                                    if st.button("✅ Satisfied & Close Task", key=f"app_{tab_prefix}_{task_id}", use_container_width=True, type="primary"):
                                        current_str = now_ist().strftime("%d/%m/%Y, %I:%M:%S %p")
                                        reply_txt = f": {manager_reply.strip()}" if manager_reply.strip() else ""
                                        new_entry = f"[Closed & Approved by {user['name']} at {current_str}]{reply_txt}"
                                        updated_notes = f"{review_notes} | {new_entry}" if review_notes else new_entry

                                        update_task_fields(task_id, {
                                            "Status": "Completed",
                                            "Review Notes": updated_notes
                                        })
                                        fetch_data.clear()
                                        st.toast("Task verified and closed!", icon="✅")
                                        st.rerun()

                                with b2:
                                    if st.button("↩️ Not Satisfied - Send Back", key=f"ret_{tab_prefix}_{task_id}", use_container_width=True):
                                        current_str = now_ist().strftime("%d/%m/%Y, %I:%M:%S %p")
                                        reply_txt = manager_reply.strip() if manager_reply.strip() else "Please check and complete properly."
                                        new_entry = f"[Sent Back by {user['name']} at {current_str}]: {reply_txt}"
                                        updated_notes = f"{review_notes} | {new_entry}" if review_notes else new_entry

                                        update_task_fields(task_id, {
                                            "Status": "Assigned",
                                            "Review Notes": updated_notes
                                        })
                                        fetch_data.clear()
                                        st.toast(f"Sent back to {assigned_to}!", icon="↩️")
                                        st.rerun()
                            else:
                                st.caption(f"⏳ Waiting for **{assigned_by}** to verify and close this task.")

                with sub_tab1:
                    sorted_active = sort_by_priority(active_df)
                    if sorted_active.empty:
                        st.caption("No active tasks right now.")
                    for _, row in sorted_active.iterrows():
                        render_task_card(row, "act")

                with sub_tab2:
                    sorted_overdue = sort_by_priority(overdue_df)
                    if sorted_overdue.empty:
                        st.success("🎉 Zero overdue items!")
                    else:
                        for _, row in sorted_overdue.iterrows():
                            render_task_card(row, "ovr")

                with sub_tab3:
                    sorted_review = sort_by_priority(review_df)
                    if sorted_review.empty:
                        st.caption("No items waiting for review.")
                    for _, row in sorted_review.iterrows():
                        render_task_card(row, "rev")

                with sub_tab4:
                    sorted_done = sort_by_priority(done_df)
                    if sorted_done.empty:
                        st.caption("No completed tasks yet.")
                    for _, row in sorted_done.iterrows():
                        render_task_card(row, "done")

    # ==========================================
    # TAB 2: CREATE TASK (ANYONE CAN ASSIGN TO ANYONE)
    # ==========================================
    with main_tab2:
        with st.expander("➕ Assign New Task Form", expanded=True):
            title = st.text_input("📋 Task Title *", key=f"t_title_{fk}", placeholder="Enter short, clear title...")
            desc = st.text_area("📝 Details / Instructions", key=f"t_desc_{fk}", height=90, placeholder="Write task instructions here...")

            # Default is Green Regular so staff don't panic
            priority = st.selectbox(
                "📌 Task Priority (Default: Regular)",
                ["🟢 Regular", "🔴 High Priority"],
                index=0,
                key=f"t_prio_{fk}"
            )

            users_df = fetch_data("User_list")
            if not users_df.empty:
                departments = ["All"] + sorted(users_df["DEPARTMENT"].astype(str).unique().tolist())
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    dept_filter = st.selectbox("🏢 Filter Department", departments, key=f"t_dept_{fk}")
                with col_f2:
                    if dept_filter == "All":
                        assignees = users_df["NAME"].astype(str).tolist()
                    else:
                        assignees = users_df[users_df["DEPARTMENT"].astype(str) == dept_filter]["NAME"].astype(str).tolist()
                    assignee = st.selectbox("👷 Assign To *", assignees, key=f"t_assignee_{fk}")
            else:
                assignee = None
                st.warning("User_list is empty.")

            col_d, col_t = st.columns(2)
            with col_d:
                deadline_d = st.date_input("📅 Deadline Date", value=now_ist().date(), format="DD/MM/YYYY", key=f"t_date_{fk}")
            with col_t:
                deadline_t = st.time_input("⏰ Time", value=now_ist().time().replace(second=0, microsecond=0), key=f"t_time_{fk}")

            st.markdown(
                f"<div style='margin-top:8px; font-weight:700; color:#1E3A8A;'>"
                f"<img src=\"{ICON_PAPERCLIP}\" style='width:18px; vertical-align:middle; margin-right:6px;'/>"
                f"Attach Photos / Documents</div>",
                unsafe_allow_html=True
            )
            uploaded_files = st.file_uploader("Upload Files", accept_multiple_files=True, key=f"t_files_{fk}", label_visibility="collapsed")

            st.markdown("<div style='margin-top:8px; font-weight:700; color:#1E3A8A;'>🎙️ Record Voice Note (Tap Mic to Start / Stop)</div>", unsafe_allow_html=True)
            audio_recording = st.audio_input("Voice Note", key=f"t_audio_{fk}", label_visibility="collapsed")

            st.write("")
            if st.button("🚀 Assign Task Now", use_container_width=True, type="primary"):
                if title.strip() and assignee:
                    with st.spinner("Assigning task & uploading attachments..."):
                        task_id = f"TSK-{random.randint(100000, 999999)}"
                        assigned_dept = users_df[users_df["NAME"].astype(str) == assignee]["DEPARTMENT"].values[0]

                        created_str = now_ist().strftime("%d/%m/%Y, %I:%M:%S %p")
                        deadline_str = f"{deadline_d.strftime('%d/%m/%Y')}, {deadline_t.strftime('%I:%M:%S %p')}"

                        att_parts = []
                        if uploaded_files:
                            for idx, file in enumerate(uploaded_files):
                                file_ext = file.name.split(".")[-1]
                                upload_bytes_to_drive(file.getvalue(), f"{task_id}_{idx+1}.{file_ext}", file.type)
                            att_parts.append(f"{len(uploaded_files)} File(s)")

                        if audio_recording is not None:
                            upload_bytes_to_drive(audio_recording.getvalue(), f"{task_id}_VoiceNote.wav", "audio/wav")
                            att_parts.append("1 Voice Note")

                        att_summary_str = " + ".join(att_parts)

                        task_dict = {
                            "Task ID": task_id,
                            "Title": title.strip(),
                            "Description": desc.strip(),
                            "Assigned By": user["name"],
                            "Assigned Dept": assigned_dept,
                            "Assigned To": str(assignee).strip().upper(),
                            "Created": created_str,
                            "Deadline": deadline_str,
                            "Status": "Assigned",
                            "Attachments": att_summary_str,
                            "Review Notes": "",
                            "Priority": priority,
                            "ItemType": "Task",
                            "Submitted At": ""
                        }
                        append_task(task_dict)

                        assignee_row = users_df[users_df["NAME"].astype(str) == assignee]
                        telegram_id = assignee_row["TELEGRAM_ID"].values[0] if "TELEGRAM_ID" in assignee_row.columns else None
                        if pd.notna(telegram_id) and str(telegram_id).strip() != "":
                            send_telegram_alert(
                                telegram_id,
                                title.strip(),
                                user["name"],
                                deadline_str,
                                desc.strip(),
                                priority,
                                assignee,
                                assigned_dept,
                                att_summary_str
                            )

                        fetch_data.clear()
                        st.session_state.form_key += 1
                    st.success(f"✅ Task '{title.strip()}' successfully assigned to {assignee}!")
                    st.toast(f"✅ Assigned to {assignee}!", icon="🚀")
                else:
                    st.error("⚠️ Task Title and Assignee are required.")

    # ==========================================
    # TAB 3: SET REMINDER (DAILY, WEEKLY, MONTHLY)
    # ==========================================
    with main_tab3:
        st.markdown("### ⏰ Set Routine Reminder")
        rem_tab1, rem_tab2, rem_tab3 = st.tabs(["📅 Daily", "📆 Weekly", "🗓️ Monthly"])
        users_df = fetch_data("User_list")
        assignees_list = users_df["NAME"].astype(str).tolist() if not users_df.empty else []

        with rem_tab1:
            d_title = st.text_input("Daily Routine Title", key="d_title")
            d_time = st.time_input("Alert Time", key="d_time")
            d_assignee = st.selectbox("Assign To", assignees_list, key="d_assignee")

            if st.button("⏰ Save Daily Reminder", type="primary", use_container_width=True):
                if d_title.strip() and d_assignee:
                    with st.spinner("Saving reminder..."):
                        task_id = f"REM-{random.randint(100000, 999999)}"
                        assigned_dept = users_df[users_df["NAME"].astype(str) == d_assignee]["DEPARTMENT"].values[0]
                        created_str = now_ist().strftime("%d/%m/%Y, %I:%M:%S %p")
                        deadline_str = f"Daily at {d_time.strftime('%I:%M %p')}"
                        priority = "🟢 Regular"

                        task_dict = {
                            "Task ID": task_id,
                            "Title": f"Daily: {d_title.strip()}",
                            "Description": "Recurring Daily Reminder",
                            "Assigned By": user["name"],
                            "Assigned Dept": assigned_dept,
                            "Assigned To": str(d_assignee).strip().upper(),
                            "Created": created_str,
                            "Deadline": deadline_str,
                            "Status": "Assigned",
                            "Attachments": "",
                            "Review Notes": "",
                            "Priority": priority,
                            "ItemType": "Reminder",
                            "Submitted At": ""
                        }
                        append_task(task_dict)

                        assignee_row = users_df[users_df["NAME"].astype(str) == d_assignee]
                        telegram_id = assignee_row["TELEGRAM_ID"].values[0] if "TELEGRAM_ID" in assignee_row.columns else None
                        if pd.notna(telegram_id) and str(telegram_id).strip() != "":
                            send_telegram_alert(
                                telegram_id,
                                f"Daily: {d_title.strip()}",
                                user["name"],
                                deadline_str,
                                "Recurring Daily Reminder",
                                priority,
                                d_assignee,
                                assigned_dept
                            )
                        fetch_data.clear()
                    st.success(f"✅ Daily reminder '{d_title}' set for {d_assignee}!")
                    st.toast("Daily reminder saved!", icon="⏰")
                else:
                    st.error("Please enter a title.")

        with rem_tab2:
            w_title = st.text_input("Weekly Routine Title", key="w_title")
            w_day = st.selectbox("Day of Week", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], key="w_day")
            w_assignee = st.selectbox("Assign To", assignees_list, key="w_assignee")

            if st.button("⏰ Save Weekly Reminder", type="primary", use_container_width=True):
                if w_title.strip() and w_assignee:
                    with st.spinner("Saving reminder..."):
                        task_id = f"REM-{random.randint(100000, 999999)}"
                        assigned_dept = users_df[users_df["NAME"].astype(str) == w_assignee]["DEPARTMENT"].values[0]
                        created_str = now_ist().strftime("%d/%m/%Y, %I:%M:%S %p")
                        deadline_str = f"Every {w_day}"
                        priority = "🟢 Regular"

                        task_dict = {
                            "Task ID": task_id,
                            "Title": f"Weekly: {w_title.strip()}",
                            "Description": f"Recurring Weekly Reminder on {w_day}",
                            "Assigned By": user["name"],
                            "Assigned Dept": assigned_dept,
                            "Assigned To": str(w_assignee).strip().upper(),
                            "Created": created_str,
                            "Deadline": deadline_str,
                            "Status": "Assigned",
                            "Attachments": "",
                            "Review Notes": "",
                            "Priority": priority,
                            "ItemType": "Reminder",
                            "Submitted At": ""
                        }
                        append_task(task_dict)

                        assignee_row = users_df[users_df["NAME"].astype(str) == w_assignee]
                        telegram_id = assignee_row["TELEGRAM_ID"].values[0] if "TELEGRAM_ID" in assignee_row.columns else None
                        if pd.notna(telegram_id) and str(telegram_id).strip() != "":
                            send_telegram_alert(
                                telegram_id,
                                f"Weekly: {w_title.strip()}",
                                user["name"],
                                deadline_str,
                                f"Recurring Weekly Reminder on {w_day}",
                                priority,
                                w_assignee,
                                assigned_dept
                            )
                        fetch_data.clear()
                    st.success(f"✅ Weekly reminder '{w_title}' set for {w_assignee}!")
                    st.toast("Weekly reminder saved!", icon="⏰")
                else:
                    st.error("Please enter a title.")

        with rem_tab3:
            m_title = st.text_input("Monthly Routine Title", key="m_title")
            m_date = st.slider("Day of Month", 1, 31, 1, key="m_date")
            m_assignee = st.selectbox("Assign To", assignees_list, key="m_assignee")

            if st.button("⏰ Save Monthly Reminder", type="primary", use_container_width=True):
                if m_title.strip() and m_assignee:
                    with st.spinner("Saving reminder..."):
                        task_id = f"REM-{random.randint(100000, 999999)}"
                        assigned_dept = users_df[users_df["NAME"].astype(str) == m_assignee]["DEPARTMENT"].values[0]
                        created_str = now_ist().strftime("%d/%m/%Y, %I:%M:%S %p")
                        deadline_str = f"Monthly on Day {m_date}"
                        priority = "🟢 Regular"

                        task_dict = {
                            "Task ID": task_id,
                            "Title": f"Monthly: {m_title.strip()}",
                            "Description": f"Recurring Monthly Reminder on Day {m_date}",
                            "Assigned By": user["name"],
                            "Assigned Dept": assigned_dept,
                            "Assigned To": str(m_assignee).strip().upper(),
                            "Created": created_str,
                            "Deadline": deadline_str,
                            "Status": "Assigned",
                            "Attachments": "",
                            "Review Notes": "",
                            "Priority": priority,
                            "ItemType": "Reminder",
                            "Submitted At": ""
                        }
                        append_task(task_dict)

                        assignee_row = users_df[users_df["NAME"].astype(str) == m_assignee]
                        telegram_id = assignee_row["TELEGRAM_ID"].values[0] if "TELEGRAM_ID" in assignee_row.columns else None
                        if pd.notna(telegram_id) and str(telegram_id).strip() != "":
                            send_telegram_alert(
                                telegram_id,
                                f"Monthly: {m_title.strip()}",
                                user["name"],
                                deadline_str,
                                f"Recurring Monthly Reminder on Day {m_date}",
                                priority,
                                m_assignee,
                                assigned_dept
                            )
                        fetch_data.clear()
                    st.success(f"✅ Monthly reminder '{m_title}' set for {m_assignee}!")
                    st.toast("Monthly reminder saved!", icon="⏰")
                else:
                    st.error("Please enter a title.")
