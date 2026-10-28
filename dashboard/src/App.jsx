import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import IntakeView from './components/IntakeView';
import ClaimsView from './components/ClaimsView';
import AuditorView from './components/AuditorView';
import NetworkView from './components/NetworkView';
import AuditLogView from './components/AuditLogView';
import AuthModal from './components/AuthModal';
import { fetchHealth, getStoredUser, getStoredToken, clearStoredAuth, setOnUnauthorized } from './api';

export default function App() {
  const [currentUser, setCurrentUser] = useState(() => getStoredUser());
  const [currentInsurer, setCurrentInsurer] = useState(() => {
    const u = getStoredUser();
    const role = (u?.role || '').toLowerCase();
    if (role.includes('auditor')) return 'insurer1';
    return u?.insurer_id || 'insurer1';
  });
  const [activeTab, setActiveTab] = useState(() => {
    const u = getStoredUser();
    const role = (u?.role || '').toLowerCase();
    if (role.includes('auditor')) return 'auditor';
    if (role.includes('admin')) return 'claims';
    return 'intake';
  });
  const [auditTargetClaim, setAuditTargetClaim] = useState('');
  const [health, setHealth] = useState(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  const userRole = (currentUser?.role || '').toLowerCase();
  const isAdjuster = userRole === 'adjuster' || userRole.includes('adjuster') || userRole.includes('officer');
  const isAdmin = userRole === 'admin' || userRole.includes('admin');
  const isAuditor = userRole === 'auditor' || userRole.includes('auditor');

  // Handle 401 Unauthorized globally: clear state and open auth modal
  useEffect(() => {
    setOnUnauthorized(() => {
      clearStoredAuth();
      setCurrentUser(null);
      setIsAuthModalOpen(true);
    });
  }, []);

  // Strict RBAC Role Guard & Route Enforcement
  useEffect(() => {
    if (!currentUser) {
      setIsAuthModalOpen(true);
      return;
    }

    if (isAdjuster) {
      // Adjuster can only view intake and my claims
      if (activeTab !== 'intake' && activeTab !== 'claims') {
        setActiveTab('intake');
      }
      if (currentUser.insurer_id && currentInsurer !== currentUser.insurer_id) {
        setCurrentInsurer(currentUser.insurer_id);
      }
    } else if (isAdmin) {
      // Admin can view claims, auditor, network; cannot submit claims
      if (activeTab === 'intake' || activeTab === 'audit_log') {
        setActiveTab('claims');
      }
      if (currentUser.insurer_id && currentInsurer !== currentUser.insurer_id) {
        setCurrentInsurer(currentUser.insurer_id);
      }
    } else if (isAuditor) {
      // Auditor has access to all insurers, cannot submit claims
      if (activeTab === 'intake' || activeTab === 'audit_log') {
        setActiveTab('auditor');
      }
      if (currentInsurer === 'auditor' || currentInsurer === 'ALL' || currentInsurer?.toUpperCase() === 'INDIVIDUAL') {
        setCurrentInsurer('insurer1');
      }
    } else {
      // Fallback: Default to claims ledger so screen is never blank
      if (activeTab === 'audit_log') {
        setActiveTab('claims');
      }
    }
  }, [currentUser, isAdjuster, isAdmin, isAuditor, activeTab, currentInsurer]);

  // Initial check: if no token, prompt sign-in
  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setIsAuthModalOpen(true);
    }
  }, []);

  useEffect(() => {
    fetchHealth().then(setHealth).catch(console.error);
    const interval = setInterval(() => {
      fetchHealth().then(setHealth).catch(console.error);
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleAuthSuccess = (user) => {
    setCurrentUser(user);
    setIsAuthModalOpen(false);
    const role = (user.role || '').toLowerCase();
    if (role.includes('auditor')) {
      setCurrentInsurer((prev) => (prev && prev !== 'ALL' && prev?.toUpperCase() !== 'INDIVIDUAL' && prev !== 'auditor' ? prev : 'insurer1'));
      setActiveTab('auditor');
    } else if (role.includes('admin')) {
      setCurrentInsurer(user.insurer_id || 'insurer1');
      setActiveTab('claims');
    } else {
      setCurrentInsurer(user.insurer_id || 'insurer1');
      setActiveTab('intake');
    }
  };

  const handleLogout = () => {
    clearStoredAuth();
    setCurrentUser(null);
    setIsAuthModalOpen(true);
  };

  const handleNavigateToAudit = (claimRef) => {
    if (isAdmin || isAuditor) {
      setAuditTargetClaim(claimRef);
      setActiveTab('auditor');
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-main)' }}>
      {/* Consortium Header with Authenticated Profile & Role-Scoped Navigation */}
      <Header
        currentInsurer={currentInsurer}
        onSelectInsurer={setCurrentInsurer}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        health={health}
        currentUser={currentUser}
        onOpenAuthModal={() => setIsAuthModalOpen(true)}
        onLogout={handleLogout}
      />

      {/* Main Content Area */}
      <main style={{ flex: 1, padding: '24px', maxWidth: '1400px', width: '100%', margin: '0 auto' }}>
        {/* Claim Intake: Only accessible to Adjusters */}
        {isAdjuster && activeTab === 'intake' && (
          <IntakeView
            currentInsurer={currentInsurer}
            onViewClaimInAudit={handleNavigateToAudit}
          />
        )}

        {/* Claims Ledger / Status: Accessible to Adjuster (own claims), Admin (own insurer), Auditor (all insurers) */}
        {activeTab === 'claims' && (
          <ClaimsView
            currentInsurer={currentInsurer}
            currentUser={currentUser}
            onSelectForAudit={handleNavigateToAudit}
          />
        )}

        {/* Auditor & Integrity View: Accessible to Admin (own insurer) and Auditor (all insurers). Hidden from Adjuster. */}
        {(isAdmin || isAuditor) && activeTab === 'auditor' && (
          <AuditorView
            currentInsurer={currentInsurer}
            initialClaimRef={auditTargetClaim}
            currentUser={currentUser}
          />
        )}

        {/* Immutable Audit Log & Hash Chain: Accessible to Admin and Auditor */}
        {(isAdmin || isAuditor) && activeTab === 'audit_log' && (
          <AuditLogView
            currentInsurer={currentInsurer}
          />
        )}

        {/* Models & Network: Accessible to Admin and Auditor */}
        {(isAdmin || isAuditor) && activeTab === 'network' && (
          <NetworkView
            health={health}
          />
        )}
      </main>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid var(--border)', padding: '16px 24px', textAlign: 'center', fontSize: '12px', color: 'var(--text-muted)' }}>
        <span>
          Crop Insurance Fraud Consortium &bull; Argon2id / Bcrypt Multi-Tenant RBAC &bull; EVM Smart Contract Audit Chain
        </span>
      </footer>

      {/* Authentication Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onAuthSuccess={handleAuthSuccess}
        currentUser={currentUser}
      />
    </div>
  );
}
