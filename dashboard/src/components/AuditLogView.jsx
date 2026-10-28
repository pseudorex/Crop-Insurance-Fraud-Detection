import React, { useState, useEffect } from 'react';
import { ShieldCheck, ShieldAlert, Link, RefreshCw, CheckCircle2, AlertTriangle, Search, Database, Lock, Eye } from 'lucide-react';
import { fetchAuditLog, verifyAuditChain, fetchMissingRecords } from '../api';

export default function AuditLogView({ currentInsurer }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [claimFilter, setClaimFilter] = useState('');
  const [chainVerification, setChainVerification] = useState(null);
  const [verifyingChain, setVerifyingChain] = useState(false);
  const [missingRecords, setMissingRecords] = useState(null);
  const [checkingMissing, setCheckingMissing] = useState(false);

  const loadLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAuditLog(currentInsurer, claimFilter || null, 100);
      setLogs(data || []);
    } catch (err) {
      setError(err.message || 'Failed to load audit log');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
    setChainVerification(null);
    setMissingRecords(null);
  }, [currentInsurer]);

  const handleVerifyChain = async () => {
    setVerifyingChain(true);
    try {
      const res = await verifyAuditChain(currentInsurer);
      setChainVerification(res);
    } catch (err) {
      setChainVerification({ valid: false, reason: err.message });
    } finally {
      setVerifyingChain(false);
    }
  };

  const handleCheckMissing = async () => {
    setCheckingMissing(true);
    try {
      const res = await fetchMissingRecords(currentInsurer);
      setMissingRecords(res);
    } catch (err) {
      setMissingRecords({ status: 'ERROR', error: err.message });
    } finally {
      setCheckingMissing(false);
    }
  };

  const getActionBadge = (action) => {
    const act = (action || '').toUpperCase();
    if (act.includes('TAMPER')) {
      return { bg: 'rgba(239, 71, 67, 0.2)', color: 'var(--accent-red)', border: '1px solid rgba(239, 71, 67, 0.4)' };
    }
    if (act.includes('ACCESS_DENIED')) {
      return { bg: 'rgba(255, 192, 30, 0.2)', color: 'var(--accent-yellow)', border: '1px solid rgba(255, 192, 30, 0.4)' };
    }
    if (act.includes('RESTORE')) {
      return { bg: 'rgba(0, 184, 163, 0.2)', color: 'var(--accent-green)', border: '1px solid rgba(0, 184, 163, 0.4)' };
    }
    if (act.includes('SUBMIT')) {
      return { bg: 'rgba(59, 130, 246, 0.2)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.4)' };
    }
    if (act.includes('AUDIT')) {
      return { bg: 'rgba(168, 85, 247, 0.2)', color: '#c084fc', border: '1px solid rgba(168, 85, 247, 0.4)' };
    }
    return { bg: '#282828', color: '#ccc', border: '1px solid #444' };
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Banner & Info */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Lock size={20} color="var(--accent-orange)" />
            <h2 style={{ fontSize: '20px', fontWeight: '700', color: '#fff' }}>
              Immutable Append-Only Audit Log — <span style={{ color: 'var(--accent-orange)' }}>{currentInsurer}</span>
            </h2>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Cryptographic SHA-256 hash chain with database-level UPDATE and DELETE revocation.
          </p>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={handleVerifyChain}
            disabled={verifyingChain}
            className="btn btn-primary"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <ShieldCheck size={16} />
            <span>{verifyingChain ? 'Verifying Chain...' : 'Verify Hash Chain'}</span>
          </button>

          <button
            type="button"
            onClick={handleCheckMissing}
            disabled={checkingMissing}
            className="btn btn-secondary"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Database size={16} />
            <span>{checkingMissing ? 'Scanning...' : 'Check Missing Records'}</span>
          </button>

          <button
            type="button"
            onClick={loadLogs}
            disabled={loading}
            className="btn btn-secondary"
            title="Refresh Log"
          >
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Hash Chain Verification Result Banner */}
      {chainVerification && (
        <div style={{
          padding: '16px 20px',
          borderRadius: '8px',
          backgroundColor: chainVerification.valid ? 'rgba(0, 184, 163, 0.12)' : 'rgba(239, 71, 67, 0.15)',
          border: `1px solid ${chainVerification.valid ? 'rgba(0, 184, 163, 0.4)' : 'rgba(239, 71, 67, 0.5)'}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            {chainVerification.valid ? (
              <CheckCircle2 size={24} color="var(--accent-green)" />
            ) : (
              <AlertTriangle size={24} color="var(--accent-red)" />
            )}
            <div>
              <div style={{ fontSize: '14px', fontWeight: '700', color: chainVerification.valid ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                {chainVerification.valid
                  ? `Cryptographic Hash Chain Intact (${chainVerification.total_entries} immutable entries verified)`
                  : `Hash Chain Integrity Broken at ID #${chainVerification.broken_at_id}!`}
              </div>
              <div style={{ fontSize: '12px', color: '#ccc', marginTop: '2px' }}>
                {chainVerification.valid
                  ? `Latest block hash: ${chainVerification.latest_hash}`
                  : chainVerification.reason}
              </div>
            </div>
          </div>
          <span style={{
            fontSize: '11px',
            fontWeight: '700',
            padding: '4px 10px',
            borderRadius: '4px',
            backgroundColor: chainVerification.valid ? 'var(--accent-green)' : 'var(--accent-red)',
            color: '#000'
          }}>
            {chainVerification.valid ? 'CHAIN VERIFIED' : 'TAMPER DETECTED'}
          </span>
        </div>
      )}

      {/* Missing Records Result Banner */}
      {missingRecords && (
        <div style={{
          padding: '14px 18px',
          borderRadius: '8px',
          backgroundColor: missingRecords.status === 'CLEAN' ? 'rgba(59, 130, 246, 0.12)' : 'rgba(239, 71, 67, 0.15)',
          border: `1px solid ${missingRecords.status === 'CLEAN' ? 'rgba(59, 130, 246, 0.3)' : 'rgba(239, 71, 67, 0.5)'}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '13px'
        }}>
          <div>
            <span style={{ fontWeight: 600 }}>On-Chain vs Database Alignment: </span>
            <span>On-chain anchors: <strong>{missingRecords.total_on_chain || 0}</strong> &bull; Local records: <strong>{missingRecords.total_in_db || 0}</strong></span>
            {missingRecords.missing_claims?.length > 0 && (
              <div style={{ color: 'var(--accent-red)', marginTop: '4px', fontWeight: 600 }}>
                Missing from DB: {missingRecords.missing_claims.join(', ')}
              </div>
            )}
          </div>
          <span style={{
            fontSize: '11px',
            fontWeight: 700,
            padding: '3px 8px',
            borderRadius: '4px',
            backgroundColor: missingRecords.status === 'CLEAN' ? '#3b82f6' : 'var(--accent-red)',
            color: '#fff'
          }}>
            {missingRecords.status === 'CLEAN' ? 'IN SYNC' : 'DISCREPANCY'}
          </span>
        </div>
      )}

      {/* Filter Bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{ position: 'relative', width: '320px' }}>
          <Search size={15} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-muted)' }} />
          <input
            type="text"
            placeholder="Filter by Claim Reference..."
            value={claimFilter}
            onChange={(e) => setClaimFilter(e.target.value)}
            style={{ paddingLeft: '32px' }}
          />
        </div>
        <button
          type="button"
          onClick={loadLogs}
          className="btn btn-secondary"
          style={{ padding: '8px 16px' }}
        >
          Apply Filter
        </button>
      </div>

      {/* Log Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '12.5px' }}>
            <thead>
              <tr style={{ backgroundColor: '#202020', borderBottom: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                <th style={{ padding: '12px 14px', width: '50px' }}>ID</th>
                <th style={{ padding: '12px 14px', width: '160px' }}>Timestamp</th>
                <th style={{ padding: '12px 14px', width: '120px' }}>User</th>
                <th style={{ padding: '12px 14px', width: '100px' }}>Role</th>
                <th style={{ padding: '12px 14px', width: '150px' }}>Action</th>
                <th style={{ padding: '12px 14px', width: '180px' }}>Claim Ref</th>
                <th style={{ padding: '12px 14px' }}>Details &amp; Audit Trail</th>
                <th style={{ padding: '12px 14px', width: '140px' }}>Hash Chain</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    Loading audit trail...
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    No audit records recorded yet.
                  </td>
                </tr>
              ) : (
                logs.map((entry) => {
                  const badge = getActionBadge(entry.action);
                  const detailsObj = typeof entry.details === 'object' && entry.details !== null
                    ? entry.details
                    : {};
                  return (
                    <tr
                      key={entry.id}
                      style={{ borderBottom: '1px solid #2e2e2e', transition: 'background-color 0.15s ease' }}
                      onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'rgba(255, 161, 22, 0.04)'; }}
                      onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; }}
                    >
                      <td style={{ padding: '10px 14px', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                        #{entry.id}
                      </td>
                      <td style={{ padding: '10px 14px', color: '#bbb' }}>
                        {entry.timestamp ? new Date(entry.timestamp).toLocaleString() : '-'}
                      </td>
                      <td style={{ padding: '10px 14px', fontWeight: 600, color: '#fff' }}>
                        {entry.username || 'system'}
                      </td>
                      <td style={{ padding: '10px 14px' }}>
                        <span style={{
                          fontSize: '10px',
                          fontWeight: 700,
                          padding: '2px 6px',
                          borderRadius: '4px',
                          backgroundColor: '#303030',
                          color: '#ddd'
                        }}>
                          {(entry.role || 'system').toUpperCase()}
                        </span>
                      </td>
                      <td style={{ padding: '10px 14px' }}>
                        <span style={{
                          fontSize: '11px',
                          fontWeight: 700,
                          padding: '3px 8px',
                          borderRadius: '4px',
                          ...badge
                        }}>
                          {entry.action}
                        </span>
                      </td>
                      <td style={{ padding: '10px 14px', fontFamily: 'monospace', color: 'var(--accent-orange)' }}>
                        {entry.claim_ref || '—'}
                      </td>
                      <td style={{ padding: '10px 14px', color: '#aaa', fontSize: '11.5px', maxWidth: '300px' }}>
                        <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={JSON.stringify(detailsObj)}>
                          {Object.keys(detailsObj).length > 0 ? JSON.stringify(detailsObj) : '—'}
                        </div>
                      </td>
                      <td style={{ padding: '10px 14px', fontFamily: 'monospace', fontSize: '10.5px' }}>
                        <div title={`Prev: ${entry.prev_hash}\nEntry: ${entry.entry_hash}`}>
                          <div style={{ color: 'var(--text-muted)' }}>
                            P: {entry.prev_hash ? `${entry.prev_hash.slice(0, 8)}...` : '00000000...'}
                          </div>
                          <div style={{ color: 'var(--accent-green)' }}>
                            E: {entry.entry_hash ? `${entry.entry_hash.slice(0, 8)}...` : '00000000...'}
                          </div>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
