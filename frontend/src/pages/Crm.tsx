import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Contact, Deal, Product } from '../lib/types'
import { Badge } from '../components/Badge'

export function Crm() {
  const [tab, setTab] = useState<'deals' | 'contacts' | 'products'>('deals')
  const [deals, setDeals] = useState<Deal[]>([])
  const [contacts, setContacts] = useState<Contact[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([api.deals(), api.contacts(), api.products()])
      .then(([d, c, p]) => {
        setDeals(d)
        setContacts(c)
        setProducts(p)
      })
      .catch((e: Error) => setError(e.message))
  }, [])

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-white">CRM</h1>
        <p className="mt-1 text-sm text-slate-400">
          Contacts & deals populate when a quote is approved
        </p>
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      <div className="flex gap-2">
        {(['deals', 'contacts', 'products'] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={[
              'rounded-lg px-3 py-1.5 text-sm capitalize',
              tab === t
                ? 'bg-cyan-500/15 text-cyan-300 ring-1 ring-cyan-500/30'
                : 'text-slate-400 hover:bg-slate-900',
            ].join(' ')}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/40">
        {tab === 'deals' && (
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-950/70 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Contact</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Stage</th>
                <th className="px-4 py-3">Quote</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {deals.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                    No deals yet — approve a quote to create one.
                  </td>
                </tr>
              ) : (
                deals.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-950/40">
                    <td className="px-4 py-3 text-slate-100">{d.title}</td>
                    <td className="px-4 py-3 text-slate-300">
                      {d.contact?.name || '—'}
                      <div className="text-xs text-slate-500">{d.contact?.company}</div>
                    </td>
                    <td className="px-4 py-3 font-medium text-cyan-300">
                      ${d.amount.toLocaleString()} {d.currency}
                    </td>
                    <td className="px-4 py-3">
                      <Badge status={d.stage} />
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">{d.quote_ref}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}

        {tab === 'contacts' && (
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-950/70 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Company</th>
                <th className="px-4 py-3">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {contacts.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-slate-500">
                    CRM contacts are empty until a quote is approved.
                  </td>
                </tr>
              ) : (
                contacts.map((c) => (
                  <tr key={c.id}>
                    <td className="px-4 py-3 text-slate-100">{c.name}</td>
                    <td className="px-4 py-3 text-slate-300">{c.email}</td>
                    <td className="px-4 py-3 text-slate-300">{c.company}</td>
                    <td className="px-4 py-3 text-xs text-slate-500">
                      {new Date(c.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}

        {tab === 'products' && (
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-950/70 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">SKU</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3">Price</th>
                <th className="px-4 py-3">Stock</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {products.map((p) => (
                <tr key={p.id}>
                  <td className="px-4 py-3 font-mono text-xs text-cyan-300">{p.sku}</td>
                  <td className="px-4 py-3 text-slate-100">{p.name}</td>
                  <td className="px-4 py-3 text-slate-400">{p.category}</td>
                  <td className="px-4 py-3 text-slate-200">
                    ${p.unit_price.toFixed(2)} / {p.unit}
                  </td>
                  <td className="px-4 py-3 text-slate-400">{p.in_stock}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
