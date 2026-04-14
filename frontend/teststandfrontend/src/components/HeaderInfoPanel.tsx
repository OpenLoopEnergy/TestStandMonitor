import { useState, useEffect } from 'react'
import type { HeaderData } from '../types/signals'

interface Props {
  onInputFactorChange: (factor: number) => void
  isAdmin?: boolean
}

export function HeaderInfoPanel({ onInputFactorChange, isAdmin = false }: Props) {
  const [data, setData] = useState<HeaderData>({})
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<HeaderData>({})
  const [toast, setToast] = useState<{ type: 'success' | 'error'; msg: string } | null>(null)

  useEffect(() => {
    fetch('/get_header_data')
      .then(r => r.json())
      .then((d: HeaderData) => {
        setData(d)
        const f = parseFloat(d.inputFactor ?? '1')
        if (!isNaN(f)) onInputFactorChange(f)
      })
      .catch(() => {})
  }, [])

  function startEdit() {
    setDraft({ ...data })
    setEditing(true)
  }

  async function save() {
    try {
      const res = await fetch('/update_header_data', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          programName: draft.programName ?? '',
          description: draft.description ?? '',
          compSet: parseInt(draft.compSet ?? '0', 10),
          inputFactor: parseFloat(draft.inputFactor ?? '1'),
          inputFactorType: draft.inputFactorType ?? 'cu/in',
          serialNumber: parseInt(draft.serialNumber ?? '0', 10),
          employeeId: parseInt(draft.employeeId ?? '0', 10),
          customerId: parseInt(draft.customerId ?? '0', 10),
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      setData(draft)
      const f = parseFloat(draft.inputFactor ?? '1')
      if (!isNaN(f)) onInputFactorChange(f)
      setEditing(false)
      showToast('success', 'Header saved.')
    } catch (e) {
      showToast('error', `Save failed: ${e}`)
    }
  }

  function showToast(type: 'success' | 'error', msg: string) {
    setToast({ type, msg })
    setTimeout(() => setToast(null), 3500)
  }

  function field(label: string, key: keyof HeaderData, type = 'text') {
    const val = editing ? (draft[key] ?? '') : (data[key] ?? '—')
    return (
      <div key={key} className="flex flex-col gap-0.5">
        <label className="text-xs text-gray-500 uppercase tracking-wide">{label}</label>
        {editing ? (
          key === 'inputFactorType' ? (
            <select
              value={draft[key] ?? 'cu/in'}
              onChange={e => setDraft(d => ({ ...d, [key]: e.target.value }))}
              className="bg-white/10 border border-white/20 rounded px-2 py-1 text-sm text-white"
            >
              <option value="cu/in">cu/in</option>
              <option value="cu/cm">cu/cm</option>
            </select>
          ) : (
            <input
              type={type}
              value={val as string}
              onChange={e => setDraft(d => ({ ...d, [key]: e.target.value }))}
              className="bg-white/10 border border-white/20 rounded px-2 py-1 text-sm text-white"
            />
          )
        ) : (
          <span className="text-sm text-white">{val as string}</span>
        )}
      </div>
    )
  }

  return (
    <div className="bg-white/5 border border-white/10 rounded-xl p-3">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wide">Test Info</h3>
        {isAdmin && (
          !editing
            ? <button onClick={startEdit} className="cursor-pointer text-sm bg-white/10 hover:bg-white/20 px-5 py-2.5 rounded-lg font-semibold transition-colors">Edit</button>
            : <div className="flex gap-2">
                <button onClick={save} className="cursor-pointer text-sm bg-red-700 hover:bg-red-600 px-5 py-2.5 rounded-lg font-semibold transition-colors">Save</button>
                <button onClick={() => setEditing(false)} className="cursor-pointer text-sm bg-white/10 hover:bg-white/20 px-5 py-2.5 rounded-lg font-semibold transition-colors">Cancel</button>
              </div>
        )}
      </div>

      <div className="grid grid-cols-4 gap-2">
        {field('Program Name', 'programName')}
        {field('Description', 'description')}
        {field('Comp Set', 'compSet', 'number')}
        {field('Input Factor', 'inputFactor', 'number')}
        {field('Factor Type', 'inputFactorType')}
        {field('Serial #', 'serialNumber', 'number')}
        {field('Employee ID', 'employeeId', 'number')}
        {field('Customer ID', 'customerId', 'number')}
      </div>

      {toast && (
        <div className={`text-xs px-3 py-2 rounded-lg ${toast.type === 'success' ? 'bg-green-800/60 text-green-200' : 'bg-red-800/60 text-red-200'}`}>
          {toast.msg}
        </div>
      )}
    </div>
  )
}
