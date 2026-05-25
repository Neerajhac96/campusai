# CampusAI

CampusAI is a production-ready multi-tenant College AI Chatbot SaaS platform for Indian colleges.  
Each college has strict data isolation (SQL + vector search) and students get source-backed answers in Hindi/English.

## Tech Stack

- Backend: FastAPI, SQLite (`aiosqlite`), ChromaDB, Sentence Transformers (`all-MiniLM-L6-v2`), Groq (`llama3-8b-8192`)
- Docs ingestion: PyMuPDF, python-docx, TXT
- Auth: JWT (`python-jose`) + `passlib` `sha256_crypt`
- Scheduler: APScheduler
- Frontend: React 18 + Vite + Tailwind + React Router v6 + Axios
- Deployment: Railway (backend), Vercel (frontend)

## Folder Structure

```text
campusai/
├── backend/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── auth.py
│   ├── rag_engine.py
│   ├── ingest.py
│   ├── language.py
│   ├── scheduler.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth_routes.py
│   │   ├── chat_routes.py
│   │   ├── admin_routes.py
│   │   ├── super_admin_routes.py
│   │   └── analytics_routes.py
│   ├── uploads/
│   ├── db/
│   ├── .env
│   ├── requirements.txt
│   └── Procfile
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── api/client.js
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx
│   │   │   ├── StudentChat.jsx
│   │   │   ├── AdminDashboard.jsx
│   │   │   └── SuperAdminPanel.jsx
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── MessageBubble.jsx
│   │   │   ├── DocumentManager.jsx
│   │   │   ├── AnalyticsDashboard.jsx
│   │   │   ├── UploadModal.jsx
│   │   │   └── Navbar.jsx
│   │   └── context/AuthContext.jsx
│   ├── .env
│   ├── index.html
│   └── package.json
└── README.md
```

## Environment Variables

### `backend/.env`

```env
GROQ_API_KEY=your_groq_api_key_here
SECRET_KEY=chatdeva2024productionsecretkey
DATABASE_URL=./chatdeva.db
UPLOAD_DIR=./uploads
CHROMA_DIR=./db
MAX_FILE_SIZE_MB=10
TOKEN_EXPIRE_HOURS=24
```

### `frontend/.env`

```env
VITE_API_URL=http://localhost:8000
```

## Run Locally

### Backend

```bash
cd campusai/backend
pip install -r requirements.txt
uvicorn main:app --reload
```

API docs: `http://localhost:8000/docs`

### Frontend

```bash
cd campusai/frontend
npm install
npm run dev
```

App: `http://localhost:5173`

## Seeded Demo Accounts

- Admin: `admin@demo.com` / `admin123`
- Student: `student@demo.com` / `student123`
- Super Admin: `super@chatdeva.com` / `super123`

## Security + Isolation Highlights

- `college_id` always comes from JWT token for protected routes.
- SQL queries are tenant-scoped (`WHERE college_id = ?`) for college data.
- Vector retrieval uses collection `col_{college_id}` only.
- No cross-college query path exists in chat or document routes.

## Deployment

### Backend (Railway)

- Start command via `Procfile`:
  - `web: uvicorn main:app --host 0.0.0.0 --port $PORT`
- Set backend env vars in Railway dashboard.

### Frontend (Vercel)

- Build command: `npm run build`
- Output directory: `dist`
- Env var: `VITE_API_URL=<your-railway-url>`

## Required Pilot Test Scenarios

1. Student Hindi query returns Hindi answer + source.
2. Student English query returns English answer + source.
3. Unknown query returns honest fallback (`I don't know` style).
4. Admin uploads document -> status `processing` -> `active`.
5. Admin deletes document -> vectors removed -> content no longer retrievable.
6. Multi-college isolation: student of College A cannot access College B data.
