# AIVOA – AI-Powered Customer Complaint Management System

Pharmaceutical QMS Customer Complaint intake module. A user pastes/uploads a complaint
(email, PDF, or plain text) and an AI pipeline extracts structured fields, auto-populates
the "Log Customer Complaint" form, checks completeness, classifies risk, and drafts a CAPA
recommendation — plus a chat assistant to ask follow-up questions.

## Stack
- **Frontend**: React + Redux Toolkit (Vite)
- **Backend**: Python + FastAPI
- **AI orchestration**: LangGraph
- **LLM**: Groq — `llama-3.1-8b-instant` for extraction, `openai/gpt-oss-120b` for risk/CAPA/chat reasoning
  (the assignment brief names `gemma2-9b-it` / `llama-3.3-70b-versatile`, but Groq deprecated both of
  those model IDs; these are Groq's recommended current replacements — worth mentioning in your demo
  video as a real debugging story). If Groq deprecates these too by the time you read this, check
  `https://console.groq.com/docs/deprecations` and swap the two `GROQ_*_MODEL` values in `backend/.env`.
- **Database**: PostgreSQL
- **Font**: Google Inter

## Architecture

```
 ┌────────────────────┐         ┌────────────────────────────────────────────┐
 │   React + Redux     │  HTTP   │                FastAPI                     │
 │  (ComplaintForm,     │───────▶│  /api/complaints/extract-text               │
 │   AIAssistantPanel,  │         │  /api/complaints/extract-file  ──┐          │
 │   ChatBox)           │◀───────│  /api/complaints (CRUD)          │          │
 └────────────────────┘  JSON    │  /api/chat                       ▼          │
                                  │                        ┌─────────────────┐ │
                                  │                        │  LangGraph      │ │
                                  │                        │  pipeline       │ │
                                  │                        │                 │ │
                                  │                        │ extract_fields  │ │
                                  │                        │      ↓          │ │
                                  │                        │ check_          │ │
                                  │                        │ completeness    │ │
                                  │                        │   ↙        ↘    │ │
                                  │                        │ flag_manual  classify_risk │
                                  │                        │  review          ↓          │
                                  │                        │              recommend_capa │
                                  │                        └─────────────────┘ │
                                  │                                 │           │
                                  │                                 ▼           │
                                  │                          Groq API (LLMs)    │
                                  └──────────────────┬───────────────────────────┘
                                                     ▼
                                              PostgreSQL (complaints table)
```

### LangGraph pipeline (`backend/app/langgraph_pipeline.py`)
1. **extract_fields** — sends raw text to `llama-3.1-8b-instant` with a strict JSON-schema prompt,
   parses the response into the 13 form fields.
2. **check_duplicates** — queries saved complaints in Postgres for matches on batch/lot number,
   product name, and description similarity (via `difflib`, no vector DB needed). Flags likely
   duplicates before the rest of the pipeline runs.
3. **check_completeness** — pure Python node; checks 6 mandatory fields, computes a
   completeness score and a `missing_fields` list. No LLM call — deterministic and fast.
4. **conditional edge** — if completeness score < 0.4, routes to `flag_for_manual_review`
   (status becomes "Manual Review Required", skips risk/CAPA to avoid the LLM guessing on too
   little information). Otherwise routes to `classify_risk`.
5. **classify_risk** — sends extracted fields to `openai/gpt-oss-120b`, returns a risk
   tier (Critical/High/Medium/Low) with justification referencing patient-safety/GMP concerns.
6. **recommend_capa** — sends fields + risk assessment to the reasoning model, drafts a CAPA
   suggestion (containment → investigation → preventive action).

Try the "Vague / incomplete" sample in the AI panel to see the manual-review branch fire.
To see duplicate detection fire: save the "Sterility complaint" sample once (click Save
Complaint), then run the same sample again — the second run will show a duplicate warning
card referencing the first saved complaint.

## Local setup

### 1. Database
```bash
docker compose up -d postgres
```
(Or point `DATABASE_URL` in `.env` at any Postgres instance you already have.)

> If you already had this running from before duplicate detection was added, the
> `complaints` table needs two new columns (`is_potential_duplicate`, `duplicate_matches`).
> Easiest fix for a dev setup: wipe and recreate the volume so the app creates a fresh
> schema on next startup:
> ```bash
> docker compose down -v
> docker compose up -d postgres
> ```

### 2. Backend
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env and paste your GROQ_API_KEY (get one free at https://console.groq.com)
uvicorn app.main:app --reload --port 8000
```
API docs will be live at http://localhost:8000/docs

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```
App runs at http://localhost:5173

## Repo structure
```
backend/
  app/
    main.py                 FastAPI app + routes
    langgraph_pipeline.py   LangGraph graph (the core AI workflow)
    groq_client.py          Groq API wrapper + robust JSON extraction
    models.py / schemas.py  SQLAlchemy models / Pydantic schemas
    database.py / config.py DB session + settings
    file_parsing.py         PDF/EML/TXT text extraction
  sample_data/               Sample pharma complaints for demo
frontend/
  src/
    App.jsx
    components/ComplaintForm.jsx       left panel (the form)
    components/AIAssistantPanel.jsx    right panel (upload/paste/risk/CAPA)
    components/ChatBox.jsx             AI copilot chat
    store/complaintSlice.js            Redux Toolkit slice + async thunks
    api/api.js                         axios client
```
