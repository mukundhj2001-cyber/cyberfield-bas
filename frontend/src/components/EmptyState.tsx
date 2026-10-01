import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { Inbox } from 'lucide-react'

export function EmptyState({
  title,
  description,
  icon: Icon = Inbox,
  actions,
}: {
  title: string
  description?: string
  icon?: LucideIcon
  actions?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center px-5 py-14 text-center">
      <div className="mb-4 rounded-2xl border border-slate-800/90 bg-slate-950/70 p-3.5 text-slate-500 shadow-inner">
        <Icon className="h-5 w-5" />
      </div>
      <div className="text-sm font-semibold text-slate-200">{title}</div>
      {description ? (
        <p className="mt-1.5 max-w-md text-[13px] leading-relaxed text-slate-500">{description}</p>
      ) : null}
      {actions ? <div className="mt-5 flex flex-wrap items-center justify-center gap-2">{actions}</div> : null}
    </div>
  )
}
