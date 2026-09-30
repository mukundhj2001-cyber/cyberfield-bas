import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Task } from '../lib/types'
import { Badge } from '../components/Badge'

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
        <h1 className="text-2xl font-semibold text-white">Tasks</h1>
        <p className="mt-1 text-sm text-slate-400">
          Follow-ups assigned by the quote workflow after approval
        </p>
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      <div className="grid gap-3">
        {tasks.length === 0 ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 px-4 py-10 text-center text-sm text-slate-500">
            No tasks yet. Approve a quote to auto-assign a sales follow-up.
          </div>
        ) : (
          tasks.map((t) => (
            <div
              key={t.id}
              className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div className="text-base font-medium text-white">{t.title}</div>
                  <p className="mt-1 text-sm text-slate-400">{t.description}</p>
                </div>
                <div className="flex gap-2">
                  <Badge status={t.priority} />
                  <Badge status={t.status} />
                </div>
              </div>
              <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-500">
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
