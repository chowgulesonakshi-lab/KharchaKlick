import calendar
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.analytics import (
    CategoryAnalyticsResponse,
    CategoryBreakdown,
    FinancialInsight,
    FinancialInsightsResponse,
    FinancialSummaryResponse,
    MonthlyAnalyticsResponse,
    MonthlySummaryPoint,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def to_decimal(val: object) -> Decimal:
    """Safely convert any numeric/scalar value to 2-decimal-place Decimal."""
    if val is None:
        return Decimal("0.00")
    if isinstance(val, Decimal):
        return val.quantize(Decimal("0.01"))
    return Decimal(str(val)).quantize(Decimal("0.01"))


def get_month_range(year: int, month: int) -> tuple[datetime, datetime]:
    """Return start and end UTC datetime bounds for a given month and year."""
    _, last_day = calendar.monthrange(year, month)
    start_dt = datetime(year, month, 1, 0, 0, 0)
    end_dt = datetime(year, month, last_day, 23, 59, 59, 999999)
    return start_dt, end_dt


@router.get("/summary", response_model=FinancialSummaryResponse)
def get_financial_summary(
    start_date: date | None = None,
    end_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    period: Literal["all", "daily", "weekly", "monthly"] | None = None,
    reference_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve total income, total expenses, net balance, and transaction counts."""
    eff_start = start_date or date_from
    eff_end = end_date or date_to
    period_label = period or "custom" if (eff_start or eff_end) else "all"

    if period is not None:
        ref = reference_date or date.today()
        if period == "daily":
            eff_start = eff_start or ref
            eff_end = eff_end or ref
        elif period == "weekly":
            start_of_week = ref - timedelta(days=ref.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            eff_start = eff_start or start_of_week
            eff_end = eff_end or end_of_week
        elif period == "monthly":
            _, last_day = calendar.monthrange(ref.year, ref.month)
            eff_start = eff_start or date(ref.year, ref.month, 1)
            eff_end = eff_end or date(ref.year, ref.month, last_day)

    if eff_start is not None and eff_end is not None and eff_start > eff_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date cannot be after end date",
        )

    date_filters = []
    if eff_start:
        date_filters.append(Transaction.transaction_date >= datetime.combine(eff_start, time.min))
    if eff_end:
        date_filters.append(
            Transaction.transaction_date < datetime.combine(eff_end + timedelta(days=1), time.min)
        )

    # Calculate total income
    raw_income = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == "income",
            *date_filters,
        )
        .scalar()
    )
    total_income = to_decimal(raw_income)

    # Calculate total expenses
    raw_expenses = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == "expense",
            *date_filters,
        )
        .scalar()
    )
    total_expenses = to_decimal(raw_expenses)

    net_balance = (total_income - total_expenses).quantize(Decimal("0.01"))

    # Transaction counts
    income_count = (
        db.query(func.count(Transaction.id))
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == "income",
            *date_filters,
        )
        .scalar()
        or 0
    )
    expense_count = (
        db.query(func.count(Transaction.id))
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == "expense",
            *date_filters,
        )
        .scalar()
        or 0
    )

    return FinancialSummaryResponse(
        total_income=total_income,
        total_expenses=total_expenses,
        net_balance=net_balance,
        period=period_label,
        start_date=eff_start,
        end_date=eff_end,
        transaction_count=income_count + expense_count,
        income_count=income_count,
        expense_count=expense_count,
    )


@router.get("/categories", response_model=CategoryAnalyticsResponse)
def get_category_breakdown(
    start_date: date | None = None,
    end_date: date | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve category-wise expense breakdown, percentages, and highest-spending category."""
    eff_start = start_date or date_from
    eff_end = end_date or date_to

    if eff_start is not None and eff_end is not None and eff_start > eff_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date cannot be after end date",
        )

    date_filters = []
    if eff_start:
        date_filters.append(Transaction.transaction_date >= datetime.combine(eff_start, time.min))
    if eff_end:
        date_filters.append(
            Transaction.transaction_date < datetime.combine(eff_end + timedelta(days=1), time.min)
        )

    # Query sum of expenses per category
    category_rows = (
        db.query(
            Transaction.category,
            func.sum(Transaction.amount).label("category_amount"),
            func.count(Transaction.id).label("tx_count"),
        )
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == "expense",
            *date_filters,
        )
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )

    raw_total = sum((to_decimal(r.category_amount) for r in category_rows), Decimal("0.00"))
    total_expenses = raw_total.quantize(Decimal("0.01"))

    categories_list: list[CategoryBreakdown] = []
    for r in category_rows:
        amount = to_decimal(r.category_amount)
        pct = (
            round(float((amount / total_expenses) * 100), 2)
            if total_expenses > 0
            else 0.0
        )
        categories_list.append(
            CategoryBreakdown(
                category=r.category,
                amount=amount,
                percentage=pct,
                transaction_count=r.tx_count,
            )
        )

    highest_category = categories_list[0].category if categories_list else None

    return CategoryAnalyticsResponse(
        total_expenses=total_expenses,
        highest_spending_category=highest_category,
        categories=categories_list,
        start_date=eff_start,
        end_date=eff_end,
    )


