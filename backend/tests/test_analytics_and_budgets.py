from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.router.on_startup.clear()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def user_a_headers(client):
    client.post(
        "/auth/register",
        json={"name": "Analytics User A", "email": "usera@analytics.com", "password": "Password123!"},
    )
    token = client.post(
        "/auth/login",
        json={"email": "usera@analytics.com", "password": "Password123!"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def user_b_headers(client):
    client.post(
        "/auth/register",
        json={"name": "Analytics User B", "email": "userb@analytics.com", "password": "Password123!"},
    )
    token = client.post(
        "/auth/login",
        json={"email": "userb@analytics.com", "password": "Password123!"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def add_tx(client, headers, amount, tx_type, category, tx_date, description="Tx"):
    res = client.post(
        "/transactions/",
        json={
            "amount": amount,
            "description": description,
            "category": category,
            "payment_method": "UPI",
            "transaction_type": tx_type,
            "transaction_date": tx_date,
        },
        headers=headers,
    )
    assert res.status_code == 201
    return res.json()


# ============================================================================
# 1. Financial Summary Tests
# ============================================================================

def test_financial_summary_empty(client, user_a_headers):
    res = client.get("/analytics/summary", headers=user_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_income"] == "0.00"
    assert data["total_expenses"] == "0.00"
    assert data["net_balance"] == "0.00"
    assert data["transaction_count"] == 0


def test_financial_summary_calculations(client, user_a_headers):
    # Add Income: 5000 + 2000 = 7000
    add_tx(client, user_a_headers, "5000.00", "income", "Other", "2026-11-01T10:00:00", "Salary")
    add_tx(client, user_a_headers, "2000.00", "income", "Other", "2026-11-05T10:00:00", "Freelance")

    # Add Expenses: 1500 + 500 + 250 = 2250
    add_tx(client, user_a_headers, "1500.00", "expense", "Bills", "2026-11-02T10:00:00", "Rent")
    add_tx(client, user_a_headers, "500.00", "expense", "Food", "2026-11-03T10:00:00", "Groceries")
    add_tx(client, user_a_headers, "250.00", "expense", "Transport", "2026-11-04T10:00:00", "Fuel")

    res = client.get("/analytics/summary", headers=user_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_income"] == "7000.00"
    assert data["total_expenses"] == "2250.00"
    assert data["net_balance"] == "4750.00"
    assert data["income_count"] == 2
    assert data["expense_count"] == 3
    assert data["transaction_count"] == 5


def test_financial_summary_date_filtering(client, user_a_headers):
    add_tx(client, user_a_headers, "1000.00", "income", "Other", "2026-11-01T10:00:00")
    add_tx(client, user_a_headers, "200.00", "expense", "Food", "2026-11-05T10:00:00")
    add_tx(client, user_a_headers, "300.00", "expense", "Food", "2026-11-20T10:00:00")

    # Filter Nov 01 to Nov 10
    res = client.get(
        "/analytics/summary",
        params={"start_date": "2026-11-01", "end_date": "2026-11-10"},
        headers=user_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_income"] == "1000.00"
    assert data["total_expenses"] == "200.00"
    assert data["net_balance"] == "800.00"
    assert data["transaction_count"] == 2


def test_financial_summary_invalid_date_range(client, user_a_headers):
    res = client.get(
        "/analytics/summary",
        params={"start_date": "2026-11-20", "end_date": "2026-11-10"},
        headers=user_a_headers,
    )
    assert res.status_code == 400


def test_financial_summary_period_views(client, user_a_headers):
    add_tx(client, user_a_headers, "100.00", "expense", "Food", "2026-11-11T12:00:00")

    # Daily view for 2026-11-11
    daily = client.get(
        "/analytics/summary",
        params={"period": "daily", "reference_date": "2026-11-11"},
        headers=user_a_headers,
    ).json()
    assert daily["total_expenses"] == "100.00"

    # Daily view for another date
    daily_other = client.get(
        "/analytics/summary",
        params={"period": "daily", "reference_date": "2026-11-12"},
        headers=user_a_headers,
    ).json()
    assert daily_other["total_expenses"] == "0.00"


# ============================================================================
# 2. Category-Wise Analytics Tests
# ============================================================================

def test_category_analytics_breakdown_and_highest(client, user_a_headers):
    add_tx(client, user_a_headers, "600.00", "expense", "Food", "2026-11-05T10:00:00")
    add_tx(client, user_a_headers, "400.00", "expense", "Food", "2026-11-06T10:00:00")
    add_tx(client, user_a_headers, "500.00", "expense", "Shopping", "2026-11-07T10:00:00")
    add_tx(client, user_a_headers, "500.00", "expense", "Bills", "2026-11-08T10:00:00")

    # Total expenses = 2000.00
    # Food = 1000.00 (50.0%)
    # Shopping = 500.00 (25.0%)
    # Bills = 500.00 (25.0%)
    res = client.get("/analytics/categories", headers=user_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_expenses"] == "2000.00"
    assert data["highest_spending_category"] == "Food"
    assert len(data["categories"]) == 3

    food_cat = next(c for c in data["categories"] if c["category"] == "Food")
    assert food_cat["amount"] == "1000.00"
    assert food_cat["percentage"] == 50.0
    assert food_cat["transaction_count"] == 2

    shop_cat = next(c for c in data["categories"] if c["category"] == "Shopping")
    assert shop_cat["amount"] == "500.00"
    assert shop_cat["percentage"] == 25.0


def test_category_analytics_empty(client, user_a_headers):
    res = client.get("/analytics/categories", headers=user_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_expenses"] == "0.00"
    assert data["highest_spending_category"] is None
    assert data["categories"] == []


# ============================================================================
# 3. Monthly Analytics Tests
# ============================================================================

def test_monthly_analytics_comparison_and_history(client, user_a_headers):
    # Previous Month: Oct 2026 -> Expense: 1000.00, Income: 2000.00
    add_tx(client, user_a_headers, "2000.00", "income", "Other", "2026-10-15T10:00:00")
    add_tx(client, user_a_headers, "1000.00", "expense", "Food", "2026-10-16T10:00:00")

    # Current Month: Nov 2026 -> Expense: 1500.00, Income: 3000.00
    add_tx(client, user_a_headers, "3000.00", "income", "Other", "2026-11-10T10:00:00")
    add_tx(client, user_a_headers, "1500.00", "expense", "Food", "2026-11-11T10:00:00")

    res = client.get(
        "/analytics/monthly",
        params={"reference_date": "2026-11-15", "months": 6},
        headers=user_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["current_month"] == "2026-11"
    assert data["current_month_income"] == "3000.00"
    assert data["current_month_expenses"] == "1500.00"
    assert data["current_month_net"] == "1500.00"

    assert data["previous_month"] == "2026-10"
    assert data["previous_month_income"] == "2000.00"
    assert data["previous_month_expenses"] == "1000.00"

    # Expense changed from 1000 to 1500 -> +500 (+50.0%)
    assert data["expense_change_amount"] == "500.00"
    assert data["expense_change_percentage"] == 50.0

    # Income changed from 2000 to 3000 -> +1000 (+50.0%)
    assert data["income_change_amount"] == "1000.00"
    assert data["income_change_percentage"] == 50.0

    # History contains requested 6 months
    assert len(data["history"]) == 6
    nov_pt = next(p for p in data["history"] if p["month"] == "2026-11")
    assert nov_pt["income"] == "3000.00"
    assert nov_pt["expenses"] == "1500.00"
    assert nov_pt["savings_rate"] == 50.0


# ============================================================================
# 4. Budget Management CRUD & Utilization Tests
# ============================================================================

def test_budget_creation_and_duplicate_prevention(client, user_a_headers):
    payload = {
        "category": "Food",
        "amount": "800.00",
        "month": 11,
        "year": 2026,
    }
    create_res = client.post("/budgets/", json=payload, headers=user_a_headers)
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["category"] == "Food"
    assert created["amount"] == "800.00"
    assert created["month"] == 11
    assert created["year"] == 2026
    assert created["spent"] == "0.00"
    assert created["remaining"] == "800.00"
    assert created["is_overrun"] is False

    # Attempting to create duplicate for same category, month, and year fails
    dup_res = client.post("/budgets/", json=payload, headers=user_a_headers)
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"].lower()


def test_budget_overall_monthly_budget(client, user_a_headers):
    # Overall budget has category = None
    payload = {
        "category": None,
        "amount": "5000.00",
        "month": 11,
        "year": 2026,
    }
    res = client.post("/budgets/", json=payload, headers=user_a_headers)
    assert res.status_code == 201
    assert res.json()["category"] is None
    assert res.json()["amount"] == "5000.00"


def test_budget_tracking_and_overrun(client, user_a_headers):
    # Create Food budget: 600.00
    client.post(
        "/budgets/",
        json={"category": "Food", "amount": "600.00", "month": 11, "year": 2026},
        headers=user_a_headers,
    )

    # Spend 400.00 on Food
    add_tx(client, user_a_headers, "400.00", "expense", "Food", "2026-11-05T10:00:00")

    # Fetch budget utilization
    util_res = client.get("/budgets/utilization", params={"month": 11, "year": 2026}, headers=user_a_headers)
    assert util_res.status_code == 200
    util_data = util_res.json()
    assert util_data["total_budgeted"] == "600.00"
    assert util_data["total_spent"] == "400.00"
    assert util_data["total_remaining"] == "200.00"
    assert util_data["overall_utilization_percentage"] == 66.67
    assert util_data["is_overrun"] is False

    # Spend another 300.00 on Food -> total spent 700.00, overrun 100.00
    add_tx(client, user_a_headers, "300.00", "expense", "Food", "2026-11-12T10:00:00")

    util_after = client.get("/budgets/utilization", params={"month": 11, "year": 2026}, headers=user_a_headers).json()
    assert util_after["total_spent"] == "700.00"
    assert util_after["total_remaining"] == "-100.00"
    assert util_after["is_overrun"] is True
    assert "Food" in util_after["overrun_categories"]
    assert util_after["budgets"][0]["is_overrun"] is True
    assert util_after["budgets"][0]["overrun_amount"] == "100.00"


def test_budget_update_and_delete(client, user_a_headers):
    created = client.post(
        "/budgets/",
        json={"category": "Transport", "amount": "300.00", "month": 11, "year": 2026},
        headers=user_a_headers,
    ).json()
    b_id = created["id"]

    # Update amount to 500.00
    patch_res = client.patch(
        f"/budgets/{b_id}",
        json={"amount": "500.00"},
        headers=user_a_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["amount"] == "500.00"

    # Get single budget
    get_res = client.get(f"/budgets/{b_id}", headers=user_a_headers)
    assert get_res.status_code == 200
    assert get_res.json()["amount"] == "500.00"

    # Delete budget
    del_res = client.delete(f"/budgets/{b_id}", headers=user_a_headers)
    assert del_res.status_code == 204

    # Fetch deleted returns 404
    assert client.get(f"/budgets/{b_id}", headers=user_a_headers).status_code == 404


# ============================================================================
# 5. Financial Insights Tests
# ============================================================================

def test_financial_insights_empty_dataset(client, user_a_headers):
    res = client.get("/analytics/insights", headers=user_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["has_sufficient_data"] is False
    assert len(data["insights"]) == 1
    assert data["insights"][0]["type"] == "info"


def test_financial_insights_with_data_and_budget_alert(client, user_a_headers):
    # Setup income and expense
    add_tx(client, user_a_headers, "10000.00", "income", "Other", "2026-11-01T10:00:00")
    add_tx(client, user_a_headers, "3500.00", "expense", "Shopping", "2026-11-02T10:00:00")

    # Setup a budget for Shopping that is overrun (Budget: 3000, Spent: 3500)
    client.post(
        "/budgets/",
        json={"category": "Shopping", "amount": "3000.00", "month": 11, "year": 2026},
        headers=user_a_headers,
    )

    res = client.get(
        "/analytics/insights",
        params={"reference_date": "2026-11-15"},
        headers=user_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["has_sufficient_data"] is True
    assert data["top_spending_category"] == "Shopping"
    assert data["savings_rate"] == 65.0  # (10000 - 3500) / 10000 = 65%

    # Overrun alert present
    assert any("budget overrun" in i["title"].lower() for i in data["insights"])
    assert len(data["budget_alerts"]) == 1


# ============================================================================
# 6. Cross-User Data Isolation Tests
# ============================================================================

def test_analytics_and_budgets_cross_user_isolation(client, user_a_headers, user_b_headers):
    # User A creates a budget and transactions
    client.post(
        "/budgets/",
        json={"category": "Bills", "amount": "1200.00", "month": 11, "year": 2026},
        headers=user_a_headers,
    )
    add_tx(client, user_a_headers, "4000.00", "income", "Other", "2026-11-01T10:00:00")
    add_tx(client, user_a_headers, "1000.00", "expense", "Bills", "2026-11-02T10:00:00")

    # User B queries summary -> sees 0 income, 0 expense
    b_summary = client.get("/analytics/summary", headers=user_b_headers).json()
    assert b_summary["total_income"] == "0.00"
    assert b_summary["total_expenses"] == "0.00"

    # User B queries budgets -> sees 0 budgets
    b_budgets = client.get("/budgets/", headers=user_b_headers).json()
    assert len(b_budgets) == 0

    # User A queries budgets -> sees 1 budget
    a_budgets = client.get("/budgets/", headers=user_a_headers).json()
    assert len(a_budgets) == 1
    a_budget_id = a_budgets[0]["id"]

    # User B cannot view User A's budget -> 404
    assert client.get(f"/budgets/{a_budget_id}", headers=user_b_headers).status_code == 404

    # User B cannot update User A's budget -> 404
    assert client.patch(f"/budgets/{a_budget_id}", json={"amount": "2000.00"}, headers=user_b_headers).status_code == 404

    # User B cannot delete User A's budget -> 404
    assert client.delete(f"/budgets/{a_budget_id}", headers=user_b_headers).status_code == 404
