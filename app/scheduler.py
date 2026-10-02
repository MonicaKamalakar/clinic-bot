import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from app.database import get_db_connection

logger = logging.getLogger("clinic_scheduler")
logger.setLevel(logging.INFO)

scheduler = BackgroundScheduler()


def check_24h_reminders():
    """
    Checks appointments scheduled for tomorrow (~24h from now)
    and posts a system notification message to the conversation history.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    cursor.execute(
        """
        SELECT id, patient_id, clinic_id, appointment_date, appointment_time, doctor_id
        FROM appointments
        WHERE appointment_date = ? AND status = 'confirmed'
        """,
        (tomorrow_str,),
    )
    upcoming = cursor.fetchall()

    for app in upcoming:
        msg = f"[SYSTEM REMINDER]: Friendly reminder about your appointment (ID #{app['id']}) scheduled for tomorrow, {app['appointment_date']} at {app['appointment_time']}."
        
        # Check if reminder already sent to prevent duplicate messages
        cursor.execute(
            """
            SELECT id FROM conversations
            WHERE patient_id = ? AND clinic_id = ? AND sender = 'system' AND message LIKE ?
            """,
            (app['patient_id'], app['clinic_id'], f"%#{app['id']}%"),
        )
        if not cursor.fetchone():
            cursor.execute(
                """
                INSERT INTO conversations (patient_id, clinic_id, sender, message)
                VALUES (?, ?, 'system', ?)
                """,
                (app['patient_id'], app['clinic_id'], msg),
            )
            conn.commit()
            print(f"⏰ [SCHEDULER 24H REMINDER]: Sent reminder for Appointment #{app['id']} to patient {app['patient_id']}.")

    conn.close()


def check_no_show_followups():
    """
    Checks yesterday's appointments and sends follow-up system messages.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    cursor.execute(
        """
        SELECT id, patient_id, clinic_id, appointment_date, appointment_time
        FROM appointments
        WHERE appointment_date = ? AND status = 'confirmed'
        """,
        (yesterday_str,),
    )
    past_apps = cursor.fetchall()

    for app in past_apps:
        msg = f"[SYSTEM FOLLOW-UP]: We missed you yesterday for your appointment (ID #{app['id']}). Would you like to reschedule for another time?"
        
        cursor.execute(
            """
            SELECT id FROM conversations
            WHERE patient_id = ? AND clinic_id = ? AND sender = 'system' AND message LIKE ?
            """,
            (app['patient_id'], app['clinic_id'], f"%#{app['id']}%"),
        )
        if not cursor.fetchone():
            cursor.execute(
                """
                INSERT INTO conversations (patient_id, clinic_id, sender, message)
                VALUES (?, ?, 'system', ?)
                """,
                (app['patient_id'], app['clinic_id'], msg),
            )
            conn.commit()
            print(f"📋 [SCHEDULER FOLLOW-UP]: Sent no-show follow-up for Appointment #{app['id']} to patient {app['patient_id']}.")

    conn.close()


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(check_24h_reminders, 'interval', minutes=1, id='check_24h_reminders')
        scheduler.add_job(check_no_show_followups, 'interval', minutes=2, id='check_no_show_followups')
        scheduler.start()
        print("✅ APScheduler started successfully for appointment reminders & follow-ups.")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        print("🛑 APScheduler stopped.")
