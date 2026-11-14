# KharchaKlick

**A personal finance and expense tracking application built to make everyday money management clearer.**

KharchaKlick helps users record income and expenses, manage budgets, and understand where their money goes. It combines a React frontend with a FastAPI backend and PostgreSQL database, with financial summaries and rule-based spending insights to make unusual activity easier to spot.

## Features

### Transaction Management
- Add, view, edit, and delete income and expense transactions.
- Filter transactions by date range and payment method.
- Sort and paginate transaction records.
- Keep each user's financial records isolated.

### Dashboard & Financial Analytics
- View total income, expenses, and net balance.
- Review spending breakdowns by category.
- Compare monthly spending trends.
- Identify high-spending categories and changes in spending patterns.

### Budget Management
- Create and manage monthly and category-wise budgets.
- Track actual spending against budget limits.
- View remaining budget and utilization.
- Surface budget overruns.

### Spending Insights & Unusual Transactions
- Highlight budget overruns, including category-specific overspending.
- Identify high category concentration in overall expenses.
- Flag unusual transactions using category spending patterns, including a minimum transaction-count check and comparison against the category median.
- Present spending signals to help users investigate activity that stands out.

### Authentication & Security
- Register and log in with securely hashed passwords.
- Authenticate API requests using JWT access tokens.
- Protect frontend routes and restore authenticated sessions.
- Enforce user-level data isolation across financial records.

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React 19, Vite, React Router, Axios |
| UI & Visualization | Tailwind CSS 4, Lucide React, Recharts |
| Backend | Python, FastAPI, Pydantic |
| Database & ORM | PostgreSQL, SQLAlchemy 2.0 |
| Authentication | JWT, bcrypt |
| Testing | Pytest, HTTPX TestClient |

## Project Structure

```text
KharchaKlick/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # Authentication, transactions, budgets, analytics
│   │   ├── core/             # Configuration, database, security
│   │   ├── models/           # Database models
│   │   ├── schemas/          # Request and response schemas
│   │   └── main.py
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── context/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   └── package.json
└── README.md
```

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js and npm
- PostgreSQL

### 1. Clone the repository

```bash
git clone https://github.com/chowgulesonakshi-lab/KharchaKlick.git
cd KharchaKlick
```

### 2. Set up the backend

```bash
cd backend
python -m venv venv
```

Activate the virtual environment:

**Windows PowerShell**
```powershell
.\venv\Scripts\Activate.ps1
```

**Linux / macOS**
```bash
source venv/bin/activate
```

Install dependencies and create the environment file:

```bash
pip install -r requirements.txt
cp .env.example .env
```

Configure your PostgreSQL connection and JWT settings in `.env`:

```ini
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=kharchaklick

JWT_SECRET_KEY=replace_with_a_secure_secret_at_least_32_characters_long
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Start the API from the `backend` directory:

```bash
uvicorn app.main:app --reload --port 8000
```

The API and interactive documentation will be available at:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs

### 3. Set up the frontend

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local Vite URL shown in the terminal (typically http://localhost:5173). The development server is configured to proxy `/api` requests to the backend.

### 4. Run backend tests

From the repository root:

```bash
python -m pytest backend/tests -v
```

The test suite covers core backend functionality, including authentication, user isolation, transactions, analytics, and budgets.

## Project Status

KharchaKlick is being developed incrementally. The current implementation includes authenticated transaction management, financial analytics, budget tracking, and spending-insight features. The project is structured to support further improvements, including AI-assisted explanations of spending patterns and natural-language financial queries.

## Future Scope
- AI-generated explanations for changes in spending patterns.
- Personalized, data-driven suggestions for managing expenses.
- Natural-language questions about transaction history and budgets.

---

Built as a full-stack personal finance project.
