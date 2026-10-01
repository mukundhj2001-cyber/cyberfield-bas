import type {
  Approval,
  Contact,
  DashboardStats,
  Deal,
  Email,
  GmailStatus,
  GmailSyncResponse,
  Product,
  QuoteRunResponse,
  Task,
  Ticket,
  WebhookInfo,
} from '../lib/types'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () =>
    request<{
      status: string
      llm_mode: string
      brand: string
      gmail_mode?: string
      n8n_secret_required?: boolean
      version?: string
    }>('/health'),
  stats: () => request<DashboardStats>('/dashboard/stats'),
  emails: (opts?: {
    priority?: string
    sort?: string
    /** Debug only — default Inbox never sets this */
    include_ignored?: boolean
    include_non_business?: boolean
  }) => {
    const params = new URLSearchParams()
    if (opts?.priority) params.set('priority', opts.priority)
    if (opts?.sort) params.set('sort', opts.sort)
    if (opts?.include_ignored) params.set('include_ignored', 'true')
    if (opts?.include_non_business) params.set('include_non_business', 'true')
    const q = params.toString()
    return request<Email[]>(`/emails${q ? `?${q}` : ''}`)
  },
  email: (id: number) => request<Email>(`/emails/${id}`),
  gmailStatus: () => request<GmailStatus>('/inbox/gmail/status'),
  syncInbox: () =>
    request<GmailSyncResponse>('/inbox/sync', {
      method: 'POST',
      body: JSON.stringify({}),
    }),
  webhookInfo: () => request<WebhookInfo>('/webhooks/n8n/info'),
  runQuote: (body: { email_id?: number; message_id?: string } = {}) =>
    request<QuoteRunResponse>('/workflows/quote/run', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  runOps: (body: { email_id?: number; message_id?: string; auto_stage?: boolean } = {}) =>
    request<QuoteRunResponse>('/workflows/ops/run', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  approvals: (status?: string) =>
    request<Approval[]>(`/approvals${status ? `?status=${status}` : ''}`),
  approval: (id: number) => request<Approval>(`/approvals/${id}`),
  approve: (
    id: number,
    body: {
      reviewed_by?: string
      review_note?: string
      quote_draft?: unknown
      email_draft?: unknown
      apply_flags?: Record<string, boolean>
    },
  ) =>
    request<Approval>(`/approvals/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  reject: (id: number, body: { reviewed_by?: string; review_note?: string }) =>
    request<Approval>(`/approvals/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  contacts: () => request<Contact[]>('/crm/contacts'),
  deals: () => request<Deal[]>('/crm/deals'),
  products: () => request<Product[]>('/crm/products'),
  tasks: (status?: string) =>
    request<Task[]>(`/tasks${status ? `?status=${status}` : ''}`),
  tickets: (status?: string) =>
    request<Ticket[]>(`/tickets${status ? `?status=${status}` : ''}`),
}

export const apiBase = BASE
