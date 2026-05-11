import { useState, useRef, useEffect } from 'react'
import { Upload, FileText, RotateCcw, AlertTriangle, Database, Search, CheckCircle, XCircle, Clock } from 'lucide-react'
import { uploadStatement, fetchUploadHistory, undoLastUpload } from '../api/client'
import type { UploadHistoryEntry } from '../api/client'
import type { DocumentUploadResponse } from '../types'

interface Props {
  clientId: string
  onUploadComplete: (result: DocumentUploadResponse) => void
  onUndoComplete: () => void
}

interface FileStatus {
  name: string
  status: 'pending' | 'uploading' | 'done' | 'error'
  error?: string
  transactionCount?: number
  stepIndex: number
}

const STEPS = [
  'Uploading document…',
  'Extracting transactions with Azure Document Intelligence…',
  'Updating portfolio database…',
  'Saving to Microsoft Fabric Lakehouse…',
  'Finalising changes…',
]

export default function DocumentUpload({ clientId, onUploadComplete, onUndoComplete }: Props) {
  const [queue, setQueue] = useState<FileStatus[]>([])
  const [processing, setProcessing] = useState(false)
  const [undoing, setUndoing] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [uploadHistory, setUploadHistory] = useState<UploadHistoryEntry[]>([])
  const [confirmUndo, setConfirmUndo] = useState(false)
  const [indexerTriggered, setIndexerTriggered] = useState<boolean | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const stepTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    fetchUploadHistory(clientId).then(setUploadHistory).catch(() => setUploadHistory([]))
    setQueue([])
    setConfirmUndo(false)
    setIndexerTriggered(null)
  }, [clientId])

  useEffect(() => {
    return () => { if (stepTimer.current) clearInterval(stepTimer.current) }
  }, [])

  const handleFiles = async (files: File[]) => {
    if (files.length === 0) return
    setProcessing(true)
    setConfirmUndo(false)
    setIndexerTriggered(null)

    setQueue(files.map(f => ({ name: f.name, status: 'pending', stepIndex: 0 })))

    let lastIndexerTriggered: boolean | null = null

    for (let i = 0; i < files.length; i++) {
      setQueue(q => q.map((item, idx) =>
        idx === i ? { ...item, status: 'uploading', stepIndex: 0 } : item
      ))

      stepTimer.current = setInterval(() => {
        setQueue(q => q.map((item, idx) =>
          idx === i ? { ...item, stepIndex: Math.min(item.stepIndex + 1, STEPS.length - 1) } : item
        ))
      }, 2200)

      try {
        const res = await uploadStatement(clientId, files[i])

        clearInterval(stepTimer.current!)
        stepTimer.current = null

        setQueue(q => q.map((item, idx) =>
          idx === i ? { ...item, status: 'done', transactionCount: res.extracted_transactions } : item
        ))
        const newEntry: UploadHistoryEntry = {
          filename: res.filename,
          uploaded_at: new Date().toISOString(),
          lakehouse_path: res.lakehouse_path,
        }
        setUploadHistory(h => [newEntry, ...h])
        lastIndexerTriggered = res.indexer_triggered ?? false
        onUploadComplete(res)
      } catch (err: any) {
        clearInterval(stepTimer.current!)
        stepTimer.current = null

        const detail = err?.response?.data?.detail
        const errorMsg = err?.response?.status === 409
          ? (detail ?? 'Already uploaded.')
          : 'Upload failed.'

        setQueue(q => q.map((item, idx) =>
          idx === i ? { ...item, status: 'error', error: errorMsg } : item
        ))
      }
    }

    setIndexerTriggered(lastIndexerTriggered)
    setProcessing(false)
  }

  const handleUndo = async () => {
    setUndoing(true)
    setConfirmUndo(false)
    try {
      await undoLastUpload(clientId)
      setUploadHistory(h => h.slice(1))
      onUndoComplete()
    } catch {
      // undo failed
    } finally {
      setUndoing(false)
    }
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const files = Array.from(e.dataTransfer.files).filter(f =>
      /\.(pdf|png|jpg|jpeg)$/i.test(f.name)
    )
    if (files.length > 0) handleFiles(files)
  }

  const busy = processing || undoing

  const doneCount  = queue.filter(f => f.status === 'done').length
  const errorCount = queue.filter(f => f.status === 'error').length
  const allSettled = queue.length > 0 && queue.every(f => f.status === 'done' || f.status === 'error')
  const currentIdx = queue.findIndex(f => f.status === 'uploading')

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <div className="flex items-center gap-2 mb-4">
        <FileText size={18} className="text-teal-500" />
        <h3 className="text-sm font-semibold text-gray-700">Upload Bank Statements</h3>
      </div>

      {/* Drop zone */}
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
          Drag & drop PDFs / images, or <span className="text-teal-600 font-medium">browse</span>
        </p>
        <p className="text-xs text-gray-400 mt-1">Multiple files supported · Processed by Azure Document Intelligence</p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg"
          multiple
          className="hidden"
          onChange={e => {
            const files = Array.from(e.target.files ?? [])
            if (files.length > 0) handleFiles(files)
            e.target.value = ''
          }}
        />
      </div>

      {/* Upload queue */}
      {queue.length > 0 && (
        <div className="mt-4">
          {/* Overall progress summary */}
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-medium text-gray-500">
              {allSettled
                ? errorCount > 0
                  ? `${doneCount} uploaded, ${errorCount} failed`
                  : `${doneCount} ${doneCount === 1 ? 'file' : 'files'} uploaded`
                : currentIdx >= 0
                  ? `Processing ${currentIdx + 1} of ${queue.length}…`
                  : 'Starting…'}
            </span>
            {allSettled && (
              <span className={`text-xs font-medium ${errorCount > 0 ? 'text-amber-600' : 'text-emerald-600'}`}>
                {errorCount > 0 ? 'Partially complete' : 'All done'}
              </span>
            )}
          </div>

          {/* Overall progress bar */}
          {processing && (
            <div className="mb-3 h-1 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-teal-500 rounded-full transition-all duration-500 ease-out"
                style={{ width: `${((doneCount + errorCount) / queue.length) * 100}%` }}
              />
            </div>
          )}

          <div className="space-y-1.5">
            {queue.map((item, i) => (
              <div
                key={i}
                className={`rounded-lg border px-3 py-2 transition-colors duration-300 ${
                  item.status === 'done'      ? 'border-emerald-100 bg-emerald-50' :
                  item.status === 'error'     ? 'border-red-100 bg-red-50' :
                  item.status === 'uploading' ? 'border-teal-100 bg-teal-50' :
                                               'border-gray-100 bg-gray-50'
                }`}
              >
                <div className="flex items-center gap-2">
                  {item.status === 'pending' && (
                    <Clock size={13} className="text-gray-300 flex-shrink-0" />
                  )}
                  {item.status === 'uploading' && (
                    <svg className="animate-spin h-3.5 w-3.5 text-teal-500 flex-shrink-0" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                    </svg>
                  )}
                  {item.status === 'done'  && <CheckCircle size={13} className="text-emerald-500 flex-shrink-0" />}
                  {item.status === 'error' && <XCircle size={13} className="text-red-400 flex-shrink-0" />}

                  <span className={`text-xs font-medium truncate flex-1 ${
                    item.status === 'pending' ? 'text-gray-400' : 'text-gray-700'
                  }`}>
                    {item.name}
                  </span>

                  {item.status === 'done' && item.transactionCount !== undefined && (
                    <span className="text-xs text-emerald-600 flex-shrink-0 font-medium">
                      {item.transactionCount} txns
                    </span>
                  )}
                </div>

                {item.status === 'uploading' && (
                  <div className="mt-2 ml-5">
                    <div className="h-0.5 bg-teal-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-teal-400 rounded-full transition-all duration-[2000ms] ease-in-out"
                        style={{ width: `${((item.stepIndex + 1) / STEPS.length) * 100}%` }}
                      />
                    </div>
                    <p className="text-xs text-teal-500 mt-1">{STEPS[item.stepIndex]}</p>
                  </div>
                )}

                {item.status === 'error' && (
                  <p className="mt-1 ml-5 text-xs text-red-400">{item.error}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Search indexer status */}
      {indexerTriggered !== null && !processing && (
        <div className={`mt-3 flex items-center gap-2 text-xs rounded-lg px-3 py-2
          ${indexerTriggered ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-50 text-gray-500'}`}
        >
          <Search size={12} />
          {indexerTriggered
            ? 'Search indexer triggered — new content will be searchable shortly'
            : 'Search indexer not configured — chunks pushed directly to index'}
        </div>
      )}

      {/* Upload history / undo */}
      {uploadHistory.length > 0 && !busy && (
        <div className="mt-4 border border-amber-100 bg-amber-50 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5">
              <RotateCcw size={13} className="text-amber-500" />
              <span className="text-xs font-semibold text-amber-800">
                Upload history ({uploadHistory.length})
              </span>
            </div>
            {!confirmUndo ? (
              <button
                onClick={() => setConfirmUndo(true)}
                className="text-xs text-amber-700 hover:text-amber-900 font-medium underline underline-offset-2"
              >
                Undo latest
              </button>
            ) : (
              <span className="text-xs text-amber-600 font-medium">Confirm below</span>
            )}
          </div>

          <div className="space-y-1">
            {uploadHistory.map((entry, i) => (
              <div key={i} className={`flex items-start gap-2 py-1 ${
                i < uploadHistory.length - 1 ? 'border-b border-amber-100' : ''
              }`}>
                <div className={`mt-1 h-1.5 w-1.5 rounded-full flex-shrink-0 ${
                  i === 0 ? 'bg-amber-500' : 'bg-amber-200'
                }`} />
                <div className="min-w-0 flex-1">
                  <p className={`text-xs truncate ${i === 0 ? 'font-medium text-amber-800' : 'text-amber-600'}`}>
                    {entry.filename}
                  </p>
                  <p className="text-xs text-amber-400 mt-0.5">
                    {new Date(entry.uploaded_at).toLocaleString()}
                  </p>
                  {entry.lakehouse_path && (
                    <div className="flex items-center gap-1 mt-0.5">
                      <Database size={10} className="text-teal-500 flex-shrink-0" />
                      <p className="text-xs text-teal-600 font-mono truncate" title={entry.lakehouse_path}>
                        {entry.lakehouse_path}
                      </p>
                    </div>
                  )}
                </div>
                {i === 0 && (
                  <span className="text-xs bg-amber-200 text-amber-700 rounded px-1 py-0.5 flex-shrink-0 font-medium">
                    latest
                  </span>
                )}
              </div>
            ))}
          </div>

          {confirmUndo && (
            <div className="mt-3 pt-2 border-t border-amber-200">
              <div className="flex items-center gap-1.5 text-xs text-amber-800 mb-2">
                <AlertTriangle size={12} />
                Revert DB changes from <span className="font-medium">{uploadHistory[0]?.filename}</span>?
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
