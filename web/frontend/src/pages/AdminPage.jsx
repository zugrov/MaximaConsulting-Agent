import { useState, useEffect } from 'react'
import { useAuthStore } from '../store/authStore'

const ROLE_COLORS = {
  admin:   { bg: '#fce7f3', color: '#be185d' },
  analyst: { bg: '#e8f0fb', color: '#1B61A6' },
  viewer:  { bg: '#e6f7f6', color: '#0D9488' },
}

export default function AdminPage() {
  const token = useAuthStore((s) => s.token)
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ email: '', name: '', password: '', role: 'analyst' })
  const [formError, setFormError] = useState('')
  const [saving, setSaving] = useState(false)

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

  const loadUsers = () =>
    fetch('/api/auth/users', { headers })
      .then((r) => r.json())
      .then(setUsers)
      .finally(() => setLoading(false))

  useEffect(() => { loadUsers() }, []) // eslint-disable-line

  const handleCreate = async (e) => {
    e.preventDefault()
    setFormError('')
    setSaving(true)
    try {
      const r = await fetch('/api/auth/users', { method: 'POST', headers, body: JSON.stringify(form) })
      if (!r.ok) { const d = await r.json(); throw new Error(d.detail) }
      await loadUsers()
      setForm({ email: '', name: '', password: '', role: 'analyst' })
      setShowForm(false)
    } catch (err) {
      setFormError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleRoleChange = async (userId, role) => {
    await fetch(`/api/auth/users/${userId}`, { method: 'PATCH', headers, body: JSON.stringify({ role }) })
    loadUsers()
  }

  const handleDelete = async (userId, name) => {
    if (!confirm(`Удалить пользователя ${name}?`)) return
    await fetch(`/api/auth/users/${userId}`, { method: 'DELETE', headers })
    loadUsers()
  }

  return (
    <div>
      <h1 style={{ fontFamily: 'var(--font-head)', fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Пользователи</h1>
      <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 28 }}>Управление доступом сотрудников</p>

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
        <button
          onClick={() => setShowForm((v) => !v)}
          style={{ background: 'var(--primary)', color: '#fff', border: 'none', borderRadius: 6, padding: '8px 16px', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
        >
          {showForm ? '× Отмена' : '+ Добавить пользователя'}
        </button>
      </div>

      {showForm && (
        <div style={{ background: 'var(--bg-white)', border: '1px solid var(--border)', borderRadius: 10, padding: 24, marginBottom: 20 }}>
          <div style={{ fontFamily: 'var(--font-head)', fontWeight: 700, fontSize: 14, marginBottom: 16 }}>Новый пользователь</div>
          <form onSubmit={handleCreate} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Field label="Имя" value={form.name} onChange={(v) => setForm({ ...form, name: v })} placeholder="Анна Кириллова" required />
            <Field label="Email" type="email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} placeholder="a.kirillova@company.ru" required />
            <Field label="Пароль" type="password" value={form.password} onChange={(v) => setForm({ ...form, password: v })} placeholder="Минимум 6 символов" required />
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 5 }}>Роль</label>
              <select
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
                style={{ width: '100%', padding: '9px 12px', border: '1px solid var(--border)', borderRadius: 6, fontSize: 13, background: 'var(--bg-white)' }}
              >
                <option value="analyst">analyst — анализ и загрузка</option>
                <option value="viewer">viewer — только просмотр</option>
                <option value="admin">admin — полный доступ</option>
              </select>
            </div>
            {formError && (
              <div style={{ gridColumn: '1/-1', background: '#fef2f2', border: '1px solid #fecaca', color: 'var(--danger)', borderRadius: 6, padding: '8px 12px', fontSize: 12 }}>
                {formError}
              </div>
            )}
            <div style={{ gridColumn: '1/-1', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                type="submit"
                disabled={saving}
                style={{ background: 'var(--primary)', color: '#fff', border: 'none', borderRadius: 6, padding: '9px 20px', fontSize: 13, fontWeight: 600, cursor: saving ? 'not-allowed' : 'pointer' }}
              >
                {saving ? 'Сохранение…' : 'Создать'}
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Загрузка…</div>
      ) : (
        <div style={{ background: 'var(--bg-white)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
          {users.map((u, i) => {
            const rc = ROLE_COLORS[u.role] || {}
            return (
              <div key={u.id} style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '12px 16px', borderBottom: i < users.length - 1 ? '1px solid var(--border)' : 'none',
              }}>
                <div style={{
                  width: 32, height: 32, borderRadius: '50%', background: 'var(--primary)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: '#fff', fontSize: 12, fontWeight: 600, flexShrink: 0,
                }}>
                  {u.name.split(' ').map((w) => w[0]).slice(0, 2).join('')}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{u.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{u.email}</div>
                </div>
                <select
                  value={u.role}
                  onChange={(e) => handleRoleChange(u.id, e.target.value)}
                  style={{
                    padding: '3px 8px', border: '1px solid var(--border)', borderRadius: 4,
                    fontSize: 11, fontWeight: 600, cursor: 'pointer',
                    background: rc.bg || 'var(--bg)', color: rc.color || 'var(--text)',
                  }}
                >
                  <option value="admin">admin</option>
                  <option value="analyst">analyst</option>
                  <option value="viewer">viewer</option>
                </select>
                <button
                  onClick={() => handleDelete(u.id, u.name)}
                  style={{ fontSize: 11, color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer', padding: '4px 8px' }}
                >
                  Удалить
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function Field({ label, value, onChange, type = 'text', placeholder, required }) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 5 }}>{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        style={{ width: '100%', padding: '9px 12px', border: '1px solid var(--border)', borderRadius: 6, fontSize: 13, outline: 'none' }}
      />
    </div>
  )
}
