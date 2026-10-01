import type { LucideIcon } from 'lucide-react'

export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  accent = 'cyan',
}: {
  label: string
  value: string | number
  hint?: string
  icon: LucideIcon
  accent?: 'cyan' | 'amber' | 'emerald' | 'violet'
}) {
  const accents = {
    cyan: {
      wash: 'from-cyan-500/18 via-cyan-500/5 to-transparent',
      icon: 'text-cyan-300 border-cyan-500/20',
    },
    amber: {
      wash: 'from-amber-500/18 via-amber-500/5 to-transparent',
      icon: 'text-amber-300 border-amber-500/20',
    },
    emerald: {
      wash: 'from-emerald-500/18 via-emerald-500/5 to-transparent',
      icon: 'text-emerald-300 border-emerald-500/20',
    },
    violet: {
      wash: 'from-violet-500/18 via-violet-500/5 to-transparent',
      icon: 'text-violet-300 border-violet-500/20',
    },
  }
  const a = accents[accent]
  return (
    <div className="ops-panel relative overflow-hidden rounded-xl p-4">
      <div className={`pointer-events-none absolute inset-0 bg-gradient-to-br ${a.wash}`} />
      <div className="relative flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">
            {label}
          </div>
          <div className="mt-2 text-[1.65rem] font-semibold tabular-nums tracking-tight text-white">
            {value}
          </div>
          {hint ? <div className="mt-1.5 text-[11px] text-slate-500">{hint}</div> : null}
        </div>
        <div className={`rounded-lg border bg-slate-950/55 p-2 ${a.icon}`}>
          <Icon className="h-3.5 w-3.5" />
        </div>
      </div>
    </div>
  )
}
