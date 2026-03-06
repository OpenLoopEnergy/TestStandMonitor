import { useState, useEffect } from 'react'

interface FileInfo {
  filename: string
  created_at: string
}

interface PastTestsData {
  files: FileInfo[]
  db_files: FileInfo[]
}

export default function PastTests() {
  const [data, setData] = useState<PastTestsData>({ files: [], db_files: [] })
  const [activeTab, setActiveTab] = useState<'results' | 'backups'>('results')
  const [toast, setToast] = useState<{ type: 'success' | 'error'; msg: string } | null>(null)
  const [renamingFile, setRenamingFile] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')

  useEffect(() => {
    fetch('/past_tests')
      .then(r => r.json())
      .then(setData)
      .catch(() => {})
  }, [])

  function showToast(type: 'success' | 'error', msg: string) {
    setToast({ type, msg })
    setTimeout(() => setToast(null), 3000)
  }

  async function deleteFile(filename: string) {
    if (!confirm(`Delete ${filename}?`)) return
    const res = await fetch(`/delete_file/${encodeURIComponent(filename)}`, { method: 'DELETE' })
    if (res.ok) {
      setData(d => ({
        files: d.files.filter(f => f.filename !== filename),
        db_files: d.db_files.filter(f => f.filename !== filename),
      }))
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
      setData(d => ({
        ...d,
        files: d.files.map(f => f.filename === oldFilename ? { ...f, filename } : f),
      }))
      setRenamingFile(null)
      showToast('success', 'File renamed.')
    } else {
      showToast('error', 'Failed to rename file.')
    }
  }

  function FileTable({ items }: { items: FileInfo[] }) {
    if (items.length === 0) {
      return <p className="text-gray-500 text-sm text-center py-8">No files found.</p>
    }
    return (
      <table className="w-full text-sm text-left text-gray-300">
        <thead>
          <tr className="bg-white/10 text-gray-400 uppercase tracking-wide text-xs">
            <th className="px-4 py-2">Filename</th>
            <th className="px-4 py-2">Exported</th>
            <th className="px-4 py-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map(f => (
            <tr key={f.filename} className="border-b border-white/5 hover:bg-white/5 transition-colors">
              <td className="px-4 py-3 font-mono text-xs">
                {renamingFile === f.filename ? (
                  <div className="flex items-center gap-2">
                    <input
                      className="bg-white/10 border border-white/20 rounded px-2 py-1 text-white text-xs w-64 outline-none focus:border-red-500"
                      value={renameValue}
                      onChange={e => setRenameValue(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === 'Enter') renameFile(f.filename, renameValue)
                        if (e.key === 'Escape') setRenamingFile(null)
                      }}
                      autoFocus
                    />
                    <button
                      onClick={() => renameFile(f.filename, renameValue)}
                      className="text-xs bg-green-700 hover:bg-green-600 px-2 py-1 rounded transition-colors"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => setRenamingFile(null)}
                      className="text-xs bg-white/10 hover:bg-white/20 px-2 py-1 rounded transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  f.filename
                )}
              </td>
              <td className="px-4 py-3 text-gray-400">
                {new Date(f.created_at).toLocaleString()}
              </td>
              <td className="px-4 py-3 flex gap-2">
                <a
                  href={`/download_test/${encodeURIComponent(f.filename)}`}
                  download
                  className="text-xs bg-red-700 hover:bg-red-600 px-3 py-1 rounded-lg transition-colors"
                >
                  Download
                </a>
                <button
                  onClick={() => {
                    setRenamingFile(f.filename)
                    setRenameValue(f.filename.replace(/\.xlsx$/i, ''))
                  }}
                  className="text-xs bg-white/10 hover:bg-white/20 px-3 py-1 rounded-lg transition-colors"
                  title="Rename"
                >
                  ✎
                </button>
                <button
                  onClick={() => deleteFile(f.filename)}
                  className="text-xs bg-white/10 hover:bg-red-900/50 px-3 py-1 rounded-lg transition-colors"
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

  return (
    <div className="min-h-screen bg-[#1a1a1a] text-white p-6">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold">Past Tests</h1>
            <p className="text-sm text-gray-500 mt-1">Previously exported test results and database backups.</p>
          </div>
          <a href="/" className="text-xs bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-lg transition-colors">
            ← Dashboard
          </a>
        </div>

        {/* Info panel */}
        <div className="bg-white/5 border border-white/10 rounded-xl p-4 mb-4 text-sm text-gray-400">
          <span className="text-white font-semibold">How this works: </span>
          Exported test results are saved to the cloud database and are accessible from any device.
          Use the <span className="text-white">Export Data</span> button on the dashboard to save results here.
          Files can be downloaded, renamed, or deleted by anyone with access.
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-4 bg-white/5 p-1 rounded-lg w-fit">
          {(['results', 'backups'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`text-sm px-4 py-1.5 rounded-md transition-colors capitalize ${
                activeTab === tab ? 'bg-red-700 text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab === 'results' ? `Test Results (${data.files.length})` : `DB Backups (${data.db_files.length})`}
            </button>
          ))}
        </div>

        <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
          {activeTab === 'results'
            ? <FileTable items={data.files} />
            : <FileTable items={data.db_files} />
          }
        </div>
      </div>

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
