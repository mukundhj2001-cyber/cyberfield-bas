import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Ticket as TicketIcon } from 'lucide-react'
import { api } from '../api/client'
import type { Ticket } from '../lib/types'
import { Badge } from '../components/Badge'
import { EmptyState } from '../components/EmptyState'
import { PageHeader } from '../components/PageHeader'
import { ErrorBanner } from '../components/ErrorBanner'
import { LoadingState } from '../components/LoadingState'

export function Tickets() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .tickets()
      .then(setTickets)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Service desk"
        title="Tickets"
        description="Support, escalation, and ops tickets created when you approve a staged plan"
      />

      {error ? <ErrorBanner message={error} /> : null}

      {loading ? (
        <LoadingState label="Loading tickets…" />
      ) : (
        <div className="grid gap-2.5">
          {tickets.length === 0 ? (
            <div className="ops-panel rounded-xl">
              <EmptyState
                title="No tickets yet"
                description="Approve a support, escalation, or complaint action plan to open a ticket."
                icon={TicketIcon}
                actions={
                  <Link to="/approvals" className="btn-primary">
                    Review approvals
                  </Link>
                }
              />
            </div>
          ) : (
            tickets.map((t) => (
              <div key={t.id} className="ops-panel rounded-xl p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="text-[14px] font-medium text-white">{t.title}</div>
                    <p className="mt-1 line-clamp-3 text-xs leading-relaxed text-slate-400">
                      {t.description}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {t.escalate ? <Badge status="Critical" label="Escalated" /> : null}
                    <Badge status={t.priority} />
                    <Badge status={t.status} />
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap gap-3 text-[11px] text-slate-500">
                  <span>Assignee: {t.assignee}</span>
                  <span>Category: {t.category.replaceAll('_', ' ')}</span>
                  {t.related_email_id ? <span>Email #{t.related_email_id}</span> : null}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
