import React, { useState } from 'react';
import { Send, Sparkles, AlertCircle, CheckCircle2, Shield, ArrowRight, ExternalLink } from 'lucide-react';
import { submitClaim } from '../api';

const CLEAN_PRESET = {
  farmer_id: 'FARMER-NORMAL-01',
  state_code: '17',
  county_code: '019',
  commodity_code: 11, // Wheat
  cause_of_loss_code: 1, // Standard / Minor Weather
  commodity_year: 2026,
  month_of_loss: 8,
  net_determined_acres: 0.0,
  net_planted_acres: 40.0,
  liability_amount: 25000.0,
  total_premium: 3200.0,
  net_indemnity: 250.0,
  determined_yield: 44.0,
  claim_ref: ''
};

const FRAUD_PRESET = {
  farmer_id: 'FARMER-SUSPECT-404',
  state_code: '17',
  county_code: '019',
  commodity_code: 11, // Wheat
  cause_of_loss_code: 11, // Drought
  commodity_year: 2026,
  month_of_loss: 7,
  net_determined_acres: 250.0,
  net_planted_acres: 250.0,
  liability_amount: 85000.0,
  total_premium: 1200.0,
  net_indemnity: 84500.0,
  determined_yield: 2.1,
  claim_ref: ''
};

export default function IntakeView({ currentInsurer, onClaimSubmitted, onViewClaimInAudit }) {
  const [formData, setFormData] = useState({
    ...CLEAN_PRESET,
    claim_ref: `CLM-${currentInsurer.toUpperCase()}-${Math.floor(1000 + Math.random() * 9000)}`
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleChange = (e) => {
    const { name, value, type } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'number' ? (value === '' ? '' : parseFloat(value)) : value
    }));
  };

  const applyCleanPreset = () => {
    setFormData({
      ...CLEAN_PRESET,
      claim_ref: `CLM-${currentInsurer.toUpperCase()}-${Math.floor(1000 + Math.random() * 9000)}`
    });
    setResult(null);
    setError(null);
  };

  const applyFraudPreset = () => {
    setFormData({
      ...FRAUD_PRESET,
      claim_ref: `CLM-${currentInsurer.toUpperCase()}-${Math.floor(1000 + Math.random() * 9000)}`
    });
    setResult(null);
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await submitClaim(currentInsurer, formData);
      setResult(res);
      if (onClaimSubmitted) onClaimSubmitted(res);
    } catch (err) {
      setError(err.message || 'Submission error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '700', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>Claim Intake & Real-Time Fraud Inference</span>
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Ingest crop insurance claims into <span style={{ color: 'var(--accent-orange)' }}>{currentInsurer}</span>. Features are normalized, scored by the XGBoost DP model, committed to PostgreSQL, and anchored on the Ethereum blockchain.
          </p>
        </div>

        {/* Quick Test Presets */}
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            type="button"
            onClick={applyCleanPreset}
            className="btn btn-secondary"
            style={{ borderColor: 'var(--accent-green)', color: 'var(--accent-green)', fontSize: '12px', padding: '6px 12px' }}
          >
            <Sparkles size={14} />
            Fill Clean Preset
          </button>
          <button
            type="button"
            onClick={applyFraudPreset}
            className="btn btn-secondary"
            style={{ borderColor: 'var(--accent-red)', color: 'var(--accent-red)', fontSize: '12px', padding: '6px 12px' }}
          >
            <AlertCircle size={14} />
            Fill Fraud Preset
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: result ? '1fr 1fr' : '1fr', gap: '24px', alignItems: 'start' }}>
        {/* Input Form */}
        <div className="card" style={{ padding: '24px' }}>
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div>
                <label>Claim Reference</label>
                <input
                  type="text"
                  name="claim_ref"
                  value={formData.claim_ref}
                  onChange={handleChange}
                  placeholder="e.g. CLM-2026-001"
                  required
                />
              </div>
              <div>
                <label>Farmer ID</label>
                <input
                  type="text"
                  name="farmer_id"
                  value={formData.farmer_id}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '14px' }}>
              <div>
                <label>Commodity / Crop</label>
                <select name="commodity_code" value={formData.commodity_code} onChange={handleChange}>
                  <option value={11}>Wheat (11)</option>
                  <option value={41}>Corn (41)</option>
                  <option value={81}>Soybeans (81)</option>
                  <option value={21}>Cotton (21)</option>
                  <option value={51}>Rice (51)</option>
                </select>
              </div>
              <div>
                <label>Loss Cause</label>
                <select name="cause_of_loss_code" value={formData.cause_of_loss_code} onChange={handleChange}>
                  <option value={1}>Standard / Minor Weather (1)</option>
                  <option value={11}>Drought (11)</option>
                  <option value={12}>Excess Moisture (12)</option>
                  <option value={21}>Hail (21)</option>
                  <option value={31}>Frost/Freeze (31)</option>
                </select>
              </div>
              <div>
                <label>Loss Month</label>
                <select name="month_of_loss" value={formData.month_of_loss} onChange={handleChange}>
                  {[...Array(12)].map((_, i) => (
                    <option key={i + 1} value={i + 1}>{`Month ${i + 1}`}</option>
                  ))}
                </select>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div>
                <label>State Code</label>
                <input
                  type="text"
                  name="state_code"
                  value={formData.state_code}
                  onChange={handleChange}
                  required
                />
              </div>
              <div>
                <label>County Code</label>
                <input
                  type="text"
                  name="county_code"
                  value={formData.county_code}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div>
                <label>Planted Acres</label>
                <input
                  type="number"
                  step="0.1"
                  name="net_planted_acres"
                  value={formData.net_planted_acres}
                  onChange={handleChange}
                  required
                />
              </div>
              <div>
                <label>Determined Acres</label>
                <input
                  type="number"
                  step="0.1"
                  name="net_determined_acres"
                  value={formData.net_determined_acres}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div>
                <label>Liability Amount ($)</label>
                <input
                  type="number"
                  step="100"
                  name="liability_amount"
                  value={formData.liability_amount}
                  onChange={handleChange}
                  required
                />
              </div>
              <div>
                <label>Total Premium ($)</label>
                <input
                  type="number"
                  step="10"
                  name="total_premium"
                  value={formData.total_premium}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
              <div>
                <label style={{ color: 'var(--accent-orange)' }}>Net Indemnity Claimed ($)</label>
                <input
                  type="number"
                  step="100"
                  name="net_indemnity"
                  value={formData.net_indemnity}
                  onChange={handleChange}
                  style={{ borderColor: 'var(--accent-orange)' }}
                  required
                />
              </div>
              <div>
                <label>Determined Yield (bu/acre)</label>
                <input
                  type="number"
                  step="0.1"
                  name="determined_yield"
                  value={formData.determined_yield}
                  onChange={handleChange}
                  required
                />
              </div>
            </div>

            {error && (
              <div style={{ padding: '12px', backgroundColor: 'var(--accent-red-subtle)', border: '1px solid var(--accent-red)', borderRadius: '6px', color: 'var(--accent-red)', fontSize: '13px' }}>
                {error}
              </div>
            )}

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ marginTop: '10px', height: '42px', fontSize: '14px', fontWeight: '600' }}
            >
              {loading ? (
                <span>Processing XGBoost Model & Ganache EVM...</span>
              ) : (
                <>
                  <Send size={16} />
                  <span>Submit Claim & Anchor On-Chain</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Live Result Panel */}
        {result && (
          <div className="card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ fontSize: '16px', fontWeight: '700', color: '#fff' }}>Inference & Ledger Result</h3>
              <span className={`badge ${result.risk_label === 'HIGH' ? 'badge-high' : 'badge-low'}`}>
                {result.risk_label} RISK
              </span>
            </div>

            {/* Score Metric Card */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '20px', padding: '16px', backgroundColor: 'var(--bg-elevated)', borderRadius: '8px', border: '1px solid var(--border)' }}>
              <div style={{
                width: '74px',
                height: '74px',
                borderRadius: '50%',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: result.risk_label === 'HIGH' ? 'var(--accent-red-subtle)' : 'var(--accent-green-subtle)',
                border: `2px solid ${result.risk_label === 'HIGH' ? 'var(--accent-red)' : 'var(--accent-green)'}`,
                color: result.risk_label === 'HIGH' ? 'var(--accent-red)' : 'var(--accent-green)'
              }}>
                <span style={{ fontSize: '18px', fontWeight: '800' }}>
                  {(result.fraud_score * 100).toFixed(1)}%
                </span>
                <span style={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Score</span>
              </div>

              <div>
                <div style={{ fontSize: '14px', fontWeight: '600', color: '#fff' }}>
                  {result.risk_label === 'HIGH' ? 'Suspicious Claim Detected' : 'Clean / Normal Claim Pattern'}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                  {result.risk_label === 'HIGH'
                    ? 'Exceeds fraud threshold. TreeSHAP generated and committed to EVM ledger.'
                    : 'Within normal agronomic variance. Claim hash committed to EVM ledger.'}
                </div>
              </div>
            </div>

            {/* Blockchain Anchoring Details */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Solidity EVM On-Chain Proof
              </div>
              <div className="mono-box" style={{ fontSize: '11px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Claim Ref: </span>
                  <span style={{ color: '#fff', fontWeight: '600' }}>{result.claim_ref}</span>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Canonical SHA-256: </span>
                  <span style={{ color: 'var(--accent-orange)' }}>{result.claim_hash}</span>
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Ethereum Tx Hash: </span>
                  <span style={{ color: 'var(--accent-green)' }}>{result.claim_tx_id}</span>
                </div>
              </div>
            </div>

            {/* SHAP preview if present */}
            {result.explanation && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Top SHAP Fraud Drivers
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {Object.entries(result.explanation.features || {})
                    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
                    .slice(0, 3)
                    .map(([feat, val]) => (
                      <div key={feat} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', padding: '6px 10px', backgroundColor: 'var(--bg-elevated)', borderRadius: '4px' }}>
                        <span style={{ color: 'var(--text-secondary)' }}>{feat}</span>
                        <span style={{ fontWeight: '600', color: val > 0 ? 'var(--accent-red)' : 'var(--accent-green)' }}>
                          {val > 0 ? `+${val.toFixed(4)}` : val.toFixed(4)}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            )}

            {/* Quick Link to Auditor View */}
            <button
              type="button"
              onClick={() => onViewClaimInAudit && onViewClaimInAudit(result.claim_ref)}
              className="btn btn-secondary"
              style={{ width: '100%', justifyContent: 'center', borderColor: 'var(--border)' }}
            >
              <span>Test Integrity & Tampering in Auditor</span>
              <ArrowRight size={14} />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
