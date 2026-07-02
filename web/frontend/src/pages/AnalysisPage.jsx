import { useState, useRef, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import ResultViewer from '../components/ResultViewer'
import CloudLinkInput from '../components/CloudLinkInput'

const SERVICES = [
  { code: '1', icon: '🔍', name: 'Финансовая диагностика', desc: 'P&L, маржа, cash flow, риски' },
  { code: '2', icon: '📊', name: 'НДС-аудит 2026',         desc: 'Выбор ставки, сценарии' },
  { code: '3', icon: '📈', name: 'Управленческий учёт',    desc: 'P&L, ДДС, KPI-дашборд' },
  { code: '4', icon: '💰', name: 'Финансовая модель',       desc: 'DCF, сценарии, NPV' },
  { code: '5', icon: '🛡',  name: 'Налоговая оптимизация', desc: 'Режимы, вычеты, риски' },
  { code: '6', icon: '👔', name: 'CFO-light',               desc: 'Подписное сопровождение' },
  { code: '7', icon: '🎯', name: 'Квалификация лида',       desc: 'BANT-скоринг + КП' },
  { code: '8', icon: '🔄', name: 'Полный цикл',             desc: 'Все услуги последовательно' },
]

const ALLOWED_EXT = ['.xlsx', '.xls', '.csv', '.json', '.txt', '.md', '.pdf', '.docx']

function isAllowedExt(filename) {
  const ext = '.' + filename.split('.').pop().toLowerCase()
  return ALLOWED_EXT.includes(ext)
}

export default function AnalysisPage() {
  const token = useAuthStore((s) => s.token)
  const user = useAuthStore((s) => s.user)
  const canAnalyze = user?.role === 'admin' || user?.role === 'analyst'
  const [searchParams] = useSearchParams()

  const [files, setFiles] = useState([])
  const [serviceCode, setServiceCode] = useState('1')
  const [clientName, setClientName] = useState('')
  const [context, setContext] = useState('')
  const [step, setStep] = useState(1)
  const [streaming, setStreaming] = useState(false)
  const [result, setResult] = useState('')
  const [error, setError] = useState('')
  const [dragging, setDragging] = useState(false)
  const [uploadTab, setUploadTab] = useState('local') // 'local' | 'cloud'
  const fileInputRef = useRef(null)
  const abortRef = useRef(null)

  // При переходе с карточки клиента (?clientId=N) — подгружаем данные клиента
  useEffect(() => {
    const clientId = searchParams.get('clientId')
    const clientNameParam = searchParams.get('clientName')
    const cloudUrl = searchParams.get('cloudUrl')

    if (clientNameParam) setClientName(decodeURIComponent(clientNameParam))
    if (cloudUrl) {
      // Переключить на вкладку «По ссылке» если есть cloudUrl
      setUploadTab('cloud')
    }
  }, [searchParams])

  const addFiles = (newFiles) => {
    const rejected = []
    const accepted = []
    for (const f of newFiles) {
      if (isAllowedExt(f.name)) {
        accepted.push(f)
      } else {
        rejected.push(f.name)
      }
    }
    if (rejected.length > 0) {
      setError(`Неподдерживаемый формат: ${rejected.join(', ')}. Допустимо: ${ALLOWED_EXT.join(', ')}`)
    } else {
      setError('')
    }
    if (accepted.length > 0) {
      setFiles((prev) => {
        const existingNames = new Set(prev.map((f) => f.name))
        const unique = accepted.filter((f) => !existingNames.has(f.name))
        const next = [...prev, ...unique]
        if (next.length > 0) setStep(2)
        return next
      })
    }
  }

  const removeFile = (index) => {
    setFiles((prev) => {
      const next = prev.filter((_, i) => i !== index)
      if (next.length === 0) setStep(1)
      return next
    })
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    addFiles(Array.from(e.dataTransfer.files))
  }

  const handleRunAnalysis = async () => {
    if (files.length === 0 || !serviceCode) return
    setStreaming(true)
    setResult('')
    setError('')
    setStep(3)

    const form = new FormData()
    files.forEach((f) => form.append('files', f))
    form.append('service_code', serviceCode)
    form.append('client_name', clientName || files[0].name)
    form.append('context', context)

    abortRef.current = new AbortController()

    try {
      const resp = await fetch('/api/analyze', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
        signal: abortRef.current.signal,
      })

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        throw new Error(err.detail || `HTTP ${resp.status}`)
      }

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let sseFinished = false

      while (!sseFinished) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const chunk = line.slice(6)
          if (chunk === '[DONE]') { setStreaming(false); sseFinished = true; break }
          if (chunk.startsWith('[ОШИБКА')) { setError(chunk); setStreaming(false); sseFinished = true; break }
          setResult((prev) => prev + chunk.replace(/\\n/g, '\n'))
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') setError(err.message)
    } finally {
      setStreaming(false)
    }
  }

  const handleReset = () => {
    abortRef.current?.abort()
    setFiles([])
    setResult('')
    setError('')
    setStreaming(false)
    setStep(1)
    setClientName('')
    setContext('')
  }

  const selectedService = SERVICES.find((s) => s.code === serviceCode)

  return (
    <div>
      <h1 style={{ fontFamily: 'var(--font-head)', fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        Новый анализ
      </h1>
      <p style={{ color: 'var(--text-muted)', fontSize: 13, marginBottom: 28 }}>
        Загрузите документы клиента, выберите услугу и получите отчёт
      </p>

      <Stepper step={step} />

      {/* Step 1 — Upload */}
      <Card
        title="📎 Документы клиента"
        badge={files.length > 0 ? `${files.length} файл${files.length > 1 ? 'а' : ''}` : null}
      >
        {/* Вкладки */}
        <div style={{ display: 'flex', gap: 0, marginBottom: 16, borderBottom: '1px solid var(--border)' }}>
          {[
            { key: 'local', label: '💻 С компьютера' },
            { key: 'cloud', label: '☁️ По ссылке' },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setUploadTab(key)}
              style={{
                padding: '7px 16px', border: 'none', cursor: 'pointer',
                background: 'transparent', fontSize: 13, fontWeight: 600,
                color: uploadTab === key ? 'var(--primary)' : 'var(--text-muted)',
                borderBottom: `2px solid ${uploadTab === key ? 'var(--primary)' : 'transparent'}`,
                marginBottom: -1,
              }}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Список добавленных файлов */}
        {files.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            {files.map((f, i) => (
              <div
                key={f.name + i}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  background: 'var(--bg)', border: '1px solid var(--border)',
                  borderRadius: 6, padding: '8px 12px', marginBottom: 6,
                }}
              >
                <span style={{ fontSize: 16 }}>📄</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{f.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                    {(f.size / 1024).toFixed(0)} KB
                  </div>
                </div>
                <button
                  onClick={() => removeFile(i)}
                  style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: 'var(--text-muted)', fontSize: 16, lineHeight: 1,
                    padding: '2px 6px', borderRadius: 4,
                  }}
                  title="Убрать файл"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Вкладка «С компьютера» */}
        {uploadTab === 'local' && (
          <>
            <div
              onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: `2px dashed ${dragging ? 'var(--primary)' : 'var(--border)'}`,
                background: dragging ? 'var(--primary-lt)' : 'var(--bg)',
                borderRadius: 8,
                padding: files.length > 0 ? '16px 24px' : '36px 24px',
                textAlign: 'center', cursor: 'pointer', transition: 'all .15s',
              }}
            >
              <div style={{ fontSize: files.length > 0 ? 22 : 32, marginBottom: 6 }}>
                {files.length > 0 ? '➕' : '📁'}
              </div>
              <div style={{ fontWeight: 600, fontSize: files.length > 0 ? 13 : 14, marginBottom: 4 }}>
                {files.length > 0 ? 'Добавить ещё файлы' : 'Перетащите файл или нажмите для выбора'}
              </div>
              {files.length === 0 && (
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
                  Максимум 100 000 символов после парсинга · Можно загрузить несколько
                </div>
              )}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, justifyContent: 'center' }}>
                {ALLOWED_EXT.map((e) => (
                  <span key={e} style={{
                    background: 'var(--bg-white)', border: '1px solid var(--border)',
                    borderRadius: 4, padding: '2px 8px', fontSize: 11,
                    fontFamily: 'var(--font-mono)', color: 'var(--text-muted)',
                  }}>{e}</span>
                ))}
              </div>
            </div>

            <input
              ref={fileInputRef}
              type="file"
              multiple
              hidden
              accept={ALLOWED_EXT.join(',')}
              onChange={(e) => {
                if (e.target.files?.length) addFiles(Array.from(e.target.files))
                e.target.value = ''
              }}
            />
          </>
        )}

        {/* Вкладка «По ссылке» */}
        {uploadTab === 'cloud' && (
          <CloudLinkInput onFilesReady={(jsFiles) => addFiles(jsFiles)} />
        )}

        {error && (
          <div style={{ marginTop: 10, background: '#fef2f2', border: '1px solid #fecaca', color: 'var(--danger)', borderRadius: 6, padding: '8px 12px', fontSize: 12 }}>
            {error}
          </div>
        )}
      </Card>

      {/* Step 2 — Service */}
      {step >= 2 && (
        <Card title="⚙️ Услуга">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
            {SERVICES.map((svc) => (
              <div
                key={svc.code}
                onClick={() => setServiceCode(svc.code)}
                style={{
                  border: `1.5px solid ${serviceCode === svc.code ? 'var(--primary)' : 'var(--border)'}`,
                  background: serviceCode === svc.code ? 'var(--primary-lt)' : 'var(--bg-white)',
                  borderRadius: 8, padding: '14px 12px', cursor: 'pointer', transition: 'all .15s',
                }}
              >
                <div style={{ fontSize: 20, marginBottom: 8 }}>{svc.icon}</div>
                <div style={{ fontWeight: 600, fontSize: 12, lineHeight: 1.3 }}>{svc.name}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>{svc.desc}</div>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 16, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 5 }}>
                Название клиента
              </label>
              <input
                value={clientName}
                onChange={(e) => setClientName(e.target.value)}
                placeholder="ООО Ромашка"
                style={{ width: '100%', padding: '9px 12px', border: '1px solid var(--border)', borderRadius: 6, outline: 'none' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 5 }}>
                Контекст (необязательно)
              </label>
              <input
                value={context}
                onChange={(e) => setContext(e.target.value)}
                placeholder="Например: переходит на НДС в Q3 2026"
                style={{ width: '100%', padding: '9px 12px', border: '1px solid var(--border)', borderRadius: 6, outline: 'none' }}
              />
            </div>
          </div>

          <div style={{ marginTop: 16, display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
            {!canAnalyze && (
              <span style={{ fontSize: 12, color: 'var(--text-muted)', alignSelf: 'center' }}>
                Роль viewer не может запускать анализ
              </span>
            )}
            <button
              onClick={handleRunAnalysis}
              disabled={!canAnalyze || streaming || files.length === 0}
              style={{
                background: (!canAnalyze || streaming || files.length === 0) ? 'var(--text-muted)' : 'var(--primary)',
                color: '#fff', border: 'none', borderRadius: 6,
                padding: '9px 22px', fontSize: 13, fontWeight: 600,
                cursor: (!canAnalyze || streaming || files.length === 0) ? 'not-allowed' : 'pointer',
              }}
            >
              {streaming ? 'Анализирую…' : 'Запустить анализ →'}
            </button>
          </div>
        </Card>
      )}

      {/* Step 3 — Result */}
      {step === 3 && (result || streaming) && (
        <ResultViewer
          content={result}
          streaming={streaming}
          serviceName={selectedService?.name || ''}
          clientName={clientName || files[0]?.name || ''}
          onReset={handleReset}
        />
      )}
    </div>
  )
}

function Stepper({ step }) {
  const steps = ['Документы', 'Услуга', 'Результат']
  return (
    <div style={{ display: 'flex', alignItems: 'center', marginBottom: 32 }}>
      {steps.map((label, i) => {
        const n = i + 1
        const done = step > n
        const active = step === n
        return (
          <div key={n} style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 500,
              color: active ? 'var(--primary)' : (done ? 'var(--success)' : 'var(--text-muted)') }}>
              <div style={{
                width: 24, height: 24, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 11, fontWeight: 700,
                background: done ? 'var(--success)' : (active ? 'var(--primary)' : 'var(--border)'),
                color: (done || active) ? '#fff' : 'var(--text-muted)',
              }}>
                {done ? '✓' : n}
              </div>
              {label}
            </div>
            {i < steps.length - 1 && (
              <div style={{ width: 60, height: 1, background: done ? 'var(--success)' : 'var(--border)', margin: '0 12px' }} />
            )}
          </div>
        )
      })}
    </div>
  )
}

function Card({ title, badge, children }) {
  return (
    <div style={{ background: 'var(--bg-white)', border: '1px solid var(--border)', borderRadius: 10, padding: 24, marginBottom: 20 }}>
      <div style={{ fontFamily: 'var(--font-head)', fontSize: 14, fontWeight: 700, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
        {title}
        {badge && (
          <span style={{ fontFamily: 'var(--font-sans)', fontSize: 10, fontWeight: 600, background: 'var(--teal-lt)', color: 'var(--teal)', borderRadius: 4, padding: '2px 6px' }}>
            {badge}
          </span>
        )}
      </div>
      {children}
    </div>
  )
}
