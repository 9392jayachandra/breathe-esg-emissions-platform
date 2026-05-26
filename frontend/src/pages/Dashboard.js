import React, { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { getDashboard, getSources } from '../services/api';

const SCOPE_COLORS = { scope1: '#3b82f6', scope2: '#00e5a0', scope3: '#c084fc' };

export default function Dashboard({ tenantId }) {
  const [stats, setStats] = useState(null);
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      getDashboard(tenantId),
      getSources(tenantId),
    ]).then(([s, src]) => {
      setStats(s.data);
      setSources(src.data);
    }).finally(() => setLoading(false));
  }, [tenantId]);

  if (loading) return <div className="loading">Loading dashboard…</div>;
  if (!stats) return null;

  const scopeData = [
    { name: 'Scope 1', value: +(stats.by_scope.scope1 / 1000).toFixed(2), color: SCOPE_COLORS.scope1 },
    { name: 'Scope 2', value: +(stats.by_scope.scope2 / 1000).toFixed(2), color: SCOPE_COLORS.scope2 },
    { name: 'Scope 3', value: +(stats.by_scope.scope3 / 1000).toFixed(2), color: SCOPE_COLORS.scope3 },
  ].filter(d => d.value > 0);

  const sourceData = (stats.by_source || []).map(s => ({
    name: s['source__source_type'],
    count: s.count,
    co2e: +((s.co2e || 0) / 1000).toFixed(2),
  }));

  const reviewData = [
    { name: 'Pending', value: stats.pending, color: '#f59e0b' },
    { name: 'Approved', value: stats.approved, color: '#22c55e' },
    { name: 'Flagged', value: stats.flagged, color: '#fb923c' },
    { name: 'Rejected', value: stats.rejected, color: '#ef4444' },
  ].filter(d => d.value > 0);

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
        <p>Emissions overview and review status</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="label">Total Records</div>
          <div className="value accent">{stats.total_records}</div>
        </div>
        <div className="stat-card">
          <div className="label">Pending Review</div>
          <div className="value warn">{stats.pending}</div>
        </div>
        <div className="stat-card">
          <div className="label">Flagged</div>
          <div className="value danger">{stats.flagged}</div>
        </div>
        <div className="stat-card">
          <div className="label">Approved</div>
          <div className="value success">{stats.approved}</div>
        </div>
        <div className="stat-card">
          <div className="label">Total CO₂e (approved)</div>
          <div className="value mono">{(stats.total_co2e_kg / 1000).toFixed(2)} t</div>
        </div>
      </div>

      <div className="charts-row">
        <div className="card">
          <h3 style={{ marginBottom: 16, fontSize: 14, color: 'var(--muted)' }}>EMISSIONS BY SCOPE (tCO₂e)</h3>
          {scopeData.length === 0 ? (
            <p style={{ color: 'var(--muted)', fontSize: 13 }}>No approved data yet</p>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={scopeData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, value }) => `${name}: ${value}t`}>
                  {scopeData.map((d, i) => <Cell key={i} fill={d.color} />)}
                </Pie>
                <Tooltip formatter={(v) => `${v} tCO₂e`} contentStyle={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 8 }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card">
          <h3 style={{ marginBottom: 16, fontSize: 14, color: 'var(--muted)' }}>REVIEW STATUS</h3>
          {reviewData.length === 0 ? (
            <p style={{ color: 'var(--muted)', fontSize: 13 }}>No data yet</p>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={reviewData}>
                <XAxis dataKey="name" tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 8 }} />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {reviewData.map((d, i) => <Cell key={i} fill={d.color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 16, fontSize: 14, color: 'var(--muted)' }}>RECENT UPLOADS</h3>
        {sources.length === 0 ? (
          <p style={{ color: 'var(--muted)', fontSize: 13 }}>No uploads yet — go to Ingest Data to upload files.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Source Type</th>
                  <th>File</th>
                  <th>Rows</th>
                  <th>Status</th>
                  <th>Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {sources.slice(0, 10).map(s => (
                  <tr key={s.id}>
                    <td><span className="badge badge-pending">{s.source_type}</span></td>
                    <td className="mono" style={{ fontSize: 12 }}>{s.original_filename || '—'}</td>
                    <td className="mono">{s.row_count}</td>
                    <td>
                      <span className={`badge badge-${s.status === 'DONE' ? 'approved' : s.status === 'FAILED' ? 'rejected' : 'pending'}`}>
                        {s.status}
                      </span>
                    </td>
                    <td style={{ color: 'var(--muted)', fontSize: 12 }}>{new Date(s.uploaded_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
