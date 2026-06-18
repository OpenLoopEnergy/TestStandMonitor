import { useState, useEffect } from 'react'
import { ThemeToggle } from '../components/ThemeToggle'

interface FileInfo {
  filename: string
  created_at: string
}

interface BackupInfo {
  id: number
  label: string
  created_at: string
  trigger: string
  row_count: number
  first_logged_at: string | null
  last_logged_at: string | null
  headers: Record<string, string>
}

// Header fields baked into the export, snapshotted on clear and editable per backup.
const HEADER_FIELDS: [string, string][] = [
  ['programName', 'Program Name'],
  ['description', 'Description'],
  ['employeeId', 'Employee ID'],
  ['compSet', 'Comp Set'],
  ['inputFactor', 'Input Factor'],
  ['inputFactorType', 'Input Factor Type'],
  ['serialNumber', 'Serial Number'],
  ['customerId', 'Customer ID'],
  ['minEfficiencyPct', 'Min Efficiency %'],
]

interface FileTableProps {
  items: FileInfo[]
  renamingFile: string | null
  renameValue: string
  onRenameValueChange: (value: string) => void
  onStartRename: (filename: string) => void
  onCancelRename: () => void
  onConfirmRename: (oldFilename: string, newFilename: string) => void
  onDelete: (filename: string) => void
}

