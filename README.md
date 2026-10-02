# Clinic Bot

Backend service built with **Python 3.11** and **FastAPI** for managing clinic data and conversational healthcare assistance.

---

## 📁 Project Structure

```text
clinic-bot/
├── app/
│   ├── __init__.py
│   └── main.py          # FastAPI application entry point
├── data/
│   └── clinics.json     # Clinic records (Glow Skin & Bright Dental)
├── tests/
│   ├── __init__.py
│   └── test_main.py     # Test suite
├── .env.example         # Environment variables template
├── .gitignore          # Git ignore rules
├── README.md            # Project documentation & run guide
└── requirements.txt     # Python dependencies
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- **Python 3.11** installed on your system.

### 2. Set Up Virtual Environment

Create and activate a virtual environment:

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

Environment variables:
- `GROQ_API_KEY`: API key for Groq Cloud.
- `OPENROUTER_API_KEY`: API key for OpenRouter AI services.

---

## 🏃 Running the Application

Start the local development server with live reload:

```bash
uvicorn app.main:app --reload
```

The server will be available at:
- **API Root**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive OpenAPI Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc Docs**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🧪 Running Tests

Execute tests using `pytest`:

```bash
pytest
```
