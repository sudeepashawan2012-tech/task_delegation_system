import streamlit as st
import gspread
import pandas as pd
from datetime import datetime, timezone, timedelta
import random
import requests
import base64
from google.oauth2 import service_account

# Mobile-first configuration
st.set_page_config(page_title="Task Pro", page_icon="📋", layout="centered", initial_sidebar_state="collapsed")

# Inject Mobile-Friendly CSS for Styling, Larger Text, & Color-Coded Buttons
st.markdown("""
    <style>
        .stButton>button {
            border-radius: 8px;
            font-weight: 600;
        }
        /* Mobile font boost & clean card spacing */
        p, div, span, label {
            font-size: 15px !important;
        }
        .stTextInput input, .stTextArea textarea, .stSelectbox select {
            font-size: 16px !important;
        }
    </style>
""", unsafe_allow_html=True)

# Constants
SHEET_ID = "1oKei6r42q5zH4g-014bNEZfMRkzdm-MoOUwU5GUbsZk"
FOLDER_ID = "1-p5zcpZa8vXtpPLMx7y4JoMsGEOYSEaR"
TELEGRAM_BOT_TOKEN = "8644417421:AAEyHCjujQU30YP_wpbXFlitXH82M7dm4Ws"
GAS_WEBAPP_URL = st.secrets.get("GAS_WEBAPP_URL", "https://script.google.com/macros/s/AKfycbwTAf2WeIGGNBlDdtRq4pjHYNf9_KxU-3Pji5Ejg8TkTesrHJUxyZSoFkTfhPQJ9GSx/exec")

# Indian Standard Time (IST) helper
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
    df = pd.DataFrame(sheet.get_all_records())
    
    required_cols = {'Priority': '🟢 Regular', 'ItemType': 'Task', 'Review Notes': '', 'Submitted At': ''}
    for col, default_val in required_cols.items():
        if col not in df.columns:
            df[col] = default_val
    return df

def append_task(task_data):
    sheet = gs_client.open_by_key(SHEET_ID).worksheet("Tasks")
    sheet.append_row(task_data)

def update_task_fields(task_id, updates_dict):
    sheet = gs_client.open_by_key(SHEET_ID).worksheet("Tasks")
    cell = sheet.find(str(task_id), in_column=1)
    if cell:
        headers = sheet.row_values(1)
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

