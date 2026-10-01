const tones: Record<string, string> = {
  pending: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
  approved: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  rejected: 'border-rose-500/30 bg-rose-500/10 text-rose-300',
  unread: 'border-sky-500/30 bg-sky-500/10 text-sky-300',
  quoted: 'border-violet-500/30 bg-violet-500/10 text-violet-300',
  processing: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300',
  ignored: 'border-slate-600/40 bg-slate-700/20 text-slate-400',
  open: 'border-sky-500/30 bg-sky-500/10 text-sky-300',
  in_progress: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300',
  done: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  quote_sent: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  qualified: 'border-sky-500/30 bg-sky-500/10 text-sky-300',
  Critical: 'border-rose-500/40 bg-rose-500/15 text-rose-200',
  High: 'border-orange-500/40 bg-orange-500/15 text-orange-200',
  Medium: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
  Low: 'border-slate-500/30 bg-slate-500/10 text-slate-300',
  high: 'border-rose-500/30 bg-rose-500/10 text-rose-300',
  medium: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
  low: 'border-slate-500/30 bg-slate-500/10 text-slate-300',
  active: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  ready: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300',
  standby: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
  mock: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
  Mock: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
  Connected: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  oauth: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  secured: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',

  action_staged: 'border-violet-500/30 bg-violet-500/10 text-violet-300',
  resolved: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  escalated: 'border-rose-500/40 bg-rose-500/15 text-rose-200',
  critical: 'border-rose-500/40 bg-rose-500/15 text-rose-200',
  rfq_quote: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300',
  support_complaint: 'border-orange-500/30 bg-orange-500/10 text-orange-200',
  escalation: 'border-rose-500/40 bg-rose-500/15 text-rose-200',
  shipping_status: 'border-sky-500/30 bg-sky-500/10 text-sky-300',
  purchase_order: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  invoice_payment: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
  meeting_request: 'border-violet-500/30 bg-violet-500/10 text-violet-300',
  product_info: 'border-sky-500/30 bg-sky-500/10 text-sky-300',
  change_order: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300',
  contract_partnership: 'border-violet-500/30 bg-violet-500/10 text-violet-300',
  vendor_onboarding: 'border-slate-500/30 bg-slate-500/10 text-slate-300',
  default: 'border-slate-600/40 bg-slate-700/30 text-slate-300',
}

/** Product-facing labels — never surface raw “mock/demo” to users. */
const labels: Record<string, string> = {
  mock: 'Offline mode',
  Mock: 'Offline mode',
  Connected: 'Gmail connected',
  oauth: 'Gmail connected',
  quote_sent: 'Quote sent',
  in_progress: 'In progress',
  ready: 'Ready',
  standby: 'Standby',
  secured: 'Secured',
  open: 'Open',
  active: 'Active',
  pending: 'Pending',
  approved: 'Approved',
  rejected: 'Rejected',
  unread: 'Unread',
  quoted: 'Quoted',
  processing: 'Processing',
  ignored: 'Ignored',
  done: 'Done',

  action_staged: 'Action staged',
  resolved: 'Resolved',
  escalated: 'Escalated',
  rfq_quote: 'RFQ / Quote',
  support_complaint: 'Support',
  shipping_status: 'Shipping',
  purchase_order: 'Purchase order',
  invoice_payment: 'Invoice / Payment',
  meeting_request: 'Meeting',
  product_info: 'Product info',
  change_order: 'Change order',
  contract_partnership: 'Contract',
  vendor_onboarding: 'Vendor onboard',
  escalation: 'Escalation',
  general_ops: 'General ops',
  other_business: 'Other',
  qualified: 'Qualified',
}

export function Badge({ status, label }: { status: string; label?: string }) {
  const tone = tones[status] || tones.default
  const text = label ?? labels[status] ?? status.replaceAll('_', ' ')
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${tone}`}
    >
      {text}
    </span>
  )
}
