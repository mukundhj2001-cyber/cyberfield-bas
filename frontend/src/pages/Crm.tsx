import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Users } from 'lucide-react'
import { api } from '../api/client'
import type { Contact, Deal, Product } from '../lib/types'
import { Badge } from '../components/Badge'
import { EmptyState } from '../components/EmptyState'
import { PageHeader } from '../components/PageHeader'
import { ErrorBanner } from '../components/ErrorBanner'
import { LoadingState } from '../components/LoadingState'

export function Crm() {
  const [tab, setTab] = useState<'deals' | 'contacts' | 'products'>('deals')
  const [deals, setDeals] = useState<Deal[]>([])
  const [contacts, setContacts] = useState<Contact[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.deals(), api.contacts(), api.products()])
      .then(([d, c, p]) => {
        setDeals(d)
        setContacts(c)
        setProducts(p)
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const tabLabels: Record<typeof tab, string> = {
    deals: 'Deals',
    contacts: 'Contacts',
    products: 'Products',
  }

  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="Pipeline"
        title="CRM"
        description="Contacts and deals populate when a quote is approved"
      />

      {error ? <ErrorBanner message={error} /> : null}

      <div className="flex w-fit gap-1 rounded-lg border border-slate-800 bg-slate-950/50 p-1">
        {(['deals', 'contacts', 'products'] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={[
              'rounded-md px-3 py-1.5 text-xs font-medium transition',
              tab === t
                ? 'bg-cyan-500/15 text-cyan-300 shadow-[inset_0_0_0_1px_rgba(34,211,238,0.25)]'
                : 'text-slate-400 hover:text-slate-200',
            ].join(' ')}
          >
            {tabLabels[t]}
          </button>
        ))}
      </div>

      {loading ? (
        <LoadingState label="Loading CRM…" />
      ) : (
        <div className="ops-panel overflow-hidden rounded-xl">
          {tab === 'deals' && (
            <table className="ops-table min-w-full text-left text-sm">
              <thead className="text-[10px] uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2.5">Title</th>
                  <th className="px-4 py-2.5">Contact</th>
                  <th className="px-4 py-2.5">Amount</th>
                  <th className="px-4 py-2.5">Stage</th>
                  <th className="px-4 py-2.5">Quote</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {deals.length === 0 ? (
                  <tr>
                    <td colSpan={5}>
                      <EmptyState
                        title="No deals yet"
                        description="Approve a quote to create a CRM deal at the Quote sent stage."
                        icon={Users}
                        actions={
                          <Link to="/approvals" className="btn-primary">
                            Open Approvals
                          </Link>
                        }
                      />
                    </td>
                  </tr>
                ) : (
                  deals.map((d) => (
                    <tr key={d.id}>
                      <td className="px-4 py-2.5 text-[13px] text-slate-100">{d.title}</td>
                      <td className="px-4 py-2.5 text-[13px] text-slate-300">
                        {d.contact?.name || '—'}
                        <div className="text-[11px] text-slate-500">{d.contact?.company}</div>
                      </td>
                      <td className="px-4 py-2.5 text-[13px] font-medium text-cyan-300">
                        ${d.amount.toLocaleString()} {d.currency}
                      </td>
                      <td className="px-4 py-2.5">
                        <Badge status={d.stage} />
                      </td>
                      <td className="px-4 py-2.5 font-mono text-[11px] text-slate-400">
                        {d.quote_ref}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}

          {tab === 'contacts' && (
            <table className="ops-table min-w-full text-left text-sm">
              <thead className="text-[10px] uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2.5">Name</th>
                  <th className="px-4 py-2.5">Email</th>
                  <th className="px-4 py-2.5">Company</th>
                  <th className="px-4 py-2.5">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {contacts.length === 0 ? (
                  <tr>
                    <td colSpan={4}>
                      <EmptyState
                        title="No contacts yet"
                        description="Contacts appear automatically when a quote is approved."
                        icon={Users}
                        actions={
                          <Link to="/emails" className="btn-primary">
                            Run a quote
                          </Link>
                        }
                      />
                    </td>
                  </tr>
                ) : (
                  contacts.map((c) => (
                    <tr key={c.id}>
                      <td className="px-4 py-2.5 text-[13px] text-slate-100">{c.name}</td>
                      <td className="px-4 py-2.5 text-[13px] text-slate-300">{c.email}</td>
                      <td className="px-4 py-2.5 text-[13px] text-slate-300">{c.company}</td>
                      <td className="px-4 py-2.5 text-[11px] tabular-nums text-slate-500">
                        {new Date(c.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}

          {tab === 'products' && (
            <table className="ops-table min-w-full text-left text-sm">
              <thead className="text-[10px] uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2.5">SKU</th>
                  <th className="px-4 py-2.5">Name</th>
                  <th className="px-4 py-2.5">Category</th>
                  <th className="px-4 py-2.5">Price</th>
                  <th className="px-4 py-2.5">Stock</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80">
                {products.length === 0 ? (
                  <tr>
                    <td colSpan={5}>
                      <EmptyState
                        title="Catalog empty"
                        description="Add products in the backend catalog to enable automatic pricing."
                        icon={Users}
                      />
                    </td>
                  </tr>
                ) : (
                  products.map((p) => (
                    <tr key={p.id}>
                      <td className="px-4 py-2.5 font-mono text-[11px] text-cyan-300">{p.sku}</td>
                      <td className="px-4 py-2.5 text-[13px] text-slate-100">{p.name}</td>
                      <td className="px-4 py-2.5 text-[13px] text-slate-400">{p.category}</td>
                      <td className="px-4 py-2.5 text-[13px] text-slate-200">
                        ${p.unit_price.toFixed(2)} / {p.unit}
                      </td>
                      <td className="px-4 py-2.5 tabular-nums text-[13px] text-slate-400">
                        {p.in_stock}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
