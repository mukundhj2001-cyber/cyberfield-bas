export type Email = {
  id: number
  message_id: string
  from_address: string
  from_name: string
  to_address: string
  subject: string
  body: string
  received_at: string
  status: string
  intent?: string | null
  extracted?: Record<string, unknown> | null
  attention_score?: number
  attention_label?: string
  attention_meta?: {
    factors?: Record<string, number>
    reasons?: string[]
    estimated_value?: number
  } | null
  business_relevant?: boolean
  business_meta?: {
    is_business?: boolean
    score?: number
    reasons?: string[]
    method?: string
  } | null
}

export type LineItem = {
  sku: string
  name: string
  quantity: number
  unit_price: number
  unit: string
  line_total?: number
  in_stock?: number
}

export type QuoteDraft = {
  quote_ref: string
  company: string
  contact_name: string
  contact_email: string
  currency: string
  line_items: LineItem[]
  subtotal: number
  tax_rate: number
  tax: number
  total: number
  validity_days: number
  payment_terms: string
  lead_time: string
  notes: string
  seller: string
}

export type EmailDraft = {
  to: string
  cc: string
  subject: string
  body: string
}

export type Approval = {
  id: number
  email_id: number
  workflow: string
  status: string
  quote_draft: QuoteDraft
  email_draft: EmailDraft
  agent_trace?: Array<Record<string, unknown>> | null
  reviewed_by?: string | null
  review_note?: string | null
  created_at: string
  decided_at?: string | null
  email?: Email | null
}

export type Contact = {
  id: number
  name: string
  email: string
  company: string
  phone: string
  created_at: string
}

export type Deal = {
  id: number
  title: string
  contact_id?: number | null
  amount: number
  currency: string
  stage: string
  source: string
  quote_ref?: string | null
  notes: string
  created_at: string
  updated_at: string
  contact?: Contact | null
}

export type Task = {
  id: number
  title: string
  description: string
  status: string
  assignee: string
  priority: string
  related_deal_id?: number | null
  related_email_id?: number | null
  created_at: string
  due_at?: string | null
}

export type Activity = {
  id: number
  kind: string
  message: string
  meta?: Record<string, unknown> | null
  created_at: string
}

export type DashboardStats = {
  emails_total: number
  emails_unread: number
  approvals_pending: number
  deals_open: number
  tasks_open: number
  products: number
  recent_activity: Activity[]
  llm_mode: string
}

export type Product = {
  id: number
  sku: string
  name: string
  description: string
  unit_price: number
  unit: string
  category: string
  in_stock: number
}

export type QuoteRunResponse = {
  approval_id: number
  email_id: number
  status: string
  quote_draft: QuoteDraft
  email_draft: EmailDraft
  agent_trace: Array<Record<string, unknown>>
  llm_mode: string
}

export type GmailStatus = {
  mode: string
  connected: boolean
  label: string
  detail: string
  oauth_configured: boolean
  requested_mode?: string | null
  scope?: string | null
  hint?: string | null
}

export type GmailSyncResponse = {
  mode: string
  imported: number
  skipped: number
  filtered?: number
  filtered_subjects?: string[]
  emails: Email[]
  status: GmailStatus
  warning?: string | null
  attention_rescored?: number
}

export type WebhookInfo = {
  email_path: string
  trigger_quote_path: string
  secret_required: boolean
  secret_header: string
  sample_email_payload: Record<string, unknown>
  sample_trigger_payload: Record<string, unknown>
  notes: string
}
