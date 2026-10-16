import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, timezone, timedelta
import random
import requests
import base64
from google.oauth2 import service_account

# Mobile-first configuration
st.set_page_config(page_title="Task Portal", page_icon="📋", layout="centered", initial_sidebar_state="collapsed")

# Custom Small Icon Base64 Strings for Custom Paperclip & Recycle Bin
ICON_PAPERCLIP = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAAA7DAAAOwwHHb6hkAAABrUlEQVR4nO2Y0WsTQRCHf5c2lVbU9kBRW6xVvBUvvQveCj5BvHiv1h5oUaQo1gqioCBaL/qjBfEVtYg/oGjVQg2ItVqC6i21FqRWo9Y0u72bH8wuczuXzWSX7oUP+MluM3Nmmd08Ozs5WXZ2M03ThC0m6bQfT/uVvBifF3B66n8u5+wYk7yZcfFpD9M6y18p5V3N83a7wIuT+e5K95j2N6L/bE04d+Uuv3TfH8pZ+7h7P9s1+w5/gJ7wV57z/4u+z5rW80+A3m+hC3i2m1TfgF+82U9D6pQ56wX2Vw+E13fB6zC3O2C42B1h5/w9lV825nL2B/gZ7kL7G3E1/c2L8h0Fvvj1tD+HlQ58u74C8d0cZ4H6A+fV0p1p8w9vYnQ5fA3q8L0+xL9k89M9p/a2d6Ff38q3zH944A0P2K8W71n0eL8B22W/nL9/5O+j3/i7W/r330c6gY9/6822S//Q43K0H/H7O+Tvf5d9pP7+G/n8ABj8aZ/081YfAAAAAElFTkSuQmCC"
ICON_TRASH = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAACXBIWXMAAA7DAAAOwwHHb6hkAAABJ0lEQVR4nO2YuwrCQBCG+1N4rS0E8QhC0MXE3vL17WyswcbC3sre00tLK7GztbWws5A2CfnHw8l5WWTWzL0w7N1k+IHu8mS243tHlUql0l8a40Wz7wU4W13k+wN47vU+V4z1nJ6OtwC178L32yJ29yB2xJ3664C727O9C3E30W0D7m7739+g6F81f9b3K+hR2vL52x0Q0L16/eWbAX3P+f9v2t57A0j3b3+WtwJvvx36277w1vK95Xj2J6jX/hJve0D/9O2z620P+Hvv7fO95X60f9YfK9z3t4Y54Pf3V5zP/oB++2D8P6c5H6VSpVKp1L8+A9g+eT6yV+0AAAAASUVORK5YII5s"

# Constants
SHEET_ID = "1oKei6r42q5zH4g-014bNEZfMRkzdm-MoOUwU5GUbsZk"
FOLDER_ID = "1-p5zcpZa8vXtpPLMx7y4JoMsGEOYSEaR"
TELEGRAM_BOT_TOKEN = "8815285939:AAFN2XvB6MGep9_GBwjdF359B97wTp1y6io"
GAS_WEBAPP_URL = st.secrets.get("GAS_WEBAPP_URL", "https://script.google.com/macros/s/AKfycbwTAf2WeIGGNBlDdtRq4pjHYNf9_KxU-3Pji5Ejg8TkTesrHJUxyZSoFkTfhPQJ9GSx/exec")

# Indian Standard Time (IST) helper so Streamlit Cloud (UTC) matches India time
IST = timezone(timedelta(hours=5, minutes=30))

def now_ist():
    return datetime.now(IST).replace(tzinfo=None)

@st.cache_resource
def get_gcp_client():
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    return gspread.authorize(creds)

gs_client = get_gcp_client()

@st.cache_data(ttl=60)
def fetch_data(sheet_name):
    sheet = gs_client.open_by_key(SHEET_ID).worksheet(sheet_name)
    return pd.DataFrame(sheet.get_all_records())

def append_task(task_data):
    sheet = gs_client.open_by_key(SHEET_ID).worksheet("Tasks")
    sheet.append_row(task_data)

