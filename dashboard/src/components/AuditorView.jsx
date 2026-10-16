import React, { useState, useEffect } from 'react';
import { ShieldCheck, ShieldAlert, AlertTriangle, RefreshCw, Database, Cpu, CheckCircle2, XCircle, ArrowRight, CornerDownRight } from 'lucide-react';
import { listClaims, runAudit, tamperClaim, tamperExplanation, restoreClaim } from '../api';

export default function AuditorView({ currentInsurer, initialClaimRef }) {
  const [claims, setClaims] = useState([]);
  const [selectedClaimRef, setSelectedClaimRef] = useState(initialClaimRef || '');
  const [auditReport, setAuditReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);
  const [tampering, setTampering] = useState(false);

  // Load claims for active insurer
  useEffect(() => {
    let isMounted = true;
    listClaims(currentInsurer).then((list) => {
      if (!isMounted) return;
      setClaims(list || []);
      if (!selectedClaimRef && list && list.length > 0) {
        setSelectedClaimRef(list[0].claim_ref);
      }
    }).catch(console.error);
    return () => { isMounted = false; };
  }, [currentInsurer]);

  // When initialClaimRef prop changes
  useEffect(() => {
    if (initialClaimRef) {
      setSelectedClaimRef(initialClaimRef);
    }
  }, [initialClaimRef]);

  // Run audit whenever selectedClaimRef changes
  useEffect(() => {
    if (selectedClaimRef) {
      executeAudit(selectedClaimRef);
    }
  }, [selectedClaimRef, currentInsurer]);

  const executeAudit = async (ref) => {
    if (!ref) return;
    setLoading(true);
    setActionMessage(null);
    try {
      const res = await runAudit(currentInsurer, ref);
      setAuditReport(res);
    } catch (err) {
      console.error('Audit failed', err);
    } finally {
      setLoading(false);
    }
  };

  const handleTamperClaim = async () => {
    if (!selectedClaimRef) return;
    setTampering(true);
    setActionMessage(null);
    try {
      await tamperClaim(currentInsurer, selectedClaimRef, 99999.0);
      setActionMessage({
        type: 'danger',
        text: `Tampered claim ${selectedClaimRef} in PostgreSQL (${currentInsurer}_db). Indemnity forced to $99,999.00.`
      });
      await executeAudit(selectedClaimRef);
    } catch (err) {
      setActionMessage({ type: 'danger', text: err.message || 'Tamper failed' });
    } finally {
      setTampering(false);
    }
  };

  const handleTamperExplanation = async () => {
    if (!selectedClaimRef) return;
    setTampering(true);
    setActionMessage(null);
    try {
      await tamperExplanation(currentInsurer, selectedClaimRef, 'indemnity_to_liability_ratio', 0.999);
      setActionMessage({
        type: 'danger',
        text: `Tampered TreeSHAP explanation for ${selectedClaimRef} in PostgreSQL. Corrupted feature weights.`
      });
      await executeAudit(selectedClaimRef);
    } catch (err) {
      setActionMessage({ type: 'danger', text: err.message || 'Tamper failed' });
    } finally {
      setTampering(false);
    }
  };

  const handleRestore = async () => {
    if (!selectedClaimRef) return;
    setTampering(true);
    setActionMessage(null);
    try {
      await restoreClaim(currentInsurer, selectedClaimRef);
      setActionMessage({
        type: 'success',
        text: `Restored original legitimate record for ${selectedClaimRef} in PostgreSQL (${currentInsurer}_db).`
      });
      await executeAudit(selectedClaimRef);
    } catch (err) {
      setActionMessage({ type: 'danger', text: err.message || 'Restore failed' });
    } finally {
      setTampering(false);
    }
  };

  const isVerified = auditReport?.overall_status === 'VERIFIED';
  const checks = auditReport?.checks || {};

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Top Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '700', color: '#fff' }}>
            Consortium Cryptographic Auditor & Tamper Defense
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            4-phase independent integrity verification comparing local PostgreSQL records against Ganache Ethereum commitments.
          </p>
        </div>

        {/* Claim Selector & Re-audit */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <select
            value={selectedClaimRef}
            onChange={(e) => setSelectedClaimRef(e.target.value)}
            style={{ width: '280px', fontWeight: '600', fontFamily: 'JetBrains Mono, monospace' }}
          >
            {claims.map((c) => {
              const cData = c.claim_data || {};
              const ind = c.net_indemnity ?? cData.net_indemnity ?? 0;
              return (
                <option key={c.claim_ref} value={c.claim_ref}>
                  {c.claim_ref} ({c.risk_label} - ${parseFloat(ind).toLocaleString()})
                </option>
              );
            })}
          </select>

          <button
            type="button"
            onClick={() => executeAudit(selectedClaimRef)}
            className="btn btn-secondary"
            disabled={loading || !selectedClaimRef}
          >
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
            <span>Verify Now</span>
          </button>
        </div>
      </div>

      {/* Main Status & Summary */}
      {auditReport && (
        <div className="card" style={{
          padding: '24px',
          borderLeft: `4px solid ${isVerified ? 'var(--accent-green)' : 'var(--accent-red)'}`,
          backgroundColor: isVerified ? 'rgba(0, 184, 163, 0.05)' : 'rgba(239, 71, 67, 0.05)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <div style={{
                width: '48px',
                height: '48px',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: isVerified ? 'var(--accent-green-subtle)' : 'var(--accent-red-subtle)',
                color: isVerified ? 'var(--accent-green)' : 'var(--accent-red)'
              }}>
                {isVerified ? <ShieldCheck size={28} /> : <ShieldAlert size={28} />}
              </div>

              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '18px', fontWeight: '800', color: isVerified ? 'var(--accent-green)' : 'var(--accent-red)', letterSpacing: '0.5px' }}>
                    {isVerified ? 'ALL CRYPTOGRAPHIC CHECKS PASSED' : 'SECURITY TAMPER DETECTED!'}
                  </span>
                  <span className={`badge ${isVerified ? 'badge-verified' : 'badge-tampered'}`}>
                    {auditReport.overall_status}
                  </span>
                </div>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  Target Claim: <span style={{ color: '#fff', fontFamily: 'JetBrains Mono, monospace', fontWeight: '600' }}>{auditReport.claim_ref}</span>
                  {auditReport.timestamp && (
                    <span style={{ marginLeft: '12px', color: 'var(--text-muted)' }}>
                      On-Chain Timestamp: {new Date(auditReport.timestamp * 1000).toLocaleString()}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Action Notification Banner */}
      {actionMessage && (
        <div style={{
          padding: '12px 18px',
          borderRadius: '6px',
          fontSize: '13px',
          backgroundColor: actionMessage.type === 'danger' ? 'var(--accent-red-subtle)' : 'var(--accent-green-subtle)',
          border: `1px solid ${actionMessage.type === 'danger' ? 'var(--accent-red)' : 'var(--accent-green)'}`,
          color: actionMessage.type === 'danger' ? 'var(--accent-red)' : 'var(--accent-green)',
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }}>
          {actionMessage.type === 'danger' ? <AlertTriangle size={16} /> : <CheckCircle2 size={16} />}
          <span>{actionMessage.text}</span>
        </div>
      )}

      {/* 4-Phase Verification Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        {/* Phase 1: Claim Integrity */}
        <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', fontWeight: '600', color: '#fff' }}>
              <Database size={16} style={{ color: 'var(--accent-orange)' }} />
              <span>Phase 1: Claim Record Integrity</span>
            </div>
            <span className={`badge ${checks.claim_integrity?.status === 'VERIFIED' ? 'badge-verified' : 'badge-tampered'}`}>
              {checks.claim_integrity?.status || 'PENDING'}
            </span>
          </div>

          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            {checks.claim_integrity?.detail || 'Verifying local PostgreSQL canonical SHA-256 against Ganache Ethereum anchor...'}
          </p>

          <div className="mono-box" style={{ fontSize: '11px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Local DB Hash: </span>
              <span style={{ color: checks.claim_integrity?.status === 'VERIFIED' ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                {checks.claim_integrity?.local_hash || checks.claim_integrity?.hash || '—'}
              </span>
            </div>
            {checks.claim_integrity?.ledger_hash && (
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Ledger Hash: </span>
                <span style={{ color: 'var(--accent-orange)' }}>
                  {checks.claim_integrity?.ledger_hash}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Phase 2: Explanation Integrity */}
        <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', fontWeight: '600', color: '#fff' }}>
              <Cpu size={16} style={{ color: 'var(--accent-orange)' }} />
              <span>Phase 2: TreeSHAP Explanation Integrity</span>
            </div>
            <span className={`badge ${checks.explanation_integrity?.status === 'VERIFIED' ? 'badge-verified' : checks.explanation_integrity?.status === 'NOT_APPLICABLE' ? 'badge-low' : 'badge-tampered'}`}>
              {checks.explanation_integrity?.status || 'PENDING'}
            </span>
          </div>

          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            {checks.explanation_integrity?.detail || 'Verifying SHAP feature weights hash against on-chain explanation commitment...'}
          </p>

          <div className="mono-box" style={{ fontSize: '11px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Local SHAP Hash: </span>
              <span style={{ color: checks.explanation_integrity?.status === 'VERIFIED' ? 'var(--accent-green)' : checks.explanation_integrity?.status === 'NOT_APPLICABLE' ? 'var(--text-muted)' : 'var(--accent-red)' }}>
                {checks.explanation_integrity?.local_hash || checks.explanation_integrity?.hash || 'Not Required (Low Risk)'}
              </span>
            </div>
            {checks.explanation_integrity?.ledger_hash && (
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Ledger Hash: </span>
                <span style={{ color: 'var(--accent-orange)' }}>
                  {checks.explanation_integrity?.ledger_hash}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Phase 3: Model Integrity */}
        <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', fontWeight: '600', color: '#fff' }}>
              <ShieldCheck size={16} style={{ color: 'var(--accent-green)' }} />
              <span>Phase 3: Global Model Commitment</span>
            </div>
            <span className={`badge ${checks.model_integrity?.status === 'VERIFIED' ? 'badge-verified' : 'badge-tampered'}`}>
              {checks.model_integrity?.status || 'PENDING'}
            </span>
          </div>

          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            {checks.model_integrity?.detail || 'Verifying local XGBoost DP model weights file against registered smart contract commitment...'}
          </p>

          <div className="mono-box" style={{ fontSize: '11px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Local Model Weights SHA-256: </span>
              <span style={{ color: 'var(--accent-green)' }}>
                {checks.model_integrity?.hash || checks.model_integrity?.local_hash || '8d7468f5ab0f6255...'}
              </span>
            </div>
          </div>
        </div>

        {/* Phase 4: Consistency Check */}
        <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px', fontWeight: '600', color: '#fff' }}>
              <CheckCircle2 size={16} style={{ color: 'var(--accent-green)' }} />
              <span>Phase 4: Risk & Version Consistency</span>
            </div>
            <span className={`badge ${checks.consistency?.status === 'VERIFIED' ? 'badge-verified' : 'badge-tampered'}`}>
              {checks.consistency?.status || 'PENDING'}
            </span>
          </div>

          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            {checks.consistency?.detail || 'Verifying risk label and model version alignment between PostgreSQL and Ethereum...'}
          </p>

          <div className="mono-box" style={{ fontSize: '11px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Status: </span>
              <span style={{ color: checks.consistency?.status === 'VERIFIED' ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                {checks.consistency?.status === 'VERIFIED' ? 'CONSISTENT (DB == Smart Contract)' : 'MISMATCH'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Interactive Tamper Attack Sandbox */}
      <div className="card" style={{ padding: '24px', border: '1px solid rgba(239, 71, 67, 0.3)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: '700', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={18} style={{ color: 'var(--accent-red)' }} />
              <span>Live Tamper Attack Sandbox</span>
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
              Simulate an insider database attack or unauthorized modification directly inside PostgreSQL to observe real-time cryptographic audit failure.
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={handleTamperClaim}
            disabled={tampering || !selectedClaimRef}
            className="btn btn-secondary"
            style={{ borderColor: 'var(--accent-red)', color: 'var(--accent-red)', backgroundColor: 'var(--accent-red-subtle)' }}
          >
            <span>Attack 1: Tamper Claim Amount ($99,999)</span>
          </button>

          <button
            type="button"
            onClick={handleTamperExplanation}
            disabled={tampering || !selectedClaimRef}
            className="btn btn-secondary"
            style={{ borderColor: 'var(--accent-yellow)', color: 'var(--accent-yellow)', backgroundColor: 'rgba(255, 192, 30, 0.1)' }}
          >
            <span>Attack 2: Tamper TreeSHAP Feature Weights</span>
          </button>

          <button
            type="button"
            onClick={handleRestore}
            disabled={tampering || !selectedClaimRef}
            className="btn btn-secondary"
            style={{ borderColor: 'var(--accent-green)', color: 'var(--accent-green)', backgroundColor: 'var(--accent-green-subtle)', marginLeft: 'auto' }}
          >
            <CheckCircle2 size={14} />
            <span>Restore Legitimate State</span>
          </button>
        </div>
      </div>
    </div>
  );
}
