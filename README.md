# KharchaKlick API

KharchaKlick is an AI-powered personal expense management and budget tracking backend built with **FastAPI**, **PostgreSQL**, **SQLAlchemy**, and **JWT Authentication**.

---

## Features Implemented

### Milestone 1 & 2: Transaction Management
- Full CRUD for income and expenses (`POST`, `GET`, `PATCH`, `DELETE /transactions/`).
- Database-level pagination with page metadata (`page`, `page_size`, `total`, `total_pages`, `has_next`, `has_previous`).
- Date-range filtering (start date, end date, preset daily/weekly/monthly views).
- Payment method filtering (`Cash`, `UPI`, `Credit Card`, `Debit Card`, `Net Banking`, `Other`).
- Sorting by date, amount, and creation time in ascending or descending order.
- Composite database indexes for high-performance multi-tenant queries.

### Milestone 3: Authentication & User Management
- Secure user registration (`POST /auth/register`) with email validation and uniqueness checks.
- Password hashing using **bcrypt** (never storing or leaking plain-text passwords).
- User login (`POST /auth/login`) generating signed **JWT access tokens** with configurable expiration.
- Reusable authentication dependency (`get_current_user`) enforcing Bearer token validation and proper HTTP error handling (`401 Unauthorized`).
- Strict user-level data isolation preventing cross-user data leakage.

### Milestone 4: Financial Analytics & Budget Tracking
- **Financial Summary (`GET /analytics/summary`)**: Total income, total expenses, net balance, and transaction counts across daily, weekly, monthly, or custom periods using exact `Decimal` arithmetic.
- **Category-Wise Analytics (`GET /analytics/categories`)**: SQL-aggregated category breakdown, percentage share, transaction counts, and highest-spending category.
- **Monthly Analytics & Trends (`GET /analytics/monthly`)**: Month-over-month spending comparison, percentage change calculation, and historical trend points for frontend charting.
- **Budget Management (`/budgets`)**: CRUD for overall monthly and category-specific budgets with real-time tracking of actual spent, remaining headroom, overrun detection, and utilization percentages.
- **Budget Utilization Dashboard (`GET /budgets/utilization`)**: Aggregated view of active monthly budgets and overrun alerts.
- **Financial Insights (`GET /analytics/insights`)**: Automated detection of category concentration, spending surges, deficit alerts, and near-capacity budget warnings.

---

## Tech Stack

- **Framework**: FastAPI (Python 3.10+)
- **ORM & Database**: SQLAlchemy 2.0 with PostgreSQL (`psycopg`) and SQLite (in-memory test isolation)
- **Data Validation & Settings**: Pydantic v2 & Pydantic-Settings
- **Security**: PyJWT (RFC 7519) and bcrypt
- **Testing**: Pytest & HTTPX TestClient

---

## Project Structure

```
KharchaKlick/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py              # Auth dependency (get_current_user)
│   │   │   └── routes/
│   │   │       ├── analytics.py     # Summary, category, monthly & insight endpoints
│   │   │       ├── auth.py          # Register, login, profile endpoints
│   │   │       ├── budgets.py       # Budget CRUD & utilization endpoints
│   │   │       └── transactions.py  # User-scoped transaction CRUD & filter endpoints
│   │   ├── core/
│   │   │   ├── config.py            # App settings & env configuration
│   │   │   ├── database.py          # SQLAlchemy engine, session & get_db dependency
│   │   │   └── security.py          # bcrypt password hashing & JWT encoding/decoding
│   │   ├── models/
│   │   │   ├── budget.py            # Budget database model
│   │   │   ├── transaction.py       # Transaction model with composite indexes
│   │   │   └── user.py              # User model with relationships
│   │   ├── schemas/
│   │   │   ├── analytics.py         # Analytics response schemas
│   │   │   ├── budget.py            # Budget request & response schemas
│   │   │   ├── transaction.py       # Transaction schemas & enums
│   │   │   └── user.py              # Auth & token schemas
│   │   └── main.py                  # FastAPI application entrypoint
│   ├── tests/
│   │   ├── test_advanced_transactions.py # Filtering, sorting & pagination tests
│   │   ├── test_analytics_and_budgets.py # Analytics, metrics & budget tests
│   │   ├── test_auth.py                  # Auth, JWT & isolation tests
│   │   ├── test_db.py                    # Database connection test
│   │   └── test_transactions.py          # Baseline CRUD tests
│   ├── .env.example
│   └── requirements.txt
├── .gitignore
└── README.md
```

---

## Installation & Setup

### 1. Clone & Set Up Virtual Environment

```bash
cd KharchaKlick/backend
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Linux / macOS:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and configure your credentials:

```bash
cp .env.example .env
```

```ini
# PostgreSQL Database Credentials
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=kharchaklick

# JWT Authentication
JWT_SECRET_KEY=your_super_secret_jwt_key_at_least_32_characters_long
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### 4. Run the Application

```bash
uvicorn app.main:app --reload --port 8000
```

Interactive API documentation will be available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## Running the Tests

KharchaKlick uses isolated in-memory SQLite databases for automated testing, requiring no live database to run the complete test suite.

```bash
# From the repository root (or backend directory):
python -m pytest backend/tests -v
```

All 56 test cases run and verify:
- Authentication & JWT validation
- Cross-user data isolation
- Pagination, sorting, and date/payment method filtering
- Financial summaries, category aggregates, and monthly comparisons
- Budget CRUD, tracking, and overrun alerts