@router.get("/monthly", response_model=MonthlyAnalyticsResponse)
def get_monthly_analytics(
    year: int | None = Query(default=None, ge=2000, le=2100),
    months: int = Query(default=6, ge=1, le=24),
    reference_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve monthly trend data, month-over-month comparison, and percentage changes."""
    ref = reference_date or date.today()
    curr_year = year or ref.year
    curr_month = ref.month if year is None else 12

    # Current month metrics
    curr_start, curr_end = get_month_range(curr_year, curr_month)
    curr_income = to_decimal(
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == "income",
            Transaction.transaction_date >= curr_start,
            Transaction.transaction_date <= curr_end,
        )
        .scalar()
    )
    curr_expenses = to_decimal(
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == "expense",
            Transaction.transaction_date >= curr_start,
            Transaction.transaction_date <= curr_end,
        )
        .scalar()
    )
    curr_net = (curr_income - curr_expenses).quantize(Decimal("0.01"))

    # Previous month metrics
    if curr_month == 1:
        prev_month = 12
        prev_year = curr_year - 1
    else:
        prev_month = curr_month - 1
        prev_year = curr_year

    prev_start, prev_end = get_month_range(prev_year, prev_month)
    prev_income = to_decimal(
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == "income",
            Transaction.transaction_date >= prev_start,
            Transaction.transaction_date <= prev_end,
        )
        .scalar()
    )
    prev_expenses = to_decimal(
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == "expense",
            Transaction.transaction_date >= prev_start,
            Transaction.transaction_date <= prev_end,
        )
        .scalar()
    )
    prev_net = (prev_income - prev_expenses).quantize(Decimal("0.01"))

    expense_change_amount = (curr_expenses - prev_expenses).quantize(Decimal("0.01"))
    income_change_amount = (curr_income - prev_income).quantize(Decimal("0.01"))

    expense_change_pct = (
        round(float(((curr_expenses - prev_expenses) / prev_expenses) * 100), 2)
        if prev_expenses > 0
        else None
    )
    income_change_pct = (
        round(float(((curr_income - prev_income) / prev_income) * 100), 2)
        if prev_income > 0
        else None
    )

    # Build historical trend for the last N months
    history: list[MonthlySummaryPoint] = []
    y, m = curr_year, curr_month
    month_slots: list[tuple[int, int]] = []
    for _ in range(months):
        month_slots.append((y, m))
        m -= 1
        if m < 1:
            m = 12
            y -= 1
    month_slots.reverse()

    for slot_y, slot_m in month_slots:
        s_dt, e_dt = get_month_range(slot_y, slot_m)
        slot_income = to_decimal(
            db.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.user_id == current_user.id,
                Transaction.transaction_type == "income",
                Transaction.transaction_date >= s_dt,
                Transaction.transaction_date <= e_dt,
            )
            .scalar()
        )
        slot_expenses = to_decimal(
            db.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.user_id == current_user.id,
                Transaction.transaction_type == "expense",
                Transaction.transaction_date >= s_dt,
                Transaction.transaction_date <= e_dt,
            )
            .scalar()
        )
        slot_net = (slot_income - slot_expenses).quantize(Decimal("0.01"))
        savings_rate = (
            round(float(((slot_income - slot_expenses) / slot_income) * 100), 2)
            if slot_income > 0
            else 0.0
        )

        history.append(
            MonthlySummaryPoint(
                month=f"{slot_y:04d}-{slot_m:02d}",
                year=slot_y,
                month_number=slot_m,
                income=slot_income,
                expenses=slot_expenses,
                net=slot_net,
                savings_rate=savings_rate,
            )
        )

    return MonthlyAnalyticsResponse(
        current_month=f"{curr_year:04d}-{curr_month:02d}",
        current_month_income=curr_income,
        current_month_expenses=curr_expenses,
        current_month_net=curr_net,
        previous_month=f"{prev_year:04d}-{prev_month:02d}",
        previous_month_income=prev_income,
        previous_month_expenses=prev_expenses,
        previous_month_net=prev_net,
        expense_change_amount=expense_change_amount,
        expense_change_percentage=expense_change_pct,
        income_change_amount=income_change_amount,
        income_change_percentage=income_change_pct,
        history=history,
    )


@router.get("/insights", response_model=FinancialInsightsResponse)
def get_financial_insights(
    reference_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate meaningful financial insights, category concentration checks, and budget alerts."""
    ref = reference_date or date.today()
    curr_year, curr_month = ref.year, ref.month

    # Total user transactions check
    total_tx_count = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.user_id == current_user.id)
        .scalar()
        or 0
    )

    if total_tx_count == 0:
        return FinancialInsightsResponse(
            has_sufficient_data=False,
            top_spending_category=None,
            savings_rate=None,
            insights=[
                FinancialInsight(
                    type="info",
                    title="No Data Available",
                    message="No transactions recorded yet. Start logging expenses to unlock personalized financial insights.",
                )
            ],
            budget_alerts=[],
        )

    # Current month data
    curr_start, curr_end = get_month_range(curr_year, curr_month)
    curr_income = to_decimal(
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == "income",
            Transaction.transaction_date >= curr_start,
            Transaction.transaction_date <= curr_end,
        )
        .scalar()
    )
    curr_expenses = to_decimal(
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == "expense",
            Transaction.transaction_date >= curr_start,
            Transaction.transaction_date <= curr_end,
        )
        .scalar()
    )

    # Previous month data
    if curr_month == 1:
        prev_month, prev_year = 12, curr_year - 1
    else:
        prev_month, prev_year = curr_month - 1, curr_year

    prev_start, prev_end = get_month_range(prev_year, prev_month)
    prev_expenses = to_decimal(
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == "expense",
            Transaction.transaction_date >= prev_start,
            Transaction.transaction_date <= prev_end,
        )
        .scalar()
    )

    # Category breakdown for current month
    category_rows = (
        db.query(
            Transaction.category,
            func.sum(Transaction.amount).label("category_amount"),
        )
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == "expense",
            Transaction.transaction_date >= curr_start,
            Transaction.transaction_date <= curr_end,
        )
        .group_by(Transaction.category)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )

    insights: list[FinancialInsight] = []
    top_category: str | None = None
    if category_rows:
        top_category = category_rows[0].category
        top_cat_amount = to_decimal(category_rows[0].category_amount)
        if curr_expenses > 0:
            top_cat_pct = round(float((top_cat_amount / curr_expenses) * 100), 1)
            if top_cat_pct >= 50.0:
                insights.append(
                    FinancialInsight(
                        type="warning",
                        title="High Category Concentration",
                        message=f"{top_category} accounts for {top_cat_pct}% of your total expenses this month (₹{top_cat_amount}).",
                        category=top_category,
                        data={"category": top_category, "percentage": top_cat_pct, "amount": float(top_cat_amount)},
                    )
                )
            else:
                insights.append(
                    FinancialInsight(
                        type="info",
                        title="Top Spending Category",
                        message=f"Your highest expenditure this month is in {top_category} at ₹{top_cat_amount} ({top_cat_pct}%).",
                        category=top_category,
                        data={"category": top_category, "percentage": top_cat_pct, "amount": float(top_cat_amount)},
                    )
                )

    # Month-over-month comparison insight
    if prev_expenses > 0 and curr_expenses > 0:
        pct_change = round(float(((curr_expenses - prev_expenses) / prev_expenses) * 100), 1)
        if pct_change >= 20.0:
            insights.append(
                FinancialInsight(
                    type="warning",
                    title="Spending Surge Detected",
                    message=f"Your expenses this month are {pct_change}% higher than last month (₹{curr_expenses} vs ₹{prev_expenses}).",
                    data={"percentage_increase": pct_change, "current": float(curr_expenses), "previous": float(prev_expenses)},
                )
            )
        elif pct_change <= -10.0:
            insights.append(
                FinancialInsight(
                    type="positive",
                    title="Spending Reduced",
                    message=f"Great job! You spent {abs(pct_change)}% less this month compared to last month.",
                    data={"percentage_decrease": abs(pct_change), "current": float(curr_expenses), "previous": float(prev_expenses)},
                )
            )
        else:
            insights.append(
                FinancialInsight(
                    type="info",
                    title="Consistent Spending",
                    message=f"Your spending is consistent with last month ({'+' if pct_change > 0 else ''}{pct_change}% change).",
                    data={"percentage_change": pct_change},
                )
            )
    elif prev_expenses == 0 and curr_expenses > 0:
        insights.append(
            FinancialInsight(
                type="info",
                title="Baseline Established",
                message="Spending recorded for this month establishes a baseline for future comparisons.",
            )
        )

    # Savings rate calculation & insight
    savings_rate: float | None = None
    if curr_income > 0:
        savings_rate = round(float(((curr_income - curr_expenses) / curr_income) * 100), 1)
        if savings_rate >= 20.0:
            insights.append(
                FinancialInsight(
                    type="positive",
                    title="Strong Savings Rate",
                    message=f"You saved {savings_rate}% of your income this month.",
                    data={"savings_rate": savings_rate},
                )
            )
        elif savings_rate < 0:
            deficit = curr_expenses - curr_income
            insights.append(
                FinancialInsight(
                    type="alert",
                    title="Deficit Warning",
                    message=f"Your expenses exceed your income this month by ₹{deficit}.",
                    data={"deficit": float(deficit)},
                )
            )

    # Budget overrun alerts
    budgets = (
        db.query(Budget)
        .filter(
            Budget.user_id == current_user.id,
            Budget.month == curr_month,
            Budget.year == curr_year,
        )
        .all()
    )

    budget_alerts: list[str] = []
    for b in budgets:
        b_query = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == current_user.id,
            Transaction.transaction_type == "expense",
            Transaction.transaction_date >= curr_start,
            Transaction.transaction_date <= curr_end,
        )
        if b.category:
            b_query = b_query.filter(Transaction.category == b.category)
        spent = to_decimal(b_query.scalar())
        cat_name = b.category or "Overall"
        if spent > b.amount:
            overrun = spent - b.amount
            alert_msg = f"{cat_name} budget exceeded by ₹{overrun} (Spent: ₹{spent}, Limit: ₹{b.amount})"
            budget_alerts.append(alert_msg)
            insights.append(
                FinancialInsight(
                    type="alert",
                    title=f"Budget Overrun: {cat_name}",
                    message=alert_msg,
                    category=b.category,
                    data={"category": cat_name, "spent": float(spent), "budget": float(b.amount), "overrun": float(overrun)},
                )
            )
        elif b.amount > 0 and (spent / b.amount) >= Decimal("0.85"):
            util = round(float((spent / b.amount) * 100), 1)
            insights.append(
                FinancialInsight(
                    type="warning",
                    title=f"Budget Warning: {cat_name}",
                    message=f"{cat_name} budget is at {util}% capacity (₹{spent} of ₹{b.amount}).",
                    category=b.category,
                    data={"category": cat_name, "spent": float(spent), "budget": float(b.amount), "utilization": util},
                )
            )

    return FinancialInsightsResponse(
        has_sufficient_data=True,
        top_spending_category=top_category,
        savings_rate=savings_rate,
        insights=insights,
        budget_alerts=budget_alerts,
    )
