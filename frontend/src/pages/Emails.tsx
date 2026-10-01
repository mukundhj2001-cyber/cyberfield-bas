import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Play, Mail, RefreshCw, Link2, Filter } from 'lucide-react'
import { api } from '../api/client'
import type { Email, GmailStatus } from '../lib/types'
import { Badge } from '../components/Badge'
import { EmptyState } from '../components/EmptyState'

const PRIORITY_FILTERS = ['All', 'Critical', 'High', 'Medium', 'Low'] as const

export function Emails() {
  const [emails, setEmails] = useState<Email[]>([])
  const [selected, setSelected] = useState<Email | null>(null)
  const [gmail, setGmail] = useState<GmailStatus | null>(null)
  const [priority, setPriority] = useState<(typeof PRIORITY_FILTERS)[number]>('All')
  const [running, setRunning] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncMsg, setSyncMsg] = useState<string | null>(null)
  const [filteredCount, setFilteredCount] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  const load = async (prio: (typeof PRIORITY_FILTERS)[number] = priority) => {
    const [rows, status] = await Promise.all([
      api.emails({
        priority: prio === 'All' ? undefined : prio,
        sort: 'attention',
      }),
      api.gmailStatus(),
    ])
    setEmails(rows)
    setGmail(status)
    setSelected((prev) => rows.find((e) => e.id === prev?.id) || rows[0] || null)
  }

  useEffect(() => {
    load().catch((e: Error) => setError(e.message))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const onPriorityChange = async (next: (typeof PRIORITY_FILTERS)[number]) => {
    setPriority(next)
    setError(null)
    try {
      await load(next)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  const syncInbox = async () => {
    setSyncing(true)
    setError(null)
    setSyncMsg(null)
    try {
      const result = await api.syncInbox()
      await load()
      const warn = result.warning ? ` · ${result.warning}` : ''
      const scored =
        result.attention_rescored != null ? ` · rescored ${result.attention_rescored}` : ''
      const filtered =
        result.filtered && result.filtered > 0
          ? ` · filtered ${result.filtered} non-business`
          : ''
      setSyncMsg(
        `Synced (${result.mode}): imported ${result.imported}, skipped ${result.skipped}${filtered}${scored}${warn}`,
      )
      if (result.filtered && result.filtered > 0) {
        setFilteredCount(result.filtered)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setSyncing(false)
    }
  }

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

  const counts = useMemo(() => {
    const map: Record<string, number> = { Critical: 0, High: 0, Medium: 0, Low: 0 }
    for (const e of emails) {
      const label = e.attention_label || 'Low'
      map[label] = (map[label] || 0) + 1
    }
    return map
  }, [emails])

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[10px] font-medium uppercase tracking-[0.16em] text-cyan-500/80">
            Communications
          </div>
          <h1 className="mt-1 text-xl font-semibold text-white">Inbox</h1>
          <p className="mt-1 text-sm text-slate-400">
            Business mail only · ranked by attention (critical first)
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {gmail ? (
            <span
              className={[
                'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-medium',
                gmail.connected
                  ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                  : 'border-amber-500/30 bg-amber-500/10 text-amber-300',
              ].join(' ')}
              title={gmail.detail}
            >
              <Link2 className="h-3 w-3" />
              {gmail.connected ? 'Connected' : 'Mock'}
            </span>
          ) : null}
          {filteredCount != null && filteredCount > 0 ? (
            <span
              className="inline-flex items-center gap-1.5 rounded-full border border-slate-600/60 bg-slate-800/80 px-2.5 py-1 text-[10px] font-medium text-slate-300"
              title="Non-business mail (newsletters, social, marketing) was not imported"
            >
              filtered {filteredCount} non-business
            </span>
          ) : null}
          <button
            type="button"
            disabled={syncing}
            onClick={syncInbox}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-xs font-medium text-slate-100 hover:border-slate-500 disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${syncing ? 'animate-spin' : ''}`} />
            {syncing ? 'Syncing…' : 'Sync Gmail'}
          </button>
          <button
            type="button"
            disabled={!selected || running}
            onClick={runQuote}
            className="inline-flex items-center gap-2 rounded-lg bg-cyan-500 px-3 py-1.5 text-xs font-medium text-slate-950 disabled:opacity-50 hover:bg-cyan-400"
          >
            <Play className="h-3.5 w-3.5" />
            {running ? 'Running…' : 'Run quote workflow'}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wide text-slate-500">
          <Filter className="h-3 w-3" />
          Priority
        </span>
        {PRIORITY_FILTERS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => onPriorityChange(p)}
            className={[
              'rounded-full border px-2.5 py-1 text-[10px] font-medium transition',
              priority === p
                ? 'border-cyan-500/40 bg-cyan-500/15 text-cyan-200'
                : 'border-slate-700 bg-slate-900/60 text-slate-400 hover:border-slate-500',
            ].join(' ')}
          >
            {p}
            {p !== 'All' && counts[p] ? (
              <span className="ml-1 tabular-nums text-slate-500">{counts[p]}</span>
            ) : null}
          </button>
        ))}
      </div>

      {syncMsg ? (
        <div className="rounded-lg border border-cyan-500/20 bg-cyan-500/10 px-3 py-2 text-xs text-cyan-100">
          {syncMsg}
        </div>
      ) : null}

      {error ? (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      <div className="grid gap-3 lg:grid-cols-5">
        <div className="ops-panel overflow-hidden rounded-xl lg:col-span-2">
          {emails.length === 0 ? (
            <EmptyState
              title="Inbox empty"
              description="Click Sync Gmail to pull mock messages, or POST via n8n webhook."
              icon={Mail}
            />
          ) : (
            <ul className="divide-y divide-slate-800/80">
              {emails.map((email) => (
                <li key={email.id}>
                  <button
                    type="button"
                    onClick={() => setSelected(email)}
                    className={[
                      'w-full px-3.5 py-2.5 text-left transition',
                      selected?.id === email.id
                        ? 'bg-cyan-500/10'
                        : 'hover:bg-slate-900/70',
                    ].join(' ')}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="truncate text-[13px] font-medium text-slate-100">
                        {email.from_name || email.from_address}
                      </div>
                      <div className="flex shrink-0 items-center gap-1">
                        <Badge status={email.attention_label || 'Low'} />
                        <Badge status={email.status} />
                      </div>
                    </div>
                    <div className="mt-0.5 truncate text-[13px] text-slate-300">{email.subject}</div>
                    <div className="mt-1 flex items-center justify-between gap-2 text-[10px] tabular-nums text-slate-500">
                      <span>{new Date(email.received_at).toLocaleString()}</span>
                      <span className="text-cyan-500/80">
                        attn {(email.attention_score ?? 0).toFixed(0)}
                      </span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="ops-panel rounded-xl p-4 lg:col-span-3">
          {selected ? (
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="rounded-lg border border-slate-800 bg-slate-950 p-2 text-cyan-300">
                  <Mail className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex flex-wrap items-center gap-1.5">
                    <Badge status={selected.attention_label || 'Low'} />
                    <span className="text-[10px] tabular-nums text-slate-500">
                      score {(selected.attention_score ?? 0).toFixed(1)}
                    </span>
                    <Badge status={selected.status} />
                  </div>
                  <h2 className="text-base font-semibold text-white">{selected.subject}</h2>
                  <p className="mt-1 text-xs text-slate-400">
                    From {selected.from_name} &lt;{selected.from_address}&gt;
                  </p>
                  <p className="mt-0.5 font-mono text-[10px] text-slate-600">
                    {selected.message_id}
                  </p>
                </div>
              </div>
              {selected.attention_meta?.reasons?.length ? (
                <div className="flex flex-wrap gap-1.5">
                  {selected.attention_meta.reasons.map((r) => (
                    <span
                      key={r}
                      className="rounded-md border border-slate-800 bg-slate-950/80 px-2 py-0.5 text-[10px] text-slate-400"
                    >
                      {r}
                    </span>
                  ))}
                </div>
              ) : null}
              <pre className="whitespace-pre-wrap rounded-lg border border-slate-800 bg-slate-950/70 p-3.5 text-[13px] leading-relaxed text-slate-300">
                {selected.body}
              </pre>
              {selected.intent ? (
                <div className="text-[11px] text-slate-500">
                  Last intent:{' '}
                  <span className="font-mono text-cyan-300">{selected.intent}</span>
                </div>
              ) : null}
            </div>
          ) : (
            <EmptyState title="Select an email" description="Choose a message from the list." />
          )}
        </div>
      </div>
    </div>
  )
}
