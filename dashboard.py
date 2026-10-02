import streamlit as st
import pandas as pd
import requests
import json
import sqlite3
from pathlib import Path

# Page config
st.set_page_config(
    page_title="Clinic Bot - Admin Dashboard",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

import sqlite3
from pathlib import Path
from app.database import init_db

# Ensure database tables and clinics are seeded
init_db()

DB_PATH = Path(__file__).parent / "clinic_bot.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def load_clinics():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM clinics")
        rows = cursor.fetchall()
        conn.close()
        return [{"id": r["id"], "name": r["name"]} for r in rows]
    except Exception as err:
        return []



def load_dashboard_data(clinic_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    c_filter = "" if clinic_id == "all" else "WHERE clinic_id = ?"
    params = () if clinic_id == "all" else (clinic_id,)

    # KPI counts
    cursor.execute(f"SELECT COUNT(*) FROM appointments {c_filter}", params)
    total_bookings = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(*) FROM appointments WHERE status = 'cancelled' {'AND clinic_id = ?' if clinic_id != 'all' else ''}", params)
    total_cancellations = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(*) FROM handoffs WHERE status = 'pending' {'AND clinic_id = ?' if clinic_id != 'all' else ''}", params)
    total_handoffs = cursor.fetchone()[0]

    # Appointments dataframe
    cursor.execute(f"SELECT * FROM appointments {c_filter} ORDER BY appointment_date DESC, appointment_time ASC", params)
    app_rows = [dict(r) for r in cursor.fetchall()]

    # Handoffs dataframe
    cursor.execute(f"SELECT * FROM handoffs {c_filter} ORDER BY created_at DESC", params)
    handoff_rows = [dict(r) for r in cursor.fetchall()]

    # Patients list
    cursor.execute(f"SELECT DISTINCT patient_id FROM conversations {c_filter}", params)
    patients = [r[0] for r in cursor.fetchall()]

    conn.close()
    return {
        "bookings": total_bookings,
        "cancellations": total_cancellations,
        "handoffs_cnt": total_handoffs,
        "appointments": app_rows,
        "handoffs": handoff_rows,
        "patients": patients
    }


def load_patient_transcript(patient_id, clinic_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    if clinic_id == "all":
        cursor.execute("SELECT sender, message, timestamp, clinic_id FROM conversations WHERE patient_id = ? ORDER BY timestamp ASC", (patient_id,))
    else:
        cursor.execute("SELECT sender, message, timestamp, clinic_id FROM conversations WHERE patient_id = ? AND clinic_id = ? ORDER BY timestamp ASC", (patient_id, clinic_id))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# Main Layout
st.title("🏥 Clinic Bot Admin Dashboard")
st.markdown("Monitor clinic appointments, patient handoffs, and AI conversation transcripts in real-time.")

# Sidebar Filters
st.sidebar.header("Filter & Controls")
clinics = load_clinics()
clinic_options = {"all": "All Clinics"}
for c in clinics:
    clinic_options[c["id"]] = c["name"]

selected_clinic_id = st.sidebar.selectbox(
    "Select Clinic",
    options=list(clinic_options.keys()),
    format_func=lambda x: clinic_options[x]
)

data = load_dashboard_data(selected_clinic_id)

# Metrics Cards
st.subheader("📊 Key Performance Indicators")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="Total Bookings", value=data["bookings"])
with col2:
    st.metric(label="Handoff Queue (Pending)", value=data["handoffs_cnt"], delta_color="inverse")
with col3:
    st.metric(label="Cancellations", value=data["cancellations"])

st.markdown("---")

# Appointments Table Section
st.subheader("📅 Appointments Overview")
if data["appointments"]:
    df_app = pd.DataFrame(data["appointments"])
    
    # Filter by status
    status_filter = st.multiselect(
        "Filter Appointment Status",
        options=["confirmed", "cancelled", "completed"],
        default=["confirmed", "cancelled", "completed"]
    )
    
    if status_filter:
        df_filtered = df_app[df_app["status"].isin(status_filter)]
    else:
        df_filtered = df_app

    cols_app = [c for c in ["id", "patient_id", "clinic_id", "doctor_id", "service_id", "appointment_date", "appointment_time", "status", "created_at"] if c in df_filtered.columns]
    st.dataframe(df_filtered[cols_app])
else:
    st.info("No appointments found for the selected clinic.")

st.markdown("---")

# Handoff Queue Section
st.subheader("🚨 Receptionist Handoff Queue")
if data["handoffs"]:
    df_handoffs = pd.DataFrame(data["handoffs"])
    cols_h = [c for c in ["id", "patient_id", "clinic_id", "reason", "status", "created_at"] if c in df_handoffs.columns]
    st.dataframe(df_handoffs[cols_h])
else:
    st.success("No pending human handoffs in queue.")



st.markdown("---")

# Conversation Transcripts Section
st.subheader("💬 Patient Conversation Transcripts")
if data["patients"]:
    selected_patient = st.selectbox("Select Patient User ID", options=data["patients"])
    if selected_patient:
        transcript = load_patient_transcript(selected_patient, selected_clinic_id)
        if transcript:
            st.markdown(f"**Chat History for Patient ID:** `{selected_patient}`")
            for msg in transcript:
                sender_label = "👤 User" if msg["sender"] == "user" else ("🤖 Clinic Bot" if msg["sender"] == "bot" else "⚙️ System")
                st.text(f"[{msg['timestamp']}] ({msg['clinic_id']}) {sender_label}: {msg['message']}")
        else:
            st.info("No message history available for this patient.")
else:
    st.info("No active conversation transcripts found.")
