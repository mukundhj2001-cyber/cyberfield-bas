import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Play, Mail, RefreshCw, Link2, Filter, Plug } from 'lucide-react'
import { api } from '../api/client'
import type { Email, GmailStatus } from '../lib/types'
import { Badge } from '../components/Badge'
import { EmptyState } from '../components/EmptyState'
import { PageHeader } from '../components/PageHeader'
import { ErrorBanner } from '../components/ErrorBanner'
import { LoadingState } from '../components/LoadingState'
import { useToast } from '../components/Toast'

const PRIORITY_FILTERS = ['All', 'Critical', 'High', 'Medium', 'Low'] as const

export function Emails() {
  const [emails, setEmails] = useState<Email[]>([])
  const [selected, setSelected] = useState<Email | null>(null)
  const [gmail, setGmail] = useState<GmailStatus | null>(null)
  const [priority, setPriority] = useState<(typeof PRIORITY_FILTERS)[number]>('All')
  const [running, setRunning] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [filteredCount, setFilteredCount] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const toast = useToast()

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
    load()
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
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
    try {
      const result = await api.syncInbox()
      await load()
      const parts = [
        `Imported ${result.imported}`,
        result.skipped ? `skipped ${result.skipped}` : null,
        result.filtered && result.filtered > 0
          ? `filtered ${result.filtered} non-business`
          : null,
      ].filter(Boolean)
      toast.success(`Inbox synced · ${parts.join(' · ')}`)
      if (result.filtered && result.filtered > 0) {
        setFilteredCount(result.filtered)
      }
      if (result.warning) {
        toast.info(result.warning)
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(msg)
      toast.error(msg)
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
      toast.success('Quote draft ready for review')
      navigate(`/approvals/${result.approval_id}`)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(msg)
      toast.error(msg)
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

  const gmailConnected = Boolean(gmail?.connected)
  const gmailChipLabel = gmailConnected ? 'Gmail connected' : 'Offline mode'

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Communications"
        title="Inbox"
        description="Business mail only · ranked by attention (critical first)"
        actions={
          <>
            {gmail ? (
              <span
                className={[
                  'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold',
                  gmailConnected
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                    : 'border-amber-500/30 bg-amber-500/10 text-amber-300',
                ].join(' ')}
                title={gmail.detail || gmail.label}
              >
                <Link2 className="h-3 w-3" />
                {gmailChipLabel}
              </span>
            ) : null}
            {filteredCount != null && filteredCount > 0 ? (
              <span
                className="inline-flex items-center gap-1.5 rounded-full border border-slate-600/60 bg-slate-800/80 px-2.5 py-1 text-[10px] font-medium text-slate-300"
                title="Non-business mail (newsletters, social, marketing) was not imported"
              >
                Filtered {filteredCount} non-business
              </span>
            ) : null}
            <button type="button" disabled={syncing} onClick={syncInbox} className="btn-secondary">
              <RefreshCw className={`h-3.5 w-3.5 ${syncing ? 'animate-spin' : ''}`} />
              {syncing ? 'Syncing…' : 'Sync inbox'}
            </button>
            <button
              type="button"
              disabled={!selected || running}
              onClick={runQuote}
              className="btn-primary"
            >
              <Play className="h-3.5 w-3.5" />
              {running ? 'Running…' : 'Run quote'}
            </button>
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
          <Filter className="h-3 w-3" />
          Priority
        </span>
        {PRIORITY_FILTERS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => onPriorityChange(p)}
            className={[
              'rounded-full border px-2.5 py-1 text-[10px] font-semibold transition',
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

      {error ? <ErrorBanner message={error} /> : null}

      {loading ? (
        <LoadingState label="Loading inbox…" />
      ) : (
        <div className="grid gap-3 lg:grid-cols-5">
          <div className="ops-panel overflow-hidden rounded-xl lg:col-span-2">
            {emails.length === 0 ? (
              <EmptyState
                title="Your inbox is ready"
                description="Sync Gmail to pull business RFQs, or connect OAuth for live mail. Non-business mail is filtered automatically."
                icon={Mail}
                actions={
                  <>
                    <button type="button" disabled={syncing} onClick={syncInbox} className="btn-primary">
                      <RefreshCw className={`h-3.5 w-3.5 ${syncing ? 'animate-spin' : ''}`} />
                      Sync inbox
                    </button>
                    <Link to="/workflows" className="btn-secondary">
                      <Plug className="h-3.5 w-3.5" />
                      Connect integrations
                    </Link>
                  </>
                }
              />
            ) : (
              <ul className="divide-y divide-slate-800/80">
                {emails.map((email) => (
                  <li key={email.id}>
                    <button
                      type="button"
                      onClick={() => setSelected(email)}
                      className={[
                        'w-full px-3.5 py-3 text-left transition',
                        selected?.id === email.id ? 'bg-cyan-500/10' : 'hover:bg-slate-900/70',
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
                      <div className="mt-1.5 flex items-center justify-between gap-2 text-[10px] tabular-nums text-slate-500">
                        <span>{new Date(email.received_at).toLocaleString()}</span>
                        <span className="text-cyan-500/80">
                          Attention {(email.attention_score ?? 0).toFixed(0)}
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
                    <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
                      <Badge status={selected.attention_label || 'Low'} />
                      <Badge status={selected.status} />
                      <span className="text-[10px] tabular-nums text-slate-500">
                        Score {(selected.attention_score ?? 0).toFixed(1)}
                      </span>
                    </div>
                    <h2 className="text-base font-semibold text-white">{selected.subject}</h2>
                    <p className="mt-1 text-xs text-slate-400">
                      From {selected.from_name} &lt;{selected.from_address}&gt;
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
                    Detected intent:{' '}
                    <span className="font-medium text-cyan-300">
                      {selected.intent.replaceAll('_', ' ')}
                    </span>
                  </div>
                ) : null}
                <div className="flex flex-wrap gap-2 border-t border-slate-800/80 pt-3">
                  <button
                    type="button"
                    disabled={running}
                    onClick={runQuote}
                    className="btn-primary"
                  >
                    <Play className="h-3.5 w-3.5" />
                    {running ? 'Running…' : 'Run quote'}
                  </button>
                </div>
              </div>
            ) : (
              <EmptyState
                title="Select a message"
                description="Choose an email from the list to preview and run a quote."
              />
            )}
          </div>
        </div>
      )}
    </div>
  )
}
