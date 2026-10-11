import { useState } from 'react'
import { useAuthStore } from '../store/authStore'
import { Modal } from '../pages/ClientsPage'

const MIN_PASSWORD_LENGTH = 8

const inputStyle = {
  width: '100%', padding: '8px 12px', border: '1px solid var(--border)',
  borderRadius: 6, fontSize: 13, outline: 'none', boxSizing: 'border-box',
}

function Field({ label, value, onChange, autoFocus }) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 5 }}>
        {label}
      </label>
      <input
        type="password"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoFocus={autoFocus}
        required
        style={inputStyle}
      />
    </div>
  )
}

function extractError(detail) {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail[0]?.msg?.replace(/^Value error, /, '')
  return null
}

// Смена пароля. Без userId — свой пароль (нужен текущий), с userId — сброс администратором.
export default function PasswordModal({ userId, userName, onClose }) {
  const token = useAuthStore((s) => s.token)
  const isOwn = userId == null

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [repeatPassword, setRepeatPassword] = useState('')
  const [error, setError] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [isDone, setIsDone] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (newPassword.length < MIN_PASSWORD_LENGTH) {
      setError(`Пароль должен быть не короче ${MIN_PASSWORD_LENGTH} символов`)
      return
    }
    if (newPassword !== repeatPassword) {
      setError('Пароли не совпадают')
      return
    }

    setIsSaving(true)
    try {
      const resp = await fetch(
        isOwn ? '/api/auth/me/password' : `/api/auth/users/${userId}/password`,
        {
          method: isOwn ? 'POST' : 'PUT',
          headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify(
            isOwn
              ? { current_password: currentPassword, new_password: newPassword }
              : { new_password: newPassword },
          ),
        },
      )
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}))
        throw new Error(extractError(data.detail) || `Ошибка ${resp.status}`)
      }
      setIsDone(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <Modal title={isOwn ? 'Смена пароля' : `Новый пароль: ${userName}`} onClose={onClose}>
      {isDone ? (
        <div>
          <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', color: '#166534', borderRadius: 6, padding: '8px 12px', fontSize: 13, marginBottom: 16 }}>
            Пароль изменён
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <button onClick={onClose} style={buttonStyle}>Закрыть</button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {isOwn && (
            <Field label="Текущий пароль" value={currentPassword} onChange={setCurrentPassword} autoFocus />
          )}
          <Field label={`Новый пароль (от ${MIN_PASSWORD_LENGTH} символов)`} value={newPassword} onChange={setNewPassword} autoFocus={!isOwn} />
          <Field label="Повторите новый пароль" value={repeatPassword} onChange={setRepeatPassword} />
          {error && (
            <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: 'var(--danger)', borderRadius: 6, padding: '8px 12px', fontSize: 12 }}>
              {error}
            </div>
          )}
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <button type="submit" disabled={isSaving} style={{ ...buttonStyle, cursor: isSaving ? 'not-allowed' : 'pointer' }}>
              {isSaving ? 'Сохранение…' : 'Сменить пароль'}
            </button>
          </div>
        </form>
      )}
    </Modal>
  )
}

const buttonStyle = {
  background: 'var(--primary)', color: '#fff', border: 'none', borderRadius: 6,
  padding: '9px 20px', fontSize: 13, fontWeight: 600, cursor: 'pointer',
}
