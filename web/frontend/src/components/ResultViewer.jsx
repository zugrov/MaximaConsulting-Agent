import { useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useAuthStore } from '../store/authStore'

export default function ResultViewer({ content, streaming, serviceName, clientName, onReset }) {
  const token = useAuthStore((s) => s.token)
  const resultRef = useRef(null)

  const handleSave = async () => {
    if (!content) return
    try {
      await fetch('/api/reports', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, client_name: clientName, service_name: serviceName }),
      })
      alert('Отчёт сохранён в историю')
    } catch {
      alert('Ошибка при сохранении')
    }
  }

  const handleDownloadPDF = async () => {
    const { jsPDF } = await import('jspdf')
    const { default: html2canvas } = await import('html2canvas')
    if (!resultRef.current) return
    const canvas = await html2canvas(resultRef.current, { scale: 2, useCORS: true })
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
    const filename = `${clientName || 'report'}_${serviceName || 'analysis'}.pdf`
      .replace(/[^a-zA-Z0-9_\-а-яА-Я.]/g, '_')
    pdf.save(filename)
  }

  const handleDownloadMd = () => {
    const blob = new Blob([content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${clientName || 'report'}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div style={{ background: 'var(--bg-white)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '14px 20px', borderBottom: '1px solid var(--border)', background: 'var(--bg)',
      }}>
        <div>
          <div style={{ fontFamily: 'var(--font-head)', fontWeight: 700, fontSize: 13 }}>
            {serviceName} — {clientName}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
            {streaming ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{
                  display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
                  background: 'var(--teal)', animation: 'blink 1s step-end infinite',
                }} />
                Генерирую отчёт…
              </span>
            ) : 'Готово'}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {!streaming && content && (
            <>
              <Btn onClick={handleDownloadMd}>⬇ MD</Btn>
              <Btn onClick={handleDownloadPDF}>⬇ PDF</Btn>
              <Btn onClick={handleSave} teal>💾 Сохранить</Btn>
            </>
          )}
          <Btn onClick={onReset}>+ Новый</Btn>
        </div>
      </div>

      {/* Body */}
      <div ref={resultRef} style={{ padding: 24 }}>
        <div className="md-result">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {content}
          </ReactMarkdown>
        </div>
        {streaming && (
          <span style={{
            display: 'inline-block', width: 2, height: 14,
            background: 'var(--primary)', animation: 'blink 1s step-end infinite',
            marginLeft: 2, verticalAlign: 'middle',
          }} />
        )}
      </div>
    </div>
  )
}

function Btn({ children, onClick, teal }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 5,
        padding: '4px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600,
        cursor: 'pointer', border: 'none', transition: 'all .12s',
        background: teal ? 'var(--teal)' : 'var(--bg-white)',
        color: teal ? '#fff' : 'var(--text)',
        ...(teal ? {} : { border: '1px solid var(--border)' }),
      }}
    >
      {children}
    </button>
  )
}
