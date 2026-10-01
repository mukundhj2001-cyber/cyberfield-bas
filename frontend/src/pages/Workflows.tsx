import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Copy, Check, ArrowRight } from 'lucide-react'
import { api, apiBase } from '../api/client'
import type { WebhookInfo } from '../lib/types'
import { Badge } from '../components/Badge'
import { PageHeader } from '../components/PageHeader'
import { useToast } from '../components/Toast'

const steps = [
  'Inbound email (inbox sync or integration webhook)',
  'Classify RFQ and extract line items',
  'Price lookup against product catalog',
  'Draft quote fields and reply email',
  'Human approval (edits allowed)',
  'On approve: send email → CRM deal → assign follow-up task',
]

export function Workflows() {
  const [info, setInfo] = useState<WebhookInfo | null>(null)
  const [copied, setCopied] = useState<string | null>(null)
  const toast = useToast()

  useEffect(() => {
    api.webhookInfo().then(setInfo).catch(() => setInfo(null))
  }, [])

  const copy = async (key: string, text: string) => {
    await navigator.clipboard.writeText(text)
    setCopied(key)
    toast.success('Copied to clipboard')
    setTimeout(() => setCopied(null), 1500)
  }

  const emailUrl = `${apiBase}${info?.email_path || '/webhooks/n8n/email'}`
  const triggerUrl = `${apiBase}${info?.trigger_quote_path || '/webhooks/n8n/trigger-quote'}`
  const examplePayload = JSON.stringify(
    info?.sample_email_payload || {
      from_address: 'buyer@example.com',
      subject: 'RFQ — NW-BRG-6205 × 100',
      body: 'Please quote 100 × NW-BRG-6205 bearings.',
      run_quote_workflow: false,
    },
    null,
    2,
  )

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Orchestration"
        title="Workflows"
        description="Flagship quote-from-email flow with optional n8n integration"
      />

      <div className="ops-panel rounded-xl p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-white">Quote from email</h2>
              <Badge status="active" />
            </div>
            <p className="mt-1 text-xs text-slate-400">
              End-to-end state machine with a human-in-the-loop approval gate
            </p>
          </div>
          <Link to="/emails" className="btn-primary">
            Open inbox to run <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
        <ol className="space-y-2">
          {steps.map((step, i) => (
            <li
              key={step}
              className="flex items-start gap-3 rounded-lg border border-slate-800/80 bg-slate-950/40 px-3 py-2.5"
            >
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-cyan-500/15 text-[10px] font-semibold text-cyan-300">
                {i + 1}
              </span>
              <span className="text-[13px] text-slate-300">{step}</span>
            </li>
          ))}
        </ol>
      </div>

      <div className="ops-panel-glow rounded-xl p-5">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <h2 className="text-base font-semibold text-white">Integrations</h2>
          <Badge status={info?.secret_required ? 'secured' : 'open'} label={info?.secret_required ? 'Secured' : 'Open'} />
        </div>
        <p className="mb-4 text-xs leading-relaxed text-slate-400">
          {info?.notes?.replace(/open demo/gi, 'open access') ||
            'Point n8n (or any orchestrator) at the email webhook. Use a shared secret in production via N8N_WEBHOOK_SECRET.'}
        </p>

        <div className="grid gap-3 lg:grid-cols-2">
          <EndpointCard
            label="Ingest email"
            method="POST"
            url={emailUrl}
            copied={copied === 'email'}
            onCopy={() => copy('email', emailUrl)}
          />
          <EndpointCard
            label="Trigger quote"
            method="POST"
            url={triggerUrl}
            copied={copied === 'trigger'}
            onCopy={() => copy('trigger', triggerUrl)}
          />
        </div>

        <div className="mt-4">
          <div className="mb-1.5 flex items-center justify-between">
            <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
              Example payload · {info?.secret_header || 'X-Webhook-Secret'}
              {info?.secret_required ? ' (required)' : ' (optional)'}
            </div>
            <button
              type="button"
              onClick={() => copy('payload', examplePayload)}
              className="inline-flex items-center gap-1 text-[10px] font-medium text-cyan-400 hover:text-cyan-300"
            >
              {copied === 'payload' ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
              Copy
            </button>
          </div>
          <pre className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950/70 p-3 font-mono text-[11px] text-slate-300">
            {examplePayload}
          </pre>
        </div>

        <p className="mt-3 text-[11px] text-slate-500">
          Example workflow:{' '}
          <code className="font-mono text-cyan-400/90">examples/n8n/gmail-to-bas.json</code>
        </p>
      </div>
    </div>
  )
}

function EndpointCard({
  label,
  method,
  url,
  copied,
  onCopy,
}: {
  label: string
  method: string
  url: string
  copied: boolean
  onCopy: () => void
}) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <div className="text-[11px] font-medium text-slate-300">{label}</div>
        <button
          type="button"
          onClick={onCopy}
          className="inline-flex items-center gap-1 text-[10px] font-medium text-cyan-400 hover:text-cyan-300"
        >
          {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
          Copy
        </button>
      </div>
      <div className="flex items-start gap-2">
        <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 font-mono text-[10px] text-emerald-300">
          {method}
        </span>
        <code className="break-all font-mono text-[11px] text-slate-300">{url}</code>
      </div>
    </div>
  )
}
