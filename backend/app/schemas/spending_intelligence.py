from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel


class FinancialSummaryResponse(BaseModel):
    total_income: Decimal
    total_expenses: Decimal
    net_balance: Decimal
    period: str
    start_date: date | None = None
    end_date: date | None = None
    transaction_count: int
    income_count: int
    expense_count: int


class CategoryBreakdown(BaseModel):
    category: str
    amount: Decimal
    percentage: float
    transaction_count: int


class CategoryAnalyticsResponse(BaseModel):
    total_expenses: Decimal
    highest_spending_category: str | None = None
    categories: list[CategoryBreakdown]
    start_date: date | None = None
    end_date: date | None = None


class MonthlySummaryPoint(BaseModel):
    month: str
    year: int
    month_number: int
    income: Decimal
    expenses: Decimal
    net: Decimal
    savings_rate: float


class MonthlyAnalyticsResponse(BaseModel):
    current_month: str
    current_month_income: Decimal
    current_month_expenses: Decimal
    current_month_net: Decimal
    previous_month: str
    previous_month_income: Decimal
    previous_month_expenses: Decimal
    previous_month_net: Decimal
    expense_change_amount: Decimal
    expense_change_percentage: float | None = None
    income_change_amount: Decimal
    income_change_percentage: float | None = None
    history: list[MonthlySummaryPoint]


class FinancialInsight(BaseModel):
    type: str
    title: str
    message: str
    category: str | None = None
    data: dict[str, Any] | None = None


class FinancialInsightsResponse(BaseModel):
    has_sufficient_data: bool
    top_spending_category: str | None = None
    savings_rate: float | None = None
    insights: list[FinancialInsight]
    budget_alerts: list[str]


class SpendingChange(BaseModel):
    category: str
    current_spend: Decimal
    expected_spend: Decimal
    change_amount: Decimal


class UnusualTransaction(BaseModel):
    transaction_id: int
    description: str
    category: str
    amount: Decimal
    historical_median: Decimal
    date: date


class SpendingIntelligenceResponse(BaseModel):
    has_sufficient_history: bool
    health_status: str
    current_month_spending: Decimal
    comparison_spending: Decimal | None = None
    spending_change_amount: Decimal | None = None
    spending_change_percentage: float | None = None
    category_changes: list[SpendingChange]
    unusual_transactions: list[UnusualTransaction]
    projected_month_end_spending: Decimal | None = None
    monthly_budget: Decimal | None = None
    projected_budget_overrun: Decimal | None = None
    recommendation: str
    explanation: str
