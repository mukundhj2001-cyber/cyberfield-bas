import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Check, X, ShieldCheck } from 'lucide-react'
import { api } from '../api/client'
import type { Approval, EmailDraft, QuoteDraft } from '../lib/types'
import { Badge } from '../components/Badge'
import { EmptyState } from '../components/EmptyState'

export function Approvals() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [rows, setRows] = useState<Approval[]>([])
  const [active, setActive] = useState<Approval | null>(null)
  const [quote, setQuote] = useState<QuoteDraft | null>(null)
  const [emailDraft, setEmailDraft] = useState<EmailDraft | null>(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    const list = await api.approvals()
    setRows(list)
    const targetId = id ? Number(id) : list[0]?.id
    if (targetId) {
      const detail = list.find((a) => a.id === targetId) || (await api.approval(targetId))
      setActive(detail)
      setQuote(structuredClone(detail.quote_draft))
      setEmailDraft(structuredClone(detail.email_draft))
    } else {
      setActive(null)
      setQuote(null)
      setEmailDraft(null)
    }
  }

  useEffect(() => {
    load().catch((e: Error) => setError(e.message))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  const canDecide = active?.status === 'pending'

  const recalc = (next: QuoteDraft) => {
    const items = next.line_items.map((li) => ({
      ...li,
      line_total: Math.round(li.quantity * li.unit_price * 100) / 100,
    }))
    const subtotal = Math.round(items.reduce((s, i) => s + (i.line_total || 0), 0) * 100) / 100
    return { ...next, line_items: items, subtotal, tax: 0, total: subtotal }
  }

  const updateQty = (sku: string, quantity: number) => {
    if (!quote) return
    const next = {
      ...quote,
      line_items: quote.line_items.map((li) =>
        li.sku === sku ? { ...li, quantity: Math.max(1, quantity) } : li,
      ),
    }
    setQuote(recalc(next))
  }

  const decide = async (action: 'approve' | 'reject') => {
    if (!active || !quote || !emailDraft) return
    setBusy(true)
    setError(null)
    try {
      if (action === 'approve') {
        await api.approve(active.id, {
          reviewed_by: 'Ops Manager',
          review_note: note || undefined,
          quote_draft: quote,
          email_draft: emailDraft,
        })
        navigate('/crm')
      } else {
        await api.reject(active.id, {
          reviewed_by: 'Ops Manager',
          review_note: note || undefined,
        })
        await load()
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const pendingCount = useMemo(() => rows.filter((r) => r.status === 'pending').length, [rows])

  return (
    <div className="space-y-4">
      <div>
        <div className="text-[10px] font-medium uppercase tracking-[0.16em] text-cyan-500/80">
          Human gate
        </div>
        <h1 className="mt-1 text-xl font-semibold text-white">Approvals</h1>
        <p className="mt-1 text-sm text-slate-400">
          Review before send · {pendingCount} pending
        </p>
      </div>

      {error ? (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      <div className="grid gap-3 lg:grid-cols-5">
        <div className="ops-panel overflow-hidden rounded-xl lg:col-span-2">
          {rows.length === 0 ? (
            <EmptyState
              title="No approvals yet"
              description="Run a quote from Inbox to create a draft for review."
              icon={ShieldCheck}
            />
          ) : (
            <ul className="divide-y divide-slate-800/80">
              {rows.map((row) => (
                <li key={row.id}>
                  <Link
                    to={`/approvals/${row.id}`}
                    className={[
                      'block px-3.5 py-2.5 transition',
                      active?.id === row.id ? 'bg-cyan-500/10' : 'hover:bg-slate-900/70',
                    ].join(' ')}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-[13px] font-medium text-slate-100">
                        {row.quote_draft?.quote_ref || `Approval #${row.id}`}
                      </div>
                      <Badge status={row.status} />
                    </div>
                    <div className="mt-0.5 truncate text-[11px] text-slate-400">
                      {row.quote_draft?.company} · $
                      {Number(row.quote_draft?.total || 0).toLocaleString()}
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="space-y-3 lg:col-span-3">
          {!active || !quote || !emailDraft ? (
            <div className="ops-panel rounded-xl">
              <EmptyState title="Select an approval" description="Pick a draft from the list." />
            </div>
          ) : (
            <>
              <div className="ops-panel rounded-xl p-4">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h2 className="text-base font-semibold text-white">{quote.quote_ref}</h2>
                    <p className="text-xs text-slate-400">
                      {quote.company} · {quote.contact_name}
                    </p>
                  </div>
                  <Badge status={active.status} />
                </div>

                <div className="overflow-x-auto rounded-lg border border-slate-800">
                  <table className="min-w-full text-left text-sm">
                    <thead className="bg-slate-950/90 text-[10px] uppercase tracking-wide text-slate-500">
                      <tr>
                        <th className="px-3 py-2">SKU</th>
                        <th className="px-3 py-2">Item</th>
                        <th className="px-3 py-2">Qty</th>
                        <th className="px-3 py-2">Unit</th>
                        <th className="px-3 py-2">Line</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/80">
                      {quote.line_items.map((li) => (
                        <tr key={li.sku} className="hover:bg-slate-950/40">
                          <td className="px-3 py-2 font-mono text-[11px] text-cyan-300">{li.sku}</td>
                          <td className="px-3 py-2 text-[13px] text-slate-200">{li.name}</td>
                          <td className="px-3 py-2">
                            <input
                              type="number"
                              min={1}
                              disabled={!canDecide}
                              value={li.quantity}
                              onChange={(e) => updateQty(li.sku, Number(e.target.value))}
                              className="w-16 rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-100 disabled:opacity-60"
                            />
                          </td>
                          <td className="px-3 py-2 text-[13px] text-slate-300">
                            ${li.unit_price.toFixed(2)}
                          </td>
                          <td className="px-3 py-2 text-[13px] text-slate-100">
                            ${(li.line_total ?? li.quantity * li.unit_price).toFixed(2)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="mt-3 flex justify-end text-sm">
                  <div className="space-y-0.5 text-right">
                    <div className="text-xs text-slate-400">
                      Subtotal{' '}
                      <span className="ml-3 font-medium text-white">${quote.subtotal.toFixed(2)}</span>
                    </div>
                    <div className="text-sm font-semibold text-cyan-300">
                      Total ${quote.total.toFixed(2)} {quote.currency}
                    </div>
                  </div>
                </div>
              </div>

              <div className="ops-panel rounded-xl p-4">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Outbound email draft
                </h3>
                <label className="mb-1 block text-[10px] uppercase tracking-wide text-slate-500">
                  Subject
                </label>
                <input
                  disabled={!canDecide}
                  value={emailDraft.subject}
                  onChange={(e) => setEmailDraft({ ...emailDraft, subject: e.target.value })}
                  className="mb-3 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 disabled:opacity-60"
                />
                <label className="mb-1 block text-[10px] uppercase tracking-wide text-slate-500">
                  Body
                </label>
                <textarea
                  disabled={!canDecide}
                  rows={10}
                  value={emailDraft.body}
                  onChange={(e) => setEmailDraft({ ...emailDraft, body: e.target.value })}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs leading-relaxed text-slate-200 disabled:opacity-60"
                />
              </div>

              {canDecide ? (
                <div className="ops-panel rounded-xl p-4">
                  <label className="mb-1 block text-[10px] uppercase tracking-wide text-slate-500">
                    Review note (optional)
                  </label>
                  <input
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Looks good / adjust lead time…"
                    className="mb-3 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"
                  />
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => decide('approve')}
                      className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-3.5 py-1.5 text-xs font-medium text-slate-950 hover:bg-emerald-400 disabled:opacity-50"
                    >
                      <Check className="h-3.5 w-3.5" /> Approve & send (mock)
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => decide('reject')}
                      className="inline-flex items-center gap-2 rounded-lg border border-rose-500/40 bg-rose-500/10 px-3.5 py-1.5 text-xs font-medium text-rose-200 hover:bg-rose-500/20 disabled:opacity-50"
                    >
                      <X className="h-3.5 w-3.5" /> Reject
                    </button>
                  </div>
                </div>
              ) : null}

              {active.agent_trace?.length ? (
                <div className="ops-panel rounded-xl p-3.5">
                  <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                    Agent trace
                  </h3>
                  <pre className="overflow-x-auto font-mono text-[11px] leading-relaxed text-slate-400">
                    {JSON.stringify(active.agent_trace, null, 2)}
                  </pre>
                </div>
              ) : null}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
