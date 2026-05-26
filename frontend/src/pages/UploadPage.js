import React, { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle, AlertCircle } from 'lucide-react';
import { uploadFile } from '../services/api';

const SOURCE_DESCRIPTIONS = {
  SAP: {
    title: 'SAP Fuel & Procurement',
    desc: 'SAP flat-file CSV export (FI/MM module). Supports German and English headers: Buchungsdatum/posting date, Menge/quantity, Mengeneinheit/unit, Material, Werk/plant.',
    scope: 'Scope 1',
    example: 'sap_export.csv',
  },
  UTILITY: {
    title: 'Utility Electricity',
    desc: 'Portal CSV export from utility providers. Expected columns: meter ID, billing period start, consumption (kWh or MWh), site name.',
    scope: 'Scope 2',
    example: 'utility_export.csv',
  },
  TRAVEL: {
    title: 'Corporate Travel',
    desc: 'Concur/Navan-style expense CSV. Columns: date, type (flight/hotel/car/train), employee, origin, destination, distance_km (optional), nights.',
    scope: 'Scope 3',
    example: 'travel_export.csv',
  },
};

export default function UploadPage({ tenants, activeTenant }) {
  const [selectedTenant, setSelectedTenant] = useState(activeTenant?.id || '');
  const [sourceType, setSourceType] = useState('SAP');
  const [file, setFile] = useState(null);
  const [drag, setDrag] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const fileInput = useRef();

  const handleDrop = (e) => {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  };

  const handleSubmit = async () => {
    if (!file) { setError('Please select a file'); return; }
    if (!selectedTenant) { setError('Please select a client'); return; }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('source_type', sourceType);
      fd.append('tenant_id', selectedTenant);
      const res = await uploadFile(fd);
      setResult(res.data);
      setFile(null);
    } catch (e) {
      setError(e.response?.data?.error || 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  const info = SOURCE_DESCRIPTIONS[sourceType];

  return (
    <div>
      <div className="page-header">
        <h1>Ingest Data</h1>
        <p>Upload CSV files from SAP, utility portals, or travel platforms</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        <div>
          <div className="card" style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 16, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Configuration</h3>

            <div className="form-group">
              <label>Client</label>
              <select value={selectedTenant} onChange={e => setSelectedTenant(e.target.value)}>
                <option value="">Select client…</option>
                {tenants.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </div>

            <div className="form-group">
              <label>Source Type</label>
              <select value={sourceType} onChange={e => setSourceType(e.target.value)}>
                <option value="SAP">SAP – Fuel & Procurement (Scope 1)</option>
                <option value="UTILITY">Utility – Electricity (Scope 2)</option>
                <option value="TRAVEL">Corporate Travel (Scope 3)</option>
              </select>
            </div>
          </div>

          <div className="card" style={{ background: 'rgba(0,229,160,0.04)', borderColor: 'rgba(0,229,160,0.2)' }}>
            <h4 style={{ fontSize: 12, color: 'var(--accent)', marginBottom: 8 }}>{info.title} · {info.scope}</h4>
            <p style={{ color: 'var(--muted)', fontSize: 12, lineHeight: 1.6 }}>{info.desc}</p>
          </div>
        </div>

        <div>
          <div className="card">
            <h3 style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 16, textTransform: 'uppercase', letterSpacing: '0.06em' }}>File Upload</h3>

            <div
              className={`upload-zone ${drag ? 'drag' : ''}`}
              onDragOver={e => { e.preventDefault(); setDrag(true); }}
              onDragLeave={() => setDrag(false)}
              onDrop={handleDrop}
              onClick={() => fileInput.current.click()}
            >
              <input ref={fileInput} type="file" accept=".csv,.xlsx,.xls" style={{ display: 'none' }}
                onChange={e => setFile(e.target.files[0])} />
              <div className="icon"><Upload size={32} /></div>
              {file ? (
                <p><strong style={{ color: 'var(--accent)' }}>{file.name}</strong><br />{(file.size / 1024).toFixed(1)} KB</p>
              ) : (
                <p>Drop CSV here or <strong>click to browse</strong></p>
              )}
            </div>

            {error && (
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', color: 'var(--danger)', marginTop: 12, fontSize: 13 }}>
                <AlertCircle size={15} /> {error}
              </div>
            )}

            {result && (
              <div style={{ marginTop: 12, padding: 12, background: 'rgba(34,197,94,0.08)', borderRadius: 8, border: '1px solid rgba(34,197,94,0.2)' }}>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', color: 'var(--success)', marginBottom: 6 }}>
                  <CheckCircle size={15} /> Upload successful
                </div>
                <p style={{ fontSize: 12, color: 'var(--muted)' }}>
                  {result.rows_created} rows ingested · {result.rows_with_errors} errors
                </p>
                {result.errors?.length > 0 && (
                  <details style={{ marginTop: 8 }}>
                    <summary style={{ fontSize: 12, color: 'var(--warn)', cursor: 'pointer' }}>Show parse errors</summary>
                    <ul style={{ marginTop: 6, paddingLeft: 16 }}>
                      {result.errors.map((e, i) => <li key={i} style={{ fontSize: 11, color: 'var(--muted)', fontFamily: 'var(--mono)' }}>{e}</li>)}
                    </ul>
                  </details>
                )}
              </div>
            )}

            <button className="btn btn-primary" style={{ width: '100%', marginTop: 16, justifyContent: 'center' }}
              onClick={handleSubmit} disabled={loading || !file}>
              {loading ? 'Uploading…' : <><Upload size={15} /> Ingest File</>}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
