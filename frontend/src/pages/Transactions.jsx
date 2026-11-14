import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowDownLeft,
  ArrowUpRight,
  ChartNoAxesCombined,
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  Sparkles,
  LogOut,
  Pencil,
  PiggyBank,
  Plus,
  ReceiptText,
  Trash2,
  Wallet,
  X,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { financeApi } from '../services/api'

const currency = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 2,
})

const categories = ['Food', 'Transport', 'Shopping', 'Bills', 'Education', 'Entertainment', 'Health', 'Travel', 'Other']
const paymentMethods = ['Cash', 'UPI', 'Credit Card', 'Debit Card', 'Card', 'Net Banking', 'Wallet', 'Other']
const today = () => {
  const now = new Date()
  return new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}
const dateLabel = (value) => new Date(value).toLocaleDateString('en-IN', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
})
const emptyForm = () => ({
  amount: '',
  description: '',
  merchant: '',
  category: 'Food',
  payment_method: 'UPI',
  transaction_type: 'expense',
  transaction_date: today(),
})
const errorMessage = (error, fallback) =>
  error.response?.data?.detail || fallback

function Transactions() {
  const { user, logout } = useAuth()
  const [transactions, setTransactions] = useState([])
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const [total, setTotal] = useState(0)
  const [type, setType] = useState('')
  const [category, setCategory] = useState('')
  const [merchant, setMerchant] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [formError, setFormError] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [isSuggesting, setIsSuggesting] = useState(false)
  const [suggestion, setSuggestion] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)

  const loadTransactions = useCallback(async () => {
    setIsLoading(true)
    setError('')
    try {
      const params = { page, page_size: 10 }
      if (type) params.transaction_type = type
      if (category) params.category = category
      if (merchant.trim()) params.merchant = merchant.trim()
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo
      const response = await financeApi.transactions(params)
      const data = response.data
      setTransactions(Array.isArray(data) ? data : data.items || data.transactions || [])
      setTotal(Array.isArray(data) ? data.length : data.total ?? data.total_count ?? 0)
      setTotalPages(Array.isArray(data) ? 1 : data.total_pages ?? 0)
    } catch (requestError) {
      setError(errorMessage(requestError, 'We could not load your transactions. Please try again.'))
    } finally {
      setIsLoading(false)
    }
  }, [page, type, category, merchant, dateFrom, dateTo, refreshKey])

  useEffect(() => {
    loadTransactions()
  }, [loadTransactions])

  const resetFilters = () => {
    setType('')
    setCategory('')
    setMerchant('')
    setDateFrom('')
    setDateTo('')
    setPage(1)
  }

  const openAddForm = () => {
    setEditingId(null)
    setForm(emptyForm())
    setFormError('')
    setSuggestion(null)
    setFormOpen(true)
  }

  const openEditForm = (transaction) => {
    setEditingId(transaction.id)
    setForm({
      amount: String(transaction.amount),
      description: transaction.description || '',
      merchant: transaction.merchant || '',
      category: transaction.category,
      payment_method: transaction.payment_method,
      transaction_type: transaction.transaction_type,
      transaction_date: new Date(transaction.transaction_date).toISOString().slice(0, 10),
    })
    setFormError('')
    setSuggestion(null)
    setFormOpen(true)
  }

  const closeForm = () => {
    if (isSaving) return
    setFormOpen(false)
    setEditingId(null)
    setFormError('')
  }

  const handleSuggestCategory = async () => {
    if (!form.description.trim()) {
      setSuggestion({ error: 'Add a description first so the assistant has something to analyze.' })
      return
    }
    setIsSuggesting(true)
    setSuggestion(null)
    try {
      const response = await financeApi.suggestCategory({
        description: form.description.trim(),
        merchant: form.merchant.trim() || null,
        transaction_type: form.transaction_type,
      })
      const result = response.data
      setForm((current) => ({ ...current, category: result.category }))
      setSuggestion({
        message: result.reason,
        source: result.source,
        confidence: result.confidence,
      })
    } catch (requestError) {
      setSuggestion({ error: errorMessage(requestError, 'Could not generate a category suggestion. Please try again.') })
    } finally {
      setIsSuggesting(false)
    }
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setFormError('')
    const amount = Number(form.amount)
    if (!Number.isFinite(amount) || amount <= 0) {
      setFormError('Enter an amount greater than zero.')
      return
    }
    setIsSaving(true)
    const payload = {
      amount: amount.toFixed(2),
      description: form.description.trim(),
      merchant: form.merchant.trim() || null,
      category: form.category,
      payment_method: form.payment_method,
      transaction_type: form.transaction_type,
      transaction_date: `${form.transaction_date}T12:00:00`,
    }
    try {
      if (editingId !== null) {
        await financeApi.updateTransaction(editingId, payload)
      } else {
        await financeApi.createTransaction(payload)
      }
      setFormOpen(false)
      setEditingId(null)
      setForm(emptyForm())
      setPage(1)
      setRefreshKey((value) => value + 1)
    } catch (requestError) {
      setFormError(errorMessage(requestError, 'Could not save this transaction. Please check the details and try again.'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async (transaction) => {
    const confirmed = window.confirm(`Delete "${transaction.description}"? This action cannot be undone.`)
    if (!confirmed) return
    setDeletingId(transaction.id)
    setError('')
    try {
      await financeApi.deleteTransaction(transaction.id)
      if (transactions.length === 1 && page > 1) setPage((value) => value - 1)
      else setRefreshKey((value) => value + 1)
    } catch (requestError) {
      setError(errorMessage(requestError, 'Could not delete this transaction. Please try again.'))
    } finally {
      setDeletingId(null)
    }
  }

  const initials = user?.name?.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || 'U'

  return (
    <div className="dashboard-layout">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark"><Wallet size={21} /></span><span>KharchaKlick</span></div>
        <div className="sidebar-label">Workspace</div>
        <Link className="sidebar-link" to="/dashboard"><LayoutDashboard size={18} /><span>Overview</span></Link>
        <Link className="sidebar-link active" to="/transactions"><ReceiptText size={18} /><span>Transactions</span></Link>
        <Link className="sidebar-link" to="/budgets"><PiggyBank size={18} /><span>Budgets</span></Link>
        <Link className="sidebar-link" to="/insights"><ChartNoAxesCombined size={18} /><span>Insights</span></Link>
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
              <p className="dashboard-intro">View and manage your income and expenses.</p>
            </div>
            <div className="transactions-heading-actions">
              <span className="current-period">{total} {total === 1 ? 'transaction' : 'transactions'}</span>
              <button className="primary-button add-transaction-button" type="button" onClick={openAddForm}>
                <Plus size={17} /> Add transaction
              </button>
            </div>
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
                {categories.map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
              <input
                aria-label="Filter from date"
                type="date"
                value={dateFrom}
                max={dateTo || undefined}
                onChange={(event) => { setDateFrom(event.target.value); setPage(1) }}
              />
              <input
                aria-label="Filter to date"
                type="date"
                value={dateTo}
                min={dateFrom || undefined}
                onChange={(event) => { setDateTo(event.target.value); setPage(1) }}
              />
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
                      <tr><th>Transaction</th><th>Category</th><th>Payment method</th><th>Date</th><th className="amount-cell">Amount</th><th>Actions</th></tr>
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
                            <td>
                              <div className="transaction-actions">
                                <button className="icon-action edit" type="button" onClick={() => openEditForm(item)} aria-label={`Edit ${item.description}`} title="Edit transaction"><Pencil size={16} /></button>
                                <button className="icon-action delete" type="button" onClick={() => handleDelete(item)} disabled={deletingId === item.id} aria-label={`Delete ${item.description}`} title="Delete transaction"><Trash2 size={16} /></button>
                              </div>
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
                No transactions found. Add your first transaction to get started.
              </div>
            )}
          </section>
        </section>
      </main>

      {formOpen && (
        <div className="transaction-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) closeForm() }}>
          <section className="transaction-modal" role="dialog" aria-modal="true" aria-labelledby="transaction-form-title">
            <div className="transaction-modal-heading">
              <div>
                <span className="eyebrow">{editingId !== null ? 'Update your activity' : 'Track your money'}</span>
                <h2 id="transaction-form-title">{editingId !== null ? 'Edit transaction' : 'Add transaction'}</h2>
              </div>
              <button className="icon-action" type="button" onClick={closeForm} disabled={isSaving} aria-label="Close form"><X size={19} /></button>
            </div>
            <form className="transaction-form" onSubmit={handleSubmit}>
              <div className="field">
                <label htmlFor="transaction-type">Transaction type</label>
                <select id="transaction-type" value={form.transaction_type} onChange={(event) => setForm({ ...form, transaction_type: event.target.value })}>
                  <option value="expense">Expense</option>
                  <option value="income">Income</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="transaction-amount">Amount (₹)</label>
                <input id="transaction-amount" type="number" min="0.01" step="0.01" required placeholder="e.g. 500" value={form.amount} onChange={(event) => setForm({ ...form, amount: event.target.value })} />
              </div>
              <div className="field">
                <label htmlFor="transaction-description">Description</label>
                <input id="transaction-description" type="text" maxLength="255" required placeholder="e.g. Weekly groceries" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
              </div>
              <div className="field">
                <label htmlFor="transaction-merchant">Merchant (optional)</label>
                <input id="transaction-merchant" type="text" maxLength="120" placeholder="e.g. BigBasket" value={form.merchant} onChange={(event) => setForm({ ...form, merchant: event.target.value })} />
              </div>
              <div className="transaction-form-grid">
                <div className="field">
                  <label htmlFor="transaction-category">Category</label>
                  <select id="transaction-category" value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}>
                    {categories.map((item) => <option key={item} value={item}>{item}</option>)}
                  </select>
                  <button className="ai-suggest-button" type="button" onClick={handleSuggestCategory} disabled={isSuggesting || !form.description.trim()}><Sparkles size={15} />{isSuggesting ? 'Analyzing...' : 'Suggest category'}</button>
                  {suggestion && <p className={suggestion.error ? 'ai-suggestion-message error' : 'ai-suggestion-message'} role="status">{suggestion.error || `${suggestion.message} (${suggestion.source === 'ollama' ? 'AI' : 'smart rules'} · ${Math.round(suggestion.confidence * 100)}% confidence)`}</p>}
                </div>
                <div className="field">
                  <label htmlFor="transaction-payment">Payment method</label>
                  <select id="transaction-payment" value={form.payment_method} onChange={(event) => setForm({ ...form, payment_method: event.target.value })}>
                    {paymentMethods.map((item) => <option key={item} value={item}>{item}</option>)}
                  </select>
                </div>
              </div>
              <div className="field">
                <label htmlFor="transaction-date">Date</label>
                <input id="transaction-date" type="date" required value={form.transaction_date} onChange={(event) => setForm({ ...form, transaction_date: event.target.value })} />
              </div>
              {formError && <div className="form-error" role="alert">{formError}</div>}
              <div className="transaction-form-actions">
                <button className="filter-reset" type="button" onClick={closeForm} disabled={isSaving}>Cancel</button>
                <button className="primary-button" type="submit" disabled={isSaving}>{isSaving ? 'Saving...' : editingId !== null ? 'Save changes' : 'Add transaction'}</button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  )
}

export default Transactions
