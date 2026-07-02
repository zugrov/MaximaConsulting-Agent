import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../hooks/useAuth'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/analysis')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      <div style={{
        background: 'var(--bg-white)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        padding: '40px 36px',
        width: '100%',
        maxWidth: 380,
        boxShadow: '0 4px 24px rgba(0,0,0,.06)',
      }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{
            fontFamily: 'var(--font-head)',
            fontWeight: 700,
            fontSize: 20,
            color: 'var(--text)',
            marginBottom: 6,
          }}>
            maxima <span style={{ color: 'var(--teal)' }}>consulting</span>
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>AI Agent · внутренний портал</div>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 5 }}>
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
              placeholder="admin@maximaconsult.ru"
              style={{
                width: '100%', padding: '9px 12px',
                border: '1px solid var(--border)', borderRadius: 6,
                fontSize: 13, outline: 'none', color: 'var(--text)',
                transition: 'border-color .15s',
              }}
              onFocus={(e) => (e.target.style.borderColor = 'var(--primary)')}
              onBlur={(e) => (e.target.style.borderColor = 'var(--border)')}
            />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 5 }}>
              Пароль
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="••••••••"
              style={{
                width: '100%', padding: '9px 12px',
                border: '1px solid var(--border)', borderRadius: 6,
                fontSize: 13, outline: 'none', color: 'var(--text)',
                transition: 'border-color .15s',
              }}
              onFocus={(e) => (e.target.style.borderColor = 'var(--primary)')}
              onBlur={(e) => (e.target.style.borderColor = 'var(--border)')}
            />
          </div>

          {error && (
            <div style={{
              background: '#fef2f2', border: '1px solid #fecaca',
              color: 'var(--danger)', borderRadius: 6,
              padding: '8px 12px', fontSize: 12,
            }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop: 4,
              background: loading ? 'var(--text-muted)' : 'var(--primary)',
              color: '#fff', border: 'none', borderRadius: 6,
              padding: '10px', fontSize: 13, fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'background .15s',
            }}
          >
            {loading ? 'Вход…' : 'Войти'}
          </button>
        </form>

        <div style={{ marginTop: 20, padding: '12px', background: 'var(--bg)', borderRadius: 6, fontSize: 11, color: 'var(--text-muted)' }}>
          <strong>Тест:</strong> admin@maximaconsult.ru / admin123
        </div>
      </div>
    </div>
  )
}
