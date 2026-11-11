import { LayoutDashboard, ReceiptText, PiggyBank, ChartNoAxesCombined, Wallet, LogOut, Sparkles } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

function Dashboard() {
  const { user, logout } = useAuth()
  const firstName = user?.name?.trim().split(/\s+/)[0] || 'there'
  const initials = user?.name?.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase() || 'U'

  return (
    <div className="dashboard-layout">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark"><Wallet size={21} /></span><span>KharchaKlick</span></div>
        <div className="sidebar-label">Workspace</div>
        <a className="sidebar-link active" href="/dashboard"><LayoutDashboard size={18} /><span>Overview</span></a>
        <div className="sidebar-link" aria-disabled="true"><ReceiptText size={18} /><span>Transactions</span></div>
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
          <span className="eyebrow">Your workspace</span>
          <h1 className="dashboard-heading">Good to see you, {firstName}.</h1>
          <p className="dashboard-intro">Your KharchaKlick account is ready. This is the starting point for your personal finance overview.</p>

          <div className="welcome-card">
            <div>
              <h3>Your money story starts here.</h3>
              <p>Your account is connected. In the next steps, we'll bring your transactions, budgets, and spending insights into this workspace.</p>
            </div>
            <div className="welcome-icon"><Sparkles size={28} /></div>
          </div>

          <div className="foundation-grid">
            <article className="foundation-card">
              <span>01 · TRACK</span>
              <h4>Transactions</h4>
              <p>Keep your income and expenses organized in one place.</p>
            </article>
            <article className="foundation-card">
              <span>02 · PLAN</span>
              <h4>Budgets</h4>
              <p>Set spending limits and stay mindful of your goals.</p>
            </article>
            <article className="foundation-card">
              <span>03 · UNDERSTAND</span>
              <h4>Insights</h4>
              <p>Turn everyday activity into a clearer picture of your money.</p>
            </article>
          </div>
        </section>
      </main>
    </div>
  )
}

export default Dashboard
