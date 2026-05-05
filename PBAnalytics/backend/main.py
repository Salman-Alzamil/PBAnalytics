from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from database import engine

# Import all models before create_all to ensure they are registered in the Base metadata
import models
from models import Base
from routes import contacts, calls, favourites, dashboard, import_csv, ai

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
async def not_found_handler(request: Request, exc): # Returns a structured JSON error when a requested route or resource doesn't exist
    return JSONResponse(status_code=404,
        content={"error": "Not found", "path": str(request.url)})

@app.exception_handler(422)
async def validation_handler(request: Request, exc): # Returns a structured JSON error when request data fails Pydantic validation
    return JSONResponse(status_code=422,
        content={"error": "Validation failed", "details": exc.errors() if hasattr(exc, 'errors') else str(exc)})

@app.exception_handler(500)
async def server_error_handler(request: Request, exc): # Catches any unhandled server crash and returns a clean JSON error instead of a traceback
    return JSONResponse(status_code=500,
        content={"error": "Internal server error", "details": str(exc)})

app.include_router(ai.router)
app.include_router(contacts.router)
app.include_router(calls.router)
app.include_router(favourites.router)
app.include_router(dashboard.router)
app.include_router(import_csv.router)

@app.get("/")
def home(): # Health check endpoint — confirms the API is running
    return {"message": "Phonebook Analytics API is running"}