import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Check, X } from 'lucide-react'
import { api } from '../api/client'
import type { Approval, EmailDraft, QuoteDraft } from '../lib/types'
import { Badge } from '../components/Badge'

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
        <h1 className="text-2xl font-semibold text-white">Approvals</h1>
        <p className="mt-1 text-sm text-slate-400">
          Human gate before send · {pendingCount} pending
        </p>
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-5">
        <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/40 lg:col-span-2">
          {rows.length === 0 ? (
            <p className="p-4 text-sm text-slate-500">No approvals yet. Run a quote from Inbox.</p>
          ) : (
            <ul className="divide-y divide-slate-800">
              {rows.map((row) => (
                <li key={row.id}>
                  <Link
                    to={`/approvals/${row.id}`}
                    className={[
                      'block px-4 py-3 transition',
                      active?.id === row.id ? 'bg-cyan-500/10' : 'hover:bg-slate-900',
                    ].join(' ')}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-sm font-medium text-slate-100">
                        {row.quote_draft?.quote_ref || `Approval #${row.id}`}
                      </div>
                      <Badge status={row.status} />
                    </div>
                    <div className="mt-1 truncate text-xs text-slate-400">
                      {row.quote_draft?.company} · ${Number(row.quote_draft?.total || 0).toLocaleString()}
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="space-y-4 lg:col-span-3">
          {!active || !quote || !emailDraft ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 text-sm text-slate-500">
              Select an approval to review.
            </div>
          ) : (
            <>
              <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h2 className="text-lg font-semibold text-white">{quote.quote_ref}</h2>
                    <p className="text-sm text-slate-400">
                      {quote.company} · {quote.contact_name}
                    </p>
                  </div>
                  <Badge status={active.status} />
                </div>

                <div className="overflow-x-auto rounded-xl border border-slate-800">
                  <table className="min-w-full text-left text-sm">
                    <thead className="bg-slate-950/80 text-xs uppercase tracking-wide text-slate-500">
                      <tr>
                        <th className="px-3 py-2">SKU</th>
                        <th className="px-3 py-2">Item</th>
                        <th className="px-3 py-2">Qty</th>
                        <th className="px-3 py-2">Unit</th>
                        <th className="px-3 py-2">Line</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {quote.line_items.map((li) => (
                        <tr key={li.sku}>
                          <td className="px-3 py-2 font-mono text-xs text-cyan-300">{li.sku}</td>
                          <td className="px-3 py-2 text-slate-200">{li.name}</td>
                          <td className="px-3 py-2">
                            <input
                              type="number"
                              min={1}
                              disabled={!canDecide}
                              value={li.quantity}
                              onChange={(e) => updateQty(li.sku, Number(e.target.value))}
                              className="w-20 rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-slate-100 disabled:opacity-60"
                            />
                          </td>
                          <td className="px-3 py-2 text-slate-300">${li.unit_price.toFixed(2)}</td>
                          <td className="px-3 py-2 text-slate-100">
                            ${(li.line_total ?? li.quantity * li.unit_price).toFixed(2)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="mt-4 flex justify-end text-sm">
                  <div className="space-y-1 text-right">
                    <div className="text-slate-400">
                      Subtotal <span className="ml-4 font-medium text-white">${quote.subtotal.toFixed(2)}</span>
                    </div>
                    <div className="text-base font-semibold text-cyan-300">
                      Total ${quote.total.toFixed(2)} {quote.currency}
                    </div>
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
                <h3 className="mb-3 text-sm font-semibold text-slate-200">Outbound email draft</h3>
                <label className="mb-2 block text-xs text-slate-500">Subject</label>
                <input
                  disabled={!canDecide}
                  value={emailDraft.subject}
                  onChange={(e) => setEmailDraft({ ...emailDraft, subject: e.target.value })}
                  className="mb-3 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 disabled:opacity-60"
                />
                <label className="mb-2 block text-xs text-slate-500">Body</label>
                <textarea
                  disabled={!canDecide}
                  rows={12}
                  value={emailDraft.body}
                  onChange={(e) => setEmailDraft({ ...emailDraft, body: e.target.value })}
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs leading-relaxed text-slate-200 disabled:opacity-60"
                />
              </div>

              {canDecide ? (
                <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5">
                  <label className="mb-2 block text-xs text-slate-500">Review note (optional)</label>
                  <input
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Looks good / adjust lead time…"
                    className="mb-4 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100"
                  />
                  <div className="flex flex-wrap gap-3">
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => decide('approve')}
                      className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-emerald-400 disabled:opacity-50"
                    >
                      <Check className="h-4 w-4" /> Approve & send (mock)
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => decide('reject')}
                      className="inline-flex items-center gap-2 rounded-lg border border-rose-500/40 bg-rose-500/10 px-4 py-2 text-sm font-medium text-rose-200 hover:bg-rose-500/20 disabled:opacity-50"
                    >
                      <X className="h-4 w-4" /> Reject
                    </button>
                  </div>
                </div>
              ) : null}

              {active.agent_trace?.length ? (
                <div className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Agent trace
                  </h3>
                  <pre className="overflow-x-auto text-[11px] leading-relaxed text-slate-400">
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
