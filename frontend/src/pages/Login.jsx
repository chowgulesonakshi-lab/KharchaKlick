import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, Wallet } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

function getErrorMessage(error) {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join(', ')
  return 'Unable to sign in right now. Check your connection and try again.'
}

function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const updateField = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)
    try {
      await login({ email: form.email.trim(), password: form.password })
      navigate('/dashboard', { replace: true })
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-showcase">
        <div className="brand"><span className="brand-mark"><Wallet size={21} /></span><span>KharchaKlick</span></div>
        <div className="showcase-copy">
          <span className="showcase-eyebrow">Your money, in focus</span>
          <h1>Make every rupee make sense.</h1>
          <p>A calmer, clearer way to understand your spending, stay on top of budgets, and build better money habits.</p>
        </div>
        <div className="showcase-note">A little more clarity. A lot more confidence.</div>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <div className="brand"><span className="brand-mark"><Wallet size={21} /></span><span>KharchaKlick</span></div>
          <span className="eyebrow">Welcome back</span>
          <h2>Sign in to your account</h2>
          <p className="auth-subtitle">Pick up right where you left off. Your finances are waiting.</p>

          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="email">Email address</label>
              <input id="email" name="email" type="email" autoComplete="email" placeholder="you@example.com" value={form.email} onChange={updateField} required />
            </div>
            <div className="field">
              <label htmlFor="password">Password</label>
              <input id="password" name="password" type="password" autoComplete="current-password" placeholder="Enter your password" value={form.password} onChange={updateField} required />
            </div>
            {error && <div className="form-error" role="alert">{error}</div>}
            <button className="primary-button" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Signing in...' : 'Sign in'} {!isSubmitting && <ArrowRight size={17} />}
            </button>
          </form>
          <p className="auth-switch">New to KharchaKlick? <Link to="/register">Create an account</Link></p>
        </div>
      </section>
    </main>
  )
}

export default Login
