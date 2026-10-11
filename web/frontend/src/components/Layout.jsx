import { useState } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import PasswordModal from './PasswordModal'

const navItems = [
  { to: '/analysis', icon: '📄', label: 'Новый анализ' },
  { to: '/history',  icon: '🕓', label: 'История отчётов' },
  { to: '/clients',  icon: '👥', label: 'Клиенты' },
]

export default function Layout() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const navigate = useNavigate()
  const [isPasswordOpen, setIsPasswordOpen] = useState(false)
  const [isNavOpen, setIsNavOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const initials = user?.name
    ? user.name.split(' ').map((w) => w[0]).slice(0, 2).join('')
    : '??'

  const closeNav = () => setIsNavOpen(false)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <header className="app-header">
        <button
          type="button"
          className="nav-toggle"
          aria-label="Меню"
          aria-expanded={isNavOpen}
          onClick={() => setIsNavOpen((open) => !open)}
        >
          {isNavOpen ? '✕' : '☰'}
        </button>
        <span style={{ fontFamily: 'var(--font-head)', fontWeight: 700, fontSize: 16, color: '#fff' }}>
          maxima <span style={{ color: 'var(--teal)' }}>consulting</span>
        </span>
        <span className="header-badge" style={{ fontSize: 11, color: '#666', background: '#2a2a29', padding: '2px 8px', borderRadius: 4 }}>
          AI Agent · internal
        </span>
        <div style={{ flex: 1 }} />
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#ccc', fontSize: 13 }}>
            <span style={{
              background: 'rgba(13,148,136,.2)', color: 'var(--teal)',
              borderRadius: 4, padding: '2px 6px', fontSize: 11, fontWeight: 600,
            }}>{user.role}</span>
            <span className="header-user-name">{user.name}</span>
            <div style={{
              width: 28, height: 28, borderRadius: '50%', background: 'var(--primary)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#fff', fontSize: 11, fontWeight: 600,
            }}>{initials}</div>
          </div>
        )}
      </header>

      <div className="app-body">
        <div
          className={isNavOpen ? 'nav-backdrop is-open' : 'nav-backdrop'}
          onClick={closeNav}
        />
        <aside className={isNavOpen ? 'app-sidebar is-open' : 'app-sidebar'}>
          <div style={{ padding: '0 12px 4px', fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--text-muted)' }}>
            Анализ
          </div>
          {navItems.map(({ to, icon, label }) => (
            <NavLink key={to} to={to} onClick={closeNav} style={({ isActive }) => ({
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '8px 16px', fontSize: 13, fontWeight: 500,
              color: isActive ? 'var(--primary)' : 'var(--text-muted)',
              background: isActive ? 'var(--primary-lt)' : 'transparent',
              transition: 'all .12s',
              textDecoration: 'none',
            })}>
              <span>{icon}</span>
              <span>{label}</span>
            </NavLink>
          ))}

          {user?.role === 'admin' && (
            <>
              <div style={{ padding: '16px 12px 4px', fontSize: 10, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--text-muted)' }}>
                Управление
              </div>
              <NavLink to="/admin" onClick={closeNav} style={({ isActive }) => ({
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '8px 16px', fontSize: 13, fontWeight: 500,
                color: isActive ? 'var(--primary)' : 'var(--text-muted)',
                background: isActive ? 'var(--primary-lt)' : 'transparent',
                textDecoration: 'none',
              })}>
                <span>👥</span>
                <span>Пользователи</span>
              </NavLink>
            </>
          )}

          <div style={{ flex: 1 }} />
          <button
            onClick={() => setIsPasswordOpen(true)}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '8px 16px', fontSize: 13, fontWeight: 500,
              color: 'var(--text-muted)', background: 'none', border: 'none',
              cursor: 'pointer', width: '100%', textAlign: 'left',
            }}
          >
            <span>🔑</span>
            <span>Сменить пароль</span>
          </button>
          <button
            onClick={handleLogout}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '8px 16px', fontSize: 13, fontWeight: 500,
              color: '#ef4444', background: 'none', border: 'none',
              cursor: 'pointer', width: '100%', textAlign: 'left',
            }}
          >
            <span>↩</span>
            <span>Выйти</span>
          </button>
        </aside>

        {/* Main */}
        <main className="app-main">
          <Outlet />
        </main>
      </div>

      {isPasswordOpen && <PasswordModal onClose={() => setIsPasswordOpen(false)} />}
    </div>
  )
}
