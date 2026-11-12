import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowDownLeft,
  ArrowUpRight,
  ChartNoAxesCombined,
  CircleAlert,
  Clock3,
  LayoutDashboard,
  LogOut,
  PiggyBank,
  ReceiptText,
  Wallet,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useAuth } from '../context/AuthContext'
import { financeApi } from '../services/api'

const currency = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})

const compactCurrency = (value) => {
  const amount = Number(value || 0)
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`
  if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}k`
  return `₹${amount.toFixed(0)}`
}

const dateLabel = (value) => new Date(value).toLocaleDateString('en-IN', {
  day: 'numeric',
  month: 'short',
})

function Dashboard() {
  const { user, logout } = useAuth()
  const [summary, setSummary] = useState(null)
  const [monthly, setMonthly] = useState(null)
  const [transactions, setTransactions] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  const firstName = user?.name?.trim().split(/\s+/)[0] || 'there'
  const initials = user?.name?.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || 'U'

  useEffect(() => {
    let isActive = true

    async function loadDashboard() {
      setIsLoading(true)
      setError('')
      try {
        const [summaryResult, monthlyResult, transactionResult] = await Promise.all([
          financeApi.summary({ period: 'monthly' }),
          financeApi.monthly({ months: 6 }),
          financeApi.transactions({ page: 1, page_size: 5 }),
        ])

        if (!isActive) return
        setSummary(summaryResult.data)
        setMonthly(monthlyResult.data)
        const transactionData = transactionResult.data
        setTransactions(Array.isArray(transactionData) ? transactionData : transactionData.items || transactionData.transactions || [])
      } catch {
        if (isActive) setError('We could not load your financial overview. Please refresh the page and try again.')
      } finally {
        if (isActive) setIsLoading(false)
      }
    }

    loadDashboard()
    return () => { isActive = false }
  }, [])

  const cards = [
    { label: 'Total income', value: summary?.total_income, icon: ArrowDownLeft, tone: 'income', note: 'This month' },
    { label: 'Total expenses', value: summary?.total_expenses, icon: ArrowUpRight, tone: 'expense', note: 'This month' },
    { label: 'Net balance', value: summary?.net_balance, icon: Wallet, tone: 'balance', note: 'Income minus expenses' },
    { label: 'Transactions', value: summary?.transaction_count ?? 0, icon: ReceiptText, tone: 'count', note: 'This month', isCount: true },
  ]

  return (
    <div className="dashboard-layout">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark"><Wallet size={21} /></span><span>KharchaKlick</span></div>
        <div className="sidebar-label">Workspace</div>
        <Link className="sidebar-link active" to="/dashboard"><LayoutDashboard size={18} /><span>Overview</span></Link>
        <Link className="sidebar-link" to="/transactions"><ReceiptText size={18} /><span>Transactions</span></Link>
        <div className="sidebar-link" aria-disabled="true"><PiggyBank size={18} /><span>Budgets</span></div>
        <div className="sidebar-link" aria-disabled="true"><ChartNoAxesCombined size={18} /><span>Insights</span></div>
        <div className="sidebar-footer">Your personal finance companion.<br />More clarity, one step at a time.</div>
      </aside>

      <main className="dashboard-main">
        <header className="topbar">
          <div className="topbar-title">Overview</div>
          <div className="user-menu">
            <div className="user-avatar" aria-label={user?.name || 'User'}>{initials}</div>
            <span className="user-name">{user?.name}</span>
            <button className="logout-button" onClick={logout} type="button"><LogOut size={14} /> Sign out</button>
          </div>
        </header>

        <section className="dashboard-content">
          <div className="dashboard-heading-row">
            <div>
              <span className="eyebrow">Your workspace</span>
              <h1 className="dashboard-heading">Good to see you, {firstName}.</h1>
              <p className="dashboard-intro">Here's how your money is looking this month.</p>
            </div>
            <span className="current-period">{new Date().toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })}</span>
          </div>

          {error && <div className="dashboard-error" role="alert"><CircleAlert size={18} />{error}</div>}

          <div className="summary-grid">
            {cards.map(({ label, value, icon: Icon, tone, note, isCount }) => (
              <article className="summary-card" key={label}>
                <div className={`summary-icon ${tone}`}><Icon size={19} /></div>
                <span className="summary-label">{label}</span>
                <strong className="summary-value">
                  {isLoading ? '—' : isCount ? Number(value || 0).toLocaleString('en-IN') : currency.format(Number(value || 0))}
                </strong>
                <span className="summary-note">{note}</span>
              </article>
            ))}
          </div>

          <div className="dashboard-panels">
            <section className="panel spending-panel">
              <div className="panel-heading">
                <div><h2>Income vs expenses</h2><p>Your six-month financial trend</p></div>
                <ChartNoAxesCombined size={20} />
              </div>
              {isLoading ? (
                <div className="chart-empty">Loading your monthly activity...</div>
              ) : monthly?.history?.length ? (
                <div className="trend-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={monthly.history} margin={{ top: 12, right: 8, left: -16, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#edf1ed" />
                      <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill: '#89968d', fontSize: 12 }} />
                      <YAxis axisLine={false} tickLine={false} tickFormatter={compactCurrency} tick={{ fill: '#89968d', fontSize: 11 }} />
                      <Tooltip formatter={(value) => currency.format(Number(value || 0))} />
                      <Bar dataKey="income" name="Income" fill="#75ad82" radius={[5, 5, 0, 0]} />
                      <Bar dataKey="expenses" name="Expenses" fill="#e4a17f" radius={[5, 5, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : <div className="chart-empty">Your monthly trend will appear here once you add transactions.</div>}
              <div className="chart-legend"><span><i className="legend-income" />Income</span><span><i className="legend-expense" />Expenses</span></div>
            </section>

            <section className="panel recent-panel">
              <div className="panel-heading">
                <div><h2>Recent transactions</h2><p>Your latest money activity</p></div>
                <Clock3 size={20} />
              </div>
              {isLoading ? <div className="transaction-empty">Loading transactions...</div> : transactions.length ? (
                <div className="transaction-list">
                  {transactions.map((transaction) => {
                    const isIncome = transaction.transaction_type === 'income'
                    return (
                      <article className="transaction-row" key={transaction.id}>
                        <div className={`transaction-type-icon ${isIncome ? 'income' : 'expense'}`}>
                          {isIncome ? <ArrowDownLeft size={17} /> : <ArrowUpRight size={17} />}
                        </div>
                        <div className="transaction-description">
                          <strong>{transaction.description}</strong>
                          <span>{transaction.category} · {dateLabel(transaction.transaction_date)}</span>
                        </div>
                        <strong className={`transaction-amount ${isIncome ? 'positive' : 'negative'}`}>
                          {isIncome ? '+' : '−'}{currency.format(Number(transaction.amount || 0))}
                        </strong>
                      </article>
                    )
                  })}
                </div>
              ) : <div className="transaction-empty">No transactions yet. Your activity will show up here.</div>}
            </section>
          </div>
        </section>
      </main>
    </div>
  )
}

export default Dashboard
