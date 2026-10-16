import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import IntakeView from './components/IntakeView';
import ClaimsView from './components/ClaimsView';
import AuditorView from './components/AuditorView';
import NetworkView from './components/NetworkView';
import { fetchHealth } from './api';

export default function App() {
  const [currentInsurer, setCurrentInsurer] = useState('insurer1');
  const [activeTab, setActiveTab] = useState('intake');
  const [auditTargetClaim, setAuditTargetClaim] = useState('');
  const [health, setHealth] = useState(null);

  useEffect(() => {
    fetchHealth().then(setHealth).catch(console.error);
    const interval = setInterval(() => {
      fetchHealth().then(setHealth).catch(console.error);
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleNavigateToAudit = (claimRef) => {
    setAuditTargetClaim(claimRef);
    setActiveTab('auditor');
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-main)' }}>
      {/* Consortium Header */}
      <Header
        currentInsurer={currentInsurer}
        onSelectInsurer={setCurrentInsurer}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        health={health}
      />

      {/* Main Tab Content */}
      <main style={{ flex: 1, padding: '24px', maxWidth: '1400px', width: '100%', margin: '0 auto' }}>
        {activeTab === 'intake' && (
          <IntakeView
            currentInsurer={currentInsurer}
            onViewClaimInAudit={handleNavigateToAudit}
          />
        )}

        {activeTab === 'claims' && (
          <ClaimsView
            currentInsurer={currentInsurer}
            onSelectForAudit={handleNavigateToAudit}
          />
        )}

        {activeTab === 'auditor' && (
          <AuditorView
            currentInsurer={currentInsurer}
            initialClaimRef={auditTargetClaim}
          />
        )}

        {activeTab === 'network' && (
          <NetworkView
            health={health}
          />
        )}
      </main>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid var(--border)', padding: '16px 24px', textAlign: 'center', fontSize: '12px', color: 'var(--text-muted)' }}>
        <span>Crop Insurance Fraud Consortium &bull; Differential Privacy ML &amp; EVM Blockchain Proof Engine &bull; PostgreSQL 16 Cluster</span>
      </footer>
    </div>
  );
}
