import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

const STATUS_LABELS = {
  lead:    { label: 'Лид',     color: '#f59e0b', bg: '#fffbeb' },
  project: { label: 'Проект',  color: '#2563eb', bg: '#eff6ff' },
  closed:  { label: 'Закрыт', color: '#6b7280', bg: '#f3f4f6' },
}

const SERVICES = [
  { code: '1', name: 'Финансовая диагностика' },
  { code: '2', name: 'НДС-аудит 2026' },
  { code: '3', name: 'Управленческий учёт' },
  { code: '4', name: 'Финансовая модель' },
  { code: '5', name: 'Налоговая оптимизация' },
  { code: '6', name: 'CFO-light' },
  { code: '7', name: 'Квалификация лида' },
  { code: '8', name: 'Полный цикл' },
]

const EMPTY_FORM = {
  name: '', contact: '', cloud_url: '',
  status: 'lead', amount: '', services: [], notes: '',
}

export default function ClientsPage() {
  const token = useAuthStore((s) => s.token)
  const user = useAuthStore((s) => s.user)
  const canEdit = user?.role === 'admin' || user?.role === 'analyst'
  const navigate = useNavigate()

  const [clients, setClients] = useState([])
  const [loading, setLoading] = useState(true)
  const [filterStatus, setFilterStatus] = useState('all')
  const [search, setSearch] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')

  const authHeaders = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

  const loadClients = async () => {
    setLoading(true)
    try {
      const resp = await fetch('/api/clients', { headers: authHeaders })
      if (!resp.ok) throw new Error()
      setClients(await resp.json())
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadClients() }, [])

  const filtered = clients.filter((c) => {
    if (filterStatus !== 'all' && c.status !== filterStatus) return false
    if (search && !c.name.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const openCreate = () => {
    setForm(EMPTY_FORM)
    setFormError('')
    setShowModal(true)
  }

  const handleSave = async () => {
    if (!form.name.trim()) { setFormError('Укажите название клиента'); return }
    setSaving(true)
    setFormError('')
    try {
      const body = {
        ...form,
        amount: form.amount ? parseFloat(form.amount) : null,
      }
      const resp = await fetch('/api/clients', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify(body),
      })
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}))
        throw new Error(data.detail || 'Ошибка сохранения')
      }
      setShowModal(false)
      loadClients()
    } catch (e) {
      setFormError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (e, id) => {
    e.stopPropagation()
    if (!confirm('Удалить клиента?')) return
    await fetch(`/api/clients/${id}`, { method: 'DELETE', headers: authHeaders })
    setClients((prev) => prev.filter((c) => c.id !== id))
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-head)', fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
            Клиенты
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
            {clients.length} клиент{clients.length === 1 ? '' : clients.length < 5 ? 'а' : 'ов'}
          </p>
        </div>
        {canEdit && (
          <button
            onClick={openCreate}
            style={{
              background: 'var(--primary)', color: '#fff', border: 'none',
              borderRadius: 6, padding: '9px 18px', fontSize: 13, fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            + Добавить клиента
          </button>
        )}
      </div>

      {/* Фильтры */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Поиск по названию…"
          style={{ padding: '7px 12px', border: '1px solid var(--border)', borderRadius: 6, fontSize: 13, outline: 'none', minWidth: 200 }}
        />
        {['all', 'lead', 'project', 'closed'].map((s) => (
          <button
            key={s}
            onClick={() => setFilterStatus(s)}
            style={{
              padding: '7px 14px', borderRadius: 6, border: `1px solid ${filterStatus === s ? 'var(--primary)' : 'var(--border)'}`,
              background: filterStatus === s ? 'var(--primary-lt)' : 'var(--bg-white)',
              color: filterStatus === s ? 'var(--primary)' : 'var(--text-muted)',
              fontSize: 12, fontWeight: 600, cursor: 'pointer',
            }}
          >
            {s === 'all' ? 'Все' : STATUS_LABELS[s]?.label}
          </button>
        ))}
      </div>

      {/* Таблица */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>Загрузка…</div>
      ) : filtered.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
          {search || filterStatus !== 'all' ? 'Ничего не найдено' : 'Клиентов пока нет'}
        </div>
      ) : (
        <div style={{ background: 'var(--bg-white)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg)' }}>
                {['Клиент', 'Статус', 'Сумма', 'Услуги', 'Контакт', ''].map((h) => (
                  <th key={h} style={{ padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.04em' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => {
                const st = STATUS_LABELS[c.status] || STATUS_LABELS.lead
                const svcNames = (c.services || [])
                  .map((code) => SERVICES.find((s) => s.code === code)?.name)
                  .filter(Boolean)
                return (
                  <tr
                    key={c.id}
                    onClick={() => navigate(`/clients/${c.id}`)}
                    style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer', transition: 'background .1s' }}
                    onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg)'}
                    onMouseLeave={(e) => e.currentTarget.style.background = ''}
                  >
                    <td style={{ padding: '12px 16px' }}>
                      <div style={{ fontWeight: 600, fontSize: 13 }}>{c.name}</div>
                      {c.notes && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2, maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.notes}</div>}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{ background: st.bg, color: st.color, borderRadius: 4, padding: '3px 8px', fontSize: 11, fontWeight: 600 }}>
                        {st.label}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: 13 }}>
                      {c.amount ? `${Number(c.amount).toLocaleString('ru-RU')} ₽` : '—'}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                        {svcNames.slice(0, 2).map((n) => (
                          <span key={n} style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 4, padding: '2px 6px', fontSize: 10 }}>{n}</span>
                        ))}
                        {svcNames.length > 2 && (
                          <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>+{svcNames.length - 2}</span>
                        )}
                      </div>
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text-muted)' }}>
                      {c.contact || '—'}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      {canEdit && (
                        <button
                          onClick={(e) => handleDelete(e, c.id)}
                          style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: 14, padding: '2px 6px' }}
                          title="Удалить"
                        >
                          🗑
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Модальное окно создания */}
      {showModal && (
        <Modal title="Новый клиент" onClose={() => setShowModal(false)}>
          <ClientForm form={form} setForm={setForm} />
          {formError && (
            <div style={{ marginTop: 12, color: 'var(--danger)', fontSize: 12 }}>{formError}</div>
          )}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 20 }}>
            <button
              onClick={() => setShowModal(false)}
              style={{ padding: '8px 16px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg)', fontSize: 13, cursor: 'pointer' }}
            >
              Отмена
            </button>
            <button
              onClick={handleSave}
              disabled={saving}
              style={{ padding: '8px 18px', borderRadius: 6, border: 'none', background: saving ? 'var(--text-muted)' : 'var(--primary)', color: '#fff', fontSize: 13, fontWeight: 600, cursor: saving ? 'not-allowed' : 'pointer' }}
            >
              {saving ? 'Сохраняю…' : 'Создать'}
            </button>
          </div>
        </Modal>
      )}
    </div>
  )
}

