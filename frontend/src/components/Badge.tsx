const tones: Record<string, string> = {
  pending: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
  approved: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  rejected: 'border-rose-500/30 bg-rose-500/10 text-rose-300',
  unread: 'border-sky-500/30 bg-sky-500/10 text-sky-300',
  quoted: 'border-violet-500/30 bg-violet-500/10 text-violet-300',
  processing: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300',
  ignored: 'border-slate-600/40 bg-slate-700/20 text-slate-400',
  open: 'border-sky-500/30 bg-sky-500/10 text-sky-300',
  in_progress: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300',
  done: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  quote_sent: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  qualified: 'border-sky-500/30 bg-sky-500/10 text-sky-300',
  high: 'border-rose-500/30 bg-rose-500/10 text-rose-300',
  medium: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
  low: 'border-slate-500/30 bg-slate-500/10 text-slate-300',
  active: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  mock: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
  oauth: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  secured: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  default: 'border-slate-600/40 bg-slate-700/30 text-slate-300',
}

export function Badge({ status }: { status: string }) {
  const tone = tones[status] || tones.default
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${tone}`}
    >
      {status.replaceAll('_', ' ')}
    </span>
  )
}
