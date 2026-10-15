import streamlit as st
import gspread
import pandas as pd
from datetime import datetime
import random
from google.oauth2 import service_account

# Mobile-first configuration
st.set_page_config(page_title="Task Portal", page_icon="📋", layout="centered", initial_sidebar_state="collapsed")

# Constants
SHEET_ID = "1oKei6r42q5zH4g-014bNEZfMRkzdm-MoOUwU5GUbsZk"

@st.cache_resource
def get_gs_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, 
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(creds)

gs_client = get_gs_client()

def fetch_data(sheet_name):
    sheet = gs_client.open_by_key(SHEET_ID).worksheet(sheet_name)
    return pd.DataFrame(sheet.get_all_records())

def append_task(task_data):
    sheet = gs_client.open_by_key(SHEET_ID).worksheet("Tasks")
    sheet.append_row(task_data)

# State Management
if 'user' not in st.session_state:
    st.session_state.user = None

# ==========================================
# LOGIN SCREEN
# ==========================================
if st.session_state.user is None:
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>Task Portal</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Sign in to access your workflow</p>", unsafe_allow_html=True)
    
    st.write("") # Spacing
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

    # --- SIDEBAR (Navigation & Actions) ---
    with st.sidebar:
        st.markdown(f"### 👤 {user['name']}")
        st.caption(f"**{user['role']}** | {user['dept']}")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user = None
            st.rerun()
            
        st.divider()

        # Task Creation Form (Hidden cleanly in sidebar)
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
                
                assignee = st.selectbox("Assign To:", [n for n in assignees if n != user['name']])
                deadline = st.date_input("Deadline")
                
                if st.form_submit_button("Launch Task", use_container_width=True, type="primary"):
                    if title and assignee:
                        task_id = f"TSK-{random.randint(100000, 999999)}"
                        assigned_dept = users_df[users_df['NAME'] == assignee]['DEPARTMENT'].values[0]
                        task_row = [
                            task_id, title, desc, user['name'], assigned_dept, 
                            assignee, datetime.now().strftime("%Y-%m-%d"), 
                            str(deadline), "Assigned", "", ""
                        ]
                        append_task(task_row)
                        st.success(f"Task sent to {assignee}!")
                        st.rerun()

    # --- MAIN SCREEN (Task Board) ---
    st.header("My Workspace")
    tasks_df = fetch_data("Tasks")

    if tasks_df.empty:
        st.info("No tasks in the system yet.")
    else:
        # Filter tasks for the logged-in user
        if user['role'] not in ['CEO', 'GM']:
            if user['role'] == 'HOD':
                tasks_df = tasks_df[(tasks_df['Assigned Dept'] == user['dept']) | (tasks_df['Assigned To'] == user['name'])]
            else:
                tasks_df = tasks_df[tasks_df['Assigned To'] == user['name']]

        # Create UI Tabs
        tab1, tab2, tab3 = st.tabs(["📌 Active", "⏳ Under Review", "✅ Completed"])

        def render_task_card(row):
            """Helper function to draw a clean, prominent task card."""
            with st.container(border=True):
                st.markdown(f"### {row['Title']}")
                
                # Prominent Assignment Logic
                colA, colB = st.columns(2)
                colA.markdown(f"**From:** 🏢 {row['Assigned By']}")
                colB.markdown(f"**To:** 👷‍♂️ {row['Assigned To']}")
                
                # Formatting the Description
                st.info(row['Description'])
                
                # Deadline Logic
                today = datetime.now().date()
                try:
                    deadline_date = datetime.strptime(str(row['Deadline']), "%Y-%m-%d").date()
                    if deadline_date < today and row['Status'] != 'Completed':
                        st.markdown(f"🚨 **Deadline Passed:** :red[{row['Deadline']}]")
                    else:
                        st.markdown(f"📅 **Due:** {row['Deadline']}")
                except:
                    st.markdown(f"📅 **Due:** {row['Deadline']}")

        # Render rows into the correct tabs
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
