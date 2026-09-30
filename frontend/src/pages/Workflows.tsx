import { Link } from 'react-router-dom'

const steps = [
  'Inbound email (mock inbox)',
  'Classify + extract line items (LLM or mock)',
  'Price lookup against product catalog',
  'Draft quote PDF-fields + reply email',
  'Human approval (edit allowed)',
  'On approve: mock send log → CRM deal → assign task',
]

export function Workflows() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-white">Workflows</h1>
        <p className="mt-1 text-sm text-slate-400">Flagship: quote_from_email</p>
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-white">quote_from_email</h2>
            <p className="text-sm text-slate-400">
              State machine with human-in-the-loop gate (LangGraph-shaped stages)
            </p>
          </div>
          <Link
            to="/emails"
            className="rounded-lg bg-cyan-500 px-3.5 py-2 text-sm font-medium text-slate-950 hover:bg-cyan-400"
          >
            Open inbox to run
          </Link>
        </div>
        <ol className="space-y-3">
          {steps.map((step, i) => (
            <li
              key={step}
              className="flex items-start gap-3 rounded-xl border border-slate-800 bg-slate-950/50 px-3 py-2.5"
            >
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-cyan-500/15 text-xs font-semibold text-cyan-300">
                {i + 1}
              </span>
              <span className="text-sm text-slate-300">{step}</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}
