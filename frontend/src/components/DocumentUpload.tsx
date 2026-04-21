import { useState, useRef } from 'react'
import { Upload, CheckCircle, FileText } from 'lucide-react'
import { uploadStatement } from '../api/client'
import type { DocumentUploadResponse } from '../types'

interface Props { clientId: string }

export default function DocumentUpload({ clientId }: Props) {
  const [result, setResult] = useState<DocumentUploadResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = async (file: File) => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await uploadStatement(clientId, file)
      setResult(res)
    } catch {
      setError('Upload failed. Is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <div className="flex items-center gap-2 mb-4">
        <FileText size={18} className="text-teal-500" />
        <h3 className="text-sm font-semibold text-gray-700">Upload Bank Statement</h3>
      </div>

      <div
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors
          ${dragging ? 'border-teal-400 bg-teal-50' : 'border-gray-200 hover:border-teal-300 hover:bg-gray-50'}`}
      >
        <Upload size={24} className={`mx-auto mb-2 ${dragging ? 'text-teal-500' : 'text-gray-400'}`} />
        <p className="text-sm text-gray-500">
          Drag & drop a PDF / image, or <span className="text-teal-600 font-medium">browse</span>
        </p>
        <p className="text-xs text-gray-400 mt-1">Processed by Azure Document Intelligence</p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg"
          className="hidden"
          onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])}
        />
      </div>

      {loading && (
        <div className="mt-4 flex items-center gap-2 text-sm text-gray-500">
          <svg className="animate-spin h-4 w-4 text-teal-500" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
          Extracting transactions…
        </div>
      )}

      {error && <p className="mt-3 text-sm text-red-500">{error}</p>}

      {result && (
        <div className="mt-4 bg-emerald-50 border border-emerald-200 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <CheckCircle size={15} className="text-emerald-600" />
            <span className="text-sm font-medium text-emerald-700">{result.filename}</span>
          </div>
          <p className="text-xs text-emerald-600">{result.summary}</p>
          <p className="text-xs text-emerald-500 mt-1">
            {result.extracted_transactions} transactions extracted and indexed for RAG
          </p>
        </div>
      )}
    </div>
  )
}
