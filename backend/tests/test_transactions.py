import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
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

    # Create a default test user in the isolated SQLite DB
    db = TestingSessionLocal()
    test_user = User(
        name="Test User",
        email="testuser@example.com",
        hashed_password="hashed_placeholder_pw",
    )
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    db.close()

    def override_get_current_user():
        db_session = TestingSessionLocal()
        try:
            return db_session.get(User, test_user.id)
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
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


def test_intelligence_category_suggestion_uses_local_ai(client, monkeypatch):
    from app.api.routes import intelligence

    monkeypatch.setattr(
        intelligence,
        "ollama_suggestion",
        lambda description, merchant, transaction_type: (
            "Food", 0.91, "The merchant and description indicate a meal."
        ),
    )
    response = client.post(
        "/intelligence/suggest-category",
        json={
            "description": "Lunch with friends",
            "merchant": "Campus Cafe",
            "transaction_type": "expense",
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "category": "Food",
        "confidence": 0.91,
        "reason": "The merchant and description indicate a meal.",
        "source": "ollama",
    }


def test_intelligence_category_suggestion_falls_back_to_rules(client, monkeypatch):
    from app.api.routes import intelligence

    monkeypatch.setattr(intelligence, "ollama_suggestion", lambda *args: None)
    response = client.post(
        "/intelligence/suggest-category",
        json={
            "description": "Monthly metro pass",
            "merchant": "City Metro",
            "transaction_type": "expense",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "Transport"
    assert data["source"] == "rules"
    assert data["confidence"] > 0


def test_intelligence_category_suggestion_requires_authentication(client):
    from app.api.deps import get_current_user

    app.dependency_overrides.pop(get_current_user, None)
    response = client.post(
        "/intelligence/suggest-category",
        json={"description": "Lunch at cafe"},
    )
    assert response.status_code == 401


def test_financial_intelligence_query_aggregates_user_expenses(client):
    client.post("/transactions/", json=sample_transaction(amount="125.50"))
    client.post("/transactions/", json=sample_transaction(
        amount="100.00", description="Groceries", transaction_date="2026-10-12T12:00:00"
    ))
    client.post("/transactions/", json=sample_transaction(
        amount="300.00", description="Bus pass", category="Transport"
    ))

    response = client.post("/intelligence/query", json={
        "question": "How much did I spend on Food in the last three months?"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "Food"
    assert data["months"] == 3
    assert data["total"] == 225.5
    assert data["transaction_count"] == 2
    assert data["source"] == "database"


def test_financial_review_returns_calculated_facts_and_advice(client, monkeypatch):
    from app.api.routes import intelligence

    monkeypatch.setattr(intelligence, "_review_narrative", lambda facts: None)
    client.post("/transactions/", json=sample_transaction(amount="500.00"))
    client.post("/transactions/", json=sample_transaction(
        amount="250.00", description="Groceries", transaction_date="2026-10-12T12:00:00"
    ))

    response = client.get("/intelligence/financial-review")
    assert response.status_code == 200
    data = response.json()
    assert data["facts"]["current_month_expenses"] == 500.0
    assert data["facts"]["previous_month_expenses"] == 250.0
    assert data["facts"]["change_percentage"] == 100.0
    assert data["advice"]
    assert data["narrative_source"] == "rules"
