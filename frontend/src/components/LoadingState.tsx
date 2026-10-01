export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-10 text-sm text-slate-500">
      <span className="relative flex h-2.5 w-2.5">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-cyan-400/40" />
        <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-cyan-400/80" />
      </span>
      {label}
    </div>
  )
}
