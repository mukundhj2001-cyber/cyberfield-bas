import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react'

type ToastTone = 'success' | 'error' | 'info'

type ToastItem = {
  id: number
  message: string
  tone: ToastTone
}

type ToastApi = {
  success: (message: string) => void
  error: (message: string) => void
  info: (message: string) => void
}

const ToastContext = createContext<ToastApi | null>(null)

let nextId = 1

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])

  const push = useCallback((message: string, tone: ToastTone) => {
    const id = nextId++
    setItems((prev) => [...prev, { id, message, tone }])
    window.setTimeout(() => {
      setItems((prev) => prev.filter((t) => t.id !== id))
    }, 3800)
  }, [])

  const api = useMemo<ToastApi>(
    () => ({
      success: (m) => push(m, 'success'),
      error: (m) => push(m, 'error'),
      info: (m) => push(m, 'info'),
    }),
    [push],
  )

  const dismiss = (id: number) => setItems((prev) => prev.filter((t) => t.id !== id))

  const toneStyles: Record<ToastTone, string> = {
    success: 'border-emerald-500/30 bg-emerald-950/90 text-emerald-100',
    error: 'border-rose-500/35 bg-rose-950/90 text-rose-100',
    info: 'border-cyan-500/30 bg-slate-950/95 text-cyan-50',
  }
  const icons = {
    success: CheckCircle2,
    error: AlertCircle,
    info: Info,
  }

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2 px-3 sm:px-0">
        {items.map((t) => {
          const Icon = icons[t.tone]
          return (
            <div
              key={t.id}
              className={`toast-enter pointer-events-auto flex items-start gap-2.5 rounded-xl border px-3.5 py-2.5 shadow-xl shadow-black/40 backdrop-blur ${toneStyles[t.tone]}`}
            >
              <Icon className="mt-0.5 h-4 w-4 shrink-0 opacity-90" />
              <div className="min-w-0 flex-1 text-[13px] leading-snug">{t.message}</div>
              <button
                type="button"
                onClick={() => dismiss(t.id)}
                className="rounded-md p-0.5 text-slate-400 hover:bg-white/5 hover:text-slate-200"
                aria-label="Dismiss"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    return {
      success: () => undefined,
      error: () => undefined,
      info: () => undefined,
    }
  }
  return ctx
}
