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
    }>('/health'),
  stats: () => request<DashboardStats>('/dashboard/stats'),
  emails: (opts?: { priority?: string; sort?: string }) => {
    const params = new URLSearchParams()
    if (opts?.priority) params.set('priority', opts.priority)
    if (opts?.sort) params.set('sort', opts.sort)
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
}

export const apiBase = BASE
