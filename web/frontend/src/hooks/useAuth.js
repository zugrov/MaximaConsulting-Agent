import { useEffect, useState } from 'react'
import { useAuthStore } from '../store/authStore'

const API = '/api/auth'

// Возвращает isReady: пока токен из localStorage проверяется через /me, маршруты
// не должны считать пользователя неавторизованным.
export function useBootAuth() {
  const { token, setAuth, logout } = useAuthStore()
  const [isReady, setIsReady] = useState(!token)

  useEffect(() => {
    if (!token) return
    fetch(`${API}/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then((user) => setAuth(user, token))
      .catch(() => logout())
      .finally(() => setIsReady(true))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return isReady
}

export async function login(email, password) {
  const form = new URLSearchParams({ username: email, password })
  const r = await fetch(`${API}/login`, { method: 'POST', body: form })
  if (!r.ok) {
    const err = await r.json().catch(() => ({}))
    if (r.status === 404) {
      throw new Error('Бэкенд недоступен. Запустите: cd web && bash start.sh')
    }
    const detail = err.detail
    const msg = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail[0]?.msg
        : null
    throw new Error(msg || 'Ошибка авторизации')
  }
  const { access_token } = await r.json()

  const me = await fetch(`${API}/me`, {
    headers: { Authorization: `Bearer ${access_token}` },
  }).then((r) => r.json())

  useAuthStore.getState().setAuth(me, access_token)
  return me
}
