from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.transaction import Category


class BudgetCreate(BaseModel):
    category: Category | None = Field(
        default=None,
        description="Category for the budget. If omitted, applies to total monthly spending.",
    )
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=2000, le=2100)


class BudgetUpdate(BaseModel):
    category: Category | None = None
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    month: int | None = Field(default=None, ge=1, le=12)
    year: int | None = Field(default=None, ge=2000, le=2100)


class BudgetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    category: str | None
    amount: Decimal
    month: int
    year: int
    created_at: datetime
    spent: Decimal = Decimal("0.00")
    remaining: Decimal = Decimal("0.00")
    utilization_percentage: float = 0.0
    is_overrun: bool = False
    overrun_amount: Decimal = Decimal("0.00")


class BudgetUtilizationSummary(BaseModel):
    month: int
    year: int
    total_budgeted: Decimal
    total_spent: Decimal
    total_remaining: Decimal
    overall_utilization_percentage: float
    is_overrun: bool
    overrun_categories: list[str]
    budgets: list[BudgetResponse]
