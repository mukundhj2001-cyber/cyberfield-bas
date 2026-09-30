import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Inbox, ShieldCheck, Users, CheckSquare, Bot, ArrowRight } from 'lucide-react'
import { api } from '../api/client'
import type { DashboardStats } from '../lib/types'
import { StatCard } from '../components/StatCard'

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
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-white">Operations dashboard</h1>
          <p className="mt-1 text-sm text-slate-400">
            Cyberfield BAS · quote-from-email agent · LLM mode:{' '}
            <span className="font-mono text-cyan-300">{stats.llm_mode}</span>
          </p>
        </div>
        <Link
          to="/emails"
          className="inline-flex items-center gap-2 rounded-lg bg-cyan-500 px-3.5 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400"
        >
          Run quote workflow <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Inbox" value={stats.emails_total} hint={`${stats.emails_unread} unread`} icon={Inbox} />
        <StatCard
          label="Pending approvals"
          value={stats.approvals_pending}
          hint="Human-in-the-loop gate"
          icon={ShieldCheck}
        />
        <StatCard label="Open deals" value={stats.deals_open} hint="CRM pipeline" icon={Users} />
        <StatCard label="Open tasks" value={stats.tasks_open} hint="Sales follow-ups" icon={CheckSquare} />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-200">Recent activity</h2>
            <Bot className="h-4 w-4 text-slate-500" />
          </div>
          {stats.recent_activity.length === 0 ? (
            <p className="text-sm text-slate-500">
              No activity yet. Process an RFQ from Inbox to generate a draft quote.
            </p>
          ) : (
            <ul className="space-y-3">
              {stats.recent_activity.map((a) => (
                <li
                  key={a.id}
                  className="flex items-start justify-between gap-3 rounded-xl border border-slate-800/80 bg-slate-950/40 px-3 py-2.5"
                >
                  <div>
                    <div className="text-xs uppercase tracking-wide text-cyan-400/80">{a.kind}</div>
                    <div className="mt-0.5 text-sm text-slate-200">{a.message}</div>
                  </div>
                  <div className="shrink-0 text-[11px] text-slate-500">
                    {new Date(a.created_at).toLocaleString()}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900/80 to-slate-950 p-5">
          <h2 className="text-sm font-semibold text-slate-200">Demo script</h2>
          <ol className="mt-3 list-decimal space-y-2 pl-4 text-sm text-slate-400">
            <li>Open Inbox → select an RFQ email</li>
            <li>Click <span className="text-cyan-300">Run quote workflow</span></li>
            <li>Review draft in Approvals (edit if needed)</li>
            <li>Approve → CRM deal + follow-up task appear</li>
          </ol>
          <p className="mt-4 text-xs text-slate-500">
            Catalog SKUs: bearings, motors, VFDs, pumps, seals, idlers. Mock LLM works offline.
          </p>
        </div>
      </div>
    </div>
  )
}
