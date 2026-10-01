import { Bot, Shield, Database, Mail, Webhook } from 'lucide-react'
import { Badge } from '../components/Badge'
import { PageHeader } from '../components/PageHeader'

const agents = [
  {
    name: 'Quote Agent',
    status: 'active',
    desc: 'Classifies inbound RFQs, extracts line items, prices from your catalog, and drafts the quote plus reply email.',
    icon: Bot,
  },
  {
    name: 'Approval Gate',
    status: 'active',
    desc: 'Holds outbound actions until a human reviews and edits the draft — nothing sends without approval.',
    icon: Shield,
  },
  {
    name: 'CRM Writer',
    status: 'active',
    desc: 'On approve: upserts the contact, creates a deal at Quote sent, and logs activity.',
    icon: Database,
  },
  {
    name: 'Gmail Ingest',
    status: 'ready',
    desc: 'Sync pulls business mail into Inbox. Connect Google OAuth for live Gmail, or use offline mode until credentials are set.',
    icon: Mail,
  },
  {
    name: 'Webhook Ingest',
    status: 'active',
    desc: 'Accepts inbound email and quote triggers from n8n or any orchestrator. Optional shared-secret authentication.',
    icon: Webhook,
  },
]

export function Agents() {
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Autonomy layer"
        title="AI Agents"
        description="Autonomous workers with human approval — not a chatbot"
      />
      <div className="grid gap-3 md:grid-cols-2">
        {agents.map((a) => (
          <div key={a.name} className="ops-panel rounded-xl p-4 transition hover:border-slate-700">
            <div className="flex items-start gap-3">
              <div className="rounded-lg border border-slate-800 bg-slate-950 p-2.5 text-cyan-300">
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
