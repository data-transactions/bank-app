import os
from pathlib import Path
import sys

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .routers import auth, users, accounts, transactions, pdf
from .config import settings

app = FastAPI(
    title="NexaBank API",
    description="Fintech online banking MVP",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(pdf.router)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}


# Serve frontend static files
FRONTEND_DIR = Path("/app/static_frontend")
if FRONTEND_DIR.exists():
    # Mount assets
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    components_dir = FRONTEND_DIR / "components"
    if components_dir.exists():
        app.mount("/components", StaticFiles(directory=str(components_dir)), name="components")

    @app.get("/login")
    @app.get("/login/")
    def serve_login():
        return FileResponse(str(FRONTEND_DIR / "login" / "index.html"))

    @app.get("/signup")
    @app.get("/signup/")
    def serve_signup():
        return FileResponse(str(FRONTEND_DIR / "signup" / "index.html"))

    @app.get("/dashboard")
    @app.get("/dashboard/")
    def serve_dashboard():
        return FileResponse(str(FRONTEND_DIR / "dashboard" / "index.html"))

    @app.get("/")
    def serve_index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