function FileTable({
  items,
  renamingFile,
  renameValue,
  onRenameValueChange,
  onStartRename,
  onCancelRename,
  onConfirmRename,
  onDelete,
}: FileTableProps) {
  if (items.length === 0) {
    return <p className="text-gray-500 text-sm text-center py-8">No files found.</p>
  }
  return (
    <table className="w-full text-sm text-left text-gray-700 dark:text-gray-300">
      <thead>
        <tr className="bg-black/10 text-gray-600 uppercase tracking-wide text-xs dark:bg-white/10 dark:text-gray-400">
          <th className="px-4 py-2">Filename</th>
          <th className="px-4 py-2">Exported</th>
          <th className="px-4 py-2">Actions</th>
        </tr>
      </thead>
      <tbody>
        {items.map(f => (
          <tr key={f.filename} className="border-b border-black/5 hover:bg-black/5 transition-colors dark:border-white/5 dark:hover:bg-white/5">
            <td className="px-4 py-3 font-mono text-xs">
              {renamingFile === f.filename ? (
                <div className="flex items-center gap-2">
                  <input
                    className="bg-black/10 border border-black/20 rounded px-2 py-1 text-gray-900 text-xs w-64 outline-none focus:border-red-500 dark:bg-white/10 dark:border-white/20 dark:text-white"
                    value={renameValue}
                    onChange={e => onRenameValueChange(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter') onConfirmRename(f.filename, renameValue)
                      if (e.key === 'Escape') onCancelRename()
                    }}
                    autoFocus
                  />
                  <button
                    onClick={() => onConfirmRename(f.filename, renameValue)}
                    className="text-xs bg-green-700 hover:bg-green-600 text-white px-2 py-1 rounded transition-colors"
                  >
                    Save
                  </button>
                  <button
                    onClick={onCancelRename}
                    className="text-xs bg-black/10 hover:bg-black/20 text-gray-900 px-2 py-1 rounded transition-colors dark:bg-white/10 dark:hover:bg-white/20 dark:text-white"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                f.filename
              )}
            </td>
            <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
              {new Date(f.created_at).toLocaleString()}
            </td>
            <td className="px-4 py-3 flex gap-2">
              <a
                href={`/download_test/${encodeURIComponent(f.filename)}`}
                download
                className="text-xs bg-red-700 hover:bg-red-600 text-white px-3 py-1 rounded-lg transition-colors"
              >
                Download
              </a>
              <button
                onClick={() => {
                  onStartRename(f.filename)
                  onRenameValueChange(f.filename.replace(/\.xlsx$/i, ''))
                }}
                className="text-xs bg-black/10 hover:bg-black/20 text-gray-900 px-3 py-1 rounded-lg transition-colors dark:bg-white/10 dark:hover:bg-white/20 dark:text-white"
                title="Rename"
              >
                ✎
              </button>
              <button
                onClick={() => onDelete(f.filename)}
                className="text-xs bg-black/10 hover:bg-red-100 text-gray-900 px-3 py-1 rounded-lg transition-colors dark:bg-white/10 dark:hover:bg-red-900/50 dark:text-white"
              >
                Delete
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

interface BackupTableProps {
  items: BackupInfo[]
  reexportingId: number | null
  renamingId: number | null
  renameValue: string
  onRenameValueChange: (value: string) => void
  onStartRename: (backup: BackupInfo) => void
  onCancelRename: () => void
  onConfirmRename: (id: number, label: string) => void
  onReexport: (backup: BackupInfo) => void
  onEditHeaders: (backup: BackupInfo) => void
  onDelete: (backup: BackupInfo) => void
}

function timeRange(b: BackupInfo): string {
  if (!b.first_logged_at || !b.last_logged_at) return '—'
  const start = new Date(b.first_logged_at)
  const end = new Date(b.last_logged_at)
  return `${start.toLocaleString()} → ${end.toLocaleTimeString()}`
}

function BackupTable({
  items,
  reexportingId,
  renamingId,
  renameValue,
  onRenameValueChange,
  onStartRename,
  onCancelRename,
  onConfirmRename,
  onReexport,
  onEditHeaders,
  onDelete,
}: BackupTableProps) {
  if (items.length === 0) {
    return <p className="text-gray-500 text-sm text-center py-8">No backups yet. Backups are created automatically when the data table is cleared.</p>
  }
  return (
    <table className="w-full text-sm text-left text-gray-700 dark:text-gray-300">
      <thead>
        <tr className="bg-black/10 text-gray-600 uppercase tracking-wide text-xs dark:bg-white/10 dark:text-gray-400">
          <th className="px-4 py-2">Label</th>
          <th className="px-4 py-2">Created</th>
          <th className="px-4 py-2">Rows</th>
          <th className="px-4 py-2">Time Range</th>
          <th className="px-4 py-2">Actions</th>
        </tr>
      </thead>
      <tbody>
        {items.map(b => (
          <tr key={b.id} className="border-b border-black/5 hover:bg-black/5 transition-colors dark:border-white/5 dark:hover:bg-white/5">
            <td className="px-4 py-3 text-xs">
              {renamingId === b.id ? (
                <div className="flex items-center gap-2">
                  <input
                    className="bg-black/10 border border-black/20 rounded px-2 py-1 text-gray-900 text-xs w-64 outline-none focus:border-red-500 dark:bg-white/10 dark:border-white/20 dark:text-white"
                    value={renameValue}
                    onChange={e => onRenameValueChange(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter') onConfirmRename(b.id, renameValue)
                      if (e.key === 'Escape') onCancelRename()
                    }}
                    autoFocus
                  />
                  <button
                    onClick={() => onConfirmRename(b.id, renameValue)}
                    className="text-xs bg-green-700 hover:bg-green-600 text-white px-2 py-1 rounded transition-colors"
                  >
                    Save
                  </button>
                  <button
                    onClick={onCancelRename}
                    className="text-xs bg-black/10 hover:bg-black/20 text-gray-900 px-2 py-1 rounded transition-colors dark:bg-white/10 dark:hover:bg-white/20 dark:text-white"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="font-medium">{b.label}</span>
                  {b.trigger === 'auto' && (
                    <span className="text-[10px] uppercase tracking-wide bg-blue-500/20 text-blue-600 px-1.5 py-0.5 rounded dark:text-blue-300">auto</span>
                  )}
                </div>
              )}
            </td>
            <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
              {new Date(b.created_at).toLocaleString()}
            </td>
            <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{b.row_count}</td>
            <td className="px-4 py-3 text-gray-600 text-xs dark:text-gray-400">{timeRange(b)}</td>
            <td className="px-4 py-3 flex gap-2">
              <button
                onClick={() => onReexport(b)}
                disabled={reexportingId === b.id}
                className="text-xs bg-red-700 hover:bg-red-600 text-white disabled:opacity-50 disabled:cursor-not-allowed px-3 py-1 rounded-lg transition-colors"
                title="Re-export this backup with the current export format"
              >
                {reexportingId === b.id ? 'Exporting…' : '⟳ Re-export'}
              </button>
              <button
                onClick={() => onEditHeaders(b)}
                className="text-xs bg-black/10 hover:bg-black/20 text-gray-900 px-3 py-1 rounded-lg transition-colors dark:bg-white/10 dark:hover:bg-white/20 dark:text-white"
                title="Edit header info (input factor, program name, etc.)"
              >
                ⚙ Info
              </button>
              <button
                onClick={() => onStartRename(b)}
                className="text-xs bg-black/10 hover:bg-black/20 text-gray-900 px-3 py-1 rounded-lg transition-colors dark:bg-white/10 dark:hover:bg-white/20 dark:text-white"
                title="Rename"
              >
                ✎
              </button>
              <button
                onClick={() => onDelete(b)}
                className="text-xs bg-black/10 hover:bg-red-100 text-gray-900 px-3 py-1 rounded-lg transition-colors dark:bg-white/10 dark:hover:bg-red-900/50 dark:text-white"
              >
                Delete
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default function PastTests() {
  const [files, setFiles] = useState<FileInfo[]>([])
  const [backups, setBackups] = useState<BackupInfo[]>([])
  const [activeTab, setActiveTab] = useState<'results' | 'backups'>('results')
  const [toast, setToast] = useState<{ type: 'success' | 'error'; msg: string } | null>(null)
  const [renamingFile, setRenamingFile] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const [renamingBackupId, setRenamingBackupId] = useState<number | null>(null)
  const [backupRenameValue, setBackupRenameValue] = useState('')
  const [reexportingId, setReexportingId] = useState<number | null>(null)
  const [editingBackup, setEditingBackup] = useState<BackupInfo | null>(null)
  const [headerDraft, setHeaderDraft] = useState<Record<string, string>>({})
  const [savingHeaders, setSavingHeaders] = useState(false)

  function loadFiles() {
    fetch('/past_tests')
      .then(r => r.json())
      .then(d => setFiles(d.files ?? []))
      .catch(() => {})
  }

  function loadBackups() {
    fetch('/data_backups')
      .then(r => r.json())
      .then(d => setBackups(d.backups ?? []))
      .catch(() => {})
  }

  useEffect(() => {
    loadFiles()
    loadBackups()
  }, [])

  function showToast(type: 'success' | 'error', msg: string) {
    setToast({ type, msg })
    setTimeout(() => setToast(null), 3000)
  }

  async function deleteFile(filename: string) {
    if (!confirm(`Delete ${filename}?`)) return
    const res = await fetch(`/delete_file/${encodeURIComponent(filename)}`, { method: 'DELETE' })
    if (res.ok) {
      setFiles(fs => fs.filter(f => f.filename !== filename))
      showToast('success', 'File deleted.')
    } else {
      showToast('error', 'Failed to delete file.')
    }
  }

  async function renameFile(oldFilename: string, newFilename: string) {
    const res = await fetch('/rename_file', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ old_filename: oldFilename, new_filename: newFilename }),
    })
    if (res.ok) {
      const { filename } = await res.json()
      setFiles(fs => fs.map(f => f.filename === oldFilename ? { ...f, filename } : f))
      setRenamingFile(null)
      showToast('success', 'File renamed.')
    } else {
      showToast('error', 'Failed to rename file.')
    }
  }

  async function reexportBackup(backup: BackupInfo) {
    setReexportingId(backup.id)
    try {
      const res = await fetch(`/export_backup/${backup.id}`, { method: 'POST' })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail ?? 'Re-export failed')
      }
      const cd = res.headers.get('Content-Disposition')
      const match = cd?.match(/filename="?([^;"]+)"?/)
      const filename = match?.[1]?.trim() ?? 'TestResults.xlsx'
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = filename; a.click()
      URL.revokeObjectURL(url)
      showToast('success', 'Re-exported successfully. Also saved to Test Results.')
      loadFiles()
    } catch (e) {
      showToast('error', `Re-export failed: ${e}`)
    } finally {
      setReexportingId(null)
    }
  }

  async function renameBackup(id: number, label: string) {
    const res = await fetch(`/rename_backup/${id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ label }),
    })
    if (res.ok) {
      const data = await res.json()
      setBackups(bs => bs.map(b => b.id === id ? { ...b, label: data.label } : b))
      setRenamingBackupId(null)
      showToast('success', 'Backup renamed.')
    } else {
      showToast('error', 'Failed to rename backup.')
    }
  }

  function openHeaderEditor(backup: BackupInfo) {
    setEditingBackup(backup)
    // Prefill from the snapshot, ensuring every field has a string value to edit.
    const draft: Record<string, string> = {}
    for (const [key] of HEADER_FIELDS) draft[key] = backup.headers?.[key] ?? ''
    setHeaderDraft(draft)
  }

  async function saveHeaders() {
    if (!editingBackup) return
    setSavingHeaders(true)
    try {
      const res = await fetch(`/update_backup_headers/${editingBackup.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ headers: headerDraft }),
      })
      if (!res.ok) throw new Error('save failed')
      const data = await res.json()
      setBackups(bs => bs.map(b => b.id === editingBackup.id ? { ...b, headers: data.headers } : b))
      setEditingBackup(null)
      showToast('success', 'Header info updated.')
    } catch {
      showToast('error', 'Failed to update header info.')
    } finally {
      setSavingHeaders(false)
    }
  }

  async function deleteBackup(backup: BackupInfo) {
    if (!confirm(`Delete backup "${backup.label}"? This permanently removes its raw data.`)) return
    const res = await fetch(`/delete_backup/${backup.id}`, { method: 'DELETE' })
    if (res.ok) {
      setBackups(bs => bs.filter(b => b.id !== backup.id))
      showToast('success', 'Backup deleted.')
    } else {
      showToast('error', 'Failed to delete backup.')
    }
  }

  const fileTableProps = {
    renamingFile,
    renameValue,
    onRenameValueChange: setRenameValue,
    onStartRename: setRenamingFile,
    onCancelRename: () => setRenamingFile(null),
    onConfirmRename: renameFile,
    onDelete: deleteFile,
  }

  const backupTableProps = {
    reexportingId,
    renamingId: renamingBackupId,
    renameValue: backupRenameValue,
    onRenameValueChange: setBackupRenameValue,
    onStartRename: (b: BackupInfo) => { setRenamingBackupId(b.id); setBackupRenameValue(b.label) },
    onCancelRename: () => setRenamingBackupId(null),
    onConfirmRename: renameBackup,
    onReexport: reexportBackup,
    onEditHeaders: openHeaderEditor,
    onDelete: deleteBackup,
  }

  return (
    <div className="min-h-screen bg-gray-100 text-gray-900 p-6 dark:bg-[#1a1a1a] dark:text-white">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold">Past Tests</h1>
            <p className="text-sm text-gray-500 mt-1">Previously exported test results and data table backups.</p>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <a href="/debug" className="text-xs bg-black/10 hover:bg-black/20 text-gray-900 px-3 py-1.5 rounded-lg transition-colors dark:bg-white/10 dark:hover:bg-white/20 dark:text-white">
              Debug
            </a>
            <a href="/" className="text-xs bg-black/10 hover:bg-black/20 text-gray-900 px-3 py-1.5 rounded-lg transition-colors dark:bg-white/10 dark:hover:bg-white/20 dark:text-white">
              ← Dashboard
            </a>
          </div>
        </div>

        {/* Info panel */}
        <div className="bg-black/5 border border-black/10 rounded-xl p-4 mb-4 text-sm text-gray-600 dark:bg-white/5 dark:border-white/10 dark:text-gray-400">
          <span className="text-gray-900 font-semibold dark:text-white">How this works: </span>
          <span className="text-gray-900 dark:text-white">Test Results</span> are exported XLSX files saved to the cloud database.
          <span className="text-gray-900 dark:text-white"> DB Backups</span> are raw snapshots of the data table, captured automatically each time it is cleared.
          Use <span className="text-gray-900 dark:text-white">Re-export</span> on a backup to regenerate an XLSX with the latest export format — useful for re-exporting older tests after the report layout changes.
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-4 bg-black/5 p-1 rounded-lg w-fit dark:bg-white/5">
          {(['results', 'backups'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`text-sm px-4 py-1.5 rounded-md transition-colors capitalize ${
                activeTab === tab ? 'bg-red-700 text-white' : 'text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white'
              }`}
            >
              {tab === 'results' ? `Test Results (${files.length})` : `DB Backups (${backups.length})`}
            </button>
          ))}
        </div>

        <div className="bg-black/5 border border-black/10 rounded-xl overflow-hidden dark:bg-white/5 dark:border-white/10">
          {activeTab === 'results'
            ? <FileTable items={files} {...fileTableProps} />
            : <BackupTable items={backups} {...backupTableProps} />
          }
        </div>
      </div>

      {editingBackup && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="bg-white border border-gray-200 rounded-2xl p-6 max-w-lg w-full shadow-2xl dark:bg-[#232323] dark:border-white/10">
            <h2 className="text-base font-bold mb-1 text-gray-900 dark:text-white">Edit Header Info</h2>
            <p className="text-xs text-gray-500 mb-4">
              These values were snapshotted when the table was cleared. Edit them to correct a
              re-export — e.g. the Input Factor used for this test.
            </p>
            <div className="grid grid-cols-2 gap-3 max-h-[55vh] overflow-y-auto pr-1">
              {HEADER_FIELDS.map(([key, label]) => (
                <label key={key} className="flex flex-col gap-1 text-xs">
                  <span className="text-gray-600 dark:text-gray-400">{label}</span>
                  <input
                    className="bg-black/5 border border-black/20 rounded px-2 py-1.5 text-gray-900 outline-none focus:border-red-500 dark:bg-white/10 dark:border-white/20 dark:text-white"
                    value={headerDraft[key] ?? ''}
                    onChange={e => setHeaderDraft(d => ({ ...d, [key]: e.target.value }))}
                  />
                </label>
              ))}
            </div>
            <div className="flex gap-3 mt-5">
              <button
                onClick={saveHeaders}
                disabled={savingHeaders}
                className="flex-1 bg-red-700 hover:bg-red-600 text-white disabled:opacity-50 px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors"
              >
                {savingHeaders ? 'Saving…' : 'Save'}
              </button>
              <button
                onClick={() => setEditingBackup(null)}
                className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-900 px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors dark:bg-white/10 dark:hover:bg-white/20 dark:text-white"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {reexportingId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="bg-white border border-gray-200 rounded-2xl px-10 py-8 flex flex-col items-center gap-4 shadow-2xl dark:bg-[#232323] dark:border-white/10">
            <div className="w-10 h-10 border-4 border-black/20 border-t-red-500 rounded-full animate-spin dark:border-white/20" />
            <p className="text-gray-900 font-semibold text-base dark:text-white">Building Export…</p>
            <p className="text-gray-600 text-sm dark:text-gray-400">Re-exporting backup to Excel, this may take a moment.</p>
          </div>
        </div>
      )}

      {toast && (
        <div className={`fixed bottom-4 right-4 text-sm px-4 py-3 rounded-xl shadow-lg ${
          toast.type === 'success' ? 'bg-green-800 text-green-100' : 'bg-red-800 text-red-100'
        }`}>
          {toast.msg}
        </div>
      )}
    </div>
  )
}
