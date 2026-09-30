import { Bot, Shield, Database, Mail, Webhook } from 'lucide-react'
import { Badge } from '../components/Badge'

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
    name: 'Gmail Ingest',
    status: 'mock',
    desc: 'Sync button pulls mock Gmail-like messages by default. Optional Google OAuth when credentials are set.',
    icon: Mail,
  },
  {
    name: 'n8n Webhooks',
    status: 'active',
    desc: 'POST /webhooks/n8n/email and /trigger-quote for external orchestration (optional shared secret).',
    icon: Webhook,
  },
]

export function Agents() {
  return (
    <div className="space-y-4">
      <div>
        <div className="text-[10px] font-medium uppercase tracking-[0.16em] text-cyan-500/80">
          Autonomy layer
        </div>
        <h1 className="mt-1 text-xl font-semibold text-white">AI Agents</h1>
        <p className="mt-1 text-sm text-slate-400">
          Autonomous workers with human approval — not a chatbot
        </p>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {agents.map((a) => (
          <div key={a.name} className="ops-panel rounded-xl p-4">
            <div className="flex items-start gap-3">
              <div className="rounded-lg border border-slate-800 bg-slate-950 p-2 text-cyan-300">
                <a.icon className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-sm font-semibold text-white">{a.name}</h2>
                  <Badge status={a.status} />
                </div>
                <p className="mt-1.5 text-xs leading-relaxed text-slate-400">{a.desc}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
