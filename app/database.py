import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_PATH = Path(__file__).parent.parent / "clinic_bot.db"
CLINICS_JSON_PATH = Path(__file__).parent.parent / "data" / "clinics.json"


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Clinics table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS clinics (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            city TEXT,
            address TEXT,
            phone TEXT,
            email TEXT,
            opening_hours TEXT,
            doctors TEXT,
            services TEXT
        )
        """
    )

    # 2. Patients table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS patients (
            id TEXT PRIMARY KEY,
            name TEXT,
            phone TEXT,
            clinic_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (clinic_id) REFERENCES clinics (id)
        )
        """
    )

    # 3. Appointments table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            clinic_id TEXT NOT NULL,
            doctor_id TEXT,
            service_id TEXT,
            appointment_date TEXT,
            appointment_time TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (id),
            FOREIGN KEY (clinic_id) REFERENCES clinics (id)
        )
        """
    )

    # 4. Conversations table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            clinic_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (id),
            FOREIGN KEY (clinic_id) REFERENCES clinics (id)
        )
        """
    )

    # 5. Handoffs table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS handoffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            clinic_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (id),
            FOREIGN KEY (clinic_id) REFERENCES clinics (id)
        )
        """
    )


    # Seed or sync data/clinics.json into SQLite
    if CLINICS_JSON_PATH.exists():
        with open(CLINICS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            clinics = data.get("clinics", [])
            for c in clinics:
                cursor.execute(
                    """
                    INSERT INTO clinics (id, name, category, city, address, phone, email, opening_hours, doctors, services)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name=excluded.name,
                        category=excluded.category,
                        city=excluded.city,
                        address=excluded.address,
                        phone=excluded.phone,
                        email=excluded.email,
                        opening_hours=excluded.opening_hours,
                        doctors=excluded.doctors,
                        services=excluded.services
                    """,
                    (
                        c["id"],
                        c["name"],
                        c.get("category", ""),
                        c.get("city", ""),
                        c.get("address", ""),
                        c.get("phone", ""),
                        c.get("email", ""),
                        json.dumps(c.get("opening_hours", {})),
                        json.dumps(c.get("doctors", [])),
                        json.dumps(c.get("services", [])),
                    ),
                )

    conn.commit()
    conn.close()


def ensure_patient_exists(patient_id: str, clinic_id: Optional[str] = None) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM patients WHERE id = ?", (patient_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute(
            "INSERT INTO patients (id, clinic_id) VALUES (?, ?)",
            (patient_id, clinic_id),
        )
        conn.commit()
    conn.close()


def save_message(patient_id: str, clinic_id: str, sender: str, message: str) -> Dict[str, Any]:
    ensure_patient_exists(patient_id, clinic_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO conversations (patient_id, clinic_id, sender, message)
        VALUES (?, ?, ?, ?)
        """,
        (patient_id, clinic_id, sender, message),
    )
    conn.commit()
    msg_id = cursor.lastrowid
    cursor.execute(
        "SELECT id, patient_id, clinic_id, sender, message, timestamp FROM conversations WHERE id = ?",
        (msg_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row)


def get_all_clinics() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clinics")
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        item = dict(r)
        item["opening_hours"] = json.loads(item["opening_hours"]) if item["opening_hours"] else {}
        item["doctors"] = json.loads(item["doctors"]) if item["doctors"] else []
        item["services"] = json.loads(item["services"]) if item["services"] else []
        result.append(item)
    return result


def get_clinic_by_id(clinic_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clinics WHERE id = ?", (clinic_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    item = dict(row)
    item["opening_hours"] = json.loads(item["opening_hours"]) if item["opening_hours"] else {}
    item["doctors"] = json.loads(item["doctors"]) if item["doctors"] else []
    item["services"] = json.loads(item["services"]) if item["services"] else []
    return item


def get_conversation_history(patient_id: str, clinic_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, patient_id, clinic_id, sender, message, timestamp
        FROM conversations
        WHERE patient_id = ? AND clinic_id = ?
        ORDER BY timestamp ASC
        """,
        (patient_id, clinic_id),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
