import { useState, useRef, useEffect } from 'react'
import { Upload, FileText, RotateCcw, AlertTriangle } from 'lucide-react'
import { uploadStatement, fetchLastUpload, undoLastUpload } from '../api/client'
import type { DocumentUploadResponse } from '../types'

interface Props {
  clientId: string
  onUploadComplete: (result: DocumentUploadResponse) => void
  onUndoComplete: () => void
}

const STEPS = [
  'Uploading document…',
  'Extracting transactions with Azure Document Intelligence…',
  'Updating portfolio database…',
  'Finalising changes…',
]

export default function DocumentUpload({ clientId, onUploadComplete, onUndoComplete }: Props) {
  const [loading, setLoading] = useState(false)
  const [undoing, setUndoing] = useState(false)
  const [stepIndex, setStepIndex] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const [lastUpload, setLastUpload] = useState<{ filename: string; uploaded_at: string } | null>(null)
  const [confirmUndo, setConfirmUndo] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const stepTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    fetchLastUpload(clientId).then(setLastUpload).catch(() => setLastUpload(null))
    setError(null)
    setConfirmUndo(false)
  }, [clientId])

  useEffect(() => {
    return () => { if (stepTimer.current) clearInterval(stepTimer.current) }
  }, [])

  const startStepAnimation = () => {
    setStepIndex(0)
    stepTimer.current = setInterval(() => {
      setStepIndex(i => Math.min(i + 1, STEPS.length - 1))
    }, 2200)
  }

  const stopStepAnimation = () => {
    if (stepTimer.current) {
      clearInterval(stepTimer.current)
      stepTimer.current = null
    }
  }

  const handleFile = async (file: File) => {
    setLoading(true)
    setError(null)
    setConfirmUndo(false)
    startStepAnimation()
    try {
      const res = await uploadStatement(clientId, file)
      setLastUpload({ filename: res.filename, uploaded_at: new Date().toISOString() })
      onUploadComplete(res)
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (err?.response?.status === 409) {
        setError(detail ?? 'This document has already been uploaded.')
      } else {
        setError('Upload failed. Is the backend running?')
      }
    } finally {
      stopStepAnimation()
      setLoading(false)
      setStepIndex(0)
    }
  }

  const handleUndo = async () => {
    setUndoing(true)
    setError(null)
    setConfirmUndo(false)
    try {
      await undoLastUpload(clientId)
      setLastUpload(null)
      onUndoComplete()
    } catch {
      setError('Undo failed. Please try again.')
    } finally {
      setUndoing(false)
    }
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const busy = loading || undoing

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
        onClick={() => !busy && inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-6 text-center transition-colors
          ${busy ? 'cursor-not-allowed opacity-60 border-gray-200' :
            dragging ? 'border-teal-400 bg-teal-50 cursor-pointer' :
            'border-gray-200 hover:border-teal-300 hover:bg-gray-50 cursor-pointer'}`}
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
        <div className="mt-4 space-y-2">
          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-teal-500 rounded-full transition-all duration-[2000ms] ease-in-out"
              style={{ width: `${((stepIndex + 1) / STEPS.length) * 100}%` }}
            />
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <svg className="animate-spin h-4 w-4 text-teal-500 flex-shrink-0" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
            </svg>
            <span>{STEPS[stepIndex]}</span>
          </div>
          <div className="flex gap-1.5 pl-6">
            {STEPS.map((_, i) => (
              <div key={i} className={`h-1.5 w-1.5 rounded-full transition-colors duration-300
                ${i <= stepIndex ? 'bg-teal-500' : 'bg-gray-200'}`} />
            ))}
          </div>
        </div>
      )}

      {error && <p className="mt-3 text-sm text-red-500">{error}</p>}

      {/* Undo last upload */}
      {lastUpload && !busy && (
        <div className="mt-4 border border-amber-100 bg-amber-50 rounded-lg p-3">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-start gap-2 min-w-0">
              <RotateCcw size={14} className="text-amber-500 flex-shrink-0 mt-0.5" />
              <div className="min-w-0">
                <p className="text-xs font-medium text-amber-800 truncate">
                  Last upload: {lastUpload.filename}
                </p>
                <p className="text-xs text-amber-600 mt-0.5">
                  {new Date(lastUpload.uploaded_at).toLocaleString()}
                </p>
              </div>
            </div>
            {!confirmUndo && (
              <button
                onClick={() => setConfirmUndo(true)}
                className="text-xs text-amber-700 hover:text-amber-900 font-medium flex-shrink-0 underline underline-offset-2"
              >
                Undo
              </button>
            )}
          </div>

          {confirmUndo && (
            <div className="mt-2 pt-2 border-t border-amber-200">
              <div className="flex items-center gap-1.5 text-xs text-amber-800 mb-2">
                <AlertTriangle size={12} />
                This will revert all DB changes from this upload.
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleUndo}
                  disabled={undoing}
                  className="flex-1 bg-amber-600 hover:bg-amber-700 text-white text-xs font-medium rounded-md py-1.5 transition-colors disabled:opacity-50"
                >
                  {undoing ? 'Reverting…' : 'Yes, undo'}
                </button>
                <button
                  onClick={() => setConfirmUndo(false)}
                  className="flex-1 bg-white border border-amber-200 text-amber-700 text-xs font-medium rounded-md py-1.5 hover:bg-amber-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
