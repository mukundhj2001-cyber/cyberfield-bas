import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckSquare } from 'lucide-react'
import { api } from '../api/client'
import type { Task } from '../lib/types'
import { Badge } from '../components/Badge'
import { EmptyState } from '../components/EmptyState'
import { PageHeader } from '../components/PageHeader'
import { ErrorBanner } from '../components/ErrorBanner'
import { LoadingState } from '../components/LoadingState'

export function Tasks() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .tasks()
      .then(setTasks)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Work queue"
        title="Tasks"
        description="Follow-ups assigned automatically after a quote is approved"
      />

      {error ? <ErrorBanner message={error} /> : null}

      {loading ? (
        <LoadingState label="Loading tasks…" />
      ) : (
        <div className="grid gap-2.5">
          {tasks.length === 0 ? (
            <div className="ops-panel rounded-xl">
              <EmptyState
                title="No tasks yet"
                description="Approve a quote to auto-assign a sales follow-up for your team."
                icon={CheckSquare}
                actions={
                  <Link to="/approvals" className="btn-primary">
                    Review approvals
                  </Link>
                }
              />
            </div>
          ) : (
            tasks.map((t) => (
              <div key={t.id} className="ops-panel rounded-xl p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-[14px] font-medium text-white">{t.title}</div>
                    <p className="mt-1 text-xs leading-relaxed text-slate-400">{t.description}</p>
                  </div>
                  <div className="flex gap-1.5">
                    <Badge status={t.priority} />
                    <Badge status={t.status} />
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-3 text-[11px] text-slate-500">
                  <span>Assignee: {t.assignee}</span>
                  {t.due_at ? <span>Due: {new Date(t.due_at).toLocaleString()}</span> : null}
                  {t.related_deal_id ? <span>Deal #{t.related_deal_id}</span> : null}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
