import streamlit as st
import gspread
import pandas as pd
import json
import io
import random
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Task Portal", layout="wide", initial_sidebar_state="collapsed")

# Constants
SHEET_ID = "1oKei6r42q5zH4g-014bNEZfMRkzdm-MoOUwU5GUbsZk"
FOLDER_ID = "1-p5zcpZa8vXtpPLMx7y4JoMsGEOYSEaR"

# Initialize connection using Streamlit Secrets
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

# Session State for Login
if 'user' not in st.session_state:
    st.session_state.user = None

# --- LOGIN VIEW ---
if st.session_state.user is None:
    st.title("Task Portal Login")
    with st.form("login_form"):
        username = st.text_input("Employee Name").strip().upper()
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            users_df = fetch_data("User_list")
            user_match = users_df[(users_df['NAME'] == username) & (users_df['PASSWORD'].astype(str) == str(password))]
            
            if not user_match.empty:
                user_info = user_match.iloc[0]
                st.session_state.user = {
                    'name': user_info['NAME'],
                    'dept': user_info['DEPARTMENT'],
                    'role': user_info['ROLE']
                }
                st.rerun()
            else:
                st.error("Invalid Name or Password")

# --- DASHBOARD VIEW ---
else:
    user = st.session_state.user
    col1, col2 = st.columns([0.8, 0.2])
    col1.markdown(f"### Welcome, {user['name']} ({user['role']} - {user['dept']})")
    if col2.button("Logout"):
        st.session_state.user = None
        st.rerun()

    st.divider()
    
    # Task Creation (HOD & Management)
    if user['role'] in ['CEO', 'GM', 'HOD']:
        with st.expander("➕ Create New Task", expanded=False):
            with st.form("new_task_form", clear_on_submit=True):
                title = st.text_input("Task Title")
                desc = st.text_area("Description")
                
                users_df = fetch_data("User_list")
                # Filter assignees based on role
                if user['role'] in ['CEO', 'GM']:
                    assignees = users_df['NAME'].tolist()
                else:
                    assignees = users_df[users_df['DEPARTMENT'] == user['dept']]['NAME'].tolist()
                
                assignee = st.selectbox("Assign To", [n for n in assignees if n != user['name']])
                deadline = st.date_input("Deadline")
                
                # NATIVE FILE UPLOADER
                uploaded_files = st.file_uploader("Attach Images", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])
                
                submit_task = st.form_submit_button("Assign Task")
                
                if submit_task and title and assignee:
                    task_id = f"TSK-{random.randint(100000, 999999)}"
                    assigned_dept = users_df[users_df['NAME'] == assignee]['DEPARTMENT'].values[0]
                    
                    # Handle Image Uploads instantly via API
                    if uploaded_files:
                        for idx, file in enumerate(uploaded_files):
                            file_ext = file.name.split('.')[-1]
                            new_filename = f"{task_id}_{idx+1}.{file_ext}"
                            upload_file_to_drive(file, new_filename)
                    
                    task_row = [
                        task_id, title, desc, user['name'], assigned_dept, 
                        assignee, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                        str(deadline), "Assigned", "", ""
                    ]
                    append_task(task_row)
                    st.success(f"Task {task_id} Assigned Successfully!")
                    st.rerun()

    # Task Board
    st.subheader("Active Tasks")
    tasks_df = fetch_data("Tasks")
    
    if not tasks_df.empty:
        # Filter tasks based on role
        if user['role'] not in ['CEO', 'GM']:
            if user['role'] == 'HOD':
                tasks_df = tasks_df[(tasks_df['Assigned Dept'] == user['dept']) | (tasks_df['Assigned To'] == user['name'])]
            else:
                tasks_df = tasks_df[tasks_df['Assigned To'] == user['name']]
        
        # Display Tasks
        for _, row in tasks_df.iterrows():
            if row['Status'] != 'Archived':
                with st.container(border=True):
                    c1, c2 = st.columns([0.8, 0.2])
                    c1.markdown(f"**{row['Task ID']}: {row['Title']}**")
                    c1.write(row['Description'])
                    c1.caption(f"To: {row['Assigned To']} | By: {row['Assigned By']} | Due: {row['Deadline']}")
                    
                    status_color = "blue" if row['Status'] == 'Assigned' else "orange" if row['Status'] == 'Under Review' else "green"
                    c2.markdown(f":{status_color}[**{row['Status']}**]")
                    
                    # File Viewer Button
                    if c2.button("View Images", key=f"img_{row['Task ID']}"):
                        query = f"'{FOLDER_ID}' in parents and name contains '{row['Task ID']}' and trashed=false"
                        results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
                        items = results.get('files', [])
                        
                        if not items:
                            st.info("No images attached to this task.")
                        else:
                            for item in items:
                                # In a full app, you would fetch the bytes and display via st.image.
                                # For this fast setup, providing a direct Drive link.
                                st.markdown(f"[{item['name']}](https://drive.google.com/file/d/{item['id']}/view)")
    else:
        st.info("No active tasks found.")
