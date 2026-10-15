import streamlit as st
import gspread
import pandas as pd
from datetime import datetime
import random
import requests
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from streamlit_mic_recorder import mic_recorder

# Mobile-first configuration
st.set_page_config(page_title="Task Portal", page_icon="📋", layout="centered", initial_sidebar_state="collapsed")

# Constants
SHEET_ID = "1oKei6r42q5zH4g-014bNEZfMRkzdm-MoOUwU5GUbsZk"
FOLDER_ID = "1-p5zcpZa8vXtpPLMx7y4JoMsGEOYSEaR" 
TELEGRAM_BOT_TOKEN = "8815285939:AAFN2XvB6MGep9_GBwjdF359B97wTp1y6io"

@st.cache_resource
def get_gcp_services():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, 
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(creds)
    drive_service = build('drive', 'v3', credentials=creds)
    return client, drive_service

gs_client, drive_service = get_gcp_services()

@st.cache_data(ttl=60) 
def fetch_data(sheet_name):
    sheet = gs_client.open_by_key(SHEET_ID).worksheet(sheet_name)
    return pd.DataFrame(sheet.get_all_records())

def append_task(task_data):
    sheet = gs_client.open_by_key(SHEET_ID).worksheet("Tasks")
    sheet.append_row(task_data)

from googleapiclient.errors import HttpError

def upload_bytes_to_drive(file_bytes, filename, mimetype):
    try:
        file_metadata = {'name': filename, 'parents': [FOLDER_ID]}
        # Set resumable=False for small in-memory byte uploads to avoid next_chunk() crashes
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mimetype, resumable=False)
        
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id',
            supportsAllDrives=True  # Required if using Shared Drives
        ).execute()
        return file.get('id')
        
    except HttpError as e:
        # Prints the exact Google API error on screen instead of Streamlit redacting it
        st.error(f"Google Drive API Error ({e.resp.status}): {e._get_reason()}")
        st.stop()

