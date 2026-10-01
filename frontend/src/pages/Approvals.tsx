import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Check, X, ShieldCheck, ChevronRight } from 'lucide-react'
import { api } from '../api/client'
import type { Approval, EmailDraft, QuoteDraft } from '../lib/types'
import { Badge } from '../components/Badge'
import { EmptyState } from '../components/EmptyState'
import { PageHeader } from '../components/PageHeader'
import { ErrorBanner } from '../components/ErrorBanner'
import { LoadingState } from '../components/LoadingState'
import { useToast } from '../components/Toast'

const APPLY_KEYS: Array<{ key: string; label: string }> = [
  { key: 'send_outbound', label: 'Send outbound reply' },
  { key: 'crm_contact', label: 'Create / update CRM contact' },
  { key: 'crm_deal', label: 'Create CRM deal' },
  { key: 'create_ticket', label: 'Create support ticket' },
  { key: 'create_tasks', label: 'Create tasks' },
]

export function Approvals() {
  const { id } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const [rows, setRows] = useState<Approval[]>([])
  const [active, setActive] = useState<Approval | null>(null)
  const [quote, setQuote] = useState<QuoteDraft | null>(null)
  const [emailDraft, setEmailDraft] = useState<EmailDraft | null>(null)
  const [applyFlags, setApplyFlags] = useState<Record<string, boolean>>({})
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    const list = await api.approvals()
    setRows(list)
    const targetId = id ? Number(id) : list[0]?.id
    if (targetId) {
      const detail = list.find((a) => a.id === targetId) || (await api.approval(targetId))
      setActive(detail)
      setQuote(structuredClone(detail.quote_draft || {}))
      setEmailDraft(structuredClone(detail.email_draft || {}))
      const defaults = {
        ...(detail.apply_defaults || detail.action_plan?.apply_defaults || {}),
      }
      setApplyFlags({
        send_outbound: defaults.send_outbound ?? true,
        crm_contact: defaults.crm_contact ?? true,
        crm_deal: defaults.crm_deal ?? false,
        create_ticket: defaults.create_ticket ?? false,
        create_tasks: defaults.create_tasks ?? true,
      })
    } else {
      setActive(null)
      setQuote(null)
      setEmailDraft(null)
    }
  }

  useEffect(() => {
    setLoading(true)
    load()
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  const canDecide = active?.status === 'pending'
  const hasQuote = Boolean(quote?.quote_ref && (quote.line_items?.length || 0) >= 0 && quote.quote_ref)
  const plan = active?.action_plan

  const recalc = (next: QuoteDraft) => {
    const items = (next.line_items || []).map((li) => ({
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
      line_items: (quote.line_items || []).map((li) =>
        li.sku === sku ? { ...li, quantity: Math.max(1, quantity) } : li,
      ),
    }
    setQuote(recalc(next))
  }

  const decide = async (action: 'approve' | 'reject') => {
    if (!active || !emailDraft) return
    setBusy(true)
    setError(null)
    try {
      if (action === 'approve') {
        await api.approve(active.id, {
          reviewed_by: 'Ops Manager',
          review_note: note || undefined,
          quote_draft: quote || {},
          email_draft: emailDraft,
          apply_flags: applyFlags,
        })
        toast.success('Approved · staged plan applied')
        navigate('/crm')
      } else {
        await api.reject(active.id, {
          reviewed_by: 'Ops Manager',
          review_note: note || undefined,
        })
        toast.info('Plan rejected')
        await load()
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(msg)
      toast.error(msg)
    } finally {
      setBusy(false)
    }
  }

  const pendingCount = useMemo(() => rows.filter((r) => r.status === 'pending').length, [rows])

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Human gate"
        title="Approvals"
        description={`Unified queue for quotes & reply drafts · ${pendingCount} pending · nothing sends without approval`}
      />

      {error ? <ErrorBanner message={error} /> : null}

      {loading ? (
        <LoadingState label="Loading approvals…" />
      ) : (
        <div className="grid gap-3 lg:grid-cols-5">
          <div className="ops-panel overflow-hidden rounded-xl lg:col-span-2">
            {rows.length === 0 ? (
              <EmptyState
                title="Nothing to review yet"
                description="Sync the inbox or click Propose action to stage drafts for approval."
                icon={ShieldCheck}
                actions={
                  <Link to="/emails" className="btn-primary">
                    Go to Inbox
                  </Link>
                }
              />
            ) : (
              <ul className="divide-y divide-slate-800/80">
                {rows.map((row) => (
                  <li key={row.id}>
                    <Link
                      to={`/approvals/${row.id}`}
                      className={[
                        'block px-3.5 py-3 transition',
                        active?.id === row.id ? 'bg-cyan-500/10' : 'hover:bg-slate-900/70',
                      ].join(' ')}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="truncate text-[13px] font-medium text-slate-100">
                          {row.title || row.quote_draft?.quote_ref || `Approval #${row.id}`}
                        </div>
                        <Badge status={row.status} />
                      </div>
                      <div className="mt-0.5 flex flex-wrap gap-1.5 text-[11px] text-slate-400">
                        {row.action_type ? (
                          <span className="rounded border border-violet-500/30 bg-violet-500/10 px-1.5 py-0.5 text-[10px] text-violet-200">
                            {row.action_type.replaceAll('_', ' ')}
                          </span>
                        ) : null}
                        {row.quote_draft?.total != null && row.quote_draft?.quote_ref ? (
                          <span>
                            {row.quote_draft.company} · $
                            {Number(row.quote_draft.total || 0).toLocaleString()}
                          </span>
                        ) : (
                          <span className="truncate">{row.email_draft?.subject || row.workflow}</span>
                        )}
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="space-y-3 lg:col-span-3">
            {!active || !emailDraft ? (
              <div className="ops-panel rounded-xl">
                <EmptyState
                  title="Select an approval"
                  description="Review the staged reply, optional quote, CRM/ticket/task plan, then approve selectively."
                />
              </div>
            ) : (
              <>
                <div className="ops-panel rounded-xl p-4">
                  <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <h2 className="text-base font-semibold text-white">
                        {active.title || quote?.quote_ref || `Approval #${active.id}`}
                      </h2>
                      <p className="text-xs text-slate-400">
                        {(active.action_type || active.workflow || '').replaceAll('_', ' ')}
                        {plan?.escalate ? ' · escalate' : ''}
                      </p>
                    </div>
                    <Badge status={active.status} />
                  </div>

                  {plan?.actions?.length ? (
                    <div className="mb-3 flex flex-wrap gap-1">
                      {plan.actions
                        .filter((a) => a !== 'await_human_approval')
                        .slice(0, 10)
                        .map((a) => (
                          <span
                            key={a}
                            className="rounded-md border border-slate-800 bg-slate-950/80 px-2 py-0.5 text-[10px] text-slate-400"
                          >
                            {a.replaceAll('_', ' ')}
                          </span>
                        ))}
                    </div>
                  ) : null}

                  {hasQuote && quote ? (
                    <>
                      <div className="overflow-x-auto rounded-lg border border-slate-800">
                        <table className="ops-table min-w-full text-left text-sm">
                          <thead className="text-[10px] uppercase tracking-wide text-slate-500">
                            <tr>
                              <th className="px-3 py-2.5">SKU</th>
                              <th className="px-3 py-2.5">Item</th>
                              <th className="px-3 py-2.5">Qty</th>
                              <th className="px-3 py-2.5">Unit</th>
                              <th className="px-3 py-2.5">Line</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/80">
                            {(quote.line_items || []).map((li) => (
                              <tr key={li.sku}>
                                <td className="px-3 py-2.5 font-mono text-[11px] text-cyan-300">
                                  {li.sku}
                                </td>
                                <td className="px-3 py-2.5 text-[13px] text-slate-200">{li.name}</td>
                                <td className="px-3 py-2.5">
                                  <input
                                    type="number"
                                    min={1}
                                    disabled={!canDecide}
                                    value={li.quantity}
                                    onChange={(e) => updateQty(li.sku, Number(e.target.value))}
                                    className="w-16 rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-100 disabled:opacity-60"
                                  />
                                </td>
                                <td className="px-3 py-2.5 text-[13px] text-slate-300">
                                  ${li.unit_price.toFixed(2)}
                                </td>
                                <td className="px-3 py-2.5 text-[13px] text-slate-100">
                                  ${(li.line_total ?? li.quantity * li.unit_price).toFixed(2)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <div className="mt-3 flex justify-end text-sm">
                        <div className="text-sm font-semibold text-cyan-300">
                          Total ${(quote.total || 0).toFixed(2)} {quote.currency || 'USD'}
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3 text-xs text-slate-400">
                      No quote line items for this intent — reply + CRM/ticket/task plan only.
                      {plan?.amounts?.length ? (
                        <div className="mt-2 text-slate-300">
                          Extracted amounts:{' '}
                          {plan.amounts.map((a) => a.raw || `${a.amount} ${a.currency}`).join(', ')}
                        </div>
                      ) : null}
                      {plan?.order_refs?.length ? (
                        <div className="mt-1 text-slate-300">Refs: {plan.order_refs.join(', ')}</div>
                      ) : null}
                    </div>
                  )}
                </div>

                <div className="ops-panel rounded-xl p-4">
                  <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Outbound draft
                  </h3>
                  <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                    Subject
                  </label>
                  <input
                    disabled={!canDecide}
                    value={emailDraft.subject || ''}
                    onChange={(e) => setEmailDraft({ ...emailDraft, subject: e.target.value })}
                    className="mb-3 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 disabled:opacity-60"
                  />
                  <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                    Body
                  </label>
                  <textarea
                    disabled={!canDecide}
                    rows={10}
                    value={emailDraft.body || ''}
                    onChange={(e) => setEmailDraft({ ...emailDraft, body: e.target.value })}
                    className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs leading-relaxed text-slate-200 disabled:opacity-60"
                  />
                </div>

                {canDecide ? (
                  <div className="ops-panel rounded-xl p-4">
                    <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                      Apply on approve (selective)
                    </h3>
                    <div className="mb-3 grid gap-2 sm:grid-cols-2">
                      {APPLY_KEYS.map(({ key, label }) => (
                        <label
                          key={key}
                          className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-950/50 px-3 py-2 text-xs text-slate-300"
                        >
                          <input
                            type="checkbox"
                            checked={Boolean(applyFlags[key])}
                            onChange={(e) =>
                              setApplyFlags({ ...applyFlags, [key]: e.target.checked })
                            }
                            className="rounded border-slate-600"
                          />
                          {label}
                        </label>
                      ))}
                    </div>
                    <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-slate-500">
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
                        <Check className="h-3.5 w-3.5" /> Approve & apply
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
                    <h3 className="mb-2.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                      Workflow steps
                    </h3>
                    <ol className="space-y-1.5">
                      {active.agent_trace.map((step, i) => {
                        const stage =
                          typeof step.stage === 'string'
                            ? step.stage
                            : typeof step.step === 'string'
                              ? step.step
                              : `Step ${i + 1}`
                        return (
                          <li
                            key={i}
                            className="flex items-start gap-2 rounded-lg border border-slate-800/70 bg-slate-950/40 px-2.5 py-2"
                          >
                            <ChevronRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-cyan-500/70" />
                            <div className="text-[12px] font-medium capitalize text-slate-200">
                              {String(stage).replaceAll('_', ' ')}
                            </div>
                          </li>
                        )
                      })}
                    </ol>
                  </div>
                ) : null}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
