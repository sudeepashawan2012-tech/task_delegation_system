import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, timezone, timedelta, time as dt_time
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

# Embedded SVG Data URIs for Paperclip & Blue Recycle Bin icons
ICON_PAPERCLIP = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%231D4ED8' stroke-width='2.3' stroke-linecap='round' stroke-linejoin='round'><path d='M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48'/></svg>"
ICON_TRASH = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%232563EB'><path d='M9 3h6a1 1 0 0 1 1 1v1h4a1 1 0 1 1 0 2h-1l-1 13a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 7H3a1 1 0 1 1 0-2h4V4a1 1 0 0 1 1-1zm1 2h4V4h-4v1zm-1 5a1 1 0 0 0-1 1v6a1 1 0 1 0 2 0v-6a1 1 0 0 0-1-1zm6 0a1 1 0 0 0-1 1v6a1 1 0 1 0 2 0v-6a1 1 0 0 0-1-1z'/></svg>"

st.markdown("""
    <style>
        /* Remove wasted top/side blank space on mobile phones */
        .block-container {
            padding-top: 0.8rem !important;
            padding-bottom: 3.5rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            max-width: 720px !important;
        }

        /* Make standard text sharp without breaking Streamlit's built-in material icons */
        body, p, label, h1, h2, h3 {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
            color: #111827;
        }

        /* Prevent Streamlit columns from stacking into giant full-width bars on mobile */
        div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 6px !important;
            align-items: center !important;
        }
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"],
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            min-width: 0 !important;
            width: auto !important;
            flex: 1 1 0% !important;
        }

        /* Prominent Top-Level & Sub-Level Tabs - Fitted so 4-5 tabs never cut off on mobile */
        div[data-baseweb="tab-list"] {
            gap: 4px !important;
            background-color: #F1F5F9;
            padding: 5px;
            border-radius: 10px;
            overflow-x: auto !important;
            flex-wrap: nowrap !important;
            scrollbar-width: none;
        }
        div[data-baseweb="tab-list"]::-webkit-scrollbar {
            display: none;
        }
        button[data-baseweb="tab"] {
            font-size: 13px !important;
            font-weight: 700 !important;
            padding: 7px 9px !important;
            border-radius: 7px !important;
            background-color: transparent !important;
            white-space: nowrap !important;
            flex-shrink: 0 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            background-color: #1E3A8A !important;
            color: #FFFFFF !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.15);
        }
        button[data-baseweb="tab"][aria-selected="true"] p {
            color: #FFFFFF !important;
            font-weight: 800 !important;
            font-size: 13px !important;
        }

        /* High-visibility input boxes */
        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
            font-size: 15px !important;
            font-weight: 500 !important;
            border-radius: 8px !important;
        }

        /* Enlarge Voice Note Recorder on Mobile */
        [data-testid="stAudioInput"] {
            border: 2px dashed #2563EB !important;
            border-radius: 12px !important;
            padding: 8px !important;
            background-color: #EFF6FF !important;
        }

        /* Compact, thumb-friendly buttons that fit side-by-side on mobile */
        .stButton > button {
            border-radius: 8px !important;
            font-weight: 700 !important;
            font-size: 13px !important;
            min-height: 36px !important;
            padding: 4px 8px !important;
            line-height: 1.2 !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.10) !important;
            white-space: nowrap !important;
        }

        /* Blue Paperclip Attachment Button */
        div[class*="st-key-att_"] button {
            background-color: #DBEAFE !important;
            color: #1D4ED8 !important;
            border: 1.5px solid #3B82F6 !important;
            font-weight: 800 !important;
            min-height: 34px !important;
            padding: 2px 8px !important;
        }

        /* Green Seen / Acknowledge Button */
        div[class*="st-key-ack_"] button {
            background-color: #DCFCE7 !important;
            color: #15803D !important;
            border: 1.5px solid #22C55E !important;
            font-weight: 800 !important;
            min-height: 34px !important;
            padding: 2px 8px !important;
        }

        /* Red Recycle Bin Delete Button */
        div[class*="st-key-del_"] button {
            background-color: #FEE2E2 !important;
            color: #DC2626 !important;
            border: 1.5px solid #EF4444 !important;
            font-weight: 800 !important;
            min-height: 34px !important;
            padding: 2px 8px !important;
        }

        /* Task Card Custom Styling - Mobile-Safe Flexbox so badges NEVER split across lines */
        .task-card-top {
            display: flex;
            flex-direction: column;
            gap: 6px;
            margin-bottom: 6px;
        }
        .task-card-title {
            font-size: 17px;
            font-weight: 800;
            color: #0F172A;
            line-height: 1.3;
            word-break: break-word;
        }
        .badge-row {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            align-items: center;
        }
        .chip-badge {
            display: inline-flex;
            align-items: center;
            white-space: nowrap !important;
            padding: 3px 7px;
            border-radius: 6px;
            font-size: 11.5px;
            font-weight: 800;
            line-height: 1.2;
        }
        .chip-id {
            color: #475569;
            background: #F1F5F9;
            border: 1px solid #CBD5E1;
        }
        .chip-high {
            background: #FEE2E2;
            color: #DC2626;
            border: 1px solid #FCA5A5;
        }
        .chip-reg {
            background: #DCFCE7;
            color: #15803D;
            border: 1px solid #86EFAC;
        }
        .chip-overdue {
            background: #DC2626;
            color: #FFFFFF;
            border: 1px solid #B91C1C;
        }
        .chip-review {
            background: #E0E7FF;
            color: #1D4ED8;
            border: 1px solid #93C5FD;
        }
        .chip-marked {
            background: #FEF3C7;
            color: #B45309;
            border: 1px solid #FCD34D;
        }
        .chip-seen {
            background: #ECFDF5;
            color: #047857;
            border: 1px solid #6EE7B7;
        }
        .chip-unseen {
            background: #FFF7ED;
            color: #C2410C;
            border: 1px solid #FDBA74;
        }

        .route-banner {
            font-size: 13.5px;
            font-weight: 700;
            color: #1E3A8A;
            background-color: #EFF6FF;
            padding: 6px 9px;
            border-radius: 6px;
            margin: 4px 0;
            border-left: 4px solid #2563EB;
            word-break: break-word;
        }
        .task-desc-box {
            font-size: 14.5px;
            font-weight: 500;
            color: #1F2937;
            background-color: #FAFAFA;
            padding: 7px 9px;
            border-radius: 6px;
            border: 1px solid #E5E7EB;
            margin: 4px 0;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .meta-grid {
            font-size: 13px;
            font-weight: 600;
            line-height: 1.55;
            margin-top: 4px;
            color: #1F2937;
        }
        .att-pill {
            display: inline-block;
            margin-top: 6px;
            padding: 5px 9px;
            background-color: #DBEAFE;
            color: #1E40AF;
            border-radius: 6px;
            font-size: 12.5px;
            font-weight: 700;
            border: 1px solid #93C5FD;
            word-break: break-word;
        }
        .thread-container {
            margin-top: 8px;
            padding: 8px;
            background-color: #F8FAFC;
            border: 1px solid #CBD5E1;
            border-left: 4px solid #1E3A8A;
            border-radius: 6px;
            max-height: 200px;
            overflow-y: auto;
        }
        .thread-msg {
            font-size: 13.5px;
            font-weight: 500;
            color: #111827;
            padding: 6px 8px;
            margin-bottom: 5px;
            background: #FFFFFF;
            border-radius: 6px;
            border: 1px solid #E2E8F0;
            word-wrap: break-word;
            white-space: pre-wrap;
            line-height: 1.35;
        }
        .stats-strip {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 4px;
            background: linear-gradient(90deg, #1E3A8A 0%, #2563EB 100%);
            color: white;
            padding: 8px 6px;
            border-radius: 10px;
            margin-bottom: 10px;
            font-weight: 700;
            font-size: 12px;
            box-shadow: 0 2px 6px rgba(30, 58, 138, 0.2);
        }
        .stats-item {
            color: #FFFFFF !important;
            text-align: center;
            white-space: nowrap;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONSTANTS & CREDENTIALS
# ==========================================
SHEET_ID = st.secrets.get("SHEET_ID", "1oKei6r42q5zH4g-014bNEZfMRkzdm-MoOUwU5GUbsZk")
FOLDER_ID = st.secrets.get("FOLDER_ID", "1-p5zcpZa8vXtpPLMx7y4JoMsGEOYSEaR")
TELEGRAM_BOT_TOKEN = st.secrets["TELEGRAM_BOT_TOKEN"]
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
    "Review Notes", "Priority", "ItemType", "Submitted At",
    "Acknowledged", "Last Reminded"
]

@st.cache_data(ttl=25)
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
            "Submitted At": "",
            "Acknowledged": "",
            "Last Reminded": ""
        }
        for col, default_val in defaults.items():
            if col not in df.columns:
                df[col] = default_val
            else:
                df[col] = df[col].fillna(default_val).replace(
                    "", default_val if col in ["Priority", "ItemType"] else ""
                )

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
# 4. TELEGRAM NOTIFICATION + SEEN ACKNOWLEDGMENT
# ==========================================
def send_telegram_alert(
    chat_id,
    task_id,
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

    # Exact template structure requested by user + Inline Acknowledge Button
    message = (
        f"🚨Title: {task_title}\n"
        f"🏢 From: {assigned_by}\n"
        f"👤 For: {assignee_name.upper()} ({assignee_dept} Dept)\n"
        f"📌 Priority: {priority}\n"
        f"📅 Deadline: {deadline}\n\n"
        f"📝 Details:\n{details_text}\n\n"
        f"👇 Please tap below to confirm you have seen this task:"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": str(chat_id).strip(),
        "text": message,
        "reply_markup": {
            "inline_keyboard": [[
                {
                    "text": "👁️ Acknowledge / Seen",
                    "callback_data": f"ack|{task_id}|{assignee_name.strip().upper()}"
                }
            ]]
        }
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass

def sync_telegram_acknowledgments():
    """
    Fallback polling sync if Telegram webhook is not set yet.
    If webhook IS set to GAS_WEBAPP_URL, Code.gs processes 'ack|...' callbacks in real time
    and getUpdates safely returns without doing anything.
    """
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        resp = requests.get(url, params={"timeout": 1, "allowed_updates": '["callback_query"]'}, timeout=4)
        if resp.status_code != 200:
            return False
        data = resp.json()
        if not data.get("ok") or not data.get("result"):
            return False

        updated_any = False
        last_update_id = None
        for item in data["result"]:
            last_update_id = item.get("update_id")
            cb = item.get("callback_query")
            if not cb:
                continue
            cb_data = str(cb.get("data", ""))
            if cb_data.startswith("ack|"):
                parts = cb_data.split("|")
                if len(parts) >= 2:
                    t_id = parts[1].strip()
                    who = parts[2].strip() if len(parts) > 2 else "Assignee"
                    ack_time = now_ist().strftime("%d/%m/%Y, %I:%M %p")
                    ack_val = f"Seen by {who} at {ack_time}"
                    update_task_fields(t_id, {"Acknowledged": ack_val})
                    updated_any = True

                    # Answer callback & update Telegram message button
                    cb_id = cb.get("id")
                    requests.post(
                        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery",
                        json={"callback_query_id": cb_id, "text": f"✅ Acknowledged at {ack_time}!"},
                        timeout=4
                    )
                    msg_obj = cb.get("message", {})
                    chat_id = msg_obj.get("chat", {}).get("id")
                    msg_id = msg_obj.get("message_id")
                    orig_text = msg_obj.get("text", "").replace("👇 Please tap below to confirm you have seen this task:", "").strip()
                    if chat_id and msg_id:
                        requests.post(
                            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText",
                            json={
                                "chat_id": chat_id,
                                "message_id": msg_id,
                                "text": f"{orig_text}\n\n✅ {ack_val}"
                            },
                            timeout=4
                        )

        if last_update_id is not None:
            requests.get(url, params={"offset": last_update_id + 1}, timeout=3)
        return updated_any
    except Exception:
        return False

def setup_automation_bridge():
    """Registers Telegram Webhook to GAS_WEBAPP_URL and activates 15-min Recurring Reminder Trigger in Apps Script."""
    results = []
    if GAS_WEBAPP_URL.startswith("http"):
        # 1. Register Telegram Webhook so '👁️ Acknowledge / Seen' works 24/7 instantly
        try:
            wh_resp = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
                json={"url": GAS_WEBAPP_URL},
                timeout=10
            ).json()
            if wh_resp.get("ok"):
                results.append("✅ Telegram 'Seen' Webhook connected")
        except Exception as e:
            results.append(f"⚠️ Webhook error: {e}")

        # 2. Ask GAS Bridge to install the 15-minute Time-Driven Cron Trigger & store Bot Token
        try:
            gas_resp = requests.post(
                GAS_WEBAPP_URL,
                json={
                    "action": "setup_automation",
                    "botToken": TELEGRAM_BOT_TOKEN,
                    "sheetId": SHEET_ID
                },
                timeout=20
            ).json()
            if gas_resp.get("status") == "success":
                results.append("✅ 24/7 Auto-Reminders Cron Trigger activated")
            else:
                results.append(f"⚠️ GAS Trigger note: {gas_resp.get('message', 'Update Code.gs deployment')}")
        except Exception:
            results.append("ℹ️ Make sure latest Code.gs is deployed as Web App")
    return " | ".join(results)

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

    # Sync any pending Telegram "Acknowledge / Seen" clicks
    if sync_telegram_acknowledgments():
        fetch_data.clear()

    # Compact Mobile Top User Bar (Stays on 1 row on mobile)
    top_c1, top_c2, top_c3 = st.columns([0.54, 0.23, 0.23])
    with top_c1:
        st.markdown(
            f"<div style='font-size:15px; font-weight:800; color:#1E3A8A; line-height:1.2;'>👤 {user['name']}<br>"
            f"<span style='font-size:11.5px; font-weight:600; color:#475569;'>{user['role']} | {user['dept']}</span></div>",
            unsafe_allow_html=True
        )
    with top_c2:
        if st.button("🔄 Refresh", use_container_width=True):
            sync_telegram_acknowledgments()
            fetch_data.clear()
            fetch_attachments_from_drive.clear()
            st.rerun()
    with top_c3:
        if st.button("🚪 Logout", key="top_logout", use_container_width=True):
            st.session_state.user = None
            st.rerun()

    # Sidebar for Bulk Maintenance & 1-Click Automation Setup
    with st.sidebar:
        st.markdown(f"### 👤 {user['name']}")
        st.caption(f"**{user['role']}** | {user['dept']}")
        st.divider()
        st.markdown(
            f"<div style='margin-bottom:6px; font-weight:800; color:#1E3A8A;'>"
            f"<img src=\"{ICON_TRASH}\" style='width:18px; vertical-align:middle; margin-right:6px;'/>"
            f"Maintenance & Automation</div>",
            unsafe_allow_html=True
        )
        if st.button("🗑️ Clear Completed Tasks", use_container_width=True):
            with st.spinner("Cleaning up completed tasks..."):
                clear_all_completed_tasks(user["name"], user["role"])
                fetch_data.clear()
            st.toast("Completed tasks cleared!", icon="🧹")
            st.rerun()

        st.write("")
        if st.button("⚡ Activate Telegram 'Seen' & Auto-Reminders", use_container_width=True):
            with st.spinner("Connecting Telegram Webhook & 24/7 Reminder Cron..."):
                msg = setup_automation_bridge()
            st.success(msg)

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
                tasks_df["is_unseen"] = (
                    (tasks_df["Status"].astype(str).str.strip() != "Completed") &
                    (tasks_df["Acknowledged"].astype(str).str.strip() == "")
                )

                active_df = tasks_df[tasks_df["Status"].astype(str).str.strip() == "Assigned"]
                unseen_df = tasks_df[tasks_df["is_unseen"] == True]
                overdue_df = tasks_df[tasks_df["is_overdue"] == True]
                review_df = tasks_df[tasks_df["Status"].astype(str).str.strip().isin(["Under Review", "Marked Complete"])]
                done_df = tasks_df[tasks_df["Status"].astype(str).str.strip() == "Completed"]

                # Mobile Quick-Stats Strip (Includes Unseen Count!)
                st.markdown(f"""
                    <div class='stats-strip'>
                        <div class='stats-item'>📌 Act: {len(active_df)}</div>
                        <div class='stats-item'>🙈 Unseen: {len(unseen_df)}</div>
                        <div class='stats-item'>🚨 Late: {len(overdue_df)}</div>
                        <div class='stats-item'>⏳ Rev: {len(review_df)}</div>
                        <div class='stats-item'>✅ Done: {len(done_df)}</div>
                    </div>
                """, unsafe_allow_html=True)

                sub_tab1, sub_tab_unseen, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
                    f"📌 Active ({len(active_df)})",
                    f"👁️ Seen Report ({len(unseen_df)} Unseen)",
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
                    ack_status = str(row.get("Acknowledged", "")).strip()
                    last_reminded = str(row.get("Last Reminded", "")).strip()
                    is_overdue = bool(row.get("is_overdue", False))

                    # Non-breaking Flexbox Badges (Never split across lines on mobile!)
                    if "High" in priority:
                        prio_badge = "<span class='chip-badge chip-high'>🔴 HIGH PRIORITY</span>"
                    else:
                        prio_badge = "<span class='chip-badge chip-reg'>🟢 Regular</span>"

                    status_badge = ""
                    if is_overdue:
                        status_badge = "<span class='chip-badge chip-overdue'>🚨 OVERDUE</span>"
                    elif status == "Marked Complete":
                        status_badge = "<span class='chip-badge chip-marked'>✔️ Marked Complete</span>"
                    elif status == "Under Review":
                        status_badge = "<span class='chip-badge chip-review'>⏳ Waiting Review</span>"

                    # Seen / Acknowledge Badge
                    if ack_status:
                        seen_badge = f"<span class='chip-badge chip-seen'>👁️ {html.escape(ack_status)}</span>"
                    else:
                        seen_badge = "<span class='chip-badge chip-unseen'>🙈 Not Seen Yet</span>"

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
                        submitted_html = f"<div>📤 <b>Submitted At:</b> {html.escape(submitted_at)} {time_tag}</div>"

                    last_rem_html = f"<div>🔔 <b>Last Auto-Alert Sent:</b> {html.escape(last_reminded)}</div>" if last_reminded else ""

                    # Instant Attachment Indicator
                    att_indicator_html = ""
                    if att_summary:
                        att_indicator_html = (
                            f"<div class='att-pill'>"
                            f"<img src=\"{ICON_PAPERCLIP}\" style='width:14px; vertical-align:middle; margin-right:4px;'/>"
                            f"Sent by {html.escape(assigned_by)}: {html.escape(att_summary)}</div>"
                        )

                    # Clean Multi-Line Conversation Thread
                    thread_html = ""
                    if review_notes:
                        cleaned_notes = review_notes.replace("<br>", " ").replace("<b>", "").replace("</b>", "")
                        entries = [e.strip() for e in cleaned_notes.split(" | ") if e.strip()]
                        bubbles = "".join([f"<div class='thread-msg'>💬 {html.escape(entry)}</div>" for entry in entries])
                        thread_html = (
                            f"<div class='thread-container'>"
                            f"<div style='font-size:12.5px; font-weight:800; color:#1E3A8A; margin-bottom:5px;'>📋 Remarks & Review Thread ({len(entries)}):</div>"
                            f"{bubbles}</div>"
                        )

                    with st.container(border=True):
                        created_line = f"<div>🕒 <b>Assigned On:</b> {html.escape(created_at)}</div>" if created_at else ""
                        deadline_color = "#DC2626" if is_overdue else "#B45309"

                        # 100% Full-Width Card Content (Never squeezed or cut off on mobile)
                        card_html = (
                            f"<div class='task-card-top'>"
                            f"  <div class='task-card-title'>{title_txt}</div>"
                            f"  <div class='badge-row'>"
                            f"    <span class='chip-badge chip-id'>{html.escape(task_id)}</span>"
                            f"    {prio_badge}{status_badge}{seen_badge}"
                            f"  </div>"
                            f"</div>"
                            f"<div class='route-banner'>🏢 From: {html.escape(assigned_by)} &nbsp;➡️&nbsp; 👷 To: {html.escape(assigned_to)} ({assigned_dept})</div>"
                            f"<div class='task-desc-box'>{desc_txt if desc_txt else 'No extra details provided.'}</div>"
                            f"<div class='meta-grid'>"
                            f"{created_line}"
                            f"<div style='color:{deadline_color};'>📅 <b>Deadline:</b> {html.escape(deadline_at)}</div>"
                            f"{last_rem_html}"
                            f"{submitted_html}"
                            f"</div>"
                            f"{att_indicator_html}"
                            f"{thread_html}"
                        )
                        st.markdown(card_html, unsafe_allow_html=True)

                        # Compact Horizontal Action Strip (Stays side-by-side on mobile, never giant stacked bars!)
                        can_delete = (assigned_by == user["name"]) or (user["role"] in ["CEO", "GM"])
                        can_ack = (user["name"] == assigned_to) and (not ack_status)

                        btn_specs = ["att"]
                        if can_ack:
                            btn_specs.append("ack")
                        if can_delete:
                            btn_specs.append("del")

                        btn_cols = st.columns(len(btn_specs))
                        for idx_b, b_type in enumerate(btn_specs):
                            with btn_cols[idx_b]:
                                if b_type == "att":
                                    toggle_key = f"{tab_prefix}_{task_id}"
                                    att_label = "📎 Files" if not att_summary else f"📎 Files ({att_summary})"
                                    if st.button(att_label, key=f"att_{toggle_key}", help="Open Assigner's Files & Voice Notes", use_container_width=True):
                                        st.session_state.open_attachments[toggle_key] = not st.session_state.open_attachments.get(toggle_key, False)
                                elif b_type == "ack":
                                    if st.button("👁️ Mark Seen", key=f"ack_{tab_prefix}_{task_id}", help="Acknowledge that you have seen this task", use_container_width=True):
                                        ack_time = now_ist().strftime("%d/%m/%Y, %I:%M %p")
                                        update_task_fields(task_id, {"Acknowledged": f"Seen by {user['name']} at {ack_time}"})
                                        fetch_data.clear()
                                        st.toast("Task marked as Seen!", icon="👁️")
                                        st.rerun()
                                elif b_type == "del":
                                    if st.button("🗑️ Delete", key=f"del_{tab_prefix}_{task_id}", help="Delete Task Permanently", use_container_width=True):
                                        with st.spinner("Deleting..."):
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
                        if status == "Assigned" and user["name"] == assigned_to:
                            st.divider()
                            user_msg = st.text_input(
                                f"✍️ Write Remark to {assigned_by}:",
                                key=f"msg_{tab_prefix}_{task_id}",
                                placeholder="Type your remark before submitting..."
                            )
                            act_col1, act_col2 = st.columns(2)
                            with act_col1:
                                if st.button("📤 Submit Review", key=f"sub_{tab_prefix}_{task_id}", use_container_width=True):
                                    current_str = now_ist().strftime("%d/%m/%Y, %I:%M:%S %p")
                                    remark_text = user_msg.strip() if user_msg.strip() else "Submitted for review."
                                    new_entry = f"[{user['name']} Submitted for Review at {current_str}]: {remark_text}"
                                    updated_notes = f"{review_notes} | {new_entry}" if review_notes else new_entry
                                    ack_val = ack_status if ack_status else f"Seen by {user['name']} at {current_str}"

                                    update_task_fields(task_id, {
                                        "Status": "Under Review",
                                        "Review Notes": updated_notes,
                                        "Submitted At": current_str,
                                        "Acknowledged": ack_val
                                    })
                                    fetch_data.clear()
                                    st.toast("Submitted for review!", icon="📤")
                                    st.rerun()

                            with act_col2:
                                if st.button("✅ Mark Done", key=f"direct_done_{tab_prefix}_{task_id}", use_container_width=True, type="primary"):
                                    current_str = now_ist().strftime("%d/%m/%Y, %I:%M:%S %p")
                                    remark_text = user_msg.strip() if user_msg.strip() else "Marked as completed."
                                    new_entry = f"[{user['name']} Marked Completed at {current_str}]: {remark_text}"
                                    updated_notes = f"{review_notes} | {new_entry}" if review_notes else new_entry
                                    ack_val = ack_status if ack_status else f"Seen by {user['name']} at {current_str}"

                                    update_task_fields(task_id, {
                                        "Status": "Marked Complete",
                                        "Review Notes": updated_notes,
                                        "Submitted At": current_str,
                                        "Acknowledged": ack_val
                                    })
                                    fetch_data.clear()
                                    st.toast(f"Marked completed! Sent to {assigned_by} for verification.", icon="✅")
                                    st.rerun()

                        elif status in ["Under Review", "Marked Complete"]:
                            if user["name"] == assigned_by:
                                st.divider()
                                st.caption(f"🔔 **{assigned_to}** submitted this task. Verify and close, or send back:")
                                manager_reply = st.text_input(
                                    f"💬 Reply to {assigned_to}:",
                                    key=f"reply_{tab_prefix}_{task_id}",
                                    placeholder="Write feedback or closing note..."
                                )
                                b1, b2 = st.columns(2)
                                with b1:
                                    if st.button("✅ Approve & Close", key=f"app_{tab_prefix}_{task_id}", use_container_width=True, type="primary"):
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
                                    if st.button("↩️ Send Back", key=f"ret_{tab_prefix}_{task_id}", use_container_width=True):
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

                with sub_tab_unseen:
                    st.markdown("##### 👁️ Telegram & Portal Acknowledgment Report")
                    seen_filter = st.radio(
                        "Filter Seen Status:",
                        [f"🙈 Unseen / Not Acknowledged ({len(unseen_df)})", "✅ Acknowledged / Seen"],
                        horizontal=True,
                        label_visibility="collapsed"
                    )
                    if "Unseen" in seen_filter:
                        target_seen_df = sort_by_priority(unseen_df)
                        if target_seen_df.empty:
                            st.success("🎉 Every active task has been seen & acknowledged!")
                        for _, row in target_seen_df.iterrows():
                            render_task_card(row, "uns")
                    else:
                        ack_df = tasks_df[tasks_df["Acknowledged"].astype(str).str.strip() != ""]
                        target_seen_df = sort_by_priority(ack_df)
                        if target_seen_df.empty:
                            st.caption("No acknowledged tasks yet.")
                        for _, row in target_seen_df.iterrows():
                            render_task_card(row, "ackd")

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
                            "Submitted At": "",
                            "Acknowledged": "",
                            "Last Reminded": ""
                        }
                        append_task(task_dict)

                        assignee_row = users_df[users_df["NAME"].astype(str) == assignee]
                        telegram_id = assignee_row["TELEGRAM_ID"].values[0] if "TELEGRAM_ID" in assignee_row.columns else None
                        if pd.notna(telegram_id) and str(telegram_id).strip() != "":
                            send_telegram_alert(
                                telegram_id,
                                task_id,
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
        st.caption("Recurring reminders automatically trigger Telegram alerts on schedule via Google Apps Script.")
        rem_tab1, rem_tab2, rem_tab3 = st.tabs(["📅 Daily", "📆 Weekly", "🗓️ Monthly"])
        users_df = fetch_data("User_list")
        assignees_list = users_df["NAME"].astype(str).tolist() if not users_df.empty else []

        with rem_tab1:
            d_title = st.text_input("Daily Routine Title", key="d_title")
            d_time = st.time_input("Alert Time (IST)", value=dt_time(10, 0), key="d_time")
            d_assignee = st.selectbox("Assign To", assignees_list, key="d_assignee")

            if st.button("⏰ Save Daily Reminder", type="primary", use_container_width=True):
                if d_title.strip() and d_assignee:
                    with st.spinner("Saving reminder..."):
                        task_id = f"REM-{random.randint(100000, 999999)}"
                        assigned_dept = users_df[users_df["NAME"].astype(str) == d_assignee]["DEPARTMENT"].values[0]
                        created_str = now_ist().strftime("%d/%m/%Y, %I:%M:%S %p")
                        deadline_str = f"Daily at {d_time.strftime('%I:%M %p')}"
                        today_tag = now_ist().strftime("%d/%m/%Y")
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
                            "Submitted At": "",
                            "Acknowledged": "",
                            "Last Reminded": today_tag
                        }
                        append_task(task_dict)

                        assignee_row = users_df[users_df["NAME"].astype(str) == d_assignee]
                        telegram_id = assignee_row["TELEGRAM_ID"].values[0] if "TELEGRAM_ID" in assignee_row.columns else None
                        if pd.notna(telegram_id) and str(telegram_id).strip() != "":
                            send_telegram_alert(
                                telegram_id,
                                task_id,
                                f"Daily: {d_title.strip()}",
                                user["name"],
                                deadline_str,
                                "Recurring Daily Reminder",
                                priority,
                                d_assignee,
                                assigned_dept
                            )
                        fetch_data.clear()
                    st.success(f"✅ Daily reminder '{d_title}' set for {d_assignee} ({deadline_str})!")
                    st.toast("Daily reminder saved!", icon="⏰")
                else:
                    st.error("Please enter a title.")

        with rem_tab2:
            w_title = st.text_input("Weekly Routine Title", key="w_title")
            w_c1, w_c2 = st.columns(2)
            with w_c1:
                w_day = st.selectbox("Day of Week", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], key="w_day")
            with w_c2:
                w_time = st.time_input("Alert Time (IST)", value=dt_time(10, 0), key="w_time")
            w_assignee = st.selectbox("Assign To", assignees_list, key="w_assignee")

            if st.button("⏰ Save Weekly Reminder", type="primary", use_container_width=True):
                if w_title.strip() and w_assignee:
                    with st.spinner("Saving reminder..."):
                        task_id = f"REM-{random.randint(100000, 999999)}"
                        assigned_dept = users_df[users_df["NAME"].astype(str) == w_assignee]["DEPARTMENT"].values[0]
                        created_str = now_ist().strftime("%d/%m/%Y, %I:%M:%S %p")
                        deadline_str = f"Every {w_day} at {w_time.strftime('%I:%M %p')}"
                        today_tag = now_ist().strftime("%d/%m/%Y")
                        priority = "🟢 Regular"

                        task_dict = {
                            "Task ID": task_id,
                            "Title": f"Weekly: {w_title.strip()}",
                            "Description": f"Recurring Weekly Reminder ({deadline_str})",
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
                            "Submitted At": "",
                            "Acknowledged": "",
                            "Last Reminded": today_tag
                        }
                        append_task(task_dict)

                        assignee_row = users_df[users_df["NAME"].astype(str) == w_assignee]
                        telegram_id = assignee_row["TELEGRAM_ID"].values[0] if "TELEGRAM_ID" in assignee_row.columns else None
                        if pd.notna(telegram_id) and str(telegram_id).strip() != "":
                            send_telegram_alert(
                                telegram_id,
                                task_id,
                                f"Weekly: {w_title.strip()}",
                                user["name"],
                                deadline_str,
                                f"Recurring Weekly Reminder ({deadline_str})",
                                priority,
                                w_assignee,
                                assigned_dept
                            )
                        fetch_data.clear()
                    st.success(f"✅ Weekly reminder '{w_title}' set for {w_assignee} ({deadline_str})!")
                    st.toast("Weekly reminder saved!", icon="⏰")
                else:
                    st.error("Please enter a title.")

        with rem_tab3:
            m_title = st.text_input("Monthly Routine Title", key="m_title")
            m_c1, m_c2 = st.columns(2)
            with m_c1:
                m_date = st.slider("Day of Month", 1, 31, 1, key="m_date")
            with m_c2:
                m_time = st.time_input("Alert Time (IST)", value=dt_time(10, 0), key="m_time")
            m_assignee = st.selectbox("Assign To", assignees_list, key="m_assignee")

            if st.button("⏰ Save Monthly Reminder", type="primary", use_container_width=True):
                if m_title.strip() and m_assignee:
                    with st.spinner("Saving reminder..."):
                        task_id = f"REM-{random.randint(100000, 999999)}"
                        assigned_dept = users_df[users_df["NAME"].astype(str) == m_assignee]["DEPARTMENT"].values[0]
                        created_str = now_ist().strftime("%d/%m/%Y, %I:%M:%S %p")
                        deadline_str = f"Monthly on Day {m_date} at {m_time.strftime('%I:%M %p')}"
                        today_tag = now_ist().strftime("%d/%m/%Y")
                        priority = "🟢 Regular"

                        task_dict = {
                            "Task ID": task_id,
                            "Title": f"Monthly: {m_title.strip()}",
                            "Description": f"Recurring Monthly Reminder ({deadline_str})",
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
                            "Submitted At": "",
                            "Acknowledged": "",
                            "Last Reminded": today_tag
                        }
                        append_task(task_dict)

                        assignee_row = users_df[users_df["NAME"].astype(str) == m_assignee]
                        telegram_id = assignee_row["TELEGRAM_ID"].values[0] if "TELEGRAM_ID" in assignee_row.columns else None
                        if pd.notna(telegram_id) and str(telegram_id).strip() != "":
                            send_telegram_alert(
                                telegram_id,
                                task_id,
                                f"Monthly: {m_title.strip()}",
                                user["name"],
                                deadline_str,
                                f"Recurring Monthly Reminder ({deadline_str})",
                                priority,
                                m_assignee,
                                assigned_dept
                            )
                        fetch_data.clear()
                    st.success(f"✅ Monthly reminder '{m_title}' set for {m_assignee} ({deadline_str})!")
                    st.toast("Monthly reminder saved!", icon="⏰")
                else:
                    st.error("Please enter a title.")
