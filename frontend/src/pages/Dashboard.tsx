import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Inbox,
  ShieldCheck,
  Users,
  CheckSquare,
  Bot,
  ArrowRight,
  Package,
  Mail,
  Workflow,
  Sparkles,
  Ticket,
} from 'lucide-react'
import { api } from '../api/client'
import type { DashboardStats } from '../lib/types'
import { StatCard } from '../components/StatCard'
import { EmptyState } from '../components/EmptyState'
import { PageHeader } from '../components/PageHeader'
import { LoadingState } from '../components/LoadingState'
import { ErrorBanner } from '../components/ErrorBanner'

const kindMeta: Record<string, { label: string; icon: typeof Bot }> = {
  gmail_sync: { label: 'Inbox sync', icon: Mail },
  webhook_ingest: { label: 'Inbound webhook', icon: Workflow },
  email_sent: { label: 'Email sent', icon: Mail },
  crm_update: { label: 'CRM update', icon: Users },
  task_created: { label: 'Task created', icon: CheckSquare },
  ticket_created: { label: 'Ticket created', icon: Ticket },
  workflow: { label: 'Workflow', icon: Bot },
}

function llmLabel(mode: string) {
  if (!mode) return 'Standard'
  if (mode.toLowerCase().includes('mock')) return 'Built-in'
  if (mode.toLowerCase().includes('openai')) return 'OpenAI'
  return mode
}

export function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .stats()
      .then(setStats)
      .catch((e: Error) => setError(e.message))
  }, [])

  if (error) {
    return (
      <ErrorBanner
        message={`Unable to reach the API (${error}). Confirm the backend is running on port 8000.`}
      />
    )
  }

  if (!stats) {
    return <LoadingState label="Loading operations overview…" />
  }

  const pipe = stats.pipeline || {}
  const isEmpty =
    stats.emails_total === 0 &&
    stats.approvals_pending === 0 &&
    stats.deals_open === 0 &&
    stats.recent_activity.length === 0

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Operations hub"
        title="Cyberfield Business Automation"
        description={
          <>
            Multi-intent inbound ops with human approval · Engine{' '}
            <span className="font-medium text-cyan-300">{llmLabel(stats.llm_mode)}</span>
          </>
        }
        actions={
          <>
            <Link to="/emails" className="btn-secondary">
              Open inbox
            </Link>
            <Link to="/approvals" className="btn-primary">
              Review approvals <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
        <StatCard label="Inbox" value={stats.emails_total} hint={`${stats.emails_unread} unread`} icon={Inbox} accent="cyan" />
        <StatCard label="Approvals" value={stats.approvals_pending} hint="Awaiting review" icon={ShieldCheck} accent="amber" />
        <StatCard label="Tickets" value={stats.tickets_open || 0} hint="Open / escalated" icon={Ticket} accent="violet" />
        <StatCard label="Open deals" value={stats.deals_open} hint="CRM pipeline" icon={Users} accent="emerald" />
        <StatCard label="Open tasks" value={stats.tasks_open} hint="Follow-ups" icon={CheckSquare} accent="violet" />
        <StatCard label="Catalog" value={stats.products} hint="Priced SKUs" icon={Package} accent="cyan" />
      </div>

      <div className="ops-panel rounded-xl p-4">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
          Multi-action pipeline
        </h2>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
          {[
            ['Unread', pipe.inbox_unread ?? stats.emails_unread],
            ['Staged', pipe.action_staged ?? 0],
            ['Pending approve', pipe.approvals_pending ?? stats.approvals_pending],
            ['Approved', pipe.approvals_approved ?? 0],
            ['Tickets', pipe.tickets_open ?? stats.tickets_open ?? 0],
            ['Tasks', pipe.tasks_open ?? stats.tasks_open],
            ['Deals', pipe.deals_open ?? stats.deals_open],
          ].map(([label, value]) => (
            <div
              key={String(label)}
              className="rounded-lg border border-slate-800 bg-slate-950/50 px-3 py-2.5 text-center"
            >
              <div className="text-lg font-semibold tabular-nums text-cyan-300">{value as number}</div>
              <div className="text-[10px] font-medium uppercase tracking-wide text-slate-500">
                {label as string}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-3">
        <div className="ops-panel rounded-xl p-4 lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
              Activity feed
            </h2>
            <Bot className="h-3.5 w-3.5 text-slate-600" />
          </div>
          {stats.recent_activity.length === 0 ? (
            <EmptyState
              title="No activity yet"
              description="Sync your inbox to classify intents and stage action plans."
              icon={Bot}
              actions={
                <Link to="/emails" className="btn-primary">
                  Go to Inbox
                </Link>
              }
            />
          ) : (
            <ul className="space-y-2">
              {stats.recent_activity.map((a) => {
                const meta = kindMeta[a.kind] || { label: a.kind.replaceAll('_', ' '), icon: Bot }
                const Icon = meta.icon
                return (
                  <li
                    key={a.id}
                    className="flex items-start gap-3 rounded-lg border border-slate-800/80 bg-slate-950/40 px-3 py-2.5"
                  >
                    <div className="mt-0.5 rounded-md border border-slate-800 bg-slate-900 p-1.5 text-cyan-400">
                      <Icon className="h-3 w-3" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-[10px] font-semibold uppercase tracking-wide text-cyan-400/85">
                        {meta.label}
                      </div>
                      <div className="mt-0.5 text-sm text-slate-200">{a.message}</div>
                    </div>
                    <div className="shrink-0 text-[10px] tabular-nums text-slate-500">
                      {new Date(a.created_at).toLocaleString()}
                    </div>
                  </li>
                )
              })}
            </ul>
          )}
        </div>

        <div className="space-y-3">
          <div className="ops-panel-glow space-y-4 rounded-xl p-4">
            <div className="flex items-center gap-2">
              <Sparkles className="h-3.5 w-3.5 text-cyan-300" />
              <h2 className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-300">
                {isEmpty ? 'Get started' : 'Quick path'}
              </h2>
            </div>
            <ol className="list-decimal space-y-2.5 pl-4 text-sm leading-relaxed text-slate-400">
              <li>
                <span className="text-cyan-300">Sync inbox</span> — classify intents & stage plans
              </li>
              <li>
                Review the unified <span className="text-cyan-300">Approvals</span> queue
              </li>
              <li>Selectively approve send / CRM / ticket / tasks</li>
              <li>Track CRM, Tickets, and Tasks as the plan applies</li>
            </ol>
            <Link to="/emails" className="btn-primary w-full justify-center">
              Start with Inbox <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          {stats.by_intent && Object.keys(stats.by_intent).length > 0 ? (
            <div className="ops-panel rounded-xl p-4">
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
                Intent mix
              </h2>
              <ul className="space-y-1.5">
                {Object.entries(stats.by_intent)
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, 8)
                  .map(([intent, n]) => (
                    <li key={intent} className="flex justify-between text-xs text-slate-300">
                      <span className="capitalize">{intent.replaceAll('_', ' ')}</span>
                      <span className="tabular-nums text-cyan-400">{n}</span>
                    </li>
                  ))}
              </ul>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