export function ClientForm({ form, setForm }) {
  const set = (field) => (e) => setForm((prev) => ({ ...prev, [field]: e.target.value }))
  const toggleService = (code) => {
    setForm((prev) => ({
      ...prev,
      services: prev.services.includes(code)
        ? prev.services.filter((c) => c !== code)
        : [...prev.services, code],
    }))
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <Field label="Название *">
        <input value={form.name} onChange={set('name')} placeholder="ООО Ромашка" style={inputStyle} />
      </Field>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <Field label="Контакт">
          <input value={form.contact} onChange={set('contact')} placeholder="+7 999 000 00 00" style={inputStyle} />
        </Field>
        <Field label="Статус">
          <select value={form.status} onChange={set('status')} style={inputStyle}>
            <option value="lead">Лид</option>
            <option value="project">Проект</option>
            <option value="closed">Закрыт</option>
          </select>
        </Field>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <Field label="Сумма (₽)">
          <input value={form.amount} onChange={set('amount')} placeholder="150000" type="number" style={inputStyle} />
        </Field>
        <Field label="Ссылка на облако">
          <input value={form.cloud_url} onChange={set('cloud_url')} placeholder="https://disk.yandex.ru/..." style={inputStyle} />
        </Field>
      </div>
      <Field label="Услуги">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {SERVICES.map((svc) => (
            <label key={svc.code} style={{ display: 'flex', alignItems: 'center', gap: 5, cursor: 'pointer', fontSize: 12 }}>
              <input
                type="checkbox"
                checked={form.services.includes(svc.code)}
                onChange={() => toggleService(svc.code)}
              />
              {svc.name}
            </label>
          ))}
        </div>
      </Field>
      <Field label="Заметки">
        <textarea
          value={form.notes}
          onChange={set('notes')}
          placeholder="Любые заметки…"
          rows={3}
          style={{ ...inputStyle, resize: 'vertical' }}
        />
      </Field>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 5, textTransform: 'uppercase', letterSpacing: '.04em' }}>
        {label}
      </label>
      {children}
    </div>
  )
}

export function Modal({ title, onClose, children }) {
  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200 }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div style={{ background: 'var(--bg-white)', borderRadius: 12, padding: 28, width: 560, maxWidth: '90vw', maxHeight: '85vh', overflowY: 'auto', boxShadow: '0 20px 60px rgba(0,0,0,.15)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
          <h2 style={{ fontFamily: 'var(--font-head)', fontSize: 16, fontWeight: 700, margin: 0 }}>{title}</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', color: 'var(--text-muted)', lineHeight: 1 }}>×</button>
        </div>
        {children}
      </div>
    </div>
  )
}

const inputStyle = {
  width: '100%', padding: '8px 12px', border: '1px solid var(--border)',
  borderRadius: 6, fontSize: 13, outline: 'none', boxSizing: 'border-box',
}
