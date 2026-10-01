import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard,
  Inbox,
  ShieldCheck,
  Users,
  Ticket,
  CheckSquare,
  Bot,
  Workflow,
  Building2,
  Zap,
  Activity,
} from 'lucide-react'

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/emails', label: 'Inbox', icon: Inbox },
  { to: '/approvals', label: 'Approvals', icon: ShieldCheck },
  { to: '/crm', label: 'CRM', icon: Users },
  { to: '/tickets', label: 'Tickets', icon: Ticket },
  { to: '/tasks', label: 'Tasks', icon: CheckSquare },
  { to: '/agents', label: 'AI Agents', icon: Bot },
  { to: '/workflows', label: 'Workflows', icon: Workflow },
]

export function Layout() {
  return (
    <div className="flex min-h-screen text-slate-100">
      <aside className="flex w-[15.5rem] shrink-0 flex-col border-r border-slate-800/90 bg-slate-950/95 backdrop-blur-md">
        <div className="border-b border-slate-800/90 px-4 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 to-sky-700 shadow-lg shadow-cyan-500/20">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <div className="min-w-0">
              <div className="truncate text-[13px] font-semibold tracking-wide text-white">
                Cyberfield BAS
              </div>
              <div className="truncate text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500">
                Business Automation
              </div>
            </div>
          </div>
        </div>

        <nav className="flex-1 space-y-0.5 px-2.5 py-3.5">
          <div className="mb-2.5 px-2.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-600">
            Workspace
          </div>
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                [
                  'group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] font-medium transition',
                  isActive
                    ? 'bg-cyan-500/10 text-cyan-100 shadow-[inset_0_0_0_1px_rgba(34,211,238,0.3)]'
                    : 'text-slate-400 hover:bg-slate-900/90 hover:text-slate-100',
                ].join(' ')
              }
            >
              <item.icon className="h-3.5 w-3.5 shrink-0 opacity-90" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="space-y-2 border-t border-slate-800/90 p-3">
          <div className="rounded-xl border border-slate-800 bg-slate-900/55 p-3">
            <div className="mb-1.5 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
              <Building2 className="h-3 w-3 text-cyan-400" />
              Organization
            </div>
            <div className="text-[13px] font-semibold text-white">Northwind Industrial</div>
            <div className="mt-0.5 text-[10px] text-slate-500">Production workspace</div>
          </div>
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 items-center justify-between border-b border-slate-800/90 bg-slate-950/50 px-5 backdrop-blur-md">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Activity className="h-3.5 w-3.5 text-cyan-500/80" />
            Multi-intent ops · human-in-the-loop
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-semibold text-emerald-300">
              <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-emerald-400" />
              System online
            </span>
          </div>
        </header>
        <div className="flex-1 overflow-auto p-5 md:p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
