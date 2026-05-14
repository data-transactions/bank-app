import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import auth, accounts, transactions, admin, users, notifications
from .config import settings
from .database import Base, engine

# Initialize database tables
if os.getenv("RESET_DATABASE") == "true":
    print("WARNING: RESET_DATABASE is true. Dropping all tables...")
    Base.metadata.drop_all(bind=engine)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NexaBank API",
    description="Full-stack banking app API",
    version="1.0.0",
)



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




@app.api_route("/health", methods=["GET", "HEAD"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}