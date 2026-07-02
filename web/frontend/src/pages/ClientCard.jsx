import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { ClientForm, Modal } from './ClientsPage'

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

export default function ClientCard() {
  const { id } = useParams()
  const navigate = useNavigate()
  const token = useAuthStore((s) => s.token)
  const user = useAuthStore((s) => s.user)
  const canEdit = user?.role === 'admin' || user?.role === 'analyst'

  const [client, setClient] = useState(null)
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState('info') // 'info' | 'reports'
  const [showEdit, setShowEdit] = useState(false)
  const [form, setForm] = useState({})
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')

  const authHeaders = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [cResp, rResp] = await Promise.all([
          fetch(`/api/clients/${id}`, { headers: authHeaders }),
          fetch(`/api/clients/${id}/reports`, { headers: authHeaders }),
        ])
        if (!cResp.ok) { navigate('/clients'); return }
        setClient(await cResp.json())
        setReports(rResp.ok ? await rResp.json() : [])
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id])

  const openEdit = () => {
    setForm({
      name: client.name,
      contact: client.contact || '',
      cloud_url: client.cloud_url || '',
      status: client.status,
      amount: client.amount || '',
      services: client.services || [],
      notes: client.notes || '',
    })
    setFormError('')
    setShowEdit(true)
  }

  const handleSave = async () => {
    if (!form.name?.trim()) { setFormError('Укажите название'); return }
    setSaving(true)
    setFormError('')
    try {
      const body = { ...form, amount: form.amount ? parseFloat(form.amount) : null }
      const resp = await fetch(`/api/clients/${id}`, {
        method: 'PATCH',
        headers: authHeaders,
        body: JSON.stringify(body),
      })
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}))
        throw new Error(data.detail || 'Ошибка сохранения')
      }
      setClient(await resp.json())
      setShowEdit(false)
    } catch (e) {
      setFormError(e.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!confirm('Удалить клиента?')) return
    await fetch(`/api/clients/${id}`, { method: 'DELETE', headers: authHeaders })
    navigate('/clients')
  }

  const handleDownloadReport = async (filename) => {
    try {
      const resp = await fetch(`/api/reports/${filename}/download`, { headers: { Authorization: `Bearer ${token}` } })
      if (!resp.ok) return
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      // silent
    }
  }

  if (loading) return <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>Загрузка…</div>
  if (!client) return null

  const st = STATUS_LABELS[client.status] || STATUS_LABELS.lead
  const svcNames = (client.services || []).map((code) => SERVICES.find((s) => s.code === code)?.name).filter(Boolean)
  const analysisUrl = `/analysis?clientId=${id}&clientName=${encodeURIComponent(client.name)}${client.cloud_url ? `&cloudUrl=${encodeURIComponent(client.cloud_url)}` : ''}`

  return (
    <div>
      {/* Хлебные крошки */}
      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
        <Link to="/clients" style={{ color: 'var(--primary)', textDecoration: 'none' }}>Клиенты</Link>
        {' / '}{client.name}
      </div>

      {/* Заголовок */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24, gap: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ width: 44, height: 44, borderRadius: '50%', background: 'var(--primary-lt)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>
            🏢
          </div>
          <div>
            <h1 style={{ fontFamily: 'var(--font-head)', fontSize: 20, fontWeight: 700, margin: 0 }}>{client.name}</h1>
            <span style={{ background: st.bg, color: st.color, borderRadius: 4, padding: '3px 8px', fontSize: 11, fontWeight: 600 }}>
              {st.label}
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
          {canEdit && (
            <button
              onClick={openEdit}
              style={{ padding: '8px 14px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg)', fontSize: 13, cursor: 'pointer' }}
            >
              Редактировать
            </button>
          )}
          <Link
            to={analysisUrl}
            style={{
              padding: '8px 18px', borderRadius: 6, border: 'none',
              background: 'var(--primary)', color: '#fff',
              fontSize: 13, fontWeight: 600, textDecoration: 'none',
              display: 'inline-flex', alignItems: 'center', gap: 6,
            }}
          >
            🚀 Запустить анализ
          </Link>
          {canEdit && (
            <button
              onClick={handleDelete}
              style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #fecaca', background: '#fef2f2', color: '#ef4444', fontSize: 13, cursor: 'pointer' }}
            >
              🗑
            </button>
          )}
        </div>
      </div>

      {/* Вкладки */}
      <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid var(--border)', marginBottom: 20 }}>
        {[
          { key: 'info', label: 'Информация' },
          { key: 'reports', label: `Отчёты (${reports.length})` },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            style={{
              padding: '10px 20px', border: 'none', cursor: 'pointer',
              background: 'transparent', fontSize: 13, fontWeight: 600,
              color: tab === key ? 'var(--primary)' : 'var(--text-muted)',
              borderBottom: `2px solid ${tab === key ? 'var(--primary)' : 'transparent'}`,
              marginBottom: -1,
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Вкладка: информация */}
      {tab === 'info' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <InfoCard title="Основное">
            <InfoRow label="Контакт" value={client.contact || '—'} />
            <InfoRow label="Статус" value={st.label} />
            <InfoRow label="Сумма" value={client.amount ? `${Number(client.amount).toLocaleString('ru-RU')} ₽` : '—'} />
            <InfoRow
              label="Создан"
              value={client.created_at ? new Date(client.created_at).toLocaleDateString('ru-RU') : '—'}
            />
          </InfoCard>
          <InfoCard title="Услуги">
            {svcNames.length === 0 ? (
              <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>Не указаны</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {svcNames.map((n) => (
                  <div key={n} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
                    <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--primary)', flexShrink: 0 }} />
                    {n}
                  </div>
                ))}
              </div>
            )}
          </InfoCard>
          {client.cloud_url && (
            <InfoCard title="Облачное хранилище">
              <a href={client.cloud_url} target="_blank" rel="noreferrer" style={{ color: 'var(--primary)', fontSize: 13, wordBreak: 'break-all' }}>
                {client.cloud_url}
              </a>
            </InfoCard>
          )}
          {client.notes && (
            <InfoCard title="Заметки">
              <p style={{ fontSize: 13, margin: 0, lineHeight: 1.6, color: 'var(--text-muted)', whiteSpace: 'pre-wrap' }}>{client.notes}</p>
            </InfoCard>
          )}
        </div>
      )}

      {/* Вкладка: отчёты */}
      {tab === 'reports' && (
        reports.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 60, color: 'var(--text-muted)' }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>📭</div>
            Отчётов по этому клиенту нет.{' '}
            <Link to={analysisUrl} style={{ color: 'var(--primary)' }}>Запустить анализ →</Link>
          </div>
        ) : (
          <div style={{ background: 'var(--bg-white)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
            {reports.map((r) => (
              <div
                key={r.filename}
                style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', borderBottom: '1px solid var(--border)' }}
              >
                <span style={{ fontSize: 20 }}>📄</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{r.service || r.filename}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{r.modified} · {r.size_kb} KB</div>
                </div>
                <button
                  onClick={() => handleDownloadReport(r.filename)}
                  style={{ padding: '5px 12px', borderRadius: 5, border: '1px solid var(--border)', background: 'var(--bg)', fontSize: 12, cursor: 'pointer' }}
                >
                  ↓ MD
                </button>
              </div>
            ))}
          </div>
        )
      )}

      {/* Модальное окно редактирования */}
      {showEdit && (
        <Modal title="Редактировать клиента" onClose={() => setShowEdit(false)}>
          <ClientForm form={form} setForm={setForm} />
          {formError && <div style={{ marginTop: 12, color: 'var(--danger)', fontSize: 12 }}>{formError}</div>}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 20 }}>
            <button onClick={() => setShowEdit(false)} style={{ padding: '8px 16px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg)', fontSize: 13, cursor: 'pointer' }}>
              Отмена
            </button>
            <button onClick={handleSave} disabled={saving} style={{ padding: '8px 18px', borderRadius: 6, border: 'none', background: saving ? 'var(--text-muted)' : 'var(--primary)', color: '#fff', fontSize: 13, fontWeight: 600, cursor: saving ? 'not-allowed' : 'pointer' }}>
              {saving ? 'Сохраняю…' : 'Сохранить'}
            </button>
          </div>
        </Modal>
      )}
    </div>
  )
}

function InfoCard({ title, children }) {
  return (
    <div style={{ background: 'var(--bg-white)', border: '1px solid var(--border)', borderRadius: 10, padding: 20 }}>
      <div style={{ fontFamily: 'var(--font-head)', fontSize: 13, fontWeight: 700, marginBottom: 14, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.04em' }}>
        {title}
      </div>
      {children}
    </div>
  )
}

function InfoRow({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 8 }}>
      <span style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span style={{ fontWeight: 500 }}>{value}</span>
    </div>
  )
}
