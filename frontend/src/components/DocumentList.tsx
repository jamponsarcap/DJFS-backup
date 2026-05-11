import { useState, useEffect } from 'react'
import { FileText, Lock, Unlock, Trash2, RefreshCw, Database } from 'lucide-react'
import { fetchDocuments, lockDocument, unlockDocument, deleteDocument } from '../api/client'
import type { LakehouseDocument } from '../api/client'

interface Props {
  clientId: string
  refreshKey?: number
  onDelete?: (path: string) => void
}

function parseFilename(name: string): { displayName: string; uploadedAt: Date | null } {
  const match = name.match(/^(\d{8})_(\d{6})_(.+)$/)
  if (!match) return { displayName: name, uploadedAt: null }
  const [, date, time, original] = match
  const uploadedAt = new Date(
    `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}T` +
    `${time.slice(0, 2)}:${time.slice(2, 4)}:${time.slice(4, 6)}`
  )
  return { displayName: original, uploadedAt }
}

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export default function DocumentList({ clientId, refreshKey, onDelete }: Props) {
  const [docs, setDocs] = useState<LakehouseDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    fetchDocuments(clientId)
      .then(setDocs)
      .catch(() => setDocs([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [clientId, refreshKey])

  const handleLockToggle = async (doc: LakehouseDocument) => {
    setBusy(doc.path)
    try {
      const result = doc.locked
        ? await unlockDocument(clientId, doc.path)
        : await lockDocument(clientId, doc.path)
      setDocs(prev => prev.map(d => d.path === doc.path ? { ...d, locked: result.locked } : d))
    } finally {
      setBusy(null)
    }
  }

  const handleDelete = async (doc: LakehouseDocument) => {
    setBusy(doc.path)
    try {
      await deleteDocument(clientId, doc.path)
      setDocs(prev => prev.filter(d => d.path !== doc.path))
      onDelete?.(doc.path)
    } catch (err: any) {
      alert(err?.response?.data?.detail ?? 'Delete failed.')
    } finally {
      setBusy(null)
      setConfirmDelete(null)
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Database size={16} className="text-teal-500" />
          <h3 className="text-sm font-semibold text-gray-700">Lakehouse Documents</h3>
          {docs.length > 0 && (
            <span className="text-xs bg-gray-100 text-gray-500 rounded-full px-2 py-0.5">{docs.length}</span>
          )}
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="text-gray-400 hover:text-gray-600 transition-colors"
          title="Refresh list"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-8 text-gray-400 text-sm gap-2">
          <RefreshCw size={14} className="animate-spin" />
          Loading documents...
        </div>
      )}

      {!loading && docs.length === 0 && (
        <div className="text-center py-8 text-gray-400 text-sm">
          No documents uploaded to the Lakehouse yet.
        </div>
      )}

      {!loading && docs.length > 0 && (
        <ul className="divide-y divide-gray-50">
          {docs.map(doc => {
            const { displayName, uploadedAt } = parseFilename(doc.name)
            const isBusy = busy === doc.path
            const isConfirming = confirmDelete === doc.path

            return (
              <li key={doc.path} className="py-3 flex items-center gap-3">
                <FileText size={16} className="text-gray-300 flex-shrink-0" />

                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 truncate" title={displayName}>
                    {displayName}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {uploadedAt ? uploadedAt.toLocaleString() : doc.last_modified ?? '-'}
                    {doc.size > 0 && <span className="ml-2">{fmtSize(doc.size)}</span>}
                  </p>
                </div>

                <div className="flex items-center gap-1.5 flex-shrink-0">
                  {/* Lock / Unlock */}
                  <button
                    onClick={() => handleLockToggle(doc)}
                    disabled={isBusy}
                    title={doc.locked ? 'Unlock document' : 'Lock document'}
                    className={`p-1.5 rounded-md transition-colors disabled:opacity-40
                      ${doc.locked
                        ? 'text-amber-500 hover:bg-amber-50'
                        : 'text-gray-400 hover:bg-gray-100'}`}
                  >
                    {doc.locked ? <Lock size={14} /> : <Unlock size={14} />}
                  </button>

                  {/* Delete */}
                  {!isConfirming ? (
                    <button
                      onClick={() => !doc.locked && setConfirmDelete(doc.path)}
                      disabled={doc.locked || isBusy}
                      title={doc.locked ? 'Unlock to delete' : 'Delete document'}
                      className="p-1.5 rounded-md transition-colors text-gray-400
                        hover:bg-red-50 hover:text-red-500
                        disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      <Trash2 size={14} />
                    </button>
                  ) : (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleDelete(doc)}
                        disabled={isBusy}
                        className="text-xs px-2 py-1 bg-red-500 text-white rounded-md hover:bg-red-600 disabled:opacity-50"
                      >
                        {isBusy ? '...' : 'Delete'}
                      </button>
                      <button
                        onClick={() => setConfirmDelete(null)}
                        className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded-md hover:bg-gray-200"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}