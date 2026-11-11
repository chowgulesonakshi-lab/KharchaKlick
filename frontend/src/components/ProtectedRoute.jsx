import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function ProtectedRoute({ children }) {
  const { user, isLoading } = useAuth()

  if (isLoading) return <div className="app-loading">Loading KharchaKlick...</div>
  return user ? children : <Navigate to="/login" replace />
}

export default ProtectedRoute