def send_telegram_alert(chat_id, task_title, assigned_by, deadline, description):
    if not chat_id:
        return
    message = (
        f"🚨 *New Task Assigned!*\n\n"
        f"📋 *Task:* {task_title}\n"
        f"🏢 *From:* {assigned_by}\n"
        f"📅 *Deadline:* {deadline}\n\n"
        f"📝 *Details:*\n_{description}_"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": str(chat_id).strip(), "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

# State Management
if 'user' not in st.session_state:
    st.session_state.user = None

# ==========================================
# LOGIN SCREEN
# ==========================================
if st.session_state.user is None:
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>Task Portal</h1>", unsafe_allow_html=True)
    
    st.write("") 
    with st.container(border=True):
        username = st.text_input("Employee Name").strip().upper()
        password = st.text_input("Password", type="password")
        
        if st.button("Secure Login", use_container_width=True, type="primary"):
            users_df = fetch_data("User_list")
            user_match = users_df[(users_df['NAME'] == username) & (users_df['PASSWORD'].astype(str) == str(password))]
            
            if not user_match.empty:
                user_info = user_match.iloc[0]
                st.session_state.user = {'name': user_info['NAME'], 'dept': user_info['DEPARTMENT'], 'role': user_info['ROLE']}
                st.rerun()
            else:
                st.error("Invalid Name or Password")

# ==========================================
# MAIN DASHBOARD
# ==========================================
else:
    user = st.session_state.user

    with st.sidebar:
        st.markdown(f"### 👤 {user['name']}")
        st.caption(f"**{user['role']}** | {user['dept']}")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user = None
            st.rerun()
            
        st.divider()

        # Task Creation Section
        if user['role'] in ['CEO', 'GM', 'HOD']:
            st.markdown("### ➕ Assign New Task")
            
            title = st.text_input("Task Title", key="t_title")
            desc = st.text_area("Details", key="t_desc", height=80)
            
            users_df = fetch_data("User_list")
            
            # Smart Dropdown for CEO/GM to prevent excessive scrolling
            if user['role'] in ['CEO', 'GM']:
                departments = ["All"] + users_df['DEPARTMENT'].unique().tolist()
                dept_filter = st.selectbox("Filter Department", departments)
                if dept_filter == "All":
                    assignees = users_df['NAME'].tolist()
                else:
                    assignees = users_df[users_df['DEPARTMENT'] == dept_filter]['NAME'].tolist()
            else:
                assignees = users_df[users_df['DEPARTMENT'] == user['dept']]['NAME'].tolist()
            
            assignee = st.selectbox("Assign To", assignees, key="t_assignee")
            
            # Exact Date & Time formatting
            col_d, col_t = st.columns(2)
            with col_d:
                deadline_d = st.date_input("Deadline Date")
            with col_t:
                deadline_t = st.time_input("Time")
            
            uploaded_files = st.file_uploader("📎 Add Photos/Files", accept_multiple_files=True)
            
            st.write("🎙️ Record Voice Note")
            audio_recording = mic_recorder(start_prompt="⏺️ Start Recording", stop_prompt="⏹️ Stop Recording", key='recorder')
            
            if st.button("Assign Task", use_container_width=True, type="primary"):
                if title and assignee:
                    with st.spinner("Assigning task..."):
                        task_id = f"TSK-{random.randint(100000, 999999)}"
                        assigned_dept = users_df[users_df['NAME'] == assignee]['DEPARTMENT'].values[0]
                        
                        created_str = datetime.now().strftime("%m/%d/%Y, %I:%M:%S %p")
                        deadline_str = f"{deadline_d.strftime('%m/%d/%Y')}, {deadline_t.strftime('%I:%M:%S %p')}"
                        
                        # Upload standard files
                        if uploaded_files:
                            for idx, file in enumerate(uploaded_files):
                                file_ext = file.name.split('.')[-1]
                                upload_bytes_to_drive(file.getvalue(), f"{task_id}_{idx+1}.{file_ext}", file.type)
                        
                        # Upload Voice Note
                        if audio_recording:
                            upload_bytes_to_drive(audio_recording['bytes'], f"{task_id}_VoiceNote.wav", 'audio/wav')
                        
                        task_row = [
                            task_id, title, desc, user['name'], assigned_dept, 
                            assignee, created_str, deadline_str, "Assigned", "", ""
                        ]
                        append_task(task_row)
                        
                        # Telegram Alert
                        assignee_row = users_df[users_df['NAME'] == assignee]
                        telegram_id = assignee_row['TELEGRAM_ID'].values[0] if 'TELEGRAM_ID' in assignee_row.columns else None
                        if pd.notna(telegram_id) and telegram_id != "":
                            send_telegram_alert(telegram_id, title, user['name'], deadline_str, desc)

                        fetch_data.clear() 
                    st.toast(f"✅ Assigned to {assignee}!", icon="🚀")
                    st.rerun()
                else:
                    st.error("Title and Assignee are required.")

    # --- MAIN SCREEN (Task Board) ---
    st.header("Workspace")
    tasks_df = fetch_data("Tasks")

    if tasks_df.empty:
        st.info("No tasks in the system yet.")
    else:
        if user['role'] not in ['CEO', 'GM']:
            if user['role'] == 'HOD':
                tasks_df = tasks_df[(tasks_df['Assigned Dept'] == user['dept']) | (tasks_df['Assigned To'] == user['name'])]
            else:
                tasks_df = tasks_df[tasks_df['Assigned To'] == user['name']]

        tab1, tab2, tab3 = st.tabs(["📌 Active", "⏳ Review", "✅ Done"])

        def render_task_card(row):
            # Ultra-compact Sleek Card UI
            with st.container(border=True):
                c1, c2 = st.columns([0.85, 0.15])
                with c1:
                    st.markdown(f"""
                        <div style='line-height: 1.3;'>
                            <b style='font-size:16px;'>{row['Title']}</b> <span style='font-size:11px;color:gray;'>{row['Task ID']}</span><br>
                            <span style='font-size:13px; color:#1E3A8A;'>🏢 {row['Assigned By']} &nbsp;➡️&nbsp; 👷‍♂️ {row['Assigned To']}</span><br>
                            <span style='font-size:14px; color:#333;'>{row['Description']}</span><br>
                            <span style='font-size:12px; font-weight:bold; color:#D97706;'>📅 {row['Deadline']}</span>
                        </div>
                    """, unsafe_allow_html=True)
                with c2:
                    view_btn = st.button("📎", key=f"btn_{row['Task ID']}", help="View Attachments")
                
                if view_btn:
                    with st.spinner("Loading files..."):
                        query = f"'{FOLDER_ID}' in parents and name contains '{row['Task ID']}' and trashed=false"
                        results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name, mimeType)').execute()
                        items = results.get('files', [])
                        
                        if not items:
                            st.warning("No files attached.")
                        else:
                            for item in items:
                                icon = "🎵" if "audio" in item.get('mimeType', '') else "📄"
                                st.markdown(f"{icon} [{item['name']}](https://drive.google.com/file/d/{item['id']}/view)")

        with tab1:
            active_tasks = tasks_df[tasks_df['Status'] == 'Assigned']
            for _, row in active_tasks.iterrows():
                render_task_card(row)

        with tab2:
            review_tasks = tasks_df[tasks_df['Status'] == 'Under Review']
            for _, row in review_tasks.iterrows():
                render_task_card(row)

        with tab3:
            completed_tasks = tasks_df[tasks_df['Status'] == 'Completed']
            for _, row in completed_tasks.iterrows():
                render_task_card(row)
