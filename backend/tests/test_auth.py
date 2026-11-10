from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import create_access_token, verify_password
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


def test_user_registration_success(client):
    payload = {
        "name": "Sonakshi Singh",
        "email": "sonakshi@example.com",
        "password": "SecurePassword123!",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Sonakshi Singh"
    assert data["email"] == "sonakshi@example.com"
    assert "id" in data
    assert "created_at" in data
    # Password must never be returned in the response
    assert "password" not in data
    assert "hashed_password" not in data

    # Verify password in database is securely hashed and not plain-text
    db = TestingSessionLocal()
    user = db.get(User, data["id"])
    assert user is not None
    assert user.hashed_password != payload["password"]
    assert verify_password(payload["password"], user.hashed_password) is True
    db.close()


def test_user_registration_duplicate_email(client):
    payload = {
        "name": "User One",
        "email": "duplicate@example.com",
        "password": "Password123!",
    }
    first_resp = client.post("/auth/register", json=payload)
    assert first_resp.status_code == 201

    # Attempt to register with the same email
    dup_resp = client.post("/auth/register", json=payload)
    assert dup_resp.status_code == 400
    assert "already registered" in dup_resp.json()["detail"].lower()

    # Case-insensitive duplicate email check
    case_dup_resp = client.post(
        "/auth/register",
        json={
            "name": "User One Upper",
            "email": "DUPLICATE@EXAMPLE.COM",
            "password": "Password123!",
        },
    )
    assert case_dup_resp.status_code == 400
    assert "already registered" in case_dup_resp.json()["detail"].lower()


def test_user_registration_invalid_email_format(client):
    payload = {
        "name": "Invalid Email",
        "email": "not-an-email",
        "password": "Password123!",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 422


def test_user_registration_short_password(client):
    payload = {
        "name": "Short Pass",
        "email": "shortpass@example.com",
        "password": "123",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 422


def test_user_login_success(client):
    register_payload = {
        "name": "Login User",
        "email": "login@example.com",
        "password": "SecretPassword123!",
    }
    reg_resp = client.post("/auth/register", json=register_payload)
    assert reg_resp.status_code == 201

    login_resp = client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "SecretPassword123!"},
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["user"]["email"] == "login@example.com"


def test_user_login_case_insensitive_email(client):
    client.post(
        "/auth/register",
        json={"name": "Case User", "email": "case@example.com", "password": "Password123!"},
    )
    login_resp = client.post(
        "/auth/login",
        json={"email": "CASE@EXAMPLE.COM", "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


def test_user_login_incorrect_password(client):
    client.post(
        "/auth/register",
        json={"name": "Bob", "email": "bob@example.com", "password": "CorrectPassword123!"},
    )
    response = client.post(
        "/auth/login",
        json={"email": "bob@example.com", "password": "WrongPassword456!"},
    )
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


def test_user_login_nonexistent_email(client):
    response = client.post(
        "/auth/login",
        json={"email": "ghost@example.com", "password": "SomePassword123!"},
    )
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


def test_get_current_user_profile(client):
    client.post(
        "/auth/register",
        json={"name": "Profile User", "email": "profile@example.com", "password": "Password123!"},
    )
    login = client.post(
        "/auth/login",
        json={"email": "profile@example.com", "password": "Password123!"},
    ).json()
    token = login["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "profile@example.com"
    assert data["name"] == "Profile User"


def test_missing_token_returns_401(client):
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.headers.get("www-authenticate") == "Bearer"


def test_invalid_jwt_token_returns_401(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.value"})
    assert response.status_code == 401
    assert "credentials" in response.json()["detail"].lower()


def test_expired_jwt_token_returns_401(client):
    # Create an expired token (expired 10 minutes ago)
    token = create_access_token(data={"sub": "1"}, expires_delta=timedelta(minutes=-10))
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_token_with_deleted_or_nonexistent_user_returns_401(client):
    token = create_access_token(data={"sub": "99999"})
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "user not found" in response.json()["detail"].lower()


def test_unauthorized_transaction_access(client):
    # Unauthenticated access to transactions must return 401
    assert client.get("/transactions/").status_code == 401
    assert client.post("/transactions/", json={}).status_code == 401
    assert client.get("/transactions/1").status_code == 401
    assert client.patch("/transactions/1", json={}).status_code == 401
    assert client.delete("/transactions/1").status_code == 401


def test_cross_user_transaction_isolation(client):
    # Register and login User A
    client.post(
        "/auth/register",
        json={"name": "User A", "email": "usera@example.com", "password": "PasswordA123!"},
    )
    token_a = client.post(
        "/auth/login",
        json={"email": "usera@example.com", "password": "PasswordA123!"},
    ).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register and login User B
    client.post(
        "/auth/register",
        json={"name": "User B", "email": "userb@example.com", "password": "PasswordB123!"},
    )
    token_b = client.post(
        "/auth/login",
        json={"email": "userb@example.com", "password": "PasswordB123!"},
    ).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User A creates a transaction
    tx_payload_a = {
        "amount": "250.00",
        "description": "User A Dinner",
        "merchant": "Trattoria",
        "category": "Food",
        "payment_method": "Card",
        "transaction_type": "expense",
        "transaction_date": "2026-11-10T19:30:00",
    }
    tx_a = client.post("/transactions/", json=tx_payload_a, headers=headers_a).json()
    assert tx_a["amount"] == "250.00"
    tx_a_id = tx_a["id"]

    # User B creates a transaction
    tx_payload_b = {
        "amount": "80.00",
        "description": "User B Metro Ticket",
        "merchant": "Metro Station",
        "category": "Transport",
        "payment_method": "UPI",
        "transaction_type": "expense",
        "transaction_date": "2026-11-10T08:30:00",
    }
    tx_b = client.post("/transactions/", json=tx_payload_b, headers=headers_b).json()
    tx_b_id = tx_b["id"]

    # User A can get their own transaction
    get_a = client.get(f"/transactions/{tx_a_id}", headers=headers_a)
    assert get_a.status_code == 200
    assert get_a.json()["description"] == "User A Dinner"

    # User B attempts to access User A's transaction -> 404 Not Found
    get_cross = client.get(f"/transactions/{tx_a_id}", headers=headers_b)
    assert get_cross.status_code == 404

    # User B attempts to update User A's transaction -> 404 Not Found
    patch_cross = client.patch(
        f"/transactions/{tx_a_id}",
        json={"description": "Hacked Description"},
        headers=headers_b,
    )
    assert patch_cross.status_code == 404

    # Verify transaction wasn't modified
    get_a_after = client.get(f"/transactions/{tx_a_id}", headers=headers_a)
    assert get_a_after.json()["description"] == "User A Dinner"

    # User B attempts to delete User A's transaction -> 404 Not Found
    del_cross = client.delete(f"/transactions/{tx_a_id}", headers=headers_b)
    assert del_cross.status_code == 404

    # Verify transaction still exists for User A
    assert client.get(f"/transactions/{tx_a_id}", headers=headers_a).status_code == 200

    # User A lists transactions -> sees only tx_a, NOT tx_b
    list_a = client.get("/transactions/", headers=headers_a).json()
    assert len(list_a) == 1
    assert list_a[0]["id"] == tx_a_id

    # User B lists transactions -> sees only tx_b, NOT tx_a
    list_b = client.get("/transactions/", headers=headers_b).json()
    assert len(list_b) == 1
    assert list_b[0]["id"] == tx_b_id

    # User A deletes their own transaction -> 204
    del_a = client.delete(f"/transactions/{tx_a_id}", headers=headers_a)
    assert del_a.status_code == 204
    assert client.get(f"/transactions/{tx_a_id}", headers=headers_a).status_code == 404

    # User B's transaction is unaffected
    assert client.get(f"/transactions/{tx_b_id}", headers=headers_b).status_code == 200


def test_cross_user_filter_isolation(client):
    # Register User 1 & 2
    client.post(
        "/auth/register",
        json={"name": "Filter 1", "email": "f1@example.com", "password": "Password123!"},
    )
    token1 = client.post(
        "/auth/login", json={"email": "f1@example.com", "password": "Password123!"}
    ).json()["access_token"]

    client.post(
        "/auth/register",
        json={"name": "Filter 2", "email": "f2@example.com", "password": "Password123!"},
    )
    token2 = client.post(
        "/auth/login", json={"email": "f2@example.com", "password": "Password123!"}
    ).json()["access_token"]

    # Both add Food transactions
    client.post(
        "/transactions/",
        json={
            "amount": "100.00",
            "description": "F1 Grocery",
            "category": "Food",
            "payment_method": "UPI",
            "transaction_type": "expense",
            "transaction_date": "2026-11-10T10:00:00",
        },
        headers={"Authorization": f"Bearer {token1}"},
    )

    client.post(
        "/transactions/",
        json={
            "amount": "200.00",
            "description": "F2 Fast Food",
            "category": "Food",
            "payment_method": "Cash",
            "transaction_type": "expense",
            "transaction_date": "2026-11-10T11:00:00",
        },
        headers={"Authorization": f"Bearer {token2}"},
    )

    f1_food = client.get(
        "/transactions/",
        params={"category": "Food"},
        headers={"Authorization": f"Bearer {token1}"},
    ).json()
    assert len(f1_food) == 1
    assert f1_food[0]["description"] == "F1 Grocery"

    f2_food = client.get(
        "/transactions/",
        params={"category": "Food"},
        headers={"Authorization": f"Bearer {token2}"},
    ).json()
    assert len(f2_food) == 1
    assert f2_food[0]["description"] == "F2 Fast Food"


def test_tampered_jwt_token_returns_401(client):
    client.post(
        "/auth/register",
        json={"name": "Tamper Test", "email": "tamper@example.com", "password": "Password123!"},
    )
    token = client.post(
        "/auth/login", json={"email": "tamper@example.com", "password": "Password123!"}
    ).json()["access_token"]

    # Tamper with the signature portion of the token
    tampered_token = token[:-6] + "xxxxxx"
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert resp.status_code == 401
    assert "credentials" in resp.json()["detail"].lower()


def test_invalid_auth_header_scheme_returns_401(client):
    resp = client.get("/auth/me", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert resp.status_code == 401
