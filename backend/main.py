import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import initialize_database
from routes.admin_routes import router as admin_router
from routes.analytics_routes import router as analytics_router
from routes.auth_routes import router as auth_router
from routes.chat_routes import router as chat_router
from routes.faculty_routes import router as faculty_router
from routes.student_routes import router as student_router
from routes.super_admin_routes import router as super_admin_router
from scheduler import start_scheduler, stop_scheduler


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
CHROMA_DIR = os.getenv("CHROMA_DIR", "./db")


def _resolve_dir(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return (BASE_DIR / path).resolve()


@asynccontextmanager
async def lifespan(_: FastAPI):
    _resolve_dir(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    _resolve_dir(CHROMA_DIR).mkdir(parents=True, exist_ok=True)
    await initialize_database()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="CampusAI API",
    description="Multi-tenant College AI Chatbot SaaS backend for Indian colleges",
    version="1.0.0",
    lifespan=lifespan,
)

origins_env = os.getenv("CORS_ALLOWED_ORIGINS")
allowed_origins = (
    [o.strip() for o in origins_env.split(",") if o.strip()]
    if origins_env
    else ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth")
app.include_router(chat_router, prefix="/chat")
app.include_router(admin_router, prefix="/admin")
app.include_router(analytics_router, prefix="/admin")
app.include_router(super_admin_router, prefix="/super")
app.include_router(student_router, prefix="/student")
app.include_router(faculty_router, prefix="/faculty")


@app.get("/")
async def root() -> dict:
    return {
        "product": "CampusAI",
        "status": "running",
        "version": "1.0.0",
        "docs_url": "/docs",
    }
