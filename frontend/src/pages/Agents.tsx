import { Bot, Shield, Database, Mail, Webhook, Ticket, Sparkles } from 'lucide-react'
import { Badge } from '../components/Badge'
import { PageHeader } from '../components/PageHeader'

const agents = [
  {
    name: 'Intent Classifier',
    status: 'active',
    desc: 'Classifies every business email into RFQ, PO, invoice, shipping, support, escalation, meeting, contract, change order, vendor onboarding, and more.',
    icon: Sparkles,
  },
  {
    name: 'Ops Action Planner',
    status: 'active',
    desc: 'Builds per-intent action plans: draft replies/quotes, stage CRM deals/contacts, tickets/tasks with due dates, KB refs, and escalate when Critical.',
    icon: Bot,
  },
  {
    name: 'Approval Gate',
    status: 'active',
    desc: 'Human approval before any outbound send, CRM create/update, or customer-facing ticket close. Selective apply flags per plan.',
    icon: Shield,
  },
  {
    name: 'CRM Writer',
    status: 'active',
    desc: 'On approve: upserts contacts and creates deals when the staged plan includes CRM steps.',
    icon: Database,
  },
  {
    name: 'Ticket Desk',
    status: 'active',
    desc: 'Opens support and escalation tickets from complaint / VIP / legal-ish intents after approval.',
    icon: Ticket,
  },
  {
    name: 'Gmail Ingest',
    status: 'ready',
    desc: 'Sync pulls business mail, filters noise, classifies intent, and stages plans. OAuth optional; offline mode included.',
    icon: Mail,
  },
  {
    name: 'Webhook Ingest',
    status: 'active',
    desc: 'n8n or any orchestrator can POST inbound email and optionally trigger the full ops workflow.',
    icon: Webhook,
  },
]

export function Agents() {
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Autonomy layer"
        title="AI Agents"
        description="Agency-grade inbound ops workers — automate up to the human gate"
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
