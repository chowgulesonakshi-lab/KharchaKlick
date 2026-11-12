import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowDownLeft,
  ArrowUpRight,
  ChartNoAxesCombined,
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  LogOut,
  PiggyBank,
  ReceiptText,
  Wallet,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { financeApi } from '../services/api'

const currency = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 2,
})

const dateLabel = (value) => new Date(value).toLocaleDateString('en-IN', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
})

function Transactions() {
  const { user, logout } = useAuth()
  const [transactions, setTransactions] = useState([])
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const [total, setTotal] = useState(0)
  const [type, setType] = useState('')
  const [category, setCategory] = useState('')
  const [merchant, setMerchant] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    async function loadTransactions() {
      setIsLoading(true)
      setError('')
      try {
        const params = { page, page_size: 10 }
        if (type) params.transaction_type = type
        if (category) params.category = category
        if (merchant.trim()) params.merchant = merchant.trim()
        const response = await financeApi.transactions(params)
        if (!active) return
        const data = response.data
        setTransactions(Array.isArray(data) ? data : data.items || data.transactions || [])
        setTotal(Array.isArray(data) ? data.length : data.total ?? data.total_count ?? 0)
        setTotalPages(Array.isArray(data) ? 1 : data.total_pages ?? 0)
      } catch {
        if (active) setError('We could not load your transactions. Please try again.')
      } finally {
        if (active) setIsLoading(false)
      }
    }
    loadTransactions()
    return () => { active = false }
  }, [page, type, category, merchant])

  const resetFilters = () => {
    setType('')
    setCategory('')
    setMerchant('')
    setPage(1)
  }

  const initials = user?.name?.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || 'U'

  return (
    <div className="dashboard-layout">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark"><Wallet size={21} /></span><span>KharchaKlick</span></div>
        <div className="sidebar-label">Workspace</div>
        <Link className="sidebar-link" to="/dashboard"><LayoutDashboard size={18} /><span>Overview</span></Link>
        <Link className="sidebar-link active" to="/transactions"><ReceiptText size={18} /><span>Transactions</span></Link>
        <div className="sidebar-link" aria-disabled="true"><PiggyBank size={18} /><span>Budgets</span></div>
        <div className="sidebar-link" aria-disabled="true"><ChartNoAxesCombined size={18} /><span>Insights</span></div>
        <div className="sidebar-footer">Your personal finance companion.<br />More clarity, one step at a time.</div>
      </aside>

      <main className="dashboard-main">
        <header className="topbar">
          <div className="topbar-title">Transactions</div>
          <div className="user-menu">
            <div className="user-avatar" aria-label={user?.name || 'User'}>{initials}</div>
            <span className="user-name">{user?.name}</span>
            <button className="logout-button" onClick={logout} type="button"><LogOut size={14} /> Sign out</button>
          </div>
        </header>

        <section className="dashboard-content">
          <div className="dashboard-heading-row">
            <div>
              <span className="eyebrow">Your activity</span>
              <h1 className="dashboard-heading">Transactions</h1>
              <p className="dashboard-intro">View and filter your income and expenses.</p>
            </div>
            <span className="current-period">{total} {total === 1 ? 'transaction' : 'transactions'}</span>
          </div>

          <section className="panel transactions-panel">
            <div className="transaction-filters">
              <input
                aria-label="Search merchant"
                placeholder="Search merchant..."
                value={merchant}
                onChange={(event) => { setMerchant(event.target.value); setPage(1) }}
              />
              <select aria-label="Filter by type" value={type} onChange={(event) => { setType(event.target.value); setPage(1) }}>
                <option value="">All types</option>
                <option value="expense">Expenses</option>
                <option value="income">Income</option>
              </select>
              <select aria-label="Filter by category" value={category} onChange={(event) => { setCategory(event.target.value); setPage(1) }}>
                <option value="">All categories</option>
                {['Food', 'Transport', 'Shopping', 'Bills', 'Education', 'Entertainment', 'Health', 'Travel', 'Other'].map((item) => (
                  <option key={item} value={item}>{item}</option>
                ))}
              </select>
              <button className="filter-reset" type="button" onClick={resetFilters}>Clear filters</button>
            </div>

            {error && <div className="dashboard-error" role="alert">{error}</div>}
            {isLoading ? (
              <div className="transaction-empty">Loading your transactions...</div>
            ) : transactions.length ? (
              <>
                <div className="transactions-table-wrap">
                  <table className="transactions-table">
                    <thead>
                      <tr><th>Transaction</th><th>Category</th><th>Payment method</th><th>Date</th><th className="amount-cell">Amount</th></tr>
                    </thead>
                    <tbody>
                      {transactions.map((item) => {
                        const income = item.transaction_type === 'income'
                        return (
                          <tr key={item.id}>
                            <td>
                              <div className="transaction-title-cell">
                                <span className={`transaction-type-icon ${income ? 'income' : 'expense'}`}>
                                  {income ? <ArrowDownLeft size={17} /> : <ArrowUpRight size={17} />}
                                </span>
                                <span><strong>{item.description}</strong><small>{item.merchant || 'No merchant'}</small></span>
                              </div>
                            </td>
                            <td>{item.category}</td>
                            <td>{item.payment_method}</td>
                            <td>{dateLabel(item.transaction_date)}</td>
                            <td className={`amount-cell transaction-amount ${income ? 'positive' : 'negative'}`}>
                              {income ? '+' : '−'}{currency.format(Number(item.amount || 0))}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
                <div className="transactions-pagination">
                  <span>Page {page}{totalPages ? ` of ${totalPages}` : ''}</span>
                  <div>
                    <button type="button" onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={page <= 1 || isLoading} aria-label="Previous page"><ChevronLeft size={17} /></button>
                    <button type="button" onClick={() => setPage((value) => value + 1)} disabled={!totalPages || page >= totalPages || isLoading} aria-label="Next page"><ChevronRight size={17} /></button>
                  </div>
                </div>
              </>
            ) : (
              <div className="transaction-empty">
                No transactions found. Try changing your filters or add your first transaction.
              </div>
            )}
          </section>
        </section>
      </main>
    </div>
  )
}

export default Transactions
