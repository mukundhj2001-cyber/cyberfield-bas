import type {
  Approval,
  Contact,
  DashboardStats,
  Deal,
  Email,
  Product,
  QuoteRunResponse,
  Task,
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
  health: () => request<{ status: string; llm_mode: string; brand: string }>('/health'),
  stats: () => request<DashboardStats>('/dashboard/stats'),
  emails: () => request<Email[]>('/emails'),
  email: (id: number) => request<Email>(`/emails/${id}`),
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
