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
    # The app's normal startup creates tables in PostgreSQL; tests use isolated SQLite.
    app.router.on_startup.clear()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def sample_transaction(**overrides):
    payload = {
        "amount": "125.50",
        "description": "Lunch",
        "merchant": "Campus Cafe",
        "category": "Food",
        "payment_method": "UPI",
        "transaction_type": "expense",
        "transaction_date": "2026-11-09T12:00:00",
    }
    payload.update(overrides)
    return payload


def test_create_and_get_transaction(client):
    response = client.post("/transactions/", json=sample_transaction())
    assert response.status_code == 201
    created = response.json()
    assert created["amount"] == "125.50"
    assert created["merchant"] == "Campus Cafe"

    fetched = client.get(f"/transactions/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["description"] == "Lunch"


def test_update_and_delete_transaction(client):
    created = client.post("/transactions/", json=sample_transaction()).json()
    updated = client.patch(
        f"/transactions/{created['id']}",
        json={"amount": "150.00", "description": "Dinner"},
    )
    assert updated.status_code == 200
    assert updated.json()["amount"] == "150.00"
    assert updated.json()["description"] == "Dinner"

    deleted = client.delete(f"/transactions/{created['id']}")
    assert deleted.status_code == 204
    assert client.get(f"/transactions/{created['id']}").status_code == 404


def test_filter_transactions(client):
    client.post("/transactions/", json=sample_transaction())
    client.post(
        "/transactions/",
        json=sample_transaction(
            amount="300.00",
            description="Bus pass",
            category="Transport",
            merchant="City Bus",
        ),
    )

    by_category = client.get("/transactions/", params={"category": "Food"})
    assert by_category.status_code == 200
    assert len(by_category.json()) == 1

    by_merchant = client.get("/transactions/", params={"merchant": "city"})
    assert by_merchant.status_code == 200
    assert len(by_merchant.json()) == 1


def test_reject_invalid_amount_and_category(client):
    invalid_amount = client.post(
        "/transactions/", json=sample_transaction(amount="-10.00")
    )
    assert invalid_amount.status_code == 422

    invalid_category = client.post(
        "/transactions/", json=sample_transaction(category="Random")
    )
    assert invalid_category.status_code == 422


def test_missing_transaction_returns_404(client):
    response = client.get("/transactions/9999")
    assert response.status_code == 404
