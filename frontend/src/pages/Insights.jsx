import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle, ArrowDownLeft, ArrowUpRight, ChartNoAxesCombined,
  CircleAlert, LayoutDashboard, Lightbulb, LogOut, PiggyBank,
  ReceiptText, Wallet,
} from 'lucide-react'
import {
  Cell, Pie, PieChart, ResponsiveContainer, Tooltip,
  Bar, BarChart, CartesianGrid, XAxis, YAxis,
} from 'recharts'
import { useAuth } from '../context/AuthContext'
import { financeApi } from '../services/api'
import './Insights.css'

const currency = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })
const compactCurrency = (value) => {
  const amount = Number(value || 0)
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`
  if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}k`
  return `₹${amount.toFixed(0)}`
}
const monthRange = () => {
  const now = new Date()
  return {
    start_date: new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10),
    end_date: new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().slice(0, 10),
  }
}
const tones = { positive: 'positive', warning: 'warning', alert: 'alert', info: 'info' }

function Insights() {
  const { user, logout } = useAuth()
  const [insights, setInsights] = useState(null)
  const [categories, setCategories] = useState(null)
  const [monthly, setMonthly] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const initials = user?.name?.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || 'U'

  useEffect(() => {
    let active = true
    async function load() {
      setIsLoading(true)
      setError('')
      try {
        const [insightResult, categoryResult, monthlyResult] = await Promise.all([
          financeApi.insights(),
          financeApi.categories(monthRange()),
          financeApi.monthly({ months: 6 }),
        ])
        if (!active) return
        setInsights(insightResult.data)
        setCategories(categoryResult.data)
        setMonthly(monthlyResult.data)
      } catch (requestError) {
        if (active) setError(requestError.response?.data?.detail || 'We could not load your financial insights. Please try again.')
      } finally {
        if (active) setIsLoading(false)
      }
    }
    load()
    return () => { active = false }
  }, [])

  const insightItems = insights?.insights || []
  const budgetAlerts = insights?.budget_alerts || []
  const categoryItems = categories?.categories || []

  return (
    <div className="dashboard-layout">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark"><Wallet size={21} /></span><span>KharchaKlick</span></div>
        <div className="sidebar-label">Workspace</div>
        <Link className="sidebar-link" to="/dashboard"><LayoutDashboard size={18} /><span>Overview</span></Link>
        <Link className="sidebar-link" to="/transactions"><ReceiptText size={18} /><span>Transactions</span></Link>
        <Link className="sidebar-link" to="/budgets"><PiggyBank size={18} /><span>Budgets</span></Link>
        <Link className="sidebar-link active" to="/insights"><ChartNoAxesCombined size={18} /><span>Insights</span></Link>
        <div className="sidebar-footer">Your personal finance companion.<br />More clarity, one step at a time.</div>
      </aside>

      <main className="dashboard-main">
        <header className="topbar">
          <div className="topbar-title">Financial insights</div>
          <div className="user-menu">
            <div className="user-avatar" aria-label={user?.name || 'User'}>{initials}</div>
            <span className="user-name">{user?.name}</span>
            <button className="logout-button" onClick={logout} type="button"><LogOut size={14} /> Sign out</button>
          </div>
        </header>

        <section className="dashboard-content insights-content">
          <div className="dashboard-heading-row">
            <div>
              <span className="eyebrow">Understand your money</span>
              <h1 className="dashboard-heading">Your financial insights</h1>
              <p className="dashboard-intro">Patterns, spending trends and practical signals from your activity.</p>
            </div>
            <span className="current-period">{new Date().toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })}</span>
          </div>

          {error && <div className="dashboard-error" role="alert"><CircleAlert size={18} />{error}</div>}

          <div className="insight-stat-grid">
            <article className="summary-card">
              <div className="summary-icon expense"><ArrowUpRight size={19} /></div>
              <span className="summary-label">This month's expenses</span>
              <strong className="summary-value">{isLoading ? '—' : currency.format(Number(categories?.total_expenses || 0))}</strong>
              <span className="summary-note">Current month spending</span>
            </article>
            <article className="summary-card">
              <div className="summary-icon balance"><ChartNoAxesCombined size={19} /></div>
              <span className="summary-label">Top spending category</span>
              <strong className="summary-value insight-stat-text">{isLoading ? '—' : insights?.top_spending_category || 'No data'}</strong>
              <span className="summary-note">Highest expense category</span>
            </article>
            <article className="summary-card">
              <div className="summary-icon income"><ArrowDownLeft size={19} /></div>
              <span className="summary-label">Savings rate</span>
              <strong className="summary-value">{isLoading ? '—' : insights?.savings_rate == null ? '—' : `${Number(insights.savings_rate).toFixed(1)}%`}</strong>
              <span className="summary-note">Income remaining after expenses</span>
            </article>
            <article className="summary-card">
              <div className="summary-icon count"><Lightbulb size={19} /></div>
              <span className="summary-label">Insights found</span>
              <strong className="summary-value">{isLoading ? '—' : insightItems.length}</strong>
              <span className="summary-note">Based on your transactions</span>
            </article>
          </div>

          <div className="dashboard-panels insights-panels">
            <section className="panel">
              <div className="panel-heading"><div><h2>Spending by category</h2><p>How this month's expenses are distributed</p></div><ChartNoAxesCombined size={20} /></div>
              {isLoading ? <div className="chart-empty">Loading category breakdown...</div> : categoryItems.length ? (
                <>
                  <div className="insight-donut">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={categoryItems} dataKey="amount" nameKey="category" innerRadius="57%" outerRadius="82%" paddingAngle={3}>
                          {categoryItems.map((item, index) => <Cell key={item.category} fill={['#75ad82', '#e4a17f', '#8aa6c1', '#d2b16f', '#9c8ab8', '#78aaa8', '#c58f9d'][index % 7]} />)}
                        </Pie>
                        <Tooltip formatter={(value) => currency.format(Number(value || 0))} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="category-insight-list">
                    {categoryItems.map((item) => (
                      <div className="category-insight-row" key={item.category}>
                        <span><i />{item.category}</span>
                        <strong>{currency.format(Number(item.amount || 0))}</strong>
                        <small>{Number(item.percentage || 0).toFixed(1)}%</small>
                      </div>
                    ))}
                  </div>
                </>
              ) : <div className="chart-empty">No expenses recorded this month yet.</div>}
            </section>

            <section className="panel">
              <div className="panel-heading"><div><h2>Six-month trend</h2><p>Income compared with expenses</p></div><ChartNoAxesCombined size={20} /></div>
              {isLoading ? <div className="chart-empty">Loading monthly trend...</div> : monthly?.history?.length ? (
                <div className="trend-chart">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={monthly.history} margin={{ top: 12, right: 8, left: -16, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#edf1ed" />
                      <XAxis dataKey="month" tickFormatter={(value) => value.slice(5)} axisLine={false} tickLine={false} tick={{ fill: '#89968d', fontSize: 12 }} />
                      <YAxis tickFormatter={compactCurrency} axisLine={false} tickLine={false} tick={{ fill: '#89968d', fontSize: 11 }} />
                      <Tooltip formatter={(value) => currency.format(Number(value || 0))} />
                      <Bar dataKey="income" name="Income" fill="#75ad82" radius={[5, 5, 0, 0]} />
                      <Bar dataKey="expenses" name="Expenses" fill="#e4a17f" radius={[5, 5, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : <div className="chart-empty">Your monthly trend will appear once you add transactions.</div>}
              <div className="chart-legend"><span><i className="legend-income" />Income</span><span><i className="legend-expense" />Expenses</span></div>
            </section>
          </div>

          <section className="insight-section">
            <div className="budgets-section-heading"><div><h2>What your activity tells us</h2><p>Automatically generated from your income, expenses and budgets.</p></div></div>
            {isLoading ? <div className="panel transaction-empty">Generating your insights...</div> : insightItems.length ? (
              <div className="financial-insight-grid">
                {insightItems.map((item, index) => (
                  <article className={`panel financial-insight-card ${tones[item.type] || 'info'}`} key={`${item.title}-${index}`}>
                    <div className="financial-insight-icon">{item.type === 'alert' || item.type === 'warning' ? <AlertTriangle size={18} /> : <Lightbulb size={18} />}</div>
                    <div><span className="financial-insight-type">{item.type}</span><h3>{item.title}</h3><p>{item.message}</p></div>
                  </article>
                ))}
              </div>
            ) : <div className="panel transaction-empty">No insights are available yet.</div>}
          </section>

          {!!budgetAlerts.length && (
            <section className="insight-section">
              <div className="budgets-section-heading"><div><h2>Budget alerts</h2><p>Keep an eye on limits that need attention.</p></div></div>
              <div className="budget-alert-list">
                {budgetAlerts.map((alert, index) => <div className="budget-alert-item" key={index}><AlertTriangle size={17} /><span>{alert}</span></div>)}
              </div>
            </section>
          )}
        </section>
      </main>
    </div>
  )
}

export default Insights
