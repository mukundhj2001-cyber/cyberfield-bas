import { Bot, Shield, Database, Mail } from 'lucide-react'

const agents = [
  {
    name: 'Quote Agent',
    status: 'active',
    desc: 'Classifies inbound RFQs, extracts line items, prices from catalog, drafts quote + email.',
    icon: Bot,
  },
  {
    name: 'Approval Gate',
    status: 'active',
    desc: 'Holds outbound actions until a human reviews and edits the draft.',
    icon: Shield,
  },
  {
    name: 'CRM Writer',
    status: 'active',
    desc: 'On approve: upserts contact, creates deal at quote_sent, logs activity.',
    icon: Database,
  },
  {
    name: 'Inbox Adapter',
    status: 'mock',
    desc: 'v1 uses seeded mock mailbox — Gmail/Outlook connectors planned later.',
    icon: Mail,
  },
]

export function Agents() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-white">AI Agents</h1>
        <p className="mt-1 text-sm text-slate-400">
          Autonomous workers with human approval — not a chatbot
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {agents.map((a) => (
          <div
            key={a.name}
            className="rounded-2xl border border-slate-800 bg-slate-900/40 p-5"
          >
            <div className="flex items-start gap-3">
              <div className="rounded-xl bg-slate-800 p-2.5 text-cyan-300">
                <a.icon className="h-4 w-4" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="font-semibold text-white">{a.name}</h2>
                  <span className="rounded-full border border-slate-700 px-2 py-0.5 text-[10px] uppercase tracking-wide text-slate-400">
                    {a.status}
                  </span>
                </div>
                <p className="mt-2 text-sm text-slate-400">{a.desc}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
