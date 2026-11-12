import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('kharchaklick_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export const authApi = {
  register: (payload) => api.post('/auth/register', payload),
  login: (payload) => api.post('/auth/login', payload),
  me: () => api.get('/auth/me'),
}

export const financeApi = {
  summary: (params = {}) => api.get('/analytics/summary', { params }),
  monthly: (params = {}) => api.get('/analytics/monthly', { params }),
  categories: (params = {}) => api.get('/analytics/categories', { params }),
  transactions: (params = {}) => api.get('/transactions/', { params }),
  budgets: (params = {}) => api.get('/budgets/', { params }),
  budgetUtilization: (params = {}) => api.get('/budgets/utilization', { params }),
}

export default api
