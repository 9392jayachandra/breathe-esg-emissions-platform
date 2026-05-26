import axios from 'axios';

const API = axios.create({
  baseURL: process.env.REACT_APP_API_URL || '/api',
});

export const getTenants = () => API.get('/tenants/');
export const createTenant = (data) => API.post('/tenants/', data);

export const uploadFile = (formData) => API.post('/upload/', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
});

export const getRecords = (params) => API.get('/records/', { params });
export const getRecord = (id) => API.get(`/records/${id}/`);
export const updateRecord = (id, data) => API.patch(`/records/${id}/`, data);
export const reviewRecord = (id, action, reviewer, notes) =>
  API.post(`/records/${id}/review/`, { action, reviewed_by: reviewer, notes });
export const bulkReview = (ids, action, reviewer) =>
  API.post('/records/bulk-review/', { ids, action, reviewed_by: reviewer });
export const getAuditLog = (id) => API.get(`/records/${id}/audit/`);

export const getDashboard = (tenantId) =>
  API.get('/dashboard/', { params: tenantId ? { tenant_id: tenantId } : {} });

export const getSources = (tenantId) =>
  API.get('/sources/', { params: tenantId ? { tenant_id: tenantId } : {} });
