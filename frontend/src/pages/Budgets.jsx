import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle, ArrowLeft, ArrowRight, ChartNoAxesCombined, LayoutDashboard,
  LogOut, Pencil, PiggyBank, Plus, ReceiptText, Trash2, Wallet, X,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { financeApi } from '../services/api'
import './Budgets.css'

const categories = ['Food', 'Transport', 'Shopping', 'Bills', 'Education', 'Entertainment', 'Health', 'Travel', 'Other']
const currency = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })
const monthName = (month, year) => new Date(year, month - 1, 1).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })
const errorMessage = (error, fallback) => error.response?.data?.detail || fallback
const blankForm = () => ({ category: '', amount: '' })

function Budgets() {
  const { user, logout } = useAuth()
  const now = new Date()
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [year, setYear] = useState(now.getFullYear())
  const [budgets, setBudgets] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editingBudget, setEditingBudget] = useState(null)
  const [form, setForm] = useState(blankForm)
  const [formError, setFormError] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)

  const loadBudgets = useCallback(async () => {
    setIsLoading(true)
    setError('')
    try {
      const response = await financeApi.budgets({ month, year })
      setBudgets(Array.isArray(response.data) ? response.data : [])
    } catch (requestError) {
      setError(errorMessage(requestError, 'We could not load your budgets. Please try again.'))
    } finally {
      setIsLoading(false)
    }
  }, [month, year, refreshKey])

  useEffect(() => { loadBudgets() }, [loadBudgets])

  const totals = useMemo(() => budgets.reduce((result, budget) => ({
    planned: result.planned + Number(budget.amount || 0),
    spent: result.spent + Number(budget.spent || 0),
    remaining: result.remaining + Number(budget.remaining || 0),
  }), { planned: 0, spent: 0, remaining: 0 }), [budgets])
  const overallPercent = totals.planned > 0 ? (totals.spent / totals.planned) * 100 : 0
  const initials = user?.name?.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || 'U'

  const changeMonth = (offset) => {
    const next = new Date(year, month - 1 + offset, 1)
    setMonth(next.getMonth() + 1)
    setYear(next.getFullYear())
    setNotice('')
  }

  const openCreate = () => {
    setEditingBudget(null)
    setForm(blankForm())
    setFormError('')
    setModalOpen(true)
  }

  const openEdit = (budget) => {
    setEditingBudget(budget)
    setForm({ category: budget.category || '', amount: String(budget.amount) })
    setFormError('')
    setModalOpen(true)
  }

  const closeModal = () => {
    if (isSaving) return
    setModalOpen(false)
    setEditingBudget(null)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setFormError('')
    const amount = Number(form.amount)
    if (!Number.isFinite(amount) || amount <= 0) {
      setFormError('Enter a budget amount greater than zero.')
      return
    }
    setIsSaving(true)
    const payload = { category: form.category || null, amount: amount.toFixed(2), month, year }
    try {
      if (editingBudget) {
        await financeApi.updateBudget(editingBudget.id, { category: payload.category, amount: payload.amount })
        setNotice('Budget updated successfully.')
      } else {
        await financeApi.createBudget(payload)
        setNotice('Budget created successfully.')
      }
      setModalOpen(false)
      setEditingBudget(null)
      setRefreshKey((value) => value + 1)
    } catch (requestError) {
      setFormError(errorMessage(requestError, 'Could not save this budget. Please try again.'))
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async (budget) => {
    const label = budget.category || 'Overall'
    if (!window.confirm(`Delete the ${label} budget for ${monthName(month, year)}?`)) return
    setDeletingId(budget.id)
    setError('')
    try {
      await financeApi.deleteBudget(budget.id)
      setNotice('Budget deleted.')
      setRefreshKey((value) => value + 1)
    } catch (requestError) {
      setError(errorMessage(requestError, 'Could not delete this budget. Please try again.'))
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="dashboard-layout">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark"><Wallet size={21} /></span><span>KharchaKlick</span></div>
        <div className="sidebar-label">Workspace</div>
        <Link className="sidebar-link" to="/dashboard"><LayoutDashboard size={18} /><span>Overview</span></Link>
        <Link className="sidebar-link" to="/transactions"><ReceiptText size={18} /><span>Transactions</span></Link>
        <Link className="sidebar-link active" to="/budgets"><PiggyBank size={18} /><span>Budgets</span></Link>
        <Link className="sidebar-link" to="/insights"><ChartNoAxesCombined size={18} /><span>Insights</span></Link>
        <div className="sidebar-footer">Your personal finance companion.<br />More clarity, one step at a time.</div>
      </aside>

      <main className="dashboard-main">
        <header className="topbar">
          <div className="topbar-title">Budgets</div>
          <div className="user-menu">
            <div className="user-avatar" aria-label={user?.name || 'User'}>{initials}</div>
            <span className="user-name">{user?.name}</span>
            <button className="logout-button" onClick={logout} type="button"><LogOut size={14} /> Sign out</button>
          </div>
        </header>

        <section className="dashboard-content budgets-content">
          <div className="dashboard-heading-row">
            <div>
              <span className="eyebrow">Plan with purpose</span>
              <h1 className="dashboard-heading">Your budgets</h1>
              <p className="dashboard-intro">Set monthly limits and keep your spending on track.</p>
            </div>
            <button className="primary-button add-transaction-button" type="button" onClick={openCreate}><Plus size={17} /> Create budget</button>
          </div>

          <div className="budget-period">
            <button className="icon-action" type="button" onClick={() => changeMonth(-1)} aria-label="Previous month"><ArrowLeft size={17} /></button>
            <strong>{monthName(month, year)}</strong>
            <button className="icon-action" type="button" onClick={() => changeMonth(1)} aria-label="Next month"><ArrowRight size={17} /></button>
          </div>

          {error && <div className="dashboard-error" role="alert"><AlertTriangle size={18} />{error}</div>}
          {notice && <div className="budget-notice" role="status">{notice}</div>}

          <div className="budget-summary-grid">
            <article className="summary-card">
              <div className="summary-icon balance"><PiggyBank size={19} /></div>
              <span className="summary-label">Total budget</span>
              <strong className="summary-value">{currency.format(totals.planned)}</strong>
              <span className="summary-note">Planned for this month</span>
            </article>
            <article className="summary-card">
              <div className="summary-icon expense"><ChartNoAxesCombined size={19} /></div>
              <span className="summary-label">Total spent</span>
              <strong className="summary-value">{currency.format(totals.spent)}</strong>
              <span className="summary-note">Against your budgets</span>
            </article>
            <article className="summary-card">
              <div className="summary-icon income"><Wallet size={19} /></div>
              <span className="summary-label">Remaining</span>
              <strong className="summary-value">{currency.format(totals.remaining)}</strong>
              <span className="summary-note">Budget minus spending</span>
            </article>
            <article className="summary-card">
              <div className="summary-icon count"><ChartNoAxesCombined size={19} /></div>
              <span className="summary-label">Overall usage</span>
              <strong className="summary-value">{overallPercent.toFixed(1)}%</strong>
              <span className="summary-note">{budgets.length} active {budgets.length === 1 ? 'budget' : 'budgets'}</span>
            </article>
          </div>

          {totals.planned > 0 && (
            <section className="panel budget-overview-panel">
              <div className="panel-heading"><div><h2>Monthly budget usage</h2><p>Combined spending across your budget limits</p></div><strong>{overallPercent.toFixed(1)}%</strong></div>
              <div className="budget-progress-track"><div className={overallPercent > 100 ? 'over' : ''} style={{ width: `${Math.min(overallPercent, 100)}%` }} /></div>
              <div className="budget-overview-foot"><span>{currency.format(totals.spent)} spent</span><span>{currency.format(totals.planned)} planned</span></div>
              {budgets.some((budget) => budget.is_overrun) && <p className="budget-warning"><AlertTriangle size={16} /> One or more budgets have exceeded their limits.</p>}
            </section>
          )}

          <div className="budgets-section-heading"><div><h2>Budget breakdown</h2><p>Track each spending limit individually.</p></div></div>
          {isLoading ? <div className="panel transaction-empty">Loading your budgets...</div> : budgets.length ? (
            <div className="budget-card-grid">
              {budgets.map((budget) => {
                const percent = Number(budget.utilization_percentage || 0)
                const isOver = Boolean(budget.is_overrun)
                const label = budget.category || 'Overall budget'
                return (
                  <article className="panel budget-card" key={budget.id}>
                    <div className="budget-card-top">
                      <div><span className="budget-category-label">{budget.category ? 'CATEGORY BUDGET' : 'TOTAL SPENDING'}</span><h3>{label}</h3></div>
                      <div className="transaction-actions">
                        <button className="icon-action edit" type="button" onClick={() => openEdit(budget)} aria-label={`Edit ${label} budget`}><Pencil size={16} /></button>
                        <button className="icon-action delete" type="button" onClick={() => handleDelete(budget)} disabled={deletingId === budget.id} aria-label={`Delete ${label} budget`}><Trash2 size={16} /></button>
                      </div>
                    </div>
                    <div className="budget-amount-row"><strong>{currency.format(Number(budget.spent || 0))}</strong><span>of {currency.format(Number(budget.amount || 0))}</span></div>
                    <div className="budget-progress-track"><div className={isOver ? 'over' : ''} style={{ width: `${Math.min(percent, 100)}%` }} /></div>
                    <div className="budget-card-foot">
                      <span className={isOver ? 'budget-over-text' : ''}>{percent.toFixed(1)}% used</span>
                      <strong className={isOver ? 'budget-over-text' : ''}>{isOver ? `${currency.format(Number(budget.overrun_amount || 0))} over budget` : `${currency.format(Number(budget.remaining || 0))} left`}</strong>
                    </div>
                    {isOver && <p className="budget-warning"><AlertTriangle size={15} /> You've exceeded this budget.</p>}
                    {!isOver && percent >= 80 && <p className="budget-caution">You're getting close to this budget limit.</p>}
                  </article>
                )
              })}
            </div>
          ) : (
            <div className="panel budget-empty">
              <div className="welcome-icon"><PiggyBank size={27} /></div>
              <h3>No budgets for {monthName(month, year)}</h3>
              <p>Create an overall monthly budget or set limits for individual categories like Food, Shopping, or Travel.</p>
              <button className="primary-button" type="button" onClick={openCreate}><Plus size={17} /> Create your first budget</button>
            </div>
          )}
        </section>
      </main>

      {modalOpen && (
        <div className="transaction-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) closeModal() }}>
          <section className="transaction-modal budget-modal" role="dialog" aria-modal="true" aria-labelledby="budget-form-title">
            <div className="transaction-modal-heading">
              <div><span className="eyebrow">{editingBudget ? 'Adjust your plan' : 'Plan your spending'}</span><h2 id="budget-form-title">{editingBudget ? 'Edit budget' : 'Create budget'}</h2></div>
              <button className="icon-action" type="button" onClick={closeModal} disabled={isSaving} aria-label="Close form"><X size={19} /></button>
            </div>
            <form className="transaction-form" onSubmit={handleSubmit}>
              <div className="field">
                <label htmlFor="budget-category">Budget type</label>
                <select id="budget-category" value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })}>
                  <option value="">Overall monthly budget</option>
                  {categories.map((category) => <option key={category} value={category}>{category}</option>)}
                </select>
                <small className="budget-field-help">Choose Overall to set one limit for all expense categories.</small>
              </div>
              <div className="field">
                <label htmlFor="budget-amount">Monthly limit (₹)</label>
                <input id="budget-amount" type="number" min="0.01" step="0.01" required placeholder="e.g. 10000" value={form.amount} onChange={(event) => setForm({ ...form, amount: event.target.value })} />
              </div>
              <div className="budget-period-note">Budget period: <strong>{monthName(month, year)}</strong></div>
              {formError && <div className="form-error" role="alert">{formError}</div>}
              <div className="transaction-form-actions">
                <button className="filter-reset" type="button" onClick={closeModal} disabled={isSaving}>Cancel</button>
                <button className="primary-button" type="submit" disabled={isSaving}>{isSaving ? 'Saving...' : editingBudget ? 'Save changes' : 'Create budget'}</button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  )
}

export default Budgets
