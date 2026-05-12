from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from database import engine

# Import all models before create_all to ensure they are registered in the Base metadata
import models
from models import Base
from routes import contacts, calls, favourites, dashboard, import_csv, ai
from routes import face_search

# Enable pgvector extension and create/migrate the face embeddings table + HNSW index
_EMBED_DIM = 512  # Must match utils/face_embeddings.py EMBED_DIM

with engine.connect() as _conn:
    _conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    # Auto-migrate: if the table exists with a different embedding dimension, drop it.
    # The index is just a cache — the user re-runs "Index Faces" after any re-deploy.
    try:
        _row = _conn.execute(text("""
            SELECT format_type(atttypid, atttypmod)
            FROM pg_attribute
            WHERE attrelid = 'contact_face_embeddings'::regclass
              AND attname = 'embedding'
        """)).first()
        if _row and _row[0] != f"vector({_EMBED_DIM})":
            _conn.execute(text("DROP TABLE contact_face_embeddings"))
            _conn.commit()
    except Exception:
        pass  # Table does not exist yet; CREATE TABLE below handles it

    _conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS contact_face_embeddings (
            id          SERIAL PRIMARY KEY,
            contact_id  INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
            embedding   vector({_EMBED_DIM}) NOT NULL,
            created_at  TIMESTAMP DEFAULT NOW()
        )
    """))
    _conn.execute(text(
        "CREATE INDEX IF NOT EXISTS idx_cfe_contact_id ON contact_face_embeddings(contact_id)"
    ))
    _conn.execute(text(f"""
        CREATE INDEX IF NOT EXISTS idx_cfe_hnsw
        ON contact_face_embeddings
        USING hnsw (embedding vector_cosine_ops)
    """))
    _conn.commit()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Phonebook Analytics")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    # Returns a structured JSON error when a requested route or resource doesn't exist
    return JSONResponse(status_code=404,
        content={"error": "Not found", "path": str(request.url)})


@app.exception_handler(422)
async def validation_handler(request: Request, exc):
    # Returns a structured JSON error when request data fails Pydantic validation
    return JSONResponse(status_code=422,
        content={"error": "Validation failed", "details": exc.errors() if hasattr(exc, 'errors') else str(exc)})


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    # Catches any unhandled server crash and returns a clean JSON error instead of a traceback
    return JSONResponse(status_code=500,
        content={"error": "Internal server error", "details": str(exc)})


app.include_router(ai.router)
app.include_router(contacts.router)
app.include_router(calls.router)
app.include_router(favourites.router)
app.include_router(dashboard.router)
app.include_router(import_csv.router)
app.include_router(face_search.router)


@app.get("/")
def home():
    # Health check endpoint — confirms the API is running
    return {"message": "Phonebook Analytics API is running"}