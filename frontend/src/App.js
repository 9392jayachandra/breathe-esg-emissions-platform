import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Upload, Table2, Settings, Leaf } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import UploadPage from './pages/UploadPage';
import ReviewPage from './pages/ReviewPage';
import TenantsPage from './pages/TenantsPage';
import { getTenants } from './services/api';
import './App.css';

function App() {
  const [tenants, setTenants] = useState([]);
  const [activeTenant, setActiveTenant] = useState(null);

  useEffect(() => {
    getTenants().then(r => {
      setTenants(r.data);
      if (r.data.length > 0) setActiveTenant(r.data[0]);
    }).catch(() => {});
  }, []);

  return (
    <BrowserRouter>
      <div className="app">
        <aside className="sidebar">
          <div className="sidebar-logo">
            <Leaf size={22} />
            <span>BreatheESG</span>
          </div>

          <div className="tenant-selector">
            <label>Client</label>
            <select
              value={activeTenant?.id || ''}
              onChange={e => setActiveTenant(tenants.find(t => t.id === e.target.value))}
            >
              <option value="">All clients</option>
              {tenants.map(t => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>

          <nav className="sidebar-nav">
            <NavLink to="/" end><LayoutDashboard size={16} /> Dashboard</NavLink>
            <NavLink to="/upload"><Upload size={16} /> Ingest Data</NavLink>
            <NavLink to="/review"><Table2 size={16} /> Review</NavLink>
            <NavLink to="/tenants"><Settings size={16} /> Clients</NavLink>
          </nav>
        </aside>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard tenantId={activeTenant?.id} />} />
            <Route path="/upload" element={<UploadPage tenants={tenants} activeTenant={activeTenant} />} />
            <Route path="/review" element={<ReviewPage tenantId={activeTenant?.id} />} />
            <Route path="/tenants" element={<TenantsPage tenants={tenants} setTenants={setTenants} />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
