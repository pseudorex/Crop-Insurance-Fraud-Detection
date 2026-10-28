import React, { useState, useEffect } from 'react';
import { Search, Filter, ShieldCheck, Eye, ExternalLink, RefreshCw, X, AlertTriangle } from 'lucide-react';
import { listClaims, getExplanation } from '../api';

export default function ClaimsView({ currentInsurer, currentUser, onSelectForAudit }) {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState('ALL');
  const [selectedClaim, setSelectedClaim] = useState(null);
  const [selectedExplanation, setSelectedExplanation] = useState(null);
  const [loadingExp, setLoadingExp] = useState(false);

  const loadClaims = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listClaims(currentInsurer);
      setClaims(data || []);
    } catch (err) {
      setError(err.message || 'Failed to load claims');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClaims();
    setSelectedClaim(null);
    setSelectedExplanation(null);
  }, [currentInsurer]);

  const handleInspect = async (claim) => {
    setSelectedClaim(claim);
    setSelectedExplanation(null);
    if (claim.risk_label === 'HIGH') {
      setLoadingExp(true);
      try {
        const exp = await getExplanation(currentInsurer, claim.claim_ref);
        setSelectedExplanation(exp);
      } catch (err) {
        console.error('Explanation load error', err);
      } finally {
        setLoadingExp(false);
      }
    }
  };

  const filteredClaims = claims.filter((c) => {
    const matchesSearch =
      (c.claim_ref || '').toLowerCase().includes(search.toLowerCase()) ||
      (c.farmer_id || '').toLowerCase().includes(search.toLowerCase());
    const matchesRisk = riskFilter === 'ALL' || c.risk_label === riskFilter;
    return matchesSearch && matchesRisk;
  });

  // Calculate sorted SHAP features if explanation exists
  const rawShap =
    selectedExplanation?.shap_json?.feature_contributions ||
    selectedExplanation?.shap_json?.features ||
    selectedExplanation?.features ||
    selectedExplanation?.feature_contributions ||
    {};
  const shapFeatures = Object.entries(rawShap).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  const maxAbsShap = shapFeatures.length > 0 ? Math.max(...shapFeatures.map(([_, v]) => Math.abs(v))) : 1;

  return (
    <div style={{ maxWidth: '1350px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '700', color: '#fff' }}>
            Consortium Claims Ledger — <span style={{ color: 'var(--accent-orange)' }}>{currentInsurer}</span>
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Multi-tenant PostgreSQL isolated storage synced with immutable Ganache Ethereum commitments.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ position: 'relative' }}>
            <Search size={15} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search Claim Ref or Farmer..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ paddingLeft: '32px', width: '240px' }}
            />
          </div>

          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            style={{ width: '140px' }}
          >
            <option value="ALL">All Risk Levels</option>
            <option value="HIGH">High Risk</option>
            <option value="MEDIUM">Medium Risk</option>
            <option value="LOW">Low Risk</option>
          </select>

          <button
            type="button"
            onClick={loadClaims}
            className="btn btn-secondary"
            title="Refresh claims list"
          >
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Main Table Card */}
      <div className="card" style={{ overflow: 'hidden' }}>
        <table className="table" style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={{ width: '100px' }}>Risk Tier</th>
              <th>Claim Reference</th>
              <th>Farmer ID</th>
              <th>Crop / Year</th>
              <th>Claimed Indemnity</th>
              <th>Liability</th>
              <th style={{ width: '140px' }}>Fraud Score</th>
              <th>Chain Status</th>
              <th style={{ textAlign: 'right', width: '180px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                  Loading claims from {currentInsurer}_db...
                </td>
              </tr>
            ) : filteredClaims.length === 0 ? (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-muted)' }}>
                  No claims found. Use the "Claim Intake" tab to submit your first claim!
                </td>
              </tr>
            ) : (
              filteredClaims.map((claim) => {
                const cData = claim.claim_data || {};
                const farmerId = claim.farmer_id || cData.farmer_id || 'Unknown';
                const commodityCode = claim.commodity_code || cData.commodity_code || 11;
                const commodityYear = claim.commodity_year || cData.commodity_year || 2026;
                const netIndemnity = claim.net_indemnity ?? cData.net_indemnity ?? 0;
                const liabilityAmount = claim.liability_amount ?? cData.liability_amount ?? 0;

                return (
                  <tr key={claim.claim_id || claim.claim_ref}>
                    <td>
                      <span className={`badge ${claim.risk_label === 'HIGH' ? 'badge-high' : claim.risk_label === 'MEDIUM' ? 'badge-medium' : 'badge-low'}`}>
                        {claim.risk_label}
                      </span>
                    </td>
                    <td style={{ fontWeight: '600', color: '#fff', fontFamily: 'JetBrains Mono, monospace', fontSize: '13px' }}>
                      {claim.claim_ref}
                    </td>
                    <td style={{ color: 'var(--text-secondary)' }}>{farmerId}</td>
                    <td>
                      <span style={{ color: 'var(--text-primary)' }}>
                        {commodityCode === 11 ? 'Wheat' : commodityCode === 41 ? 'Corn' : commodityCode === 81 ? 'Soybean' : `Code ${commodityCode}`}
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: '6px' }}>({commodityYear})</span>
                    </td>
                    <td style={{ fontWeight: '600', color: 'var(--accent-orange)' }}>
                      ${parseFloat(netIndemnity).toLocaleString()}
                    </td>
                    <td style={{ color: 'var(--text-secondary)' }}>
                      ${parseFloat(liabilityAmount).toLocaleString()}
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ flex: 1, height: '6px', backgroundColor: '#333', borderRadius: '3px', overflow: 'hidden' }}>
                          <div style={{
                            height: '100%',
                            width: `${Math.min(100, (claim.fraud_score || 0) * 100)}%`,
                            backgroundColor: claim.risk_label === 'HIGH' ? 'var(--accent-red)' : 'var(--accent-green)'
                          }} />
                        </div>
                        <span style={{ fontSize: '11px', fontFamily: 'JetBrains Mono, monospace', minWidth: '38px', color: 'var(--text-muted)' }}>
                          {((claim.fraud_score || 0) * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '12px', color: 'var(--accent-green)', fontWeight: '500' }}>
                        <ShieldCheck size={14} />
                        {claim.chain_status || 'ANCHORED'}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: '6px' }}>
                        <button
                          type="button"
                          onClick={() => handleInspect(claim)}
                          className="btn btn-secondary"
                          style={{ padding: '4px 8px', fontSize: '11px' }}
                        >
                          <Eye size={12} />
                          Inspect
                        </button>
                        {(currentUser?.role?.toLowerCase() === 'auditor' || currentUser?.role?.toLowerCase() === 'admin') && (
                          <button
                            type="button"
                            onClick={() => onSelectForAudit && onSelectForAudit(claim.claim_ref)}
                            className="btn btn-secondary"
                            style={{ padding: '4px 8px', fontSize: '11px', borderColor: 'var(--accent-orange)', color: 'var(--accent-orange)' }}
                          >
                            Audit
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Claim Detail & SHAP Drawer / Modal */}
      {selectedClaim && (
        <div style={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width: '560px',
          backgroundColor: 'var(--bg-card)',
          borderLeft: '1px solid var(--border)',
          zIndex: 200,
          boxShadow: '-4px 0 24px rgba(0,0,0,0.6)',
          display: 'flex',
          flexDirection: 'column'
        }}>
          {/* Drawer Header */}
          <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-muted)' }}>
                Claim Inspection & SHAP
              </div>
              <h3 style={{ fontSize: '17px', fontWeight: '700', color: '#fff', marginTop: '2px', fontFamily: 'JetBrains Mono, monospace' }}>
                {selectedClaim.claim_ref}
              </h3>
            </div>
            <button
              type="button"
              onClick={() => setSelectedClaim(null)}
              style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '4px' }}
            >
              <X size={18} />
            </button>
          </div>

          {/* Drawer Body */}
          <div style={{ padding: '24px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px', flex: 1 }}>
            {/* Risk & Fraud Score Banner */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px', backgroundColor: 'var(--bg-elevated)', borderRadius: '8px', border: '1px solid var(--border)' }}>
              <div>
                <span className={`badge ${selectedClaim.risk_label === 'HIGH' ? 'badge-high' : 'badge-low'}`}>
                  {selectedClaim.risk_label} RISK
                </span>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Model: {selectedClaim.model_version || 'M1'} (DP-XGBoost)
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '20px', fontWeight: '800', color: selectedClaim.risk_label === 'HIGH' ? 'var(--accent-red)' : 'var(--accent-green)' }}>
                  {((selectedClaim.fraud_score || 0) * 100).toFixed(1)}%
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Fraud Probability</div>
              </div>
            </div>

            {/* Core Agronomic Metrics */}
            {(() => {
              const cData = selectedClaim.claim_data || {};
              const farmerId = selectedClaim.farmer_id || cData.farmer_id || 'Unknown';
              const netIndemnity = selectedClaim.net_indemnity ?? cData.net_indemnity ?? 0;
              const liabilityAmount = selectedClaim.liability_amount ?? cData.liability_amount ?? 0;
              const totalPremium = selectedClaim.total_premium ?? cData.total_premium ?? 0;
              const acres = selectedClaim.net_determined_acres ?? cData.net_determined_acres ?? 0;
              const yieldVal = selectedClaim.determined_yield ?? cData.determined_yield ?? 0;

              return (
                <div>
                  <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
                    Agronomic & Financial Attributes
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '13px' }}>
                    <div style={{ padding: '10px', backgroundColor: 'var(--bg-elevated)', borderRadius: '6px' }}>
                      <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Farmer ID</div>
                      <div style={{ fontWeight: '600', color: '#fff', marginTop: '2px' }}>{farmerId}</div>
                    </div>
                    <div style={{ padding: '10px', backgroundColor: 'var(--bg-elevated)', borderRadius: '6px' }}>
                      <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Net Indemnity Claimed</div>
                      <div style={{ fontWeight: '600', color: 'var(--accent-orange)', marginTop: '2px' }}>
                        ${parseFloat(netIndemnity).toLocaleString()}
                      </div>
                    </div>
                    <div style={{ padding: '10px', backgroundColor: 'var(--bg-elevated)', borderRadius: '6px' }}>
                      <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Liability & Premium</div>
                      <div style={{ fontWeight: '500', color: 'var(--text-primary)', marginTop: '2px' }}>
                        ${parseFloat(liabilityAmount).toLocaleString()} / ${parseFloat(totalPremium).toLocaleString()}
                      </div>
                    </div>
                    <div style={{ padding: '10px', backgroundColor: 'var(--bg-elevated)', borderRadius: '6px' }}>
                      <div style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Acres & Yield</div>
                      <div style={{ fontWeight: '500', color: 'var(--text-primary)', marginTop: '2px' }}>
                        {acres} ac / {yieldVal} bu/ac
                      </div>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* Cryptographic Hashes */}
            <div>
              <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
                Blockchain Ledger Hashes
              </div>
              <div className="mono-box" style={{ fontSize: '11px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Claim Canonical Hash:</span>
                  <div style={{ color: 'var(--accent-orange)', wordBreak: 'break-all', marginTop: '2px' }}>
                    {selectedClaim.claim_hash}
                  </div>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Ethereum Transaction ID:</span>
                  <div style={{ color: 'var(--accent-green)', wordBreak: 'break-all', marginTop: '2px' }}>
                    {selectedClaim.claim_tx_id || 'On-chain commitment active'}
                  </div>
                </div>
              </div>
            </div>

            {/* SHAP Diverging Bar Chart */}
            <div>
              <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px', display: 'flex', justifyContent: 'space-between' }}>
                <span>TreeSHAP Feature Contributions</span>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Green: Normal | Red: Suspicious</span>
              </div>

              {loadingExp ? (
                <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
                  Computing and verifying TreeSHAP values...
                </div>
              ) : selectedClaim.risk_label !== 'HIGH' ? (
                <div style={{ padding: '16px', backgroundColor: 'var(--bg-elevated)', borderRadius: '6px', fontSize: '12px', color: 'var(--text-muted)' }}>
                  No on-chain SHAP explanation is required for Low/Normal risk claims under the Consortium audit protocol.
                </div>
              ) : shapFeatures.length === 0 ? (
                <div style={{ padding: '16px', backgroundColor: 'var(--bg-elevated)', borderRadius: '6px', fontSize: '12px', color: 'var(--text-muted)' }}>
                  No explanation record found for this claim.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {shapFeatures.map(([feat, val]) => {
                    const isPositive = val >= 0;
                    const pct = Math.min(100, (Math.abs(val) / maxAbsShap) * 100);
                    return (
                      <div key={feat} style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px' }}>
                          <span style={{ color: 'var(--text-primary)', fontFamily: 'JetBrains Mono, monospace' }}>{feat}</span>
                          <span style={{ fontWeight: '600', color: isPositive ? 'var(--accent-red)' : 'var(--accent-green)', fontFamily: 'JetBrains Mono, monospace' }}>
                            {isPositive ? `+${val.toFixed(4)}` : val.toFixed(4)}
                          </span>
                        </div>
                        <div style={{ height: '8px', backgroundColor: 'var(--bg-elevated)', borderRadius: '4px', overflow: 'hidden', position: 'relative' }}>
                          <div style={{
                            height: '100%',
                            width: `${pct}%`,
                            backgroundColor: isPositive ? 'var(--accent-red)' : 'var(--accent-green)',
                            borderRadius: '4px'
                          }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Drawer Footer */}
          <div style={{ padding: '16px 24px', borderTop: '1px solid var(--border)', display: 'flex', gap: '12px' }}>
            <button
              type="button"
              onClick={() => {
                const ref = selectedClaim.claim_ref;
                setSelectedClaim(null);
                if (onSelectForAudit) onSelectForAudit(ref);
              }}
              className="btn btn-primary"
              style={{ flex: 1, justifyContent: 'center' }}
            >
              <span>Verify Integrity in Auditor</span>
              <ShieldCheck size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
