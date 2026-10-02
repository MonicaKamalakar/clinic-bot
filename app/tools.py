import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from app.database import get_db_connection, ensure_patient_exists, get_clinic_by_id

# OpenAI-compatible function tool definitions
TOOLS_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "check_slots",
            "description": "Check available 30-minute appointment slots for a clinic on a given date (YYYY-MM-DD format).",
            "parameters": {
                "type": "object",
                "properties": {
                    "clinic_id": {"type": "string", "description": "ID of the clinic (e.g. glow-skin, bright-dental)"},
                    "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                    "doctor_id": {"type": "string", "description": "Optional doctor ID to filter slots for a specific doctor"}
                },
                "required": ["clinic_id", "date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book an appointment for a patient with a doctor for a specific service, date, and time slot.",
            "parameters": {
                "type": "object",
                "properties": {
                    "clinic_id": {"type": "string", "description": "Clinic ID"},
                    "patient_id": {"type": "string", "description": "Patient user ID"},
                    "doctor_id": {"type": "string", "description": "Doctor ID (e.g. doc-01)"},
                    "service_id": {"type": "string", "description": "Service ID or service name"},
                    "appointment_date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                    "appointment_time": {"type": "string", "description": "Time slot (e.g. 10:00 AM)"},
                    "patient_name": {"type": "string", "description": "Optional patient full name"},
                    "patient_phone": {"type": "string", "description": "Optional patient contact phone number"}
                },
                "required": ["clinic_id", "patient_id", "doctor_id", "service_id", "appointment_date", "appointment_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reschedule_appointment",
            "description": "Reschedule an existing confirmed appointment to a new date and time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "integer", "description": "ID of the appointment to reschedule"},
                    "patient_id": {"type": "string", "description": "Patient user ID"},
                    "new_date": {"type": "string", "description": "New date in YYYY-MM-DD format"},
                    "new_time": {"type": "string", "description": "New time slot (e.g. 11:30 AM)"}
                },
                "required": ["appointment_id", "patient_id", "new_date", "new_time"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "Cancel an existing appointment by appointment ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "integer", "description": "ID of the appointment to cancel"},
                    "patient_id": {"type": "string", "description": "Patient user ID"}
                },
                "required": ["appointment_id", "patient_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "handoff_to_human",
            "description": "Transfer the conversation to a human clinic receptionist (used when user requests medical diagnosis, medication, complex issue, or explicit receptionist request).",
            "parameters": {
                "type": "object",
                "properties": {
                    "clinic_id": {"type": "string", "description": "Clinic ID"},
                    "patient_id": {"type": "string", "description": "Patient user ID"},
                    "reason": {"type": "string", "description": "Reason for human handoff"}
                },
                "required": ["clinic_id", "patient_id", "reason"]
            }
        }
    }
]


# Tool implementations with real SQLite logic

def check_slots(clinic_id: str, date: str, doctor_id: Optional[str] = None) -> Dict[str, Any]:
    clinic = get_clinic_by_id(clinic_id)
    if not clinic:
        return {"error": f"Clinic with ID '{clinic_id}' not found."}

    doctors = clinic.get("doctors", [])
    if doctor_id:
        doctors = [d for d in doctors if d["id"] == doctor_id or d["name"].lower() == doctor_id.lower()]

    if not doctors:
        doctors = clinic.get("doctors", [])

    # Default 30-min slots generation from 10:00 AM to 06:00 PM (or based on hours)
    default_times = [
        "10:00 AM", "10:30 AM", "11:00 AM", "11:30 AM",
        "12:00 PM", "12:30 PM", "02:00 PM", "02:30 PM",
        "03:00 PM", "03:30 PM", "04:00 PM", "04:30 PM",
        "05:00 PM", "05:30 PM"
    ]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT doctor_id, appointment_time FROM appointments
        WHERE clinic_id = ? AND appointment_date = ? AND status != 'cancelled'
        """,
        (clinic_id, date),
    )
    booked_rows = cursor.fetchall()
    conn.close()

    booked_set = set((row["doctor_id"], row["appointment_time"]) for row in booked_rows)

    available_slots = []
    for doc in doctors:
        doc_slots = []
        for t in default_times:
            if (doc["id"], t) not in booked_set:
                doc_slots.append(t)
        available_slots.append({
            "doctor_id": doc["id"],
            "doctor_name": doc["name"],
            "specialization": doc.get("specialization", ""),
            "available_slots": doc_slots
        })

    return {
        "clinic_id": clinic_id,
        "date": date,
        "results": available_slots
    }


def book_appointment(
    clinic_id: str,
    patient_id: str,
    doctor_id: str,
    service_id: str,
    appointment_date: str,
    appointment_time: str,
    patient_name: Optional[str] = None,
    patient_phone: Optional[str] = None,
) -> Dict[str, Any]:
    ensure_patient_exists(patient_id, clinic_id)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Update patient name/phone if provided
    if patient_name or patient_phone:
        cursor.execute(
            """
            UPDATE patients SET name = COALESCE(?, name), phone = COALESCE(?, phone)
            WHERE id = ?
            """,
            (patient_name, patient_phone, patient_id),
        )

    # Check for double-booking
    cursor.execute(
        """
        SELECT id FROM appointments
        WHERE clinic_id = ? AND doctor_id = ? AND appointment_date = ? AND appointment_time = ? AND status != 'cancelled'
        """,
        (clinic_id, doctor_id, appointment_date, appointment_time),
    )
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return {
            "success": False,
            "message": f"Slot {appointment_time} on {appointment_date} with doctor {doctor_id} is already booked. Please select another time slot."
        }

    cursor.execute(
        """
        INSERT INTO appointments (patient_id, clinic_id, doctor_id, service_id, appointment_date, appointment_time, status)
        VALUES (?, ?, ?, ?, ?, ?, 'confirmed')
        """,
        (patient_id, clinic_id, doctor_id, service_id, appointment_date, appointment_time),
    )
    conn.commit()
    app_id = cursor.lastrowid
    conn.close()

    return {
        "success": True,
        "appointment_id": app_id,
        "message": f"Appointment #{app_id} successfully booked for {appointment_date} at {appointment_time}."
    }


def reschedule_appointment(
    appointment_id: Any,
    patient_id: str,
    new_date: str,
    new_time: str,
) -> Dict[str, Any]:
    try:
        appointment_id = int(str(appointment_id).strip())
    except (ValueError, TypeError):
        return {
            "success": False,
            "message": f"Invalid appointment ID format: '{appointment_id}'. Please provide a valid numerical appointment ID."
        }

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM appointments WHERE id = ? AND patient_id = ?",
        (appointment_id, patient_id),
    )
    app = cursor.fetchone()
    if not app:
        conn.close()
        return {
            "success": False,
            "message": f"No active appointment found with ID #{appointment_id} for patient {patient_id}."
        }

    doctor_id = app["doctor_id"]
    clinic_id = app["clinic_id"]

    # Check if new slot is taken by another appointment
    cursor.execute(
        """
        SELECT id FROM appointments
        WHERE clinic_id = ? AND doctor_id = ? AND appointment_date = ? AND appointment_time = ? AND id != ? AND status != 'cancelled'
        """,
        (clinic_id, doctor_id, new_date, new_time, appointment_id),
    )
    conflict = cursor.fetchone()
    if conflict:
        conn.close()
        return {
            "success": False,
            "message": f"Slot {new_time} on {new_date} is already taken. Please choose a different time."
        }

    cursor.execute(
        """
        UPDATE appointments
        SET appointment_date = ?, appointment_time = ?, status = 'confirmed'
        WHERE id = ?
        """,
        (new_date, new_time, appointment_id),
    )
    conn.commit()
    conn.close()

    return {
        "success": True,
        "appointment_id": appointment_id,
        "message": f"Appointment #{appointment_id} successfully rescheduled to {new_date} at {new_time}."
    }


def cancel_appointment(appointment_id: Any, patient_id: str) -> Dict[str, Any]:
    try:
        appointment_id = int(str(appointment_id).strip())
    except (ValueError, TypeError):
        return {
            "success": False,
            "message": f"Invalid appointment ID format: '{appointment_id}'. Please provide a valid numerical appointment ID."
        }

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM appointments WHERE id = ? AND patient_id = ?",
        (appointment_id, patient_id),
    )
    app = cursor.fetchone()
    if not app:
        conn.close()
        return {
            "success": False,
            "message": f"No appointment found with ID #{appointment_id} for patient {patient_id}."
        }

    cursor.execute(
        "UPDATE appointments SET status = 'cancelled' WHERE id = ?",
        (appointment_id,),
    )
    conn.commit()
    conn.close()

    return {
        "success": True,
        "appointment_id": appointment_id,
        "message": f"Appointment #{appointment_id} has been cancelled successfully."
    }



def handoff_to_human(clinic_id: str, patient_id: str, reason: str) -> Dict[str, Any]:
    ensure_patient_exists(patient_id, clinic_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO handoffs (patient_id, clinic_id, reason, status)
        VALUES (?, ?, ?, 'pending')
        """,
        (patient_id, clinic_id, reason),
    )
    conn.commit()
    handoff_id = cursor.lastrowid
    conn.close()

    return {
        "success": True,
        "handoff_id": handoff_id,
        "message": "Transferring your request to our clinic receptionist. A staff member will connect with you shortly."
    }


def execute_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Executes a tool by name with arguments and returns JSON string result."""
    tool_map = {
        "check_slots": check_slots,
        "book_appointment": book_appointment,
        "reschedule_appointment": reschedule_appointment,
        "cancel_appointment": cancel_appointment,
        "handoff_to_human": handoff_to_human,
    }

    if tool_name not in tool_map:
        return json.dumps({"error": f"Unknown tool '{tool_name}'"})

    try:
        res = tool_map[tool_name](**arguments)
        return json.dumps(res)
    except Exception as e:
        return json.dumps({"error": f"Error executing {tool_name}: {str(e)}"})
