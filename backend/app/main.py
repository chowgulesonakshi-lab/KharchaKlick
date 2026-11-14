from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.analytics import router as analytics_router
from app.api.routes.intelligence import router as intelligence_router
from app.api.routes.auth import router as auth_router
from app.api.routes.budgets import router as budgets_router
from app.api.routes.transactions import router as transactions_router
from app.core.database import Base, engine
from app.models.budget import Budget  # noqa: F401 - registers model metadata
from app.models.transaction import Transaction  # noqa: F401 - registers model metadata
from app.models.user import User  # noqa: F401 - registers model metadata

app = FastAPI(
    title="KharchaKlick API",
    description="AI-powered personal expense companion",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def create_database_tables():
    Base.metadata.create_all(bind=engine)


app.include_router(auth_router)
app.include_router(transactions_router)
app.include_router(budgets_router)
app.include_router(analytics_router)
app.include_router(intelligence_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to KharchaKlick API",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
