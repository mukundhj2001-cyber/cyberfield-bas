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
    cyan: 'from-cyan-500/15 to-transparent text-cyan-300',
    amber: 'from-amber-500/15 to-transparent text-amber-300',
    emerald: 'from-emerald-500/15 to-transparent text-emerald-300',
    violet: 'from-violet-500/15 to-transparent text-violet-300',
  }
  return (
    <div className="ops-panel relative overflow-hidden rounded-xl p-3.5">
      <div
        className={`pointer-events-none absolute inset-0 bg-gradient-to-br ${accents[accent]} opacity-80`}
      />
      <div className="relative flex items-start justify-between gap-2">
        <div>
          <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">
            {label}
          </div>
          <div className="mt-1.5 text-2xl font-semibold tabular-nums tracking-tight text-white">
            {value}
          </div>
          {hint ? <div className="mt-1 text-[11px] text-slate-500">{hint}</div> : null}
        </div>
        <div className="rounded-lg border border-slate-700/60 bg-slate-950/50 p-2 text-cyan-300">
          <Icon className="h-3.5 w-3.5" />
        </div>
      </div>
    </div>
  )
}
