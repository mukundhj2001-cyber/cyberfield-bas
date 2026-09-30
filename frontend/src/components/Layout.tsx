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
  Activity,
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
    <div className="flex min-h-screen text-slate-100">
      <aside className="flex w-56 shrink-0 flex-col border-r border-slate-800/90 bg-slate-950/90 backdrop-blur">
        <div className="border-b border-slate-800/90 px-3.5 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-cyan-400 to-sky-700 shadow-md shadow-cyan-500/25">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <div className="min-w-0">
              <div className="truncate text-[13px] font-semibold tracking-wide text-white">
                Cyberfield BAS
              </div>
              <div className="text-[10px] uppercase tracking-[0.16em] text-slate-500">
                Ops automation
              </div>
            </div>
          </div>
        </div>

        <nav className="flex-1 space-y-0.5 px-2 py-3">
          <div className="mb-2 px-2 text-[10px] font-medium uppercase tracking-[0.14em] text-slate-600">
            Console
          </div>
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                [
                  'group flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] transition',
                  isActive
                    ? 'bg-cyan-500/10 text-cyan-200 shadow-[inset_0_0_0_1px_rgba(34,211,238,0.28)]'
                    : 'text-slate-400 hover:bg-slate-900/80 hover:text-slate-100',
                ].join(' ')
              }
            >
              <item.icon className="h-3.5 w-3.5 shrink-0 opacity-90" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="space-y-2 border-t border-slate-800/90 p-2.5">
          <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-2.5">
            <div className="mb-1 flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-slate-500">
              <Package className="h-3 w-3 text-cyan-400" />
              Tenant
            </div>
            <div className="text-[13px] font-semibold text-white">Northwind Industrial</div>
            <div className="mt-0.5 text-[10px] text-slate-500">Demo · v0.2</div>
          </div>
        </div>
      </aside>

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-12 items-center justify-between border-b border-slate-800/90 bg-slate-950/40 px-5 backdrop-blur">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Activity className="h-3.5 w-3.5 text-cyan-500/80" />
            Autonomous ops · human-in-the-loop
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-300">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
              Online
            </span>
          </div>
        </header>
        <div className="flex-1 overflow-auto p-5">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