def update_task_status(task_id, new_status):
    sheet = gs_client.open_by_key(SHEET_ID).worksheet("Tasks")
    cell = sheet.find(str(task_id), in_column=1)
    if cell:
        headers = sheet.row_values(1)
        status_col = headers.index("Status") + 1 if "Status" in headers else 9
        sheet.update_cell(cell.row, status_col, new_status)

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

def clear_all_completed_tasks():
    sheet = gs_client.open_by_key(SHEET_ID).worksheet("Tasks")
    records = sheet.get_all_records()
    for idx in range(len(records) - 1, -1, -1):
        if str(records[idx].get("Status", "")).strip() == "Completed":
            task_id = records[idx].get("Task ID")
            sheet.delete_rows(idx + 2)
            if task_id and GAS_WEBAPP_URL.startswith("http"):
                try:
                    requests.post(GAS_WEBAPP_URL, json={"action": "delete", "taskId": task_id}, timeout=10)
                except Exception:
                    pass

def upload_bytes_to_drive(file_bytes, filename, mimetype):
    if not GAS_WEBAPP_URL.startswith("http"):
        st.error("⚠️ Please paste your Google Apps Script Web App URL into GAS_WEBAPP_URL first.")
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
        st.error("Drive Bridge Error: Make sure your Apps Script deployment has 'Who has access' set to 'Anyone'.")
        st.stop()

    if res_json.get("status") != "success":
        st.error(f"Drive Upload Error: {res_json.get('message')}")
        st.stop()
    return res_json.get("id")

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

def parse_deadline(deadline_str):
    if not deadline_str or pd.isna(deadline_str):
        return None
    s = str(deadline_str).strip()
    for fmt in ["%d/%m/%Y, %I:%M:%S %p", "%d/%m/%Y, %I:%M %p", "%m/%d/%Y, %I:%M:%S %p", "%Y-%m-%d %H:%M:%S"]:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None

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
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass

# State Management
if 'user' not in st.session_state:
    st.session_state.user = None
if 'form_key' not in st.session_state:
    st.session_state.form_key = 0

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
                st.session_state.user = {
                    'name': user_info['NAME'],
                    'dept': user_info['DEPARTMENT'],
                    'role': user_info['ROLE']
                }
                st.rerun()
            else:
                st.error("Invalid Name or Password")

