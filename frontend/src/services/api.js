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
  insights: (params = {}) => api.get('/analytics/insights', { params }),
  suggestCategory: (payload) => api.post('/intelligence/suggest-category', payload),
  transactions: (params = {}) => api.get('/transactions/', { params }),
  createTransaction: (payload) => api.post('/transactions/', payload),
  updateTransaction: (id, payload) => api.patch(`/transactions/${id}`, payload),
  deleteTransaction: (id) => api.delete(`/transactions/${id}`),
  budgets: (params = {}) => api.get('/budgets/', { params }),
  budgetUtilization: (params = {}) => api.get('/budgets/utilization', { params }),
  createBudget: (payload) => api.post('/budgets/', payload),
  updateBudget: (id, payload) => api.patch(`/budgets/${id}`, payload),
  deleteBudget: (id) => api.delete(`/budgets/${id}`),
}

export default api
