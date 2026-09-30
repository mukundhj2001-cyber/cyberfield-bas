import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard,
  Inbox,
  ShieldCheck,
  Users,
  CheckSquare,
  Bot,
  Workflow,
  Package,
  Zap,
} from 'lucide-react'

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/emails', label: 'Inbox', icon: Inbox },
  { to: '/approvals', label: 'Approvals', icon: ShieldCheck },
  { to: '/crm', label: 'CRM', icon: Users },
  { to: '/tasks', label: 'Tasks', icon: CheckSquare },
  { to: '/agents', label: 'AI Agents', icon: Bot },
  { to: '/workflows', label: 'Workflows', icon: Workflow },
]

export function Layout() {
  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <aside className="flex w-64 shrink-0 flex-col border-r border-slate-800/80 bg-slate-950/95">
        <div className="border-b border-slate-800/80 px-5 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-sky-700 shadow-lg shadow-cyan-500/20">
              <Zap className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="text-sm font-semibold tracking-wide text-white">Cyberfield BAS</div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
                Business Automation
              </div>
            </div>
          </div>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-4">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                [
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition',
                  isActive
                    ? 'bg-cyan-500/10 text-cyan-300 ring-1 ring-cyan-500/30'
                    : 'text-slate-400 hover:bg-slate-900 hover:text-slate-100',
                ].join(' ')
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-slate-800/80 px-4 py-4">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
            <div className="mb-1 flex items-center gap-2 text-xs font-medium text-slate-300">
              <Package className="h-3.5 w-3.5 text-cyan-400" />
              Sample tenant
            </div>
            <div className="text-sm font-semibold text-white">Northwind Industrial</div>
            <div className="mt-1 text-[11px] text-slate-500">Ops console · v0.1</div>
          </div>
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-slate-800/80 px-6">
          <div className="text-sm text-slate-400">
            Autonomous ops · human-in-the-loop approvals
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-medium text-emerald-300">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              System online
            </span>
          </div>
        </header>
        <div className="flex-1 overflow-auto p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