# ==========================================
# MAIN DASHBOARD
# ==========================================
else:
    user = st.session_state.user
    fk = st.session_state.form_key

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
            
            title = st.text_input("Task Title", key=f"t_title_{fk}")
            desc = st.text_area("Details", key=f"t_desc_{fk}", height=80)
            
            users_df = fetch_data("User_list")
            
            if user['role'] in ['CEO', 'GM']:
                departments = ["All"] + users_df['DEPARTMENT'].unique().tolist()
                dept_filter = st.selectbox("Filter Department", departments, key=f"t_dept_{fk}")
                if dept_filter == "All":
                    assignees = users_df['NAME'].tolist()
                else:
                    assignees = users_df[users_df['DEPARTMENT'] == dept_filter]['NAME'].tolist()
            else:
                assignees = users_df[users_df['DEPARTMENT'] == user['dept']]['NAME'].tolist()
            
            assignee = st.selectbox("Assign To", assignees, key=f"t_assignee_{fk}")
            
            col_d, col_t = st.columns(2)
            with col_d:
                deadline_d = st.date_input("Deadline Date", value=now_ist().date(), format="DD/MM/YYYY", key=f"t_date_{fk}")
            with col_t:
                deadline_t = st.time_input("Time", value=now_ist().time().replace(second=0, microsecond=0), key=f"t_time_{fk}")
            
            uploaded_files = st.file_uploader("📎 Add Photos/Files", accept_multiple_files=True, key=f"t_files_{fk}")
            audio_recording = st.audio_input("🎙️ Record Voice Note", key=f"t_audio_{fk}")
            
            if st.button("Assign Task", use_container_width=True, type="primary"):
                if title and assignee:
                    with st.spinner("Assigning task & uploading attachments..."):
                        task_id = f"TSK-{random.randint(100000, 999999)}"
                        assigned_dept = users_df[users_df['NAME'] == assignee]['DEPARTMENT'].values[0]
                        
                        created_str = now_ist().strftime("%d/%m/%Y, %I:%M:%S %p")
                        deadline_str = f"{deadline_d.strftime('%d/%m/%Y')}, {deadline_t.strftime('%I:%M:%S %p')}"
                        
                        if uploaded_files:
                            for idx, file in enumerate(uploaded_files):
                                file_ext = file.name.split('.')[-1]
                                upload_bytes_to_drive(file.getvalue(), f"{task_id}_{idx+1}.{file_ext}", file.type)
                        
                        if audio_recording is not None:
                            upload_bytes_to_drive(audio_recording.getvalue(), f"{task_id}_VoiceNote.wav", "audio/wav")
                        
                        task_row = [
                            task_id, title, desc, user['name'], assigned_dept,
                            assignee, created_str, deadline_str, "Assigned", "", ""
                        ]
                        append_task(task_row)
                        
                        assignee_row = users_df[users_df['NAME'] == assignee]
                        telegram_id = assignee_row['TELEGRAM_ID'].values[0] if 'TELEGRAM_ID' in assignee_row.columns else None
                        if pd.notna(telegram_id) and str(telegram_id).strip() != "":
                            send_telegram_alert(telegram_id, title, user['name'], deadline_str, desc)

                        fetch_data.clear()
                        st.session_state.form_key += 1
                    st.toast(f"✅ Assigned to {assignee}!", icon="🚀")
                    st.rerun()
                else:
                    st.error("Title and Assignee are required.")

            st.divider()
            st.markdown("### 🧹 Maintenance")
            if st.button("🗑️ Clear All Completed Tasks", use_container_width=True):
                with st.spinner("Cleaning up completed tasks..."):
                    clear_all_completed_tasks()
                    fetch_data.clear()
                st.toast("All completed tasks deleted!", icon="🧹")
                st.rerun()

    # --- MAIN SCREEN (Task Board) ---
    st.header("Workspace")
    all_tasks_df = fetch_data("Tasks")

    if all_tasks_df.empty:
        st.info("No tasks in the system yet.")
    else:
        current_time = now_ist()

        def check_is_overdue(row):
            if str(row.get('Status', '')).strip() == 'Completed':
                return False
            dt = parse_deadline(row.get('Deadline', ''))
            return (dt is not None) and (dt < current_time)

        all_tasks_df['is_overdue'] = all_tasks_df.apply(check_is_overdue, axis=1)
        overdue_tasks = all_tasks_df[all_tasks_df['is_overdue'] == True]

        if user['role'] in ['CEO', 'GM']:
            role_tasks_df = all_tasks_df
        elif user['role'] == 'HOD':
            role_tasks_df = all_tasks_df[(all_tasks_df['Assigned Dept'] == user['dept']) | (all_tasks_df['Assigned To'] == user['name'])]
        else:
            role_tasks_df = all_tasks_df[all_tasks_df['Assigned To'] == user['name']]

        overdue_count = len(overdue_tasks)
        tab1, tab2, tab3, tab4 = st.tabs([
            "📌 Active",
            f"🚨 Overdue ({overdue_count})",
            "⏳ Review",
            "✅ Done"
        ])

        def render_task_card(row, tab_prefix):
            is_overdue = row.get('is_overdue', False)
            status = str(row.get('Status', '')).strip()
            deadline_color = "#DC2626" if is_overdue else "#D97706"
            overdue_badge = " <span style='background-color:#FEE2E2; color:#DC2626; padding:2px 6px; border-radius:4px; font-size:11px; font-weight:bold;'>🚨 OVERDUE</span>" if is_overdue else ""

            with st.container(border=True):
                can_manage = user['role'] in ['CEO', 'GM', 'HOD']
                if can_manage:
                    c1, c2, c3 = st.columns([0.76, 0.12, 0.12])
                else:
                    c1, c2 = st.columns([0.85, 0.15])
                    c3 = None

                with c1:
                    st.markdown(f"""
                        <div style='line-height: 1.35;'>
                            <b style='font-size:16px;'>{row['Title']}</b> <span style='font-size:11px;color:gray;'>{row['Task ID']}</span>{overdue_badge}<br>
                            <span style='font-size:13px; color:#1E3A8A;'>🏢 {row['Assigned By']} &nbsp;➡️&nbsp; 👷‍♂️ {row['Assigned To']} ({row['Assigned Dept']})</span><br>
                            <span style='font-size:14px; color:#333;'>{row['Description']}</span><br>
                            <span style='font-size:12px; font-weight:bold; color:{deadline_color};'>📅 {row['Deadline']}</span>
                        </div>
                    """, unsafe_allow_html=True)

                with c2:
                    # Using your custom resized Paperclip icon image
                    view_btn = st.button(
                        f"📎", 
                        key=f"att_{tab_prefix}_{row['Task ID']}", 
                        help="View / Play Attachments"
                    )

                if can_manage and c3 is not None:
                    with c3:
                        # Using your custom resized Recycle Bin icon image
                        del_btn = st.button(
                            f"🗑️", 
                            key=f"del_{tab_prefix}_{row['Task ID']}", 
                            help="Delete Task"
                        )
                        if del_btn:
                            with st.spinner("Deleting task..."):
                                delete_task_from_sheet(row['Task ID'])
                                fetch_data.clear()
                            st.toast(f"Deleted {row['Task ID']}", icon="🗑️")
                            st.rerun()

                if status == "Assigned":
                    if user['name'] == row['Assigned To'] or can_manage:
                        if st.button("📤 Submit for Review", key=f"sub_{tab_prefix}_{row['Task ID']}", use_container_width=True):
                            update_task_status(row['Task ID'], "Under Review")
                            fetch_data.clear()
                            st.rerun()
                elif status == "Under Review" and can_manage:
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("✅ Approve & Complete", key=f"app_{tab_prefix}_{row['Task ID']}", use_container_width=True, type="primary"):
                            update_task_status(row['Task ID'], "Completed")
                            fetch_data.clear()
                            st.rerun()
                    with b2:
                        if st.button("↩️ Send Back", key=f"ret_{tab_prefix}_{row['Task ID']}", use_container_width=True):
                            update_task_status(row['Task ID'], "Assigned")
                            fetch_data.clear()
                            st.rerun()

                if view_btn:
                    with st.spinner("Loading attachments..."):
                        items = fetch_attachments_from_drive(row['Task ID'])
                        if not items:
                            st.warning("No files attached.")
                        else:
                            for item in items:
                                mime = item.get('mimeType', '')
                                raw_bytes = base64.b64decode(item['b64']) if 'b64' in item else None
                                
                                if "audio" in mime and raw_bytes:
                                    st.caption(f"🎵 **{item['name']}**")
                                    st.audio(raw_bytes, format="audio/wav")
                                elif "image" in mime and raw_bytes:
                                    st.caption(f"🖼️ **{item['name']}**")
                                    st.image(raw_bytes, use_container_width=True)
                                else:
                                    st.markdown(f"📄 [{item['name']}]({item.get('url', '#')})")

        with tab1:
            active_tasks = role_tasks_df[role_tasks_df['Status'] == 'Assigned']
            if active_tasks.empty:
                st.caption("No active tasks.")
            for _, row in active_tasks.iterrows():
                render_task_card(row, "act")

        with tab2:
            if overdue_tasks.empty:
                st.success("🎉 Zero overdue tasks across the workspace!")
            else:
                st.caption("Showing all overdue tasks across all departments:")
                for _, row in overdue_tasks.iterrows():
                    render_task_card(row, "ovr")

        with tab3:
            review_tasks = role_tasks_df[role_tasks_df['Status'] == 'Under Review']
            if review_tasks.empty:
                st.caption("No tasks under review.")
            for _, row in review_tasks.iterrows():
                render_task_card(row, "rev")

        with tab4:
            completed_tasks = role_tasks_df[role_tasks_df['Status'] == 'Completed']
            if completed_tasks.empty:
                st.caption("No completed tasks.")
            for _, row in completed_tasks.iterrows():
                render_task_card(row, "done")
