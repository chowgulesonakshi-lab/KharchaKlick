from app.api.routes.analytics import router as analytics_router
from app.api.routes.auth import router as auth_router
from app.api.routes.budgets import router as budgets_router
from app.api.routes.transactions import router as transactions_router

__all__ = [
    "analytics_router",
    "auth_router",
    "budgets_router",
    "transactions_router",
]
