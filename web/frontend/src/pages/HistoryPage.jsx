import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useAuthStore } from '../store/authStore'

const TAG_COLORS = {
  'НДС': { bg: '#e8f0fb', color: '#1B61A6' },
  'Диагностика': { bg: '#e6f7f6', color: '#0D9488' },
  'Налоги': { bg: '#fef3c7', color: '#b45309' },
  'Учёт': { bg: '#f3e8ff', color: '#7c3aed' },
  'Модель': { bg: '#fce7f3', color: '#be185d' },
}

function guessTag(service) {
  if (!service) return ''
  if (/НДС/i.test(service)) return 'НДС'
  if (/диагност/i.test(service)) return 'Диагностика'
  if (/налог/i.test(service)) return 'Налоги'
  if (/учёт/i.test(service)) return 'Учёт'
  if (/модель/i.test(service)) return 'Модель'
  return ''
}

export default function HistoryPage() {
  const token = useAuthStore((s) => s.token)
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const [content, setContent] = useState('')
  const [loadingReport, setLoadingReport] = useState(false)
  const [clientFilter, setClientFilter] = useState('')
  const [serviceFilter, setServiceFilter] = useState('')
  const contentRef = useRef(null)

  useEffect(() => {
    fetch('/api/reports', { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.json())
      .then(setReports)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [token])

  const openReport = async (filename) => {
    setSelected(filename)
    setLoadingReport(true)
    try {
      const r = await fetch(`/api/reports/${filename}`, { headers: { Authorization: `Bearer ${token}` } })
      const data = await r.json()
      setContent(data.content)
    } catch {
      setContent('Ошибка загрузки отчёта')
    } finally {
      setLoadingReport(false)
    }
  }

  const handleDownloadMd = async () => {
    if (!selected) return
    try {
      const r = await fetch(`/api/reports/${selected}/download`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = selected
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      alert(`Ошибка скачивания: ${e.message}`)
    }
  }

  const handleDownloadPDF = async () => {
    if (!contentRef.current) return
    try {
      const { jsPDF } = await import('jspdf')
      const { default: html2canvas } = await import('html2canvas')
      const canvas = await html2canvas(contentRef.current, { scale: 2, useCORS: true })
      const imgData = canvas.toDataURL('image/png')
      const pdf = new jsPDF({ orientation: 'p', unit: 'mm', format: 'a4' })
      const pageWidth = pdf.internal.pageSize.getWidth()
      const pageHeight = pdf.internal.pageSize.getHeight()
      const margin = 10
      const imgWidth = pageWidth - margin * 2
      const imgHeight = (canvas.height * imgWidth) / canvas.width
      let renderedHeight = 0
      pdf.addImage(imgData, 'PNG', margin, margin, imgWidth, imgHeight)
      renderedHeight += pageHeight - margin
      while (renderedHeight < imgHeight) {
        pdf.addPage()
        pdf.addImage(imgData, 'PNG', margin, -(renderedHeight - margin), imgWidth, imgHeight)
        renderedHeight += pageHeight
      }
      const filename = selected.replace(/\.md$/, '') + '.pdf'
      pdf.save(filename)
    } catch (e) {
      alert(`Ошибка создания PDF: ${e.message}`)
    }
  }

  // уникальные значения для фильтров
  const uniqueClients = [...new Set(reports.map((r) => r.client).filter(Boolean))].sort()
  const uniqueServices = [...new Set(reports.map((r) => r.service).filter(Boolean))].sort()

  const filteredReports = reports.filter((r) => {
    if (clientFilter && r.client !== clientFilter) return false
    if (serviceFilter && r.service !== serviceFilter) return false
    return true
  })

  const selectStyle = {
    padding: '6px 10px', border: '1px solid var(--border)', borderRadius: 6,
    fontSize: 12, background: 'var(--bg-white)', color: 'var(--text)',
    outline: 'none', cursor: 'pointer',
  }

  if (selected) {
    const reportMeta = reports.find((r) => r.filename === selected)
    return (
      <div>
        <button
          onClick={() => { setSelected(null); setContent('') }}
          style={{ marginBottom: 20, fontSize: 13, color: 'var(--primary)', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600 }}
        >
          ← Назад к списку
        </button>
        <div style={{ background: 'var(--bg-white)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
          <div style={{
            padding: '14px 20px', borderBottom: '1px solid var(--border)',
            background: 'var(--bg)', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <div>
              <div style={{ fontFamily: 'var(--font-head)', fontWeight: 700, fontSize: 13 }}>
                {reportMeta ? `${reportMeta.client} — ${reportMeta.service}` : selected}
              </div>
              {reportMeta && (
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                  {reportMeta.modified} · {reportMeta.size_kb} KB
                </div>
              )}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <Btn onClick={handleDownloadMd} disabled={loadingReport}>⬇ MD</Btn>
              <Btn onClick={handleDownloadPDF} disabled={loadingReport}>⬇ PDF</Btn>
            </div>
          </div>
          <div ref={contentRef} style={{ padding: 24 }}>
            {loadingReport ? (
              <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Загрузка…</div>
            ) : (
              <div className="md-result">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <h1 style={{ fontFamily: 'var(--font-head)', fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        История отчётов
      </h1>
      <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 20 }}>
        Последние 50 сохранённых отчётов
      </p>

      {/* Фильтры */}
      {!loading && reports.length > 0 && (
        <div style={{ display: 'flex', gap: 10, marginBottom: 16, alignItems: 'center' }}>
          <select
            value={clientFilter}
            onChange={(e) => setClientFilter(e.target.value)}
            style={selectStyle}
          >
            <option value="">Все клиенты</option>
            {uniqueClients.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <select
            value={serviceFilter}
            onChange={(e) => setServiceFilter(e.target.value)}
            style={selectStyle}
          >
            <option value="">Все услуги</option>
            {uniqueServices.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          {(clientFilter || serviceFilter) && (
            <button
              onClick={() => { setClientFilter(''); setServiceFilter('') }}
              style={{ fontSize: 12, color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}
            >
              × Сбросить
            </button>
          )}
          <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 'auto' }}>
            {filteredReports.length} из {reports.length}
          </span>
        </div>
      )}

      {loading ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>Загрузка…</div>
      ) : reports.length === 0 ? (
        <div style={{
          background: 'var(--bg-white)', border: '1px solid var(--border)', borderRadius: 10,
          padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13,
        }}>
          Отчётов пока нет. <Link to="/analysis" style={{ color: 'var(--primary)' }}>Создать первый →</Link>
        </div>
      ) : filteredReports.length === 0 ? (
        <div style={{
          background: 'var(--bg-white)', border: '1px solid var(--border)', borderRadius: 10,
          padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13,
        }}>
          Ничего не найдено по выбранным фильтрам.
        </div>
      ) : (
        <div style={{ background: 'var(--bg-white)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
          {filteredReports.map((r, i) => {
            const tag = guessTag(r.service)
            const tagStyle = TAG_COLORS[tag] || {}
            return (
              <div
                key={r.filename}
                style={{
                  display: 'flex', alignItems: 'center', gap: 14,
                  padding: '12px 16px',
                  borderBottom: i < filteredReports.length - 1 ? '1px solid var(--border)' : 'none',
                  cursor: 'pointer', transition: 'background .1s',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg)')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                onClick={() => openReport(r.filename)}
              >
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--teal)', flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{r.client} — {r.service}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                    {r.modified} · {r.size_kb} KB
                  </div>
                </div>
                {tag && (
                  <span style={{ borderRadius: 4, padding: '2px 7px', fontSize: 10, fontWeight: 600, ...tagStyle }}>
                    {tag}
                  </span>
                )}
                <button
                  onClick={(e) => { e.stopPropagation(); openReport(r.filename) }}
                  style={{
                    fontSize: 11, fontWeight: 600, padding: '4px 10px', borderRadius: 6,
                    border: '1px solid var(--border)', background: 'var(--bg-white)', cursor: 'pointer',
                  }}
                >
                  Открыть
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function Btn({ children, onClick, disabled }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 5,
        padding: '4px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600,
        cursor: disabled ? 'not-allowed' : 'pointer',
        border: '1px solid var(--border)',
        background: 'var(--bg-white)',
        color: disabled ? 'var(--text-muted)' : 'var(--text)',
        transition: 'all .12s',
      }}
    >
      {children}
    </button>
  )
}
