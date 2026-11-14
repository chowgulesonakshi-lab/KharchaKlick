# KharchaKlick

KharchaKlick is a personal expense management and budget tracking application with a **FastAPI + PostgreSQL backend** and a **React frontend**.

## Features Implemented

### Milestones 1 & 2: Transaction Management
- Full CRUD for income and expenses (`POST`, `GET`, `PATCH`, `DELETE /transactions/`).
- Database-level pagination with page metadata.
- Date-range filtering, payment method filtering, and sorting.
- Composite database indexes for high-performance multi-tenant queries.

### Milestone 3: Authentication & User Management
- Secure user registration (`POST /auth/register`) with email validation and uniqueness checks.
- Password hashing using bcrypt.
- User login (`POST /auth/login`) generating signed JWT access tokens.
- Reusable Bearer token validation and strict user-level data isolation.

### Milestone 4: Financial Analytics & Budget Tracking
- **Financial Summary (`GET /analytics/summary`)**: Income, expenses, net balance, and transaction counts across selected periods.
- **Category Analytics (`GET /analytics/categories`)**: Category breakdown, percentage share, transaction counts, and highest-spending category.
- **Monthly Trends (`GET /analytics/monthly`)**: Month-over-month spending comparison and historical trend points.
- **Budget Management (`/budgets`)**: CRUD for monthly and category budgets, actual spending, remaining headroom, and utilization.
- **Budget Utilization (`GET /budgets/utilization`)**: Active budget tracking and overrun alerts.
- **Financial Insights (`GET /analytics/insights`)**: Category concentration, spending surges, deficit alerts, and budget warnings.

### Milestone 9: Financial Insights
- Dedicated protected Insights dashboard with category spending distribution and six-month income/expense trends.
- Savings-rate summary, generated financial insight cards, and budget alerts powered by the existing analytics API.

### Milestone 10: AI Expense Intelligence
- Authenticated category suggestions from a local Ollama model (`qwen2.5:7b`) using transaction description and merchant context.
- Transparent offline keyword-based fallback when Ollama is unavailable; the response identifies whether the suggestion came from AI or rules.
- Suggestions are optional and never save a transaction or change its category until the user accepts them in the form.

### Milestone 5: Frontend Foundation
- React application with client-side routing.
- Login and registration screens connected to the FastAPI authentication endpoints.
- Axios API client with JWT Bearer token injection.
- Persistent authentication state and authenticated profile restoration.
- Protected dashboard route and sign-out flow.
- Responsive dashboard shell ready for transaction, budget, and analytics screens.

## Tech Stack

**Backend**
- FastAPI, Python 3.10+
- PostgreSQL, SQLAlchemy 2.0
- Pydantic v2 and Pydantic Settings
- PyJWT and bcrypt
- Pytest and HTTPX TestClient

**Frontend**
- React 19 and Vite
- React Router
- Axios
- Tailwind CSS 4 and Lucide React
- Recharts (for upcoming analytics visualizations)

## Project Structure

```
KharchaKlick/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # Auth, transactions, budgets, analytics
│   │   ├── core/             # Database, configuration, security
│   │   ├── models/           # User, transaction, budget
│   │   ├── schemas/          # API request and response schemas
│   │   └── main.py
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # Protected route
│   │   ├── context/          # Authentication state
│   │   ├── pages/            # Login, register, dashboard
│   │   ├── services/         # Axios API client
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   └── package.json
└── README.md
```

## Backend Setup

### 1. Create and activate a virtual environment

```bash
cd KharchaKlick/backend
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Linux / macOS
source venv/bin/activate
```

### 2. Install dependencies and configure environment

```bash
pip install -r requirements.txt
cp .env.example .env
```

Set your PostgreSQL credentials and JWT settings in `backend/.env`:

```ini
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=kharchaklick

JWT_SECRET_KEY=your_super_secret_jwt_key_at_least_32_characters_long
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### 3. Run the API

From the `backend` directory:

```bash
uvicorn app.main:app --reload --port 8000
```

API documentation: `http://localhost:8000/docs`

## Frontend Setup

Open a second terminal:

```bash
cd KharchaKlick/frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal (normally `http://localhost:5173`). The Vite development server proxies `/api` requests to the backend at `http://127.0.0.1:8000`.

## Running Backend Tests

From the repository root:

```bash
python -m pytest backend/tests -v
```

The backend test suite uses isolated test databases to verify authentication, user isolation, transactions, analytics, and budgets.
