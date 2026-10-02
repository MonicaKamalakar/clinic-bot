import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, get_db_connection
from app.tools import book_appointment, cancel_appointment, reschedule_appointment, check_slots, handoff_to_human

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM conversations")
    cursor.execute("DELETE FROM appointments")
    cursor.execute("DELETE FROM handoffs")
    conn.commit()
    conn.close()


def test_read_root_serves_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Clinic Bot" in response.text


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_list_clinics():
    response = client.get("/api/clinics")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    clinic_ids = [c["id"] for c in data]
    assert "glow-skin" in clinic_ids
    assert "bright-dental" in clinic_ids


def test_book_and_prevent_double_booking():
    clinic_id = "glow-skin"
    patient_1 = "pat_test_101"
    patient_2 = "pat_test_102"
    doc_id = "doc-01"
    date_str = "2026-10-10"
    time_str = "10:00 AM"

    # 1. Book first appointment
    res1 = book_appointment(clinic_id, patient_1, doc_id, "srv-acne", date_str, time_str)
    assert res1["success"] is True
    assert "appointment_id" in res1

    # 2. Attempt double booking for same doctor, date, and time slot
    res2 = book_appointment(clinic_id, patient_2, doc_id, "srv-acne", date_str, time_str)
    assert res2["success"] is False
    assert "already booked" in res2["message"].lower()


def test_cancel_appointment_logic():
    clinic_id = "bright-dental"
    patient_id = "pat_cancel_201"
    doc_id = "doc-03"
    date_str = "2026-10-12"
    time_str = "02:00 PM"

    # Book appointment
    res = book_appointment(clinic_id, patient_id, doc_id, "srv-cleaning", date_str, time_str)
    app_id = res["appointment_id"]

    # Cancel appointment
    cancel_res = cancel_appointment(app_id, patient_id)
    assert cancel_res["success"] is True
    assert "cancelled successfully" in cancel_res["message"].lower()

    # Slot should now be available again for re-booking
    res_rebook = book_appointment(clinic_id, "pat_new_202", doc_id, "srv-cleaning", date_str, time_str)
    assert res_rebook["success"] is True


def test_reschedule_appointment_logic():
    clinic_id = "glow-skin"
    patient_id = "pat_resched_301"
    doc_id = "doc-01"

    res = book_appointment(clinic_id, patient_id, doc_id, "srv-peels", "2026-10-15", "11:00 AM")
    app_id = res["appointment_id"]

    resched_res = reschedule_appointment(app_id, patient_id, "2026-10-16", "03:00 PM")
    assert resched_res["success"] is True
    assert "rescheduled to 2026-10-16 at 03:00 PM" in resched_res["message"]


def test_handoff_to_human_logic():
    handoff_res = handoff_to_human("glow-skin", "pat_handoff_401", "User requested medical advice on skin infection")
    assert handoff_res["success"] is True
    assert "handoff_id" in handoff_res
