import { useEffect } from 'react'
import { useAuthStore } from '../store/authStore'

const API = '/api/auth'

export function useBootAuth() {
  const { token, setAuth, logout } = useAuthStore()

  useEffect(() => {
    if (!token) return
    fetch(`${API}/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((user) => setAuth(user, token))
      .catch(() => logout())
  }, []) // eslint-disable-line react-hooks/exhaustive-deps
}

export async function login(email, password) {
  const form = new URLSearchParams({ username: email, password })
  const r = await fetch(`${API}/login`, { method: 'POST', body: form })
  if (!r.ok) {
    const err = await r.json().catch(() => ({}))
    throw new Error(err.detail || 'Ошибка авторизации')
  }
  const { access_token } = await r.json()

  const me = await fetch(`${API}/me`, {
    headers: { Authorization: `Bearer ${access_token}` },
  }).then((r) => r.json())

  useAuthStore.getState().setAuth(me, access_token)
  return me
}
