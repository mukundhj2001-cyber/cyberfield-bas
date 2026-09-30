import type { LucideIcon } from 'lucide-react'
import { Inbox } from 'lucide-react'

export function EmptyState({
  title,
  description,
  icon: Icon = Inbox,
}: {
  title: string
  description?: string
  icon?: LucideIcon
}) {
  return (
    <div className="flex flex-col items-center justify-center px-4 py-12 text-center">
      <div className="mb-3 rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-slate-500">
        <Icon className="h-5 w-5" />
      </div>
      <div className="text-sm font-medium text-slate-300">{title}</div>
      {description ? <p className="mt-1 max-w-sm text-xs text-slate-500">{description}</p> : null}
    </div>
  )
}