def send_telegram_alert(chat_id, task_title, assigned_by, deadline, description, priority="🟢 Regular", item_type="Task", assignee_name="STAFF", assignee_dept="General"):
    if not chat_id:
        return
    # Exact requested template structure
    message = (
        f"🚨Title: {task_title}\n"
        f"🏢 From: {assigned_by}\n"
        f"👤 For: {assignee_name.upper()} ({assignee_dept} Dept)\n"
        f"📌 Priority: {priority}\n"
        f"📅 Deadline: {deadline}\n\n"
        f"📝 Details:\n_{description}_"
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
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>Task Pro</h1>", unsafe_allow_html=True)
    
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

    # Sidebar for User Profile & Logout
    with st.sidebar:
        st.markdown(f"### 👤 {user['name']}")
        st.caption(f"**{user['role']}** | {user['dept']}")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user = None
            st.rerun()
            
        st.divider()
        if user['role'] in ['CEO', 'GM', 'HOD']:
            st.markdown("### 🧹 Maintenance")
            if st.button("🗑️ Clear All Completed Tasks", use_container_width=True):
                with st.spinner("Cleaning up completed tasks..."):
                    clear_all_completed_tasks()
                    fetch_data.clear()
                st.toast("All completed tasks deleted!", icon="🧹")
                st.rerun()

    # --- TOP-LEVEL TAB SWITCHER ---
    main_tab1, main_tab2, main_tab3 = st.tabs(["📋 Task Pro", "➕ Create Task", "⏰ Set Reminder"])

    # ==========================================
    # TAB 1: TASK PRO (Workspace & Filtering)
    # ==========================================
    with main_tab1:
        st.header("Workspace")
        all_df = fetch_data("Tasks")

        if all_df.empty:
            st.info("No items in the system yet.")
        else:
            view_mode = st.radio("View Section:", ["📋 Operational Tasks", "⏰ Reminders"], horizontal=True, label_visibility="collapsed")
            
            if 'ItemType' in all_df.columns:
                if view_mode == "📋 Operational Tasks":
                    tasks_df = all_df[all_df['ItemType'].isin(['Task', '', None])]
                else:
                    tasks_df = all_df[all_df['ItemType'] == 'Reminder']
            else:
                tasks_df = all_df

            if tasks_df.empty:
                st.info(f"No items found under {view_mode}.")
            else:
                current_time = now_ist()

                def check_is_overdue(row):
                    if str(row.get('Status', '')).strip() == 'Completed':
                        return False
                    dt = parse_deadline(row.get('Deadline', ''))
                    return (dt is not None) and (dt < current_time)

                tasks_df['is_overdue'] = tasks_df.apply(check_is_overdue, axis=1)
                overdue_tasks = tasks_df[tasks_df['is_overdue'] == True]

                if user['role'] in ['CEO', 'GM']:
                    role_tasks_df = tasks_df[tasks_df['Assigned By'] == user['name']]
                    overdue_tasks = overdue_tasks[overdue_tasks['Assigned By'] == user['name']]
                elif user['role'] == 'HOD':
                    role_tasks_df = tasks_df[(tasks_df['Assigned By'] == user['name']) | (tasks_df['Assigned Dept'] == user['dept']) | (tasks_df['Assigned To'] == user['name'])]
                else:
                    role_tasks_df = tasks_df[tasks_df['Assigned To'] == user['name']]
                    overdue_tasks = overdue_tasks[overdue_tasks['Assigned To'] == user['name']]

                overdue_count = len(overdue_tasks)
                sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
                    "📌 Active",
                    f"🚨 Overdue ({overdue_count})",
                    "⏳ Review",
                    "✅ Done"
                ])

                def render_task_card(row, tab_prefix):
                    is_overdue = row.get('is_overdue', False)
                    status = str(row.get('Status', '')).strip()
                    priority = str(row.get('Priority', '🟢 Regular')).strip()
                    review_notes = str(row.get('Review Notes', '')).strip()
                    submitted_at = str(row.get('Submitted At', '')).strip()
                    task_id = row['Task ID']
                    
                    if "High" in priority:
                        priority_badge = " <span style='background-color:#FEE2E2; color:#DC2626; padding:3px 8px; border-radius:4px; font-size:12px; font-weight:bold;'>🔴 HIGH PRIORITY</span>"
                    else:
                        priority_badge = " <span style='background-color:#ECFDF5; color:#059669; padding:3px 8px; border-radius:4px; font-size:12px; font-weight:bold;'>🟢 Regular</span>"

                    deadline_color = "#DC2626" if is_overdue else "#D97706"
                    overdue_badge = " <span style='background-color:#FEE2E2; color:#DC2626; padding:3px 8px; border-radius:4px; font-size:12px; font-weight:bold;'>🚨 OVERDUE</span>" if is_overdue else ""

                    # Quick check for attachments to show badges immediately on the card
                    attachments = fetch_attachments_from_drive(task_id)
                    file_count = sum(1 for a in attachments if "audio" not in a.get('mimeType', ''))
                    audio_count = sum(1 for a in attachments if "audio" in a.get('mimeType', ''))
                    
                    att_badge_html = ""
                    if file_count > 0 or audio_count > 0:
                        badges = []
                        if file_count > 0:
                            badges.append(f"📎 {file_count} File(s)")
                        if audio_count > 0:
                            badges.append(f"🎙️ {audio_count} Voice Note")
                        att_badge_html = f"<div style='margin-top:6px; font-size:13px; color:#2563EB; font-weight:600;'>{' | '.join(badges)}</div>"

                    with st.container(border=True):
                        can_manage = (user['role'] in ['CEO', 'GM', 'HOD'] and row['Assigned By'] == user['name']) or user['role'] in ['CEO', 'GM']
                        
                        cols_layout = [0.70, 0.15, 0.15] if can_manage else [0.80, 0.20]
                        if can_manage:
                            c1, c2, c3 = st.columns(cols_layout)
                        else:
                            c1, c2 = st.columns(cols_layout)
                            c3 = None

                        with c1:
                            # Formatted chat-style thread box for review notes
                            notes_html = ""
                            if review_notes:
                                formatted_notes = review_notes.replace(" | ", "<br><br>")
                                notes_html = f"<div style='margin-top:8px; padding:10px; background-color:#F3F4F6; border-left:4px solid #1E3A8A; border-radius:4px; font-size:13px;'><b>💬 Conversation Thread:</b><br>{formatted_notes}</div>"
                            
                            submitted_html = f"<br>⏱️ <b>Submitted At:</b> {submitted_at}" if submitted_at else ""
                            
                            st.markdown(f"""
                                <div style='line-height: 1.4;'>
                                    <b style='font-size:17px;'>{row['Title']}</b> <span style='font-size:12px;color:gray;'>{task_id}</span>{priority_badge}{overdue_badge}<br>
                                    <span style='font-size:14px; color:#1E3A8A;'>🏢 <b>{row['Assigned By']}</b> &nbsp;➡️&nbsp; 👷‍♂️ <b>{row['Assigned To']}</b> ({row['Assigned Dept']})</span><br>
                                    <span style='font-size:15px; color:#222;'>{row['Description']}</span><br>
                                    <span style='font-size:13px; font-weight:bold; color:{deadline_color};'>📅 Deadline: {row['Deadline']}</span>
                                    {submitted_html}
                                    {att_badge_html}
                                    {notes_html}
                                </div>
                            """, unsafe_allow_html=True)

                        with c2:
                            view_clicked = st.button("📎 View", key=f"att_{tab_prefix}_{task_id}", help="View Attachments")

                        if can_manage and c3 is not None:
                            with c3:
                                del_clicked = st.button("🗑️ Delete", key=f"del_{tab_prefix}_{task_id}", help="Delete Task")
                                if del_clicked:
                                    with st.spinner("Deleting task..."):
                                        delete_task_from_sheet(task_id)
                                        fetch_data.clear()
                                    st.toast(f"Deleted {task_id}", icon="🗑️")
                                    st.rerun()

                        if status == "Assigned":
                            if user['name'] == row['Assigned To']:
                                st.write("")
                                user_msg = st.text_input("Personal Remark / Status Note (e.g., Done, will complete by tomorrow)", key=f"msg_{tab_prefix}_{task_id}")
                                if st.button("📤 Submit for Review", key=f"sub_{tab_prefix}_{task_id}", use_container_width=True, type="primary"):
                                    current_str = now_ist().strftime("%d/%m/%Y, %I:%M:%S %p")
                                    new_entry = f"<b>{user['name']}</b> ({current_str}): {user_msg}" if user_msg else f"<b>{user['name']}</b> ({current_str}): Submitted for review."
                                    updated_notes = f"{review_notes} | {new_entry}" if review_notes else new_entry
                                    
                                    update_task_fields(task_id, {
                                        "Status": "Under Review",
                                        "Review Notes": updated_notes,
                                        "Submitted At": current_str
                                    })
                                    fetch_data.clear()
                                    st.toast("Submitted for review with remark!", icon="📤")
                                    st.rerun()
                        elif status == "Under Review" and (row['Assigned By'] == user['name'] or user['role'] in ['CEO', 'GM']):
                            st.write("")
                            manager_reply = st.text_input("Manager Feedback / Reply Note", key=f"reply_{tab_prefix}_{task_id}")
                            b1, b2 = st.columns(2)
                            with b1:
                                if st.button("✅ Approve & Complete", key=f"app_{tab_prefix}_{task_id}", use_container_width=True, type="primary"):
                                    current_str = now_ist().strftime("%d/%m/%Y, %I:%M:%S %p")
                                    reply_entry = f"<b>Manager Approved ({user['name']} - {current_str})</b>: {manager_reply}" if manager_reply else f"<b>Manager Approved ({user['name']} - {current_str})</b>"
                                    updated_notes = f"{review_notes} | {reply_entry}" if review_notes else reply_entry
                                    
                                    update_task_fields(task_id, {
                                        "Status": "Completed",
                                        "Review Notes": updated_notes
                                    })
                                    fetch_data.clear()
                                    st.toast("Task approved and completed!", icon="✅")
                                    st.rerun()
                            with b2:
                                if st.button("↩️ Send Back", key=f"ret_{tab_prefix}_{task_id}", use_container_width=True):
                                    current_str = now_ist().strftime("%d/%m/%Y, %I:%M:%S %p")
                                    reply_entry = f"<b>Sent Back by {user['name']} ({current_str})</b>: {manager_reply}" if manager_reply else f"<b>Sent Back by {user['name']} ({current_str})</b>"
                                    updated_notes = f"{review_notes} | {reply_entry}" if review_notes else reply_entry
                                    
                                    update_task_fields(task_id, {
                                        "Status": "Assigned",
                                        "Review Notes": updated_notes
                                    })
                                    fetch_data.clear()
                                    st.toast("Task sent back for revision!", icon="↩️")
                                    st.rerun()

                        if view_clicked:
                            with st.spinner("Loading attachments..."):
                                if not attachments:
                                    st.warning("No files attached.")
                                else:
                                    for item in attachments:
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

                def sort_by_priority(df_subset):
                    if df_subset.empty:
                        return df_subset
                    p_order = {"🔴 High Priority": 0, "🔴 High": 0, "🟢 Regular": 1}
                    df_subset['p_rank'] = df_subset['Priority'].map(lambda x: p_order.get(str(x).strip(), 1))
                    return df_subset.sort_values(by='p_rank', ascending=True)

                with sub_tab1:
                    active_tasks = sort_by_priority(role_tasks_df[role_tasks_df['Status'] == 'Assigned'])
                    if active_tasks.empty:
                        st.caption("No active tasks.")
                    for _, row in active_tasks.iterrows():
                        render_task_card(row, "act")

                with sub_tab2:
                    if overdue_tasks.empty:
                        st.success("🎉 Zero overdue items across your assigned workspace!")
                    else:
                        st.caption("Showing all overdue items:")
                        for _, row in overdue_tasks.iterrows():
                            render_task_card(row, "ovr")

                with sub_tab3:
                    review_tasks = sort_by_priority(role_tasks_df[role_tasks_df['Status'] == 'Under Review'])
                    if review_tasks.empty:
                        st.caption("No items under review.")
                    for _, row in review_tasks.iterrows():
                        render_task_card(row, "rev")

                with sub_tab4:
                    completed_tasks = sort_by_priority(role_tasks_df[role_tasks_df['Status'] == 'Completed'])
                    if completed_tasks.empty:
                        st.caption("No completed items.")
                    for _, row in completed_tasks.iterrows():
                        render_task_card(row, "done")

    # ==========================================
    # TAB 2: CREATE TASK
    # ==========================================
    with main_tab2:
        st.header("Task Assignment Center")
        
        if user['role'] not in ['CEO', 'GM', 'HOD']:
            st.warning("⚠️ Only Management (CEO, GM, HOD) can assign new tasks.")
        else:
            with st.expander("➕ Assign New Task Form", expanded=True):
                title = st.text_input("Task Title", key=f"t_title_{fk}")
                desc = st.text_area("Details", key=f"t_desc_{fk}", height=80)
                
                priority = st.selectbox("Task Priority", ["🟢 Regular", "🔴 High Priority"], index=0, key=f"t_prio_{fk}")
                
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
                
                uploaded_files = st.file_uploader("Add Photos/Files", accept_multiple_files=True, key=f"t_files_{fk}")
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
                                assignee, created_str, deadline_str, "Assigned", "", "", priority, "Task", ""
                            ]
                            append_task(task_row)
                            
                            assignee_row = users_df[users_df['NAME'] == assignee]
                            telegram_id = assignee_row['TELEGRAM_ID'].values[0] if 'TELEGRAM_ID' in assignee_row.columns else None
                            if pd.notna(telegram_id) and str(telegram_id).strip() != "":
                                send_telegram_alert(telegram_id, title, user['name'], deadline_str, desc, priority, "Task", assignee, assigned_dept)

                            fetch_data.clear()
                            st.session_state.form_key += 1
                        st.success(f"✅ Task successfully assigned to {assignee}!")
                        st.toast(f"✅ Assigned to {assignee}!", icon="🚀")
                        st.rerun()
                    else:
                        st.error("Title and Assignee are required.")

    # ==========================================
    # TAB 3: SET REMINDER
    # ==========================================
    with main_tab3:
        st.header("⏰ Reminder Center")
        st.markdown("Manage recurring factory routines and scheduled alerts (Daily, Weekly, Monthly).")
        
        if user['role'] not in ['CEO', 'GM', 'HOD']:
            st.warning("⚠️ Only Management can set reminders.")
        else:
            rem_tab1, rem_tab2, rem_tab3 = st.tabs(["📅 Daily", "📆 Weekly", "🗓️ Monthly"])
            
            users_df = fetch_data("User_list")
            
            with rem_tab1:
                st.subheader("Daily Reminder")
                d_title = st.text_input("Daily Routine Title", key="d_title")
                d_time = st.time_input("Alert Time", key="d_time")
                d_assignee = st.selectbox("Assign To", users_df['NAME'].tolist(), key="d_assignee")
                
                if st.button("Set Daily Reminder", type="primary"):
                    if d_title:
                        with st.spinner("Saving reminder..."):
                            task_id = f"REM-{random.randint(100000, 999999)}"
                            assigned_dept = users_df[users_df['NAME'] == d_assignee]['DEPARTMENT'].values[0]
                            created_str = now_ist().strftime("%d/%m/%Y, %I:%M:%S %p")
                            deadline_str = f"Daily at {d_time.strftime('%I:%M %p')}"
                            priority = "🟢 Regular"
                            
                            task_row = [
                                task_id, f"Daily: {d_title}", "Recurring Daily Routine", user['name'], assigned_dept,
                                d_assignee, created_str, deadline_str, "Assigned", "", "", priority, "Reminder", ""
                            ]
                            append_task(task_row)
                            
                            assignee_row = users_df[users_df['NAME'] == d_assignee]
                            telegram_id = assignee_row['TELEGRAM_ID'].values[0] if 'TELEGRAM_ID' in assignee_row.columns else None
                            if pd.notna(telegram_id) and str(telegram_id).strip() != "":
                                send_telegram_alert(telegram_id, f"Daily: {d_title}", user['name'], deadline_str, "Recurring Daily Routine", priority, "Reminder", d_assignee, assigned_dept)

                            fetch_data.clear()
                        st.success(f"✅ Daily reminder '{d_title}' set for {d_assignee}!")
                        st.toast("Daily reminder saved!", icon="⏰")
                    else:
                        st.error("Please enter a title.")
                        
            with rem_tab2:
                st.subheader("Weekly Reminder")
                w_title = st.text_input("Weekly Routine Title", key="w_title")
                w_day = st.selectbox("Day of Week", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], key="w_day")
                w_assignee = st.selectbox("Assign To", users_df['NAME'].tolist(), key="w_assignee")
                
                if st.button("Set Weekly Reminder", type="primary"):
                    if w_title:
                        with st.spinner("Saving reminder..."):
                            task_id = f"REM-{random.randint(100000, 999999)}"
                            assigned_dept = users_df[users_df['NAME'] == w_assignee]['DEPARTMENT'].values[0]
                            created_str = now_ist().strftime("%d/%m/%Y, %I:%M:%S %p")
                            deadline_str = f"Every {w_day}"
                            priority = "🟢 Regular"
                            
                            task_row = [
                                task_id, f"Weekly: {w_title}", f"Recurring Weekly Routine on {w_day}", user['name'], assigned_dept,
                                w_assignee, created_str, deadline_str, "Assigned", "", "", priority, "Reminder", ""
                            ]
                            append_task(task_row)
                            
                            assignee_row = users_df[users_df['NAME'] == w_assignee]
                            telegram_id = assignee_row['TELEGRAM_ID'].values[0] if 'TELEGRAM_ID' in assignee_row.columns else None
                            if pd.notna(telegram_id) and str(telegram_id).strip() != "":
                                send_telegram_alert(telegram_id, f"Weekly: {w_title}", user['name'], deadline_str, f"Recurring Weekly Routine on {w_day}", priority, "Reminder", w_assignee, assigned_dept)

                            fetch_data.clear()
                        st.success(f"✅ Weekly reminder '{w_title}' set for {w_assignee}!")
                        st.toast("Weekly reminder saved!", icon="⏰")
                    else:
                        st.error("Please enter a title.")
                        
            with rem_tab3:
                st.subheader("Monthly Reminder")
                m_title = st.text_input("Monthly Routine Title", key="m_title")
                m_date = st.slider("Day of Month", 1, 31, 1, key="m_date")
                m_assignee = st.selectbox("Assign To", users_df['NAME'].tolist(), key="m_assignee")
                
                if st.button("Set Monthly Reminder", type="primary"):
                    if m_title:
                        with st.spinner("Saving reminder..."):
                            task_id = f"REM-{random.randint(100000, 999999)}"
                            assigned_dept = users_df[users_df['NAME'] == m_assignee]['DEPARTMENT'].values[0]
                            created_str = now_ist().strftime("%d/%m/%Y, %I:%M:%S %p")
                            deadline_str = f"Monthly on Day {m_date}"
                            priority = "🟢 Regular"
                            
                            task_row = [
                                task_id, f"Monthly: {m_title}", f"Recurring Monthly Routine on Day {m_date}", user['name'], assigned_dept,
                                m_assignee, created_str, deadline_str, "Assigned", "", "", priority, "Reminder", ""
                            ]
                            append_task(task_row)
                            
                            assignee_row = users_df[users_df['NAME'] == m_assignee]
                            telegram_id = assignee_row['TELEGRAM_ID'].values[0] if 'TELEGRAM_ID' in assignee_row.columns else None
                            if pd.notna(telegram_id) and str(telegram_id).strip() != "":
                                send_telegram_alert(telegram_id, f"Monthly: {m_title}", user['name'], deadline_str, f"Recurring Monthly Routine on Day {m_date}", priority, "Reminder", m_assignee, assigned_dept)

                            fetch_data.clear()
                        st.success(f"✅ Monthly reminder '{m_title}' set for {m_assignee}!")
                        st.toast("Monthly reminder saved!", icon="⏰")
                    else:
                        st.error("Please enter a title.")
