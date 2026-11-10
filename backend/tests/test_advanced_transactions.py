from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.user import User

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
def auth_headers(client):
    client.post(
        "/auth/register",
        json={"name": "Tx User", "email": "txuser@example.com", "password": "Password123!"},
    )
    login_resp = client.post(
        "/auth/login",
        json={"email": "txuser@example.com", "password": "Password123!"},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def second_user_headers(client):
    client.post(
        "/auth/register",
        json={"name": "Second User", "email": "second@example.com", "password": "Password123!"},
    )
    login_resp = client.post(
        "/auth/login",
        json={"email": "second@example.com", "password": "Password123!"},
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_sample_tx(client, headers, **overrides):
    payload = {
        "amount": "100.00",
        "description": "Coffee",
        "merchant": "Cafe",
        "category": "Food",
        "payment_method": "UPI",
        "transaction_type": "expense",
        "transaction_date": "2026-11-05T10:00:00",
    }
    payload.update(overrides)
    res = client.post("/transactions/", json=payload, headers=headers)
    assert res.status_code == 201
    return res.json()


# ============================================================================
# 1. Date-Range Filtering Tests
# ============================================================================

def test_date_range_filtering_both_dates(client, auth_headers):
    # Nov 1, Nov 5, Nov 10
    create_sample_tx(client, auth_headers, description="Nov 1", transaction_date="2026-11-01T10:00:00")
    create_sample_tx(client, auth_headers, description="Nov 5", transaction_date="2026-11-05T10:00:00")
    create_sample_tx(client, auth_headers, description="Nov 10", transaction_date="2026-11-10T10:00:00")

    # Filter Nov 2 to Nov 8 -> only Nov 5
    res = client.get(
        "/transactions/",
        params={"start_date": "2026-11-02", "end_date": "2026-11-08"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["description"] == "Nov 5"

    # Also test date_from and date_to alias
    res_alias = client.get(
        "/transactions/",
        params={"date_from": "2026-11-02", "date_to": "2026-11-08"},
        headers=auth_headers,
    )
    assert res_alias.status_code == 200
    assert len(res_alias.json()) == 1


def test_start_date_only_filtering(client, auth_headers):
    create_sample_tx(client, auth_headers, description="Oct 31", transaction_date="2026-10-31T23:59:00")
    create_sample_tx(client, auth_headers, description="Nov 01", transaction_date="2026-11-01T08:00:00")
    create_sample_tx(client, auth_headers, description="Nov 05", transaction_date="2026-11-05T12:00:00")

    res = client.get(
        "/transactions/",
        params={"start_date": "2026-11-01"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    descriptions = [tx["description"] for tx in res.json()]
    assert "Nov 01" in descriptions
    assert "Nov 05" in descriptions
    assert "Oct 31" not in descriptions


def test_end_date_only_filtering(client, auth_headers):
    create_sample_tx(client, auth_headers, description="Early Nov", transaction_date="2026-11-02T10:00:00")
    create_sample_tx(client, auth_headers, description="Mid Nov", transaction_date="2026-11-15T10:00:00")

    res = client.get(
        "/transactions/",
        params={"end_date": "2026-11-05"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    descriptions = [tx["description"] for tx in res.json()]
    assert "Early Nov" in descriptions
    assert "Mid Nov" not in descriptions


def test_invalid_date_range_rejected(client, auth_headers):
    res = client.get(
        "/transactions/",
        params={"start_date": "2026-11-15", "end_date": "2026-11-10"},
        headers=auth_headers,
    )
    assert res.status_code == 400
    assert "start date cannot be after end date" in res.json()["detail"].lower()


def test_preset_view_daily_weekly_monthly(client, auth_headers):
    # Anchor date: Wednesday 2026-11-11
    # Monday of that week: 2026-11-09
    # Sunday of that week: 2026-11-15
    create_sample_tx(client, auth_headers, description="Today Tx", transaction_date="2026-11-11T14:00:00")
    create_sample_tx(client, auth_headers, description="This Week Tx", transaction_date="2026-11-09T09:00:00")
    create_sample_tx(client, auth_headers, description="This Month Tx", transaction_date="2026-11-20T10:00:00")
    create_sample_tx(client, auth_headers, description="Next Month Tx", transaction_date="2026-12-05T10:00:00")

    # Daily view
    daily_res = client.get(
        "/transactions/",
        params={"view": "daily", "reference_date": "2026-11-11"},
        headers=auth_headers,
    )
    assert daily_res.status_code == 200
    daily_descs = [tx["description"] for tx in daily_res.json()]
    assert daily_descs == ["Today Tx"]

    # Weekly view
    weekly_res = client.get(
        "/transactions/",
        params={"view": "weekly", "reference_date": "2026-11-11"},
        headers=auth_headers,
    )
    assert weekly_res.status_code == 200
    weekly_descs = [tx["description"] for tx in weekly_res.json()]
    assert "Today Tx" in weekly_descs
    assert "This Week Tx" in weekly_descs
    assert "This Month Tx" not in weekly_descs

    # Monthly view
    monthly_res = client.get(
        "/transactions/",
        params={"view": "monthly", "reference_date": "2026-11-11"},
        headers=auth_headers,
    )
    assert monthly_res.status_code == 200
    monthly_descs = [tx["description"] for tx in monthly_res.json()]
    assert "Today Tx" in monthly_descs
    assert "This Week Tx" in monthly_descs
    assert "This Month Tx" in monthly_descs
    assert "Next Month Tx" not in monthly_descs


# ============================================================================
# 2. Payment Method Filtering Tests
# ============================================================================

def test_payment_method_filtering(client, auth_headers):
    create_sample_tx(client, auth_headers, description="Cash Lunch", payment_method="Cash")
    create_sample_tx(client, auth_headers, description="UPI Groceries", payment_method="UPI")
    create_sample_tx(client, auth_headers, description="Credit Card Laptop", payment_method="Credit Card")
    create_sample_tx(client, auth_headers, description="Debit Card Fuel", payment_method="Debit Card")
    create_sample_tx(client, auth_headers, description="Net Banking Rent", payment_method="Net Banking")
    create_sample_tx(client, auth_headers, description="Other Fee", payment_method="Other")

    # Filter UPI
    upi_res = client.get("/transactions/", params={"payment_method": "UPI"}, headers=auth_headers)
    assert upi_res.status_code == 200
    assert len(upi_res.json()) == 1
    assert upi_res.json()[0]["description"] == "UPI Groceries"

    # Filter Credit Card
    cc_res = client.get("/transactions/", params={"payment_method": "Credit Card"}, headers=auth_headers)
    assert cc_res.status_code == 200
    assert len(cc_res.json()) == 1
    assert cc_res.json()[0]["description"] == "Credit Card Laptop"

    # Filter Debit Card
    dc_res = client.get("/transactions/", params={"payment_method": "Debit Card"}, headers=auth_headers)
    assert dc_res.status_code == 200
    assert len(dc_res.json()) == 1
    assert dc_res.json()[0]["description"] == "Debit Card Fuel"


def test_invalid_payment_method_rejected(client, auth_headers):
    res = client.get("/transactions/", params={"payment_method": "Crypto"}, headers=auth_headers)
    assert res.status_code == 422


# ============================================================================
# 3. Sorting Tests
# ============================================================================

def test_sorting_by_transaction_date(client, auth_headers):
    create_sample_tx(client, auth_headers, description="Oldest", transaction_date="2026-11-01T10:00:00")
    create_sample_tx(client, auth_headers, description="Middle", transaction_date="2026-11-05T10:00:00")
    create_sample_tx(client, auth_headers, description="Newest", transaction_date="2026-11-10T10:00:00")

    # Ascending
    asc_res = client.get(
        "/transactions/",
        params={"sort_by": "transaction_date", "sort_order": "asc"},
        headers=auth_headers,
    )
    assert asc_res.status_code == 200
    assert [tx["description"] for tx in asc_res.json()] == ["Oldest", "Middle", "Newest"]

    # Descending
    desc_res = client.get(
        "/transactions/",
        params={"sort_by": "transaction_date", "sort_order": "desc"},
        headers=auth_headers,
    )
    assert desc_res.status_code == 200
    assert [tx["description"] for tx in desc_res.json()] == ["Newest", "Middle", "Oldest"]


def test_sorting_by_amount(client, auth_headers):
    create_sample_tx(client, auth_headers, description="Small", amount="25.00")
    create_sample_tx(client, auth_headers, description="Medium", amount="150.00")
    create_sample_tx(client, auth_headers, description="Large", amount="999.00")

    # Ascending
    asc_res = client.get(
        "/transactions/",
        params={"sort_by": "amount", "sort_order": "asc"},
        headers=auth_headers,
    )
    assert asc_res.status_code == 200
    assert [tx["description"] for tx in asc_res.json()] == ["Small", "Medium", "Large"]

    # Descending
    desc_res = client.get(
        "/transactions/",
        params={"sort_by": "amount", "sort_order": "desc"},
        headers=auth_headers,
    )
    assert desc_res.status_code == 200
    assert [tx["description"] for tx in desc_res.json()] == ["Large", "Medium", "Small"]


def test_sorting_by_created_at(client, auth_headers):
    tx1 = create_sample_tx(client, auth_headers, description="Created First")
    tx2 = create_sample_tx(client, auth_headers, description="Created Second")

    asc_res = client.get(
        "/transactions/",
        params={"sort_by": "created_at", "sort_order": "asc"},
        headers=auth_headers,
    )
    assert asc_res.status_code == 200
    assert [tx["id"] for tx in asc_res.json()] == [tx1["id"], tx2["id"]]

    desc_res = client.get(
        "/transactions/",
        params={"sort_by": "created_at", "sort_order": "desc"},
        headers=auth_headers,
    )
    assert desc_res.status_code == 200
    assert [tx["id"] for tx in desc_res.json()] == [tx2["id"], tx1["id"]]


def test_invalid_sorting_parameters_rejected(client, auth_headers):
    res_field = client.get("/transactions/", params={"sort_by": "password"}, headers=auth_headers)
    assert res_field.status_code == 422

    res_order = client.get("/transactions/", params={"sort_order": "sideways"}, headers=auth_headers)
    assert res_order.status_code == 422


# ============================================================================
# 4. Pagination Tests
# ============================================================================

def test_pagination_pages_and_metadata(client, auth_headers):
    # Create 5 transactions
    for i in range(1, 6):
        create_sample_tx(client, auth_headers, description=f"Item {i}", amount=f"{i * 10}.00")

    # Page 1 with page_size=2
    p1 = client.get(
        "/transactions/",
        params={"page": 1, "page_size": 2, "sort_by": "amount", "sort_order": "asc"},
        headers=auth_headers,
    ).json()
    assert p1["total"] == 5
    assert p1["total_count"] == 5
    assert p1["page"] == 1
    assert p1["page_size"] == 2
    assert p1["total_pages"] == 3
    assert p1["has_previous"] is False
    assert p1["has_next"] is True
    assert len(p1["items"]) == 2
    assert [tx["description"] for tx in p1["items"]] == ["Item 1", "Item 2"]

    # Page 2 with page_size=2
    p2 = client.get(
        "/transactions/",
        params={"page": 2, "page_size": 2, "sort_by": "amount", "sort_order": "asc"},
        headers=auth_headers,
    ).json()
    assert p2["page"] == 2
    assert p2["has_previous"] is True
    assert p2["has_next"] is True
    assert len(p2["items"]) == 2
    assert [tx["description"] for tx in p2["items"]] == ["Item 3", "Item 4"]

    # Page 3 with page_size=2
    p3 = client.get(
        "/transactions/",
        params={"page": 3, "page_size": 2, "sort_by": "amount", "sort_order": "asc"},
        headers=auth_headers,
    ).json()
    assert p3["page"] == 3
    assert p3["has_previous"] is True
    assert p3["has_next"] is False
    assert len(p3["items"]) == 1
    assert p3["items"][0]["description"] == "Item 5"


def test_pagination_defaults_and_explicit_flag(client, auth_headers):
    create_sample_tx(client, auth_headers, description="Default Tx")

    # Specifying page=1 uses default page_size=10
    res_page = client.get("/transactions/", params={"page": 1}, headers=auth_headers).json()
    assert isinstance(res_page, dict)
    assert res_page["page"] == 1
    assert res_page["page_size"] == 10
    assert res_page["total"] == 1

    # Specifying page_size=5 uses default page=1
    res_size = client.get("/transactions/", params={"page_size": 5}, headers=auth_headers).json()
    assert isinstance(res_size, dict)
    assert res_size["page"] == 1
    assert res_size["page_size"] == 5

    # Specifying paginate=true uses defaults page=1, page_size=10
    res_flag = client.get("/transactions/", params={"paginate": "true"}, headers=auth_headers).json()
    assert isinstance(res_flag, dict)
    assert res_flag["page"] == 1
    assert res_flag["page_size"] == 10


def test_pagination_limits_and_validation(client, auth_headers):
    # Max page size is 100
    res_large = client.get("/transactions/", params={"page_size": 101}, headers=auth_headers)
    assert res_large.status_code == 422

    # Min page is 1
    res_zero = client.get("/transactions/", params={"page": 0}, headers=auth_headers)
    assert res_zero.status_code == 422


def test_empty_transaction_results(client, auth_headers):
    # Empty unpaginated returns []
    res_unpaginated = client.get("/transactions/", headers=auth_headers)
    assert res_unpaginated.status_code == 200
    assert res_unpaginated.json() == []

    # Empty paginated returns total=0, total_pages=0, items=[]
    res_paginated = client.get("/transactions/", params={"paginate": "true"}, headers=auth_headers).json()
    assert res_paginated["total"] == 0
    assert res_paginated["total_pages"] == 0
    assert res_paginated["has_previous"] is False
    assert res_paginated["has_next"] is False
    assert res_paginated["items"] == []


# ============================================================================
# 5. Combined Filters & Cross-User Isolation Tests
# ============================================================================

def test_combining_all_filters(client, auth_headers):
    # Create several transactions with different combinations
    create_sample_tx(
        client,
        auth_headers,
        description="Target 1",
        category="Food",
        payment_method="UPI",
        amount="50.00",
        transaction_date="2026-11-05T12:00:00",
    )
    create_sample_tx(
        client,
        auth_headers,
        description="Target 2",
        category="Food",
        payment_method="UPI",
        amount="150.00",
        transaction_date="2026-11-06T12:00:00",
    )
    # Different category
    create_sample_tx(
        client,
        auth_headers,
        description="Wrong Cat",
        category="Transport",
        payment_method="UPI",
        amount="75.00",
        transaction_date="2026-11-05T12:00:00",
    )
    # Different payment method
    create_sample_tx(
        client,
        auth_headers,
        description="Wrong Payment",
        category="Food",
        payment_method="Cash",
        amount="80.00",
        transaction_date="2026-11-05T12:00:00",
    )
    # Different date
    create_sample_tx(
        client,
        auth_headers,
        description="Wrong Date",
        category="Food",
        payment_method="UPI",
        amount="90.00",
        transaction_date="2026-11-20T12:00:00",
    )

    # Combine: Food category + UPI + start_date 2026-11-01 + end_date 2026-11-10 + sort by amount desc + paginate
    res = client.get(
        "/transactions/",
        params={
            "category": "Food",
            "payment_method": "UPI",
            "start_date": "2026-11-01",
            "end_date": "2026-11-10",
            "sort_by": "amount",
            "sort_order": "desc",
            "page": 1,
            "page_size": 10,
        },
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert [tx["description"] for tx in data["items"]] == ["Target 2", "Target 1"]


def test_cross_user_isolation_with_filters(client, auth_headers, second_user_headers):
    # Both users create Food UPI transactions on the exact same date
    create_sample_tx(
        client,
        auth_headers,
        description="User 1 Dinner",
        category="Food",
        payment_method="UPI",
        transaction_date="2026-11-10T20:00:00",
    )
    create_sample_tx(
        client,
        second_user_headers,
        description="User 2 Dinner",
        category="Food",
        payment_method="UPI",
        transaction_date="2026-11-10T20:00:00",
    )

    # User 1 queries
    u1_res = client.get(
        "/transactions/",
        params={"category": "Food", "payment_method": "UPI", "paginate": "true"},
        headers=auth_headers,
    ).json()
    assert u1_res["total"] == 1
    assert u1_res["items"][0]["description"] == "User 1 Dinner"

    # User 2 queries
    u2_res = client.get(
        "/transactions/",
        params={"category": "Food", "payment_method": "UPI", "paginate": "true"},
        headers=second_user_headers,
    ).json()
    assert u2_res["total"] == 1
    assert u2_res["items"][0]["description"] == "User 2 Dinner"


# ============================================================================
# 6. CRUD Functionality with New Payment Methods Preserved
# ============================================================================

def test_crud_with_new_payment_methods(client, auth_headers):
    # Create with Credit Card
    create_payload = {
        "amount": "450.00",
        "description": "Airline Ticket",
        "merchant": "Airways",
        "category": "Travel",
        "payment_method": "Credit Card",
        "transaction_type": "expense",
        "transaction_date": "2026-11-10T15:00:00",
    }
    create_res = client.post("/transactions/", json=create_payload, headers=auth_headers)
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["payment_method"] == "Credit Card"
    tx_id = created["id"]

    # Update payment method to Debit Card
    patch_res = client.patch(
        f"/transactions/{tx_id}",
        json={"payment_method": "Debit Card", "amount": "475.00"},
        headers=auth_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["payment_method"] == "Debit Card"
    assert patch_res.json()["amount"] == "475.00"

    # Fetch
    get_res = client.get(f"/transactions/{tx_id}", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["description"] == "Airline Ticket"

    # Delete
    del_res = client.delete(f"/transactions/{tx_id}", headers=auth_headers)
    assert del_res.status_code == 204
    assert client.get(f"/transactions/{tx_id}", headers=auth_headers).status_code == 404
