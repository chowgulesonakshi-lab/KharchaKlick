import calendar
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.budget import (
    BudgetCreate,
    BudgetResponse,
    BudgetUpdate,
    BudgetUtilizationSummary,
)

router = APIRouter(prefix="/budgets", tags=["Budgets"])


def get_month_date_range(year: int, month: int) -> tuple[datetime, datetime]:
    """Return start and end UTC datetime bounds for a given month and year."""
    _, last_day = calendar.monthrange(year, month)
    start_dt = datetime(year, month, 1, 0, 0, 0)
    end_dt = datetime(year, month, last_day, 23, 59, 59, 999999)
    return start_dt, end_dt


def compute_budget_metrics(budget: Budget, db: Session) -> BudgetResponse:
    """Calculate actual spent, remaining, overrun, and utilization percentage for a budget."""
    start_dt, end_dt = get_month_date_range(budget.year, budget.month)
    query = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == budget.user_id,
        Transaction.transaction_type == "expense",
        Transaction.transaction_date >= start_dt,
        Transaction.transaction_date <= end_dt,
    )
    if budget.category is not None:
        query = query.filter(Transaction.category == budget.category)

    raw_spent = query.scalar() or Decimal("0.00")
    spent = Decimal(str(raw_spent)).quantize(Decimal("0.01"))
    remaining = (budget.amount - spent).quantize(Decimal("0.01"))
    is_overrun = spent > budget.amount
    overrun_amount = max(Decimal("0.00"), spent - budget.amount).quantize(Decimal("0.01"))
    utilization_percentage = (
        round(float((spent / budget.amount) * 100), 2) if budget.amount > 0 else 0.0
    )

    return BudgetResponse(
        id=budget.id,
        user_id=budget.user_id,
        category=budget.category,
        amount=budget.amount,
        month=budget.month,
        year=budget.year,
        created_at=budget.created_at,
        spent=spent,
        remaining=remaining,
        utilization_percentage=utilization_percentage,
        is_overrun=is_overrun,
        overrun_amount=overrun_amount,
    )


@router.post("/", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    payload: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new monthly or category-specific budget for the authenticated user."""
    # Prevent duplicate budgets for the same category, month, and year
    existing = (
        db.query(Budget)
        .filter(
            Budget.user_id == current_user.id,
            Budget.category == payload.category,
            Budget.month == payload.month,
            Budget.year == payload.year,
        )
        .first()
    )
    if existing:
        target = f"for '{payload.category}'" if payload.category else "overall"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A budget {target} in {payload.month}/{payload.year} already exists. Update the existing budget instead.",
        )

    budget = Budget(
        user_id=current_user.id,
        category=payload.category,
        amount=payload.amount,
        month=payload.month,
        year=payload.year,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return compute_budget_metrics(budget, db)


@router.get("/utilization", response_model=BudgetUtilizationSummary)
def get_budget_utilization(
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get aggregated budget utilization and overruns for a specific month and year."""
    now = datetime.now(timezone.utc)
    target_month = month or now.month
    target_year = year or now.year

    budgets = (
        db.query(Budget)
        .filter(
            Budget.user_id == current_user.id,
            Budget.month == target_month,
            Budget.year == target_year,
        )
        .order_by(Budget.category.asc().nullsfirst(), Budget.id.asc())
        .all()
    )

    budget_responses = [compute_budget_metrics(b, db) for b in budgets]
    total_budgeted = sum((b.amount for b in budget_responses), Decimal("0.00")).quantize(Decimal("0.01"))
    total_spent = sum((b.spent for b in budget_responses), Decimal("0.00")).quantize(Decimal("0.01"))
    total_remaining = (total_budgeted - total_spent).quantize(Decimal("0.01"))
    overall_utilization = (
        round(float((total_spent / total_budgeted) * 100), 2) if total_budgeted > 0 else 0.0
    )
    overrun_categories = [
        b.category or "Overall" for b in budget_responses if b.is_overrun
    ]

    return BudgetUtilizationSummary(
        month=target_month,
        year=target_year,
        total_budgeted=total_budgeted,
        total_spent=total_spent,
        total_remaining=total_remaining,
        overall_utilization_percentage=overall_utilization,
        is_overrun=len(overrun_categories) > 0,
        overrun_categories=overrun_categories,
        budgets=budget_responses,
    )


@router.get("/", response_model=list[BudgetResponse])
def list_budgets(
    month: int | None = Query(default=None, ge=1, le=12),
    year: int | None = Query(default=None, ge=2000, le=2100),
    category: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all budgets belonging to the authenticated user with utilization status."""
    query = db.query(Budget).filter(Budget.user_id == current_user.id)
    if month is not None:
        query = query.filter(Budget.month == month)
    if year is not None:
        query = query.filter(Budget.year == year)
    if category is not None:
        query = query.filter(Budget.category == category)

    budgets = query.order_by(Budget.year.desc(), Budget.month.desc(), Budget.id.desc()).all()
    return [compute_budget_metrics(b, db) for b in budgets]


@router.get("/{budget_id}", response_model=BudgetResponse)
def get_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a specific budget by ID along with its utilization metrics."""
    budget = (
        db.query(Budget)
        .filter(Budget.id == budget_id, Budget.user_id == current_user.id)
        .first()
    )
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return compute_budget_metrics(budget, db)


@router.patch("/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: int,
    payload: BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a budget amount, category, or time period."""
    budget = (
        db.query(Budget)
        .filter(Budget.id == budget_id, Budget.user_id == current_user.id)
        .first()
    )
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")

    updates = payload.model_dump(exclude_unset=True)
    new_category = updates.get("category", budget.category)
    new_month = updates.get("month", budget.month)
    new_year = updates.get("year", budget.year)

    # If category/month/year changed, verify it doesn't conflict with another budget
    if (new_category != budget.category) or (new_month != budget.month) or (new_year != budget.year):
        conflict = (
            db.query(Budget)
            .filter(
                Budget.user_id == current_user.id,
                Budget.category == new_category,
                Budget.month == new_month,
                Budget.year == new_year,
                Budget.id != budget.id,
            )
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Another budget for this category and month/year already exists.",
            )

    for field, value in updates.items():
        setattr(budget, field, value)

    db.commit()
    db.refresh(budget)
    return compute_budget_metrics(budget, db)


@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a budget."""
    budget = (
        db.query(Budget)
        .filter(Budget.id == budget_id, Budget.user_id == current_user.id)
        .first()
    )
    if budget is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")

    db.delete(budget)
    db.commit()
