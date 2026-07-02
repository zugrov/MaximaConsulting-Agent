import { useState } from 'react'
import { useAuthStore } from '../store/authStore'

const PROVIDER_LABELS = {
  yandex: { icon: '☁️', name: 'Яндекс.Диск' },
  dropbox: { icon: '📦', name: 'Dropbox' },
  gdrive:  { icon: '🔵', name: 'Google Drive' },
  direct:  { icon: '🔗', name: 'Прямая ссылка' },
}

/**
 * CloudLinkInput
 * Вводит URL → резолвит через /api/cloud/resolve
 * Если папка — показывает список файлов с чекбоксами
 * При готовности вызывает onFilesReady(File[])
 */
export default function CloudLinkInput({ onFilesReady }) {
  const token = useAuthStore((s) => s.token)

  const [url, setUrl] = useState('')
  const [status, setStatus] = useState('idle') // idle | loading | folder | unsupported | error
  const [provider, setProvider] = useState('')
  const [folderFiles, setFolderFiles] = useState([])
  const [selected, setSelected] = useState(new Set())
  const [resolvedFile, setResolvedFile] = useState(null) // {name, download_url, provider}
  const [folderMeta, setFolderMeta] = useState({}) // {public_key, folder_url}
  const [errorMsg, setErrorMsg] = useState('')
  const [downloading, setDownloading] = useState(false)

  const apiCall = (path, body) =>
    fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    })

  const handleResolve = async () => {
    if (!url.trim()) return
    setStatus('loading')
    setErrorMsg('')
    setFolderFiles([])
    setSelected(new Set())
    setResolvedFile(null)

    try {
      const resp = await apiCall('/api/cloud/resolve', { url: url.trim() })
      const data = await resp.json()
      if (!resp.ok) throw new Error(data.detail || 'Ошибка разрешения ссылки')

      setProvider(data.provider)

      if (data.type === 'file') {
        setResolvedFile(data)
        setStatus('file_ready')
      } else if (data.type === 'folder') {
        setFolderFiles(data.files || [])
        setFolderMeta({
          public_key: data.public_key || '',
          folder_url: data.folder_url || url.trim(),
        })
        setSelected(new Set())
        setStatus('folder')
      } else if (data.type === 'folder_unsupported') {
        setStatus('unsupported')
        setErrorMsg(data.message || 'Папки этого провайдера не поддерживаются')
      }
    } catch (e) {
      setStatus('error')
      setErrorMsg(e.message)
    }
  }

  const toggleFile = (name) => {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(name) ? next.delete(name) : next.add(name)
      return next
    })
  }

  const handleDownloadSelected = async () => {
    if (selected.size === 0) return
    setDownloading(true)
    setErrorMsg('')

    const fileRefs = folderFiles
      .filter((f) => selected.has(f.name))
      .map((f) => ({
        name: f.name,
        url: f.url || '',
        provider,
        path: f.path || '',
        zip_path: f.zip_path || '',
        folder_url: f.folder_url || folderMeta.folder_url || '',
        public_key: folderMeta.public_key || '',
      }))

    try {
      const resp = await apiCall('/api/cloud/download', { files: fileRefs })
      const data = await resp.json()
      if (!resp.ok) throw new Error(data.detail || 'Ошибка загрузки')

      const jsFiles = data.files.map(({ name, content_b64 }) => {
        const binary = atob(content_b64)
        const bytes = new Uint8Array(binary.length)
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
        return new File([bytes], name)
      })
      onFilesReady(jsFiles)
      setStatus('done')
    } catch (e) {
      setErrorMsg(e.message)
    } finally {
      setDownloading(false)
    }
  }

  const handleDownloadFile = async () => {
    if (!resolvedFile) return
    setDownloading(true)
    setErrorMsg('')

    try {
      const resp = await apiCall('/api/cloud/download', {
        files: [{
          name: resolvedFile.name,
          url: resolvedFile.download_url,
          provider: resolvedFile.provider,
        }],
      })
      const data = await resp.json()
      if (!resp.ok) throw new Error(data.detail || 'Ошибка загрузки')

      const { name, content_b64 } = data.files[0]
      const binary = atob(content_b64)
      const bytes = new Uint8Array(binary.length)
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
      const jsFile = new File([bytes], name)
      onFilesReady([jsFile])
      setStatus('done')
    } catch (e) {
      setErrorMsg(e.message)
    } finally {
      setDownloading(false)
    }
  }

  const handleReset = () => {
    setUrl('')
    setStatus('idle')
    setProvider('')
    setFolderFiles([])
    setSelected(new Set())
    setResolvedFile(null)
    setErrorMsg('')
  }

  const providerInfo = PROVIDER_LABELS[provider] || {}

  return (
    <div>
      {/* Поле ввода */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleResolve()}
          placeholder="Вставьте ссылку Dropbox, Google Drive, Яндекс.Диск или прямую URL"
          style={{
            flex: 1, padding: '9px 12px',
            border: '1px solid var(--border)', borderRadius: 6,
            outline: 'none', fontSize: 13,
          }}
          disabled={status === 'loading' || downloading}
        />
        <button
          onClick={handleResolve}
          disabled={!url.trim() || status === 'loading' || downloading}
          style={{
            padding: '9px 18px', borderRadius: 6, border: 'none',
            background: (!url.trim() || status === 'loading') ? 'var(--text-muted)' : 'var(--primary)',
            color: '#fff', fontSize: 13, fontWeight: 600,
            cursor: (!url.trim() || status === 'loading') ? 'not-allowed' : 'pointer',
          }}
        >
          {status === 'loading' ? '…' : 'Загрузить'}
        </button>
        {status !== 'idle' && (
          <button
            onClick={handleReset}
            style={{ padding: '9px 12px', borderRadius: 6, border: '1px solid var(--border)', background: 'var(--bg)', fontSize: 13, cursor: 'pointer' }}
          >
            ✕
          </button>
        )}
      </div>

      {/* Провайдер */}
      {provider && (
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>
          {providerInfo.icon} {providerInfo.name}
        </div>
      )}

      {/* Ошибка */}
      {status === 'error' && errorMsg && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: 'var(--danger)', borderRadius: 6, padding: '8px 12px', fontSize: 12, marginBottom: 8 }}>
          {errorMsg}
        </div>
      )}

      {/* Файл готов */}
      {status === 'file_ready' && resolvedFile && (
        <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 8, padding: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 18 }}>📄</span>
            <span style={{ flex: 1, fontSize: 13, fontWeight: 500 }}>{resolvedFile.name}</span>
            <button
              onClick={handleDownloadFile}
              disabled={downloading}
              style={{
                padding: '7px 16px', borderRadius: 6, border: 'none',
                background: downloading ? 'var(--text-muted)' : 'var(--primary)',
                color: '#fff', fontSize: 12, fontWeight: 600, cursor: downloading ? 'not-allowed' : 'pointer',
              }}
            >
              {downloading ? 'Загружаю…' : 'Добавить в анализ'}
            </button>
          </div>
        </div>
      )}

      {/* Папка — список файлов */}
      {status === 'folder' && (
        <div style={{ border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
          <div style={{ padding: '10px 14px', background: 'var(--bg)', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, fontWeight: 600 }}>
              Файлы в папке ({folderFiles.length})
            </span>
            <label style={{ fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
              <input
                type="checkbox"
                checked={selected.size === folderFiles.length && folderFiles.length > 0}
                onChange={(e) => setSelected(e.target.checked ? new Set(folderFiles.map((f) => f.name)) : new Set())}
              />
              Выбрать все
            </label>
          </div>
          <div style={{ maxHeight: 240, overflowY: 'auto' }}>
            {folderFiles.length === 0 ? (
              <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                Нет поддерживаемых файлов в папке
              </div>
            ) : folderFiles.map((f) => (
              <label key={f.name} style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '8px 14px', cursor: 'pointer',
                borderBottom: '1px solid var(--border)',
                background: selected.has(f.name) ? 'var(--primary-lt)' : 'transparent',
              }}>
                <input
                  type="checkbox"
                  checked={selected.has(f.name)}
                  onChange={() => toggleFile(f.name)}
                />
                <span style={{ fontSize: 14 }}>📄</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>{f.name}</div>
                  {f.size > 0 && (
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      {(f.size / 1024).toFixed(0)} KB
                    </div>
                  )}
                </div>
              </label>
            ))}
          </div>
          <div style={{ padding: '10px 14px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'flex-end' }}>
            <button
              onClick={handleDownloadSelected}
              disabled={selected.size === 0 || downloading}
              style={{
                padding: '8px 18px', borderRadius: 6, border: 'none',
                background: (selected.size === 0 || downloading) ? 'var(--text-muted)' : 'var(--primary)',
                color: '#fff', fontSize: 12, fontWeight: 600,
                cursor: (selected.size === 0 || downloading) ? 'not-allowed' : 'pointer',
              }}
            >
              {downloading ? 'Загружаю…' : `Добавить выбранные (${selected.size})`}
            </button>
          </div>
        </div>
      )}

      {/* Не поддерживается */}
      {status === 'unsupported' && (
        <div style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 6, padding: '10px 14px', fontSize: 12 }}>
          ⚠️ {errorMsg}
        </div>
      )}

      {/* Файлы добавлены */}
      {status === 'done' && (
        <div style={{ background: '#f0fdf4', border: '1px solid #86efac', borderRadius: 6, padding: '10px 14px', fontSize: 12, color: '#166534' }}>
          ✅ Файлы добавлены в анализ. <button onClick={handleReset} style={{ background: 'none', border: 'none', color: 'var(--primary)', cursor: 'pointer', fontSize: 12, padding: 0 }}>Добавить ещё</button>
        </div>
      )}
    </div>
  )
}
