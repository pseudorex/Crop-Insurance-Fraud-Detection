const API_BASE = 'http://localhost:8000';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return res.json();
}

export async function submitClaim(insurerId, payload) {
  const res = await fetch(`${API_BASE}/insurers/${insurerId}/claims`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Claim submission failed');
  }
  return res.json();
}

export async function listClaims(insurerId, limit = 50) {
  const res = await fetch(`${API_BASE}/insurers/${insurerId}/claims?limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch claims');
  return res.json();
}

export async function getClaim(insurerId, claimRef) {
  const res = await fetch(`${API_BASE}/insurers/${insurerId}/claims/${claimRef}`);
  if (!res.ok) throw new Error('Claim not found');
  return res.json();
}

export async function getExplanation(insurerId, claimRef) {
  const res = await fetch(`${API_BASE}/insurers/${insurerId}/claims/${claimRef}/explanation`);
  if (!res.ok) return null;
  return res.json();
}

export async function runAudit(insurerId, claimRef) {
  const res = await fetch(`${API_BASE}/insurers/${insurerId}/claims/${claimRef}/audit`, {
    method: 'POST'
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Audit execution failed');
  }
  return res.json();
}

export async function listModels() {
  const res = await fetch(`${API_BASE}/models`);
  return res.json();
}

export async function verifyModel(version) {
  const res = await fetch(`${API_BASE}/models/${version}/verify`, { method: 'POST' });
  return res.json();
}

export async function fetchMetrics() {
  const res = await fetch(`${API_BASE}/metrics`);
  return res.json();
}

export async function tamperClaim(insurerId, claimRef, newIndemnity) {
  const res = await fetch(`${API_BASE}/demo/tamper/claim/${claimRef}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ insurer_id: insurerId, new_indemnity: parseFloat(newIndemnity) })
  });
  if (!res.ok) throw new Error('Failed to tamper claim');
  return res.json();
}

export async function tamperExplanation(insurerId, claimRef, featureName, newValue) {
  const res = await fetch(`${API_BASE}/demo/tamper/explanation/${claimRef}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      insurer_id: insurerId,
      feature_name: featureName,
      new_value: parseFloat(newValue)
    })
  });
  if (!res.ok) throw new Error('Failed to tamper explanation');
  return res.json();
}

export async function restoreClaim(insurerId, claimRef) {
  const res = await fetch(`${API_BASE}/demo/restore/${claimRef}?insurer_id=${insurerId}`, {
    method: 'POST'
  });
  if (!res.ok) throw new Error('Failed to restore claim');
  return res.json();
}
