
from fastapi import FastAPI

app = FastAPI(
    title="KharchaKlick API",
    description="AI-powered personal expense companion",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "message": "Welcome to KharchaKlick API",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }
