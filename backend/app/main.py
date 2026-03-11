from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import auth, accounts, transactions, admin
from .config import settings

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


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}
