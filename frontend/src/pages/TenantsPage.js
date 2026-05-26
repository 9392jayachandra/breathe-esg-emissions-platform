import React, { useState } from 'react';
import { Plus } from 'lucide-react';
import { createTenant } from '../services/api';

export default function TenantsPage({ tenants, setTenants }) {
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleCreate = async () => {
    if (!name || !slug) { setError('Name and slug required'); return; }
    setLoading(true);
    setError(null);
    try {
      const res = await createTenant({ name, slug });
      setTenants(t => [...t, res.data]);
      setName(''); setSlug('');
    } catch (e) {
      setError(e.response?.data?.slug?.[0] || e.response?.data?.name?.[0] || 'Failed to create client');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Client Management</h1>
        <p>Manage client companies (tenants) for multi-tenancy</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: 20 }}>
        <div className="card">
          <h3 style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 16, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Add Client</h3>
          <div className="form-group">
            <label>Company Name</label>
            <input value={name} onChange={e => { setName(e.target.value); setSlug(e.target.value.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')); }}
              placeholder="Acme Corp" />
          </div>
          <div className="form-group">
            <label>Slug (URL identifier)</label>
            <input value={slug} onChange={e => setSlug(e.target.value)} placeholder="acme-corp" />
          </div>
          {error && <p style={{ color: 'var(--danger)', fontSize: 12, marginBottom: 12 }}>{error}</p>}
          <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }}
            onClick={handleCreate} disabled={loading}>
            <Plus size={14} /> {loading ? 'Creating…' : 'Add Client'}
          </button>
        </div>

        <div className="card">
          <h3 style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 16, textTransform: 'uppercase', letterSpacing: '0.06em' }}>All Clients</h3>
          {tenants.length === 0 ? (
            <p style={{ color: 'var(--muted)', fontSize: 13 }}>No clients yet. Add one to get started.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Slug</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {tenants.map(t => (
                    <tr key={t.id}>
                      <td style={{ fontWeight: 500 }}>{t.name}</td>
                      <td className="mono" style={{ fontSize: 12 }}>{t.slug}</td>
                      <td style={{ color: 'var(--muted)', fontSize: 12 }}>{new Date(t.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
