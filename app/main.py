from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.database import (
    init_db,
    save_message,
    get_all_clinics,
    get_clinic_by_id,
    get_conversation_history,
    get_db_connection,
)
from app.schemas import ChatRequest, ChatResponse
from app.llm import run_agent_loop
from app.scheduler import start_scheduler, stop_scheduler

BASE_DIR = Path(__file__).parent.parent
STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database and seed clinics.json
    init_db()
    # Start APScheduler background tasks
    start_scheduler()
    yield
    # Stop scheduler on shutdown
    stop_scheduler()


app = FastAPI(
    title="Clinic Bot API",
    description="Backend API for Clinic Bot healthcare assistant service",
    version="0.2.0",
    lifespan=lifespan,
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
def read_root():
    """Serve the single-page chat UI."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>Clinic Bot API is running</h1>")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Return 204 No Content for favicon requests."""
    return Response(status_code=204)


@app.get("/chat")
def chat_get_fallback():
    """Redirect or inform user if /chat is accessed via GET."""
    index_path = STATIC_DIR / "index.html"
    return FileResponse(index_path) if index_path.exists() else {"message": "Please send POST request to /chat"}


@app.get("/health")
def health_check():
    return {"status": "ok", "database": "connected"}


@app.get("/api/clinics")
def list_clinics():
    """Retrieve all available clinics from SQLite database."""
    return get_all_clinics()


@app.get("/api/conversations/{user_id}/{clinic_id}")
def get_conversations(user_id: str, clinic_id: str):
    """Retrieve chat conversation history for a specific patient and clinic."""
    return get_conversation_history(user_id, clinic_id)


@app.get("/api/dashboard/stats")
def get_dashboard_stats(clinic_id: str = "all"):
    """API endpoint for Streamlit dashboard statistics & data tables."""
    conn = get_db_connection()
    cursor = conn.cursor()

    clinic_filter = "" if clinic_id == "all" else "WHERE clinic_id = ?"
    params = () if clinic_id == "all" else (clinic_id,)

    # Total Bookings
    cursor.execute(f"SELECT COUNT(*) FROM appointments {clinic_filter}", params)
    total_bookings = cursor.fetchone()[0]

    # Cancellations
    cursor.execute(
        f"SELECT COUNT(*) FROM appointments WHERE status = 'cancelled' {'AND clinic_id = ?' if clinic_id != 'all' else ''}",
        params,
    )
    total_cancellations = cursor.fetchone()[0]

    # Pending Handoffs
    cursor.execute(
        f"SELECT COUNT(*) FROM handoffs WHERE status = 'pending' {'AND clinic_id = ?' if clinic_id != 'all' else ''}",
        params,
    )
    total_handoffs = cursor.fetchone()[0]

    # Appointments list
    cursor.execute(
        f"SELECT * FROM appointments {clinic_filter} ORDER BY appointment_date DESC, appointment_time ASC",
        params,
    )
    appointments = [dict(r) for r in cursor.fetchall()]

    # Handoff Queue
    cursor.execute(
        f"SELECT * FROM handoffs {clinic_filter} ORDER BY created_at DESC",
        params,
    )
    handoffs = [dict(r) for r in cursor.fetchall()]

    # Patient IDs for transcripts
    cursor.execute(
        f"SELECT DISTINCT patient_id FROM conversations {clinic_filter}",
        params,
    )
    patients = [r[0] for r in cursor.fetchall()]

    conn.close()

    return {
        "total_bookings": total_bookings,
        "total_cancellations": total_cancellations,
        "total_handoffs": total_handoffs,
        "appointments": appointments,
        "handoffs": handoffs,
        "patients": patients,
    }


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(req: ChatRequest):
    """
    POST /chat endpoint with LLM Agent Loop.
    Logs user message, executes agent loop (tools + Groq/OpenRouter fallback),
    logs bot reply, and logs which model answered.
    """
    # 1. Save user message to database
    save_message(
        patient_id=req.user_id,
        clinic_id=req.clinic_id,
        sender="user",
        message=req.message,
    )

    # 2. Run agent loop with LLM & tools
    bot_reply, model_used = run_agent_loop(req.clinic_id, req.user_id, req.message)

    # 3. Save assistant reply to database
    bot_msg_entry = save_message(
        patient_id=req.user_id,
        clinic_id=req.clinic_id,
        sender="bot",
        message=bot_reply,
    )

    print(f"🤖 [CHAT ANSWER]: Model={model_used} | Clinic={req.clinic_id} | User={req.user_id}")

    return ChatResponse(
        reply=bot_reply,
        clinic_id=req.clinic_id,
        user_id=req.user_id,
        timestamp=bot_msg_entry.get("timestamp"),
        model_used=model_used,
    )
