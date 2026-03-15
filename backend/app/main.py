from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles
from .routes import auth, accounts, transactions, admin, users, notifications
from .config import settings

import os

app = FastAPI(
    title="NexaBank API",
    description="Full-stack banking app API",
    version="1.0.0",
)

# Ensure uploads directory exists for StaticFiles
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(transactions.router)
app.include_router(admin.router)
app.include_router(users.router)
app.include_router(notifications.router)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}
