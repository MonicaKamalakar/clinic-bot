# 🏥 Clinic Bot

A production-ready **AI Clinic Assistant & Receptionist System** built with **Python 3.11**, **FastAPI**, **SQLite**, and **OpenAI-compatible LLM APIs (Groq primary with OpenRouter automatic fallback)**. 

Includes an interactive **Single-Page Chat UI**, **APScheduler automated reminders**, a **Streamlit Admin Dashboard**, and a **15-scenario patient simulation evaluation suite**.

---

## 📸 Screenshots

| 💬 Single-Page Chat Interface | 📊 Streamlit Admin Dashboard |
|:---:|:---:|
| ![Chat UI](docs/chat.png) | ![Dashboard UI](docs/dashboard.png) |

---

## ✨ Features

- 🏥 **Multi-Clinic Support**: Manages multiple clinics (e.g. *Glow Skin Clinic* and *Bright Dental Care*) with unified JSON schemas for doctors, services, pricing in ₹, and opening hours.
- 🤖 **Autonomous AI Agent Loop**: Multi-turn tool calling agent using Groq (`openai/gpt-oss-120b`) with seamless fallback to OpenRouter (`openrouter/auto`) on rate limits, errors, or timeouts.
- 🛠️ **Real SQLite Clinic Tools**:
  - `check_slots`: Calculates available 30-min time slots during opening hours for the next 7 days.
  - `book_appointment`: Prevents double-booking and confirms appointments.
  - `reschedule_appointment`: Reschedules confirmed appointments.
  - `cancel_appointment`: Cancels existing appointments.
  - `handoff_to_human`: Automatically routes medical diagnosis/prescription requests or complex user queries to human receptionists.
- 🛡️ **Guardrails & Safety**:
  - **No Medical Advice**: Refuses medical diagnosis or medication prescriptions and triggers human handoff.
  - **Prompt Injection Defense**: Resistant to identity resets, DAN mode, and system prompt leaks.
  - **Conversational Step-by-Step Booking**: Asks for details (date, time, doctor, name) one at a time.
- ⏰ **Automated Background Scheduler**: APScheduler sends 24h appointment reminders and no-show follow-up notifications directly to the chat stream.
- 📊 **Streamlit Admin Dashboard**: Real-time KPI metrics (Bookings, Handoff Queue, Cancellations), appointments management table, and full patient conversation transcripts.

---

## 📁 Project Structure

```text
clinic-bot/
├── app/
│   ├── __init__.py
│   ├── database.py       # SQLite schema creation, data seeding & queries
│   ├── llm.py            # LLM engine (Groq primary & OpenRouter fallback agent loop)
│   ├── main.py           # FastAPI web application & REST endpoints
│   ├── scheduler.py      # APScheduler 24h reminders & follow-up jobs
│   ├── schemas.py        # Pydantic data schemas
│   ├── tools.py          # Clinic function tools with real SQLite execution logic
│   └── static/
│       └── index.html    # Single-page mobile-style glassmorphic Chat UI
├── data/
│   └── clinics.json      # Clinic catalog data (services, doctors, hours)
├── docs/
│   ├── chat.png          # Chat UI screenshot
│   └── dashboard.png     # Admin Dashboard screenshot
├── tests/
│   ├── __init__.py
│   ├── test_main.py      # Pytest unit & tool execution test suite
│   └── chat_scenarios.py # 15 simulated patient chat evaluation scenarios
├── .env.example          # Environment variables template
├── .gitignore           # Git ignore rules (.env, *.db)
├── dashboard.py          # Streamlit Admin Dashboard
├── LICENSE               # MIT License
├── README.md             # Project documentation
└── requirements.txt     # Python dependencies
```

---

## 🚀 Quickstart Guide

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/clinic-bot.git
cd clinic-bot
```

### 2. Set Up Virtual Environment

```bash
# macOS / Linux
python3.11 -m venv .venv
source .venv/bin/activate

# Windows (Command Prompt)
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy `.env.example` to create `.env` and fill in your API keys:

```bash
cp .env.example .env
```

#### Environment Variables Reference

| Variable | Required | Description | Example |
|---|---|---|---|
| `GROQ_API_KEY` | **Yes** | Primary LLM API key from [Groq Cloud](https://console.groq.com) | `gsk_...` |
| `OPENROUTER_API_KEY` | **Yes** | Fallback LLM API key from [OpenRouter](https://openrouter.ai) | `sk-or-v1-...` |
| `LLM_MODEL` | Optional | Primary model name for Groq | `openai/gpt-oss-120b` |
| `FALLBACK_MODEL` | Optional | Fallback model name for OpenRouter | `openrouter/auto` |

---

## 🏃 Running the Services

### Start FastAPI Chat Server

```bash
uvicorn app.main:app --reload --port 8000
```
- **Web Chat Interface**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive OpenAPI Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### Start Streamlit Admin Dashboard

In a new terminal window:

```bash
streamlit run dashboard.py
```
- **Admin Dashboard**: [http://localhost:8501](http://localhost:8501)

---

## 🧪 Testing & Evaluation

### Run Unit Test Suite

Verifies database seeding, API routes, tool execution, double-booking prevention, cancellations, and handoffs:

```bash
pytest
```

### Run 15 Simulated Patient Evaluation Scenarios

Executes the full evaluation suite covering FAQ, multi-turn booking, double-booking prevention, medical advice refusals, Hinglish queries, off-topic handling, and prompt injection attempts:

```bash
python tests/chat_scenarios.py
```

---

## 🗺️ Roadmap

- [ ] **WhatsApp Business API Integration**: Support direct chat bookings via WhatsApp webhook.
- [ ] **Multi-doctor Calendar Sync**: Integration with Google Calendar / Outlook APIs.
- [ ] **Automated SMS & Email Confirmations**: Send instant booking confirmation codes.

---

## 📄 License

This project is open-source under the [MIT License](LICENSE).
