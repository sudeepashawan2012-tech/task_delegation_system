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

# Mobile-first configuration
st.set_page_config(page_title="Task Portal", page_icon="📋", layout="centered", initial_sidebar_state="collapsed")

# Constants
SHEET_ID = "1oKei6r42q5zH4g-014bNEZfMRkzdm-MoOUwU5GUbsZk"
FOLDER_ID = "1-p5zcpZa8vXtpPLMx7y4JoMsGEOYSEaR" # The master Drive folder
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

@st.cache_data(ttl=60) # Cache data for 60 seconds to keep app fast, but clearable
def fetch_data(sheet_name):
    sheet = gs_client.open_by_key(SHEET_ID).worksheet(sheet_name)
    return pd.DataFrame(sheet.get_all_records())

def append_task(task_data):
    sheet = gs_client.open_by_key(SHEET_ID).worksheet("Tasks")
    sheet.append_row(task_data)

def upload_file_to_drive(file_obj, filename):
    file_metadata = {'name': filename, 'parents': [FOLDER_ID]}
    media = MediaIoBaseUpload(io.BytesIO(file_obj.getvalue()), mimetype=file_obj.type, resumable=True)
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

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
    st.markdown("<p style='text-align: center;'>Sign in to access your workflow</p>", unsafe_allow_html=True)
    
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

        # Task Creation Form
        if user['role'] in ['CEO', 'GM', 'HOD']:
            st.markdown("### ➕ Assign New Task")
            with st.form("new_task_form", clear_on_submit=True):
                title = st.text_input("Task Title")
                desc = st.text_area("Details & Instructions")
                
                users_df = fetch_data("User_list")
                if user['role'] in ['CEO', 'GM']:
                    assignees = users_df['NAME'].tolist()
                else:
                    assignees = users_df[users_df['DEPARTMENT'] == user['dept']]['NAME'].tolist()
                
                assignee = st.selectbox("Assign To:", assignees)
                deadline = st.date_input("Deadline")
                
                # Attachment Uploader (Paperclip icon style handled natively by Streamlit)
                uploaded_files = st.file_uploader("📎 Attach Files/Images", accept_multiple_files=True)
                
                if st.form_submit_button("Assign Task", use_container_width=True, type="primary"):
                    if title and assignee:
                        with st.spinner("Assigning task & uploading files..."):
                            task_id = f"TSK-{random.randint(100000, 999999)}"
                            assigned_dept = users_df[users_df['NAME'] == assignee]['DEPARTMENT'].values[0]
                            
                            # Handle File Uploads securely to Drive
                            if uploaded_files:
                                for idx, file in enumerate(uploaded_files):
                                    file_ext = file.name.split('.')[-1]
                                    new_filename = f"{task_id}_{idx+1}.{file_ext}" # Ties file to the specific task
                                    upload_file_to_drive(file, new_filename)
                            
                            task_row = [
                                task_id, title, desc, user['name'], assigned_dept, 
                                assignee, datetime.now().strftime("%Y-%m-%d"), 
                                str(deadline), "Assigned", "", ""
                            ]
                            append_task(task_row)
                            
                            # Telegram Alert
                            assignee_row = users_df[users_df['NAME'] == assignee]
                            telegram_id = assignee_row['TELEGRAM_ID'].values[0] if 'TELEGRAM_ID' in assignee_row.columns else None
                            if pd.notna(telegram_id) and telegram_id != "":
                                send_telegram_alert(telegram_id, title, user['name'], str(deadline), desc)

                            # Clear cache so the new task appears immediately
                            fetch_data.clear() 
                            
                        st.toast(f"✅ Task successfully assigned to {assignee}!", icon="🚀")
                        st.rerun()

    # --- MAIN SCREEN (Task Board) ---
    st.header("My Workspace")
    tasks_df = fetch_data("Tasks")

    if tasks_df.empty:
        st.info("No tasks in the system yet.")
    else:
        if user['role'] not in ['CEO', 'GM']:
            if user['role'] == 'HOD':
                tasks_df = tasks_df[(tasks_df['Assigned Dept'] == user['dept']) | (tasks_df['Assigned To'] == user['name'])]
            else:
                tasks_df = tasks_df[tasks_df['Assigned To'] == user['name']]

        tab1, tab2, tab3 = st.tabs(["📌 Active", "⏳ Under Review", "✅ Completed"])

        def render_task_card(row):
            with st.container(border=True):
                st.markdown(f"### {row['Title']}")
                st.caption(f"ID: `{row['Task ID']}`")
                
                colA, colB = st.columns(2)
                colA.markdown(f"**From:** 🏢 {row['Assigned By']}")
                colB.markdown(f"**To:** 👷‍♂️ {row['Assigned To']}")
                
                st.info(row['Description'])
                
                # Attachment viewer button
                if st.button("📎 View Attachments", key=f"btn_{row['Task ID']}"):
                    with st.spinner("Finding files..."):
                        query = f"'{FOLDER_ID}' in parents and name contains '{row['Task ID']}' and trashed=false"
                        results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
                        items = results.get('files', [])
                        
                        if not items:
                            st.warning("No files attached to this task.")
                        else:
                            for item in items:
                                st.markdown(f"📄 [{item['name']}](https://drive.google.com/file/d/{item['id']}/view)")
                
                today = datetime.now().date()
                try:
                    deadline_date = datetime.strptime(str(row['Deadline']), "%Y-%m-%d").date()
                    if deadline_date < today and row['Status'] != 'Completed':
                        st.markdown(f"🚨 **Deadline Passed:** :red[{row['Deadline']}]")
                    else:
                        st.markdown(f"📅 **Due:** {row['Deadline']}")
                except:
                    st.markdown(f"📅 **Due:** {row['Deadline']}")

        with tab1:
            active_tasks = tasks_df[tasks_df['Status'] == 'Assigned']
            if active_tasks.empty:
                st.write("You are all caught up!")
            for _, row in active_tasks.iterrows():
                render_task_card(row)

        with tab2:
            review_tasks = tasks_df[tasks_df['Status'] == 'Under Review']
            if review_tasks.empty:
                st.write("No tasks currently pending review.")
            for _, row in review_tasks.iterrows():
                render_task_card(row)

        with tab3:
            completed_tasks = tasks_df[tasks_df['Status'] == 'Completed']
            for _, row in completed_tasks.iterrows():
                render_task_card(row)
