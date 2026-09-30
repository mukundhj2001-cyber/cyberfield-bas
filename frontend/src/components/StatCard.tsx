import type { LucideIcon } from 'lucide-react'

export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
}: {
  label: string
  value: string | number
  hint?: string
  icon: LucideIcon
}) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4 shadow-sm shadow-black/20">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-wider text-slate-500">{label}</div>
          <div className="mt-2 text-2xl font-semibold text-white">{value}</div>
          {hint ? <div className="mt-1 text-xs text-slate-500">{hint}</div> : null}
        </div>
        <div className="rounded-xl bg-slate-800/80 p-2.5 text-cyan-300">
          <Icon className="h-4 w-4" />
        </div>
      </div>
    </div>
  )
}
