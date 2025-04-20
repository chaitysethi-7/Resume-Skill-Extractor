from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.extractor import extract_information, extract_text_from_pdf
import sqlite3
import os

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS resumes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        name TEXT,
        email TEXT,
        phone TEXT,
        skills TEXT,
        work_experience TEXT,
        cgpa TEXT
    )''')
    try:
        conn.execute('ALTER TABLE resumes ADD COLUMN cgpa TEXT')
    except Exception:
        pass
    conn.commit()
    conn.close()
    yield

# Create FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# Serve React build (static files)
frontend_build_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'build')
if os.path.isdir(frontend_build_dir):
    app.mount("/", StaticFiles(directory=frontend_build_dir, html=True), name="static")

@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS resumes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        name TEXT,
        email TEXT,
        phone TEXT,
        skills TEXT,
        work_experience TEXT,
        cgpa TEXT
    )''')
    # Add cgpa column if missing
    try:
        conn.execute('ALTER TABLE resumes ADD COLUMN cgpa TEXT')
    except Exception:
        pass
    conn.commit()
    conn.close()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "db.sqlite3"
os.makedirs("uploads", exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    contents = await file.read()
    path = f"uploads/{file.filename}"
    with open(path, "wb") as f:
        f.write(contents)
    text = extract_text_from_pdf(path)
    info = extract_information(text)
    conn = get_db()
    conn.execute(
        "INSERT INTO resumes (filename, name, email, phone, skills, work_experience, cgpa) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            file.filename,
            info["name"],
            info["email"],
            info["phone"],
            ",".join(info["skills"]),
            str(info["work_experience"]),
            info["cgpa"]
        ),
    )
    conn.commit()
    conn.close()
    return {"detail": "Resume processed", "info": info}

@app.get("/resumes")
def list_resumes():
    conn = get_db()
    rows = conn.execute("SELECT id, filename, name, email, phone, skills, cgpa FROM resumes").fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/resume/{resume_id}")
def get_resume(resume_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM resumes WHERE id=?", (resume_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Resume not found")
    return dict(row)

from fastapi import Response

@app.delete("/resume/{resume_id}")
def delete_resume(resume_id: int):
    conn = get_db()
    row = conn.execute("SELECT filename FROM resumes WHERE id=?", (resume_id,)).fetchone()
    if not row:
        conn.close()
        return Response(status_code=404, content="Resume not found")
    filename = row["filename"]
    conn.execute("DELETE FROM resumes WHERE id=?", (resume_id,))
    conn.commit()
    conn.close()
    # Remove uploaded file if present
    try:
        os.remove(f"uploads/{filename}")
    except Exception:
        pass
    return {"detail": "Resume deleted"}
