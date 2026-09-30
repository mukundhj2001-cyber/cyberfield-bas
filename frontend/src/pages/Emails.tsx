import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Play, Mail } from 'lucide-react'
import { api } from '../api/client'
import type { Email } from '../lib/types'
import { Badge } from '../components/Badge'

export function Emails() {
  const [emails, setEmails] = useState<Email[]>([])
  const [selected, setSelected] = useState<Email | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  const load = () =>
    api
      .emails()
      .then((rows) => {
        setEmails(rows)
        setSelected((prev) => rows.find((e) => e.id === prev?.id) || rows[0] || null)
      })
      .catch((e: Error) => setError(e.message))

  useEffect(() => {
    load()
  }, [])

  const runQuote = async () => {
    if (!selected) return
    setRunning(true)
    setError(null)
    try {
      const result = await api.runQuote({ email_id: selected.id })
      await load()
      navigate(`/approvals/${result.approval_id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-white">Inbox</h1>
          <p className="mt-1 text-sm text-slate-400">
            Mock inbound mailbox for Northwind Industrial (no Gmail in v1)
          </p>
        </div>
        <button
          type="button"
          disabled={!selected || running}
          onClick={runQuote}
          className="inline-flex items-center gap-2 rounded-lg bg-cyan-500 px-3.5 py-2 text-sm font-medium text-slate-950 disabled:opacity-50 hover:bg-cyan-400"
        >
          <Play className="h-4 w-4" />
          {running ? 'Running…' : 'Run quote workflow'}
        </button>
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-5">
        <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/40 lg:col-span-2">
          <ul className="divide-y divide-slate-800">
            {emails.map((email) => (
              <li key={email.id}>
                <button
                  type="button"
                  onClick={() => setSelected(email)}
                  className={[
                    'w-full px-4 py-3 text-left transition',
                    selected?.id === email.id ? 'bg-cyan-500/10' : 'hover:bg-slate-900',
                  ].join(' ')}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="truncate text-sm font-medium text-slate-100">
                      {email.from_name || email.from_address}
                    </div>
                    <Badge status={email.status} />
                  </div>
                  <div className="mt-1 truncate text-sm text-slate-300">{email.subject}</div>
                  <div className="mt-1 text-[11px] text-slate-500">
                    {new Date(email.received_at).toLocaleString()}
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 lg:col-span-3">
          {selected ? (
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="rounded-xl bg-slate-800 p-2.5 text-cyan-300">
                  <Mail className="h-4 w-4" />
                </div>
                <div className="min-w-0">
                  <h2 className="text-lg font-semibold text-white">{selected.subject}</h2>
                  <p className="mt-1 text-sm text-slate-400">
                    From {selected.from_name} &lt;{selected.from_address}&gt;
                  </p>
                </div>
              </div>
              <pre className="whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm leading-relaxed text-slate-300">
                {selected.body}
              </pre>
              {selected.intent ? (
                <div className="text-xs text-slate-500">
                  Last intent: <span className="font-mono text-cyan-300">{selected.intent}</span>
                </div>
              ) : null}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Select an email</p>
          )}
        </div>
      </div>
    </div>
  )
}
