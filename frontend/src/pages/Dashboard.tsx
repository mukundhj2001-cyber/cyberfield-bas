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
      <ErrorBanner message={`Unable to reach the API (${error}). Confirm the backend is running on port 8000.`} />
    )
  }

  if (!stats) {
    return <LoadingState label="Loading operations overview…" />
  }

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
            Quote-from-email automation with human approval · Engine{' '}
            <span className="font-medium text-cyan-300">{llmLabel(stats.llm_mode)}</span>
          </>
        }
        actions={
          <>
            <Link to="/emails" className="btn-secondary">
              Open inbox
            </Link>
            <Link to="/emails" className="btn-primary">
              Run quote <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </>
        }
      />

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
          hint="Awaiting review"
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
              description="Sync your inbox or run a quote workflow to see live operations here."
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

        <div className="ops-panel-glow space-y-4 rounded-xl p-4">
          <div className="flex items-center gap-2">
            <Sparkles className="h-3.5 w-3.5 text-cyan-300" />
            <h2 className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-300">
              {isEmpty ? 'Get started' : 'Quick path'}
            </h2>
          </div>
          <ol className="list-decimal space-y-2.5 pl-4 text-sm leading-relaxed text-slate-400">
            <li>
              Open <span className="text-cyan-300">Inbox</span> → Sync Gmail or connect your mailbox
            </li>
            <li>
              Select an RFQ and click <span className="text-cyan-300">Run quote</span>
            </li>
            <li>Review the draft in Approvals — edit quantities or the email</li>
            <li>Approve to send, create a CRM deal, and assign a follow-up</li>
          </ol>
          <div className="rounded-lg border border-slate-800/80 bg-slate-950/50 p-3 text-[11px] leading-relaxed text-slate-500">
            Optional: connect n8n or another orchestrator via Workflows for inbound email automation.
          </div>
          <Link to="/emails" className="btn-primary w-full justify-center">
            Start with Inbox <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>
    </div>
  )
}
