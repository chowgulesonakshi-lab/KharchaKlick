from fastapi import FastAPI

from app.api.routes.transactions import router as transactions_router
from app.core.database import Base, engine
from app.models.transaction import Transaction  # noqa: F401 - registers model metadata

app = FastAPI(
    title="KharchaKlick API",
    description="AI-powered personal expense companion",
    version="0.1.0",
)


@app.on_event("startup")
def create_database_tables():
    Base.metadata.create_all(bind=engine)


app.include_router(transactions_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to KharchaKlick API",
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
