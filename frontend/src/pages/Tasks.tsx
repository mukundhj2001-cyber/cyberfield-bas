import { useEffect, useState } from 'react'
import { CheckSquare } from 'lucide-react'
import { api } from '../api/client'
import type { Task } from '../lib/types'
import { Badge } from '../components/Badge'
import { EmptyState } from '../components/EmptyState'

export function Tasks() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .tasks()
      .then(setTasks)
      .catch((e: Error) => setError(e.message))
  }, [])

  return (
    <div className="space-y-4">
      <div>
        <div className="text-[10px] font-medium uppercase tracking-[0.16em] text-cyan-500/80">
          Work queue
        </div>
        <h1 className="mt-1 text-xl font-semibold text-white">Tasks</h1>
        <p className="mt-1 text-sm text-slate-400">
          Follow-ups assigned by the quote workflow after approval
        </p>
      </div>

      {error ? (
        <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      <div className="grid gap-2.5">
        {tasks.length === 0 ? (
          <div className="ops-panel rounded-xl">
            <EmptyState
              title="No tasks yet"
              description="Approve a quote to auto-assign a sales follow-up."
              icon={CheckSquare}
            />
          </div>
        ) : (
          tasks.map((t) => (
            <div key={t.id} className="ops-panel rounded-xl p-3.5">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div className="text-[14px] font-medium text-white">{t.title}</div>
                  <p className="mt-1 text-xs text-slate-400">{t.description}</p>
                </div>
                <div className="flex gap-1.5">
                  <Badge status={t.priority} />
                  <Badge status={t.status} />
                </div>
              </div>
              <div className="mt-2.5 flex flex-wrap gap-3 text-[11px] text-slate-500">
                <span>Assignee: {t.assignee}</span>
                {t.due_at ? <span>Due: {new Date(t.due_at).toLocaleString()}</span> : null}
                {t.related_deal_id ? <span>Deal #{t.related_deal_id}</span> : null}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
