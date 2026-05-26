import React, { useEffect, useState, useCallback } from 'react';
import { CheckCircle, XCircle, Flag, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';
import { getRecords, reviewRecord, bulkReview, getAuditLog } from '../services/api';

const STATUS_BADGES = {
  PENDING: 'badge-pending',
  APPROVED: 'badge-approved',
  REJECTED: 'badge-rejected',
  FLAGGED: 'badge-flagged',
};

export default function ReviewPage({ tenantId }) {
  const [records, setRecords] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({ review_status: '', scope: '', source_type: '' });
  const [selected, setSelected] = useState([]);
  const [expanded, setExpanded] = useState(null);
  const [auditLog, setAuditLog] = useState([]);
  const [toast, setToast] = useState(null);
  const reviewer = 'analyst';

  const load = useCallback(() => {
    setLoading(true);
    const params = { page, ...filters };
    if (tenantId) params.tenant_id = tenantId;
    Object.keys(params).forEach(k => !params[k] && delete params[k]);
    getRecords(params).then(r => {
      setRecords(r.data.results);
      setCount(r.data.count);
    }).finally(() => setLoading(false));
  }, [page, filters, tenantId]);

  useEffect(() => { load(); }, [load]);

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  const doReview = async (id, action, notes = '') => {
    try {
      await reviewRecord(id, action, reviewer, notes);
      showToast(`Record ${action.toLowerCase()}d`);
      load();
    } catch (e) {
      showToast('Action failed', 'error');
    }
  };

  const doBulk = async (action) => {
    if (!selected.length) return;
    await bulkReview(selected, action, reviewer);
    showToast(`${selected.length} records ${action.toLowerCase()}d`);
    setSelected([]);
    load();
  };

  const toggleExpand = async (id) => {
    if (expanded === id) { setExpanded(null); return; }
    setExpanded(id);
    const res = await getAuditLog(id);
    setAuditLog(res.data);
  };

  const toggleSelect = (id) => setSelected(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id]);
  const toggleAll = () => setSelected(s => s.length === records.length ? [] : records.map(r => r.id));

  const totalPages = Math.ceil(count / 50);

  return (
    <div>
      <div className="page-header">
        <h1>Review Dashboard</h1>
        <p>Inspect, flag, approve, or reject ingested emission records</p>
      </div>

      {/* Filters */}
      <div className="filter-bar">
        <select value={filters.review_status} onChange={e => setFilters(f => ({ ...f, review_status: e.target.value }))}>
          <option value="">All statuses</option>
          <option value="PENDING">Pending</option>
          <option value="FLAGGED">Flagged</option>
          <option value="APPROVED">Approved</option>
          <option value="REJECTED">Rejected</option>
        </select>
        <select value={filters.scope} onChange={e => setFilters(f => ({ ...f, scope: e.target.value }))}>
          <option value="">All scopes</option>
          <option value="1">Scope 1</option>
          <option value="2">Scope 2</option>
          <option value="3">Scope 3</option>
        </select>
        <select value={filters.source_type} onChange={e => setFilters(f => ({ ...f, source_type: e.target.value }))}>
          <option value="">All sources</option>
          <option value="SAP">SAP</option>
          <option value="UTILITY">Utility</option>
          <option value="TRAVEL">Travel</option>
        </select>
        <button className="btn btn-ghost btn-sm" onClick={() => setFilters({ review_status: '', scope: '', source_type: '' })}>
          Clear
        </button>
      </div>

      {/* Bulk actions */}
      {selected.length > 0 && (
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 14, padding: '10px 14px', background: 'var(--surface2)', borderRadius: 8, border: '1px solid var(--border)' }}>
          <span style={{ fontSize: 13, color: 'var(--muted)' }}>{selected.length} selected</span>
          <button className="btn btn-approve btn-sm" onClick={() => doBulk('APPROVE')}><CheckCircle size={13} /> Approve All</button>
          <button className="btn btn-reject btn-sm" onClick={() => doBulk('REJECT')}><XCircle size={13} /> Reject All</button>
          <button className="btn btn-ghost btn-sm" onClick={() => setSelected([])} style={{ marginLeft: 'auto' }}>Clear selection</button>
        </div>
      )}

      {loading ? (
        <div className="loading">Loading records…</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th><input type="checkbox" checked={selected.length === records.length && records.length > 0} onChange={toggleAll} /></th>
                <th>Date</th>
                <th>Category</th>
                <th>Scope</th>
                <th>Source</th>
                <th>Quantity</th>
                <th>CO₂e (kg)</th>
                <th>Status</th>
                <th>Actions</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {records.map(rec => (
                <React.Fragment key={rec.id}>
                  <tr style={rec.flag_reason ? { borderLeft: '3px solid #fb923c' } : {}}>
                    <td><input type="checkbox" checked={selected.includes(rec.id)} onChange={() => toggleSelect(rec.id)} /></td>
                    <td className="mono" style={{ fontSize: 12 }}>{rec.activity_date}</td>
                    <td style={{ textTransform: 'capitalize' }}>{rec.category?.replace('_', ' ')}</td>
                    <td><span className={`scope-badge scope-${rec.scope}`}>S{rec.scope}</span></td>
                    <td style={{ fontSize: 11, color: 'var(--muted)' }}>{rec.source_type}</td>
                    <td className="mono" style={{ fontSize: 12 }}>{rec.normalized_quantity?.toFixed(2)} {rec.normalized_unit}</td>
                    <td className="mono" style={{ fontSize: 12 }}>{rec.co2e_kg?.toFixed(2) ?? '—'}</td>
                    <td>
                      <span className={`badge ${STATUS_BADGES[rec.review_status]}`}>
                        {rec.flag_reason && <AlertTriangle size={10} />}
                        {rec.review_status}
                      </span>
                    </td>
                    <td>
                      {!rec.is_locked && (
                        <div style={{ display: 'flex', gap: 5 }}>
                          <button className="btn btn-approve btn-sm" onClick={() => doReview(rec.id, 'approve')} title="Approve">
                            <CheckCircle size={12} />
                          </button>
                          <button className="btn btn-reject btn-sm" onClick={() => doReview(rec.id, 'reject')} title="Reject">
                            <XCircle size={12} />
                          </button>
                          <button className="btn btn-ghost btn-sm" onClick={() => doReview(rec.id, 'flag')} title="Flag">
                            <Flag size={12} />
                          </button>
                        </div>
                      )}
                      {rec.is_locked && <span style={{ fontSize: 11, color: 'var(--success)' }}>🔒 Locked</span>}
                    </td>
                    <td>
                      <button className="btn btn-ghost btn-sm" onClick={() => toggleExpand(rec.id)}>
                        {expanded === rec.id ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                      </button>
                    </td>
                  </tr>

                  {expanded === rec.id && (
                    <tr>
                      <td colSpan={10} style={{ background: 'var(--surface2)', padding: '14px 18px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                          <div>
                            <h4 style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 8 }}>RECORD DETAILS</h4>
                            <table style={{ width: '100%' }}>
                              <tbody>
                                {[
                                  ['Description', rec.description],
                                  ['Location', rec.location],
                                  ['Raw value', `${rec.raw_quantity} ${rec.raw_unit}`],
                                  ['Normalized', `${rec.normalized_quantity} ${rec.normalized_unit}`],
                                  ['Reviewed by', rec.reviewed_by || '—'],
                                  ['Notes', rec.review_notes || '—'],
                                  ['Edited', rec.is_edited ? 'Yes' : 'No'],
                                ].map(([k, v]) => (
                                  <tr key={k}>
                                    <td style={{ color: 'var(--muted)', fontSize: 11, paddingRight: 12, whiteSpace: 'nowrap' }}>{k}</td>
                                    <td style={{ fontSize: 12 }}>{v}</td>
                                  </tr>
                                ))}
                                {rec.flag_reason && (
                                  <tr>
                                    <td style={{ color: '#fb923c', fontSize: 11 }}>⚠ Flag</td>
                                    <td style={{ fontSize: 12, color: '#fb923c' }}>{rec.flag_reason}</td>
                                  </tr>
                                )}
                              </tbody>
                            </table>
                          </div>
                          <div>
                            <h4 style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 8 }}>AUDIT TRAIL</h4>
                            {auditLog.length === 0 ? (
                              <p style={{ fontSize: 12, color: 'var(--muted)' }}>No changes recorded</p>
                            ) : (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                                {auditLog.map(log => (
                                  <div key={log.id} style={{ fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--muted)' }}>
                                    <span style={{ color: 'var(--accent)' }}>{log.action}</span> · {log.field_changed}: {log.old_value} → {log.new_value} · {log.changed_by} · {new Date(log.changed_at).toLocaleString()}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginTop: 16 }}>
          <button className="btn btn-ghost btn-sm" disabled={page === 1} onClick={() => setPage(p => p - 1)}>← Prev</button>
          <span style={{ padding: '5px 10px', fontSize: 13, color: 'var(--muted)' }}>Page {page} of {totalPages} ({count} records)</span>
          <button className="btn btn-ghost btn-sm" disabled={page === totalPages} onClick={() => setPage(p => p + 1)}>Next →</button>
        </div>
      )}

      {toast && <div className={`toast ${toast.type}`}>{toast.msg}</div>}
    </div>
  );
}
