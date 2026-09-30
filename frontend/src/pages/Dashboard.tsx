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
} from 'lucide-react'
import { api } from '../api/client'
import type { DashboardStats } from '../lib/types'
import { StatCard } from '../components/StatCard'
import { EmptyState } from '../components/EmptyState'

const kindIcon: Record<string, typeof Bot> = {
  gmail_sync: Mail,
  webhook_ingest: Workflow,
  email_sent: Mail,
  crm_update: Users,
  task_created: CheckSquare,
  workflow: Bot,
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
      <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-200">
        Backend unreachable: {error}. Start the API on :8000.
      </div>
    )
  }

  if (!stats) {
    return <div className="text-sm text-slate-500">Loading ops overview…</div>
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[10px] font-medium uppercase tracking-[0.16em] text-cyan-500/80">
            Operations hub
          </div>
          <h1 className="mt-1 text-xl font-semibold tracking-tight text-white">
            Cyberfield BAS dashboard
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Quote-from-email agent · LLM{' '}
            <span className="font-mono text-cyan-300">{stats.llm_mode}</span>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            to="/emails"
            className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-xs font-medium text-slate-200 hover:border-slate-600"
          >
            Inbox
          </Link>
          <Link
            to="/emails"
            className="inline-flex items-center gap-2 rounded-lg bg-cyan-500 px-3 py-1.5 text-xs font-medium text-slate-950 hover:bg-cyan-400"
          >
            Run quote workflow <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <StatCard
          label="Inbox"
          value={stats.emails_total}
          hint={`${stats.emails_unread} unread`}
          icon={Inbox}
          accent="cyan"
        />
        <StatCard
          label="Approvals"
          value={stats.approvals_pending}
          hint="Awaiting human"
          icon={ShieldCheck}
          accent="amber"
        />
        <StatCard
          label="Open deals"
          value={stats.deals_open}
          hint="CRM pipeline"
          icon={Users}
          accent="emerald"
        />
        <StatCard
          label="Open tasks"
          value={stats.tasks_open}
          hint="Follow-ups"
          icon={CheckSquare}
          accent="violet"
        />
        <StatCard
          label="Catalog"
          value={stats.products}
          hint="Priced SKUs"
          icon={Package}
          accent="cyan"
        />
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
              description="Sync Gmail or process an RFQ from Inbox to generate a draft quote."
              icon={Bot}
            />
          ) : (
            <ul className="space-y-2">
              {stats.recent_activity.map((a) => {
                const Icon = kindIcon[a.kind] || Bot
                return (
                  <li
                    key={a.id}
                    className="flex items-start gap-3 rounded-lg border border-slate-800/80 bg-slate-950/40 px-3 py-2.5"
                  >
                    <div className="mt-0.5 rounded-md border border-slate-800 bg-slate-900 p-1.5 text-cyan-400">
                      <Icon className="h-3 w-3" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-[10px] font-medium uppercase tracking-wide text-cyan-400/80">
                        {a.kind}
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

        <div className="ops-panel-glow space-y-4 rounded-xl p-4">
          <h2 className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-300">
            Demo script
          </h2>
          <ol className="list-decimal space-y-2 pl-4 text-sm text-slate-400">
            <li>
              Inbox → <span className="text-cyan-300">Sync Gmail</span> (mock) or pick an RFQ
            </li>
            <li>
              Click <span className="text-cyan-300">Run quote workflow</span>
            </li>
            <li>Review draft in Approvals (edit qty / email)</li>
            <li>Approve → CRM deal + follow-up task</li>
          </ol>
          <div className="rounded-lg border border-slate-800/80 bg-slate-950/50 p-3 text-[11px] leading-relaxed text-slate-500">
            Optional: POST from n8n to{' '}
            <code className="font-mono text-cyan-400/90">/webhooks/n8n/email</code>. See Workflows.
          </div>
        </div>
      </div>
    </div>
  )
}
