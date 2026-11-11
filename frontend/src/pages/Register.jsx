import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, Wallet } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

function getErrorMessage(error) {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join(', ')
  return 'Unable to create your account right now. Check your connection and try again.'
}

function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', password: '', confirmPassword: '' })
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const updateField = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')

    if (form.password.length < 6) {
      setError('Your password must contain at least 6 characters.')
      return
    }
    if (form.password !== form.confirmPassword) {
      setError('Your passwords do not match.')
      return
    }

    setIsSubmitting(true)
    try {
      await register({
        name: form.name.trim(),
        email: form.email.trim(),
        password: form.password,
      })
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
          <span className="showcase-eyebrow">A fresh start with your finances</span>
          <h1>Small steps. Smarter spending.</h1>
          <p>Bring your expenses, budgets, and money goals into one simple space designed to make everyday decisions easier.</p>
        </div>
        <div className="showcase-note">Your personal finance companion starts here.</div>
      </section>

      <section className="auth-panel">
        <div className="auth-card">
          <div className="brand"><span className="brand-mark"><Wallet size={21} /></span><span>KharchaKlick</span></div>
          <span className="eyebrow">Get started</span>
          <h2>Create your account</h2>
          <p className="auth-subtitle">Set up your account and take the first step toward clearer finances.</p>

          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="name">Full name</label>
              <input id="name" name="name" type="text" autoComplete="name" placeholder="Your name" value={form.name} onChange={updateField} maxLength={100} required />
            </div>
            <div className="field">
              <label htmlFor="email">Email address</label>
              <input id="email" name="email" type="email" autoComplete="email" placeholder="you@example.com" value={form.email} onChange={updateField} required />
            </div>
            <div className="field">
              <label htmlFor="password">Password</label>
              <input id="password" name="password" type="password" autoComplete="new-password" placeholder="At least 6 characters" value={form.password} onChange={updateField} minLength={6} maxLength={128} required />
            </div>
            <div className="field">
              <label htmlFor="confirmPassword">Confirm password</label>
              <input id="confirmPassword" name="confirmPassword" type="password" autoComplete="new-password" placeholder="Re-enter your password" value={form.confirmPassword} onChange={updateField} required />
            </div>
            {error && <div className="form-error" role="alert">{error}</div>}
            <button className="primary-button" type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Creating account...' : 'Create account'} {!isSubmitting && <ArrowRight size={17} />}
            </button>
          </form>
          <p className="auth-switch">Already have an account? <Link to="/login">Sign in</Link></p>
        </div>
      </section>
    </main>
  )
}

export default Register
