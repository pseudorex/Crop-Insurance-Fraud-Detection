const API_BASE = 'http://localhost:8000';

const AUTH_TOKEN_KEY = 'consortium_auth_token';
const AUTH_USER_KEY = 'consortium_auth_user';

let onUnauthorizedCallback = null;

export function setOnUnauthorized(cb) {
  onUnauthorizedCallback = cb;
}

export function handleAuthResponse(res) {
  if (res.status === 401) {
    clearStoredAuth();
    if (onUnauthorizedCallback) onUnauthorizedCallback();
  }
  return res;
}

export function getStoredToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

export function getStoredUser() {
  try {
    const u = localStorage.getItem(AUTH_USER_KEY);
    return u ? JSON.parse(u) : null;
  } catch {
    return null;
  }
}

export function storeAuth(token, user) {
  if (token) localStorage.setItem(AUTH_TOKEN_KEY, token);
  if (user) localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
}

export function clearStoredAuth() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
}

function getAuthHeaders(custom = {}) {
  const token = getStoredToken();
  const headers = {
    'Content-Type': 'application/json',
    ...custom
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

// =============================================================================
// Authentication API
// =============================================================================

export async function loginInsurer(username, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Authentication failed' }));
    throw new Error(err.detail || 'Login failed. Please check your credentials.');
  }
  const data = await res.json();
  storeAuth(data.access_token, data.user);
  return data;
}

export async function registerInsurer(payload) {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Registration failed' }));
    throw new Error(err.detail || 'Registration failed');
  }
  const data = await res.json();
  storeAuth(data.access_token, data.user);
  return data;
}

export async function fetchCurrentUser() {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) {
    clearStoredAuth();
    throw new Error('Session expired. Please log in again.');
  }
  return res.json();
}

export async function fetchConsortiumInsurers() {
  const res = await fetch(`${API_BASE}/auth/insurers`);
  if (!res.ok) return [];
  return res.json();
}

// =============================================================================
// Core Consortium Claims & Auditing API
// =============================================================================

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function submitClaim(insurerId, payload) {
  const res = await fetch(`${API_BASE}/insurers/${insurerId}/claims`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(payload)
  });
  handleAuthResponse(res);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Claim submission failed');
  }
  return res.json();
}

export async function listClaims(insurerId, limit = 50) {
  const res = await fetch(`${API_BASE}/insurers/${insurerId}/claims?limit=${limit}`, {
    headers: getAuthHeaders()
  });
  handleAuthResponse(res);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Failed to fetch claims');
  }
  return res.json();
}

export async function getClaim(insurerId, claimRef) {
  const res = await fetch(`${API_BASE}/insurers/${insurerId}/claims/${claimRef}`, {
    headers: getAuthHeaders()
  });
  handleAuthResponse(res);
  if (!res.ok) throw new Error('Claim not found');
  return res.json();
}

export async function getExplanation(insurerId, claimRef) {
  const res = await fetch(`${API_BASE}/insurers/${insurerId}/claims/${claimRef}/explanation`, {
    headers: getAuthHeaders()
  });
  handleAuthResponse(res);
  if (!res.ok) return null;
  return res.json();
}

export async function runAudit(insurerId, claimRef) {
  const res = await fetch(`${API_BASE}/insurers/${insurerId}/claims/${claimRef}/audit`, {
    method: 'POST',
    headers: getAuthHeaders()
  });
  handleAuthResponse(res);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Audit execution failed');
  }
  return res.json();
}

export async function listModels() {
  const res = await fetch(`${API_BASE}/models`, {
    headers: getAuthHeaders()
  });
  handleAuthResponse(res);
  return res.json();
}

export async function verifyModel(version) {
  const res = await fetch(`${API_BASE}/models/${version}/verify`, {
    method: 'POST',
    headers: getAuthHeaders()
  });
  handleAuthResponse(res);
  return res.json();
}

export async function fetchMetrics() {
  const res = await fetch(`${API_BASE}/metrics`, {
    headers: getAuthHeaders()
  });
  handleAuthResponse(res);
  return res.json();
}

export async function fetchAuditLog(insurerId, claimRef = null, limit = 50) {
  const url = claimRef
    ? `${API_BASE}/insurers/${insurerId}/audit-log?claim_ref=${claimRef}&limit=${limit}`
    : `${API_BASE}/insurers/${insurerId}/audit-log?limit=${limit}`;
  const res = await fetch(url, { headers: getAuthHeaders() });
  handleAuthResponse(res);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to fetch audit log' }));
    throw new Error(err.detail || 'Failed to fetch audit log');
  }
  return res.json();
}

export async function verifyAuditChain(insurerId) {
  const res = await fetch(`${API_BASE}/insurers/${insurerId}/audit-log/verify`, {
    headers: getAuthHeaders()
  });
  handleAuthResponse(res);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Hash chain verification failed' }));
    throw new Error(err.detail || 'Verification failed');
  }
  return res.json();
}

export async function fetchMissingRecords(insurerId) {
  const res = await fetch(`${API_BASE}/insurers/${insurerId}/audit/missing-records`, {
    headers: getAuthHeaders()
  });
  handleAuthResponse(res);
  if (!res.ok) {
    return { insurer_id: insurerId, missing_claims: [], status: 'ERROR' };
  }
  return res.json();
}

export async function tamperClaim(insurerId, claimRef, newIndemnity) {
  const res = await fetch(`${API_BASE}/simulate/tamper/claim/${claimRef}`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ insurer_id: insurerId, new_indemnity: parseFloat(newIndemnity) })
  });
  handleAuthResponse(res);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to tamper claim' }));
    throw new Error(err.detail || 'Failed to tamper claim');
  }
  return res.json();
}

export async function tamperExplanation(insurerId, claimRef, featureName, newValue) {
  const res = await fetch(`${API_BASE}/simulate/tamper/explanation/${claimRef}`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      insurer_id: insurerId,
      feature_name: featureName,
      new_value: parseFloat(newValue)
    })
  });
  handleAuthResponse(res);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to tamper explanation' }));
    throw new Error(err.detail || 'Failed to tamper explanation');
  }
  return res.json();
}

export async function restoreClaim(insurerId, claimRef) {
  const res = await fetch(`${API_BASE}/simulate/restore/${claimRef}?insurer_id=${insurerId}`, {
    method: 'POST',
    headers: getAuthHeaders()
  });
  handleAuthResponse(res);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to restore claim' }));
    throw new Error(err.detail || 'Failed to restore claim');
  }
  return res.json();
}
