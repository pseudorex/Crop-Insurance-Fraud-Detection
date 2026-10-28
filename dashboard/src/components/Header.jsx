import React from 'react';
import { ShieldCheck, Database, Cpu, Lock, LogIn, LogOut, KeyRound, SearchCode, Building2 } from 'lucide-react';

const CONSORTIUM_INSURERS = [
  { id: 'insurer1', name: 'Insurer 1 (Alliance Agri)' },
  { id: 'insurer2', name: 'Insurer 2 (Midwest Mutual)' },
  { id: 'insurer3', name: 'Insurer 3 (Great Plains Corp)' },
  { id: 'insurer4', name: 'Insurer 4 (National Crop)' },
  { id: 'insurer5', name: 'Insurer 5 (Pioneer Harvest)' },
  { id: 'insurer6', name: 'Insurer 6 (Frontier Farm)' },
];

export default function Header({
  currentInsurer,
  onSelectInsurer,
  activeTab,
  onSelectTab,
  health,
  currentUser,
  onOpenAuthModal,
  onLogout
}) {
  const userRole = (currentUser?.role || '').toLowerCase();
  const isAdjuster = userRole === 'adjuster' || userRole.includes('adjuster') || userRole.includes('officer');
  const isAdmin = userRole === 'admin' || userRole.includes('admin');
  const isAuditor = userRole === 'auditor' || userRole.includes('auditor');

  const allInsurers = [...CONSORTIUM_INSURERS];
  if (currentUser?.insurer_id && !allInsurers.some(i => i.id === currentUser.insurer_id) && currentUser.insurer_id.toLowerCase() !== 'all' && currentUser.insurer_id.toLowerCase() !== 'individual') {
    allInsurers.push({ id: currentUser.insurer_id, name: currentUser.insurer_name || currentUser.insurer_id });
  }

  // Role-based separation of duties (RBAC):
  // - Adjusters: Only submit claims and view own claims status list. No audit, no network, no tamper.
  // - Admins: Claims Ledger, Auditor & Integrity, Models & Network (scoped to own tenant).
  // - Auditors: Consortium-wide read-only access to all 6 insurers. No claim intake.
  let tabs = [];
  if (isAdjuster) {
    tabs = [
      { id: 'intake', label: 'Claim Intake' },
      { id: 'claims', label: 'My Claims' },
    ];
  } else if (isAdmin) {
    tabs = [
      { id: 'claims', label: 'Claims Ledger' },
      { id: 'auditor', label: 'Auditor & Integrity' },
      { id: 'network', label: 'Models & Network' },
    ];
  } else if (isAuditor) {
    tabs = [
      { id: 'auditor', label: 'Auditor & Integrity' },
      { id: 'claims', label: 'Claims Ledger' },
      { id: 'network', label: 'Models & Network' },
    ];
  } else {
    tabs = [
      { id: 'intake', label: 'Claim Intake' },
      { id: 'claims', label: 'Claims Ledger' },
      { id: 'network', label: 'Models & Network' },
    ];
  }

  const roleColor = isAdjuster ? '#60a5fa' : isAdmin ? 'var(--accent-green)' : 'var(--accent-orange)';
  const roleBg = isAdjuster ? 'rgba(59, 130, 246, 0.2)' : isAdmin ? 'rgba(34, 197, 94, 0.2)' : 'rgba(255, 161, 22, 0.25)';

  return (
    <header style={{ borderBottom: '1px solid var(--border)', backgroundColor: '#181818', position: 'sticky', top: 0, zIndex: 100 }}>
      {/* Top Banner */}
      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '12px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '20px', flexWrap: 'wrap' }}>
        
        {/* Left: Consortium Branding */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            backgroundColor: 'var(--accent-orange-subtle)',
            color: 'var(--accent-orange)',
            border: '1px solid rgba(255, 161, 22, 0.3)'
          }}>
            <ShieldCheck size={22} />
          </div>
          <div>
            <h1 style={{ fontSize: '16px', fontWeight: '700', letterSpacing: '-0.3px', color: '#fff', margin: 0 }}>
              Crop Insurance Fraud Consortium
            </h1>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)', margin: '2px 0 0 0' }}>
              Federated DP-ML &bull; Solidity Ethereum Ledger &bull; Role-Based Governance
            </p>
          </div>
        </div>

        {/* Center: Authenticated User Profile & Insurer Scope */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          {currentUser ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              {/* If Auditor: Display target insurer switcher across all 6 */}
              {isAuditor ? (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  backgroundColor: 'rgba(255, 161, 22, 0.08)',
                  border: '1px solid rgba(255, 161, 22, 0.3)',
                  borderRadius: '8px',
                  padding: '5px 10px'
                }}>
                  <SearchCode size={15} color="var(--accent-orange)" />
                  <span style={{ fontSize: '12px', fontWeight: 600, color: '#ddd' }}>
                    Auditing Insurer:
                  </span>
                  <select
                    value={currentInsurer}
                    onChange={(e) => onSelectInsurer(e.target.value)}
                    style={{
                      backgroundColor: '#222',
                      borderColor: '#444',
                      color: '#fff',
                      fontSize: '12px',
                      fontWeight: 600,
                      padding: '4px 8px',
                      borderRadius: '4px',
                      cursor: 'pointer'
                    }}
                  >
                    {allInsurers.map((ins) => (
                      <option key={ins.id} value={ins.id}>{ins.name}</option>
                    ))}
                  </select>
                </div>
              ) : (
                /* Admin or Adjuster: Strictly locked to their tenant */
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  backgroundColor: '#222',
                  border: '1px solid #383838',
                  borderRadius: '8px',
                  padding: '6px 12px'
                }}>
                  <Building2 size={15} color={roleColor} />
                  <span style={{ fontSize: '12px', fontWeight: 600, color: '#aaa' }}>
                    Tenant:
                  </span>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: '#fff' }}>
                    {CONSORTIUM_INSURERS.find(i => i.id === currentUser?.insurer_id)?.name || currentUser?.insurer_name || currentUser?.insurer_id}
                  </span>
                </div>
              )}

              {/* User Profile Pill */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                backgroundColor: '#222',
                border: '1px solid #383838',
                borderRadius: '8px',
                padding: '6px 12px'
              }}>
                <div style={{
                  width: '26px',
                  height: '26px',
                  borderRadius: '50%',
                  backgroundColor: roleBg,
                  color: roleColor,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}>
                  <Lock size={13} />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '13px', fontWeight: 700, color: '#fff' }}>
                      {currentUser.username}
                    </span>
                    <span style={{
                      fontSize: '10px',
                      backgroundColor: roleBg,
                      color: roleColor,
                      padding: '1px 6px',
                      borderRadius: '4px',
                      fontWeight: 700,
                      textTransform: 'uppercase'
                    }}>
                      {isAuditor ? 'INDIVIDUAL AUDITOR' : userRole}
                    </span>
                  </div>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    {isAuditor
                      ? 'Independent Auditor (Individual Sign-in)'
                      : isAdmin
                      ? `Admin Scope (${currentUser.insurer_id})`
                      : `Adjuster (${currentUser.insurer_id})`}
                  </span>
                </div>

                {/* Switch Account */}
                <button
                  type="button"
                  onClick={onOpenAuthModal}
                  title="Switch Insurer / Auditor Account"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    backgroundColor: '#303030',
                    border: '1px solid #484848',
                    color: '#eee',
                    fontSize: '11px',
                    fontWeight: 600,
                    padding: '5px 9px',
                    borderRadius: '5px',
                    cursor: 'pointer',
                    marginLeft: '4px'
                  }}
                >
                  <KeyRound size={12} />
                  Switch
                </button>

                {/* Sign Out */}
                <button
                  type="button"
                  onClick={onLogout}
                  title="Sign Out"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    backgroundColor: 'transparent',
                    border: 'none',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    padding: '4px',
                    borderRadius: '4px'
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.color = '#ef4444'; }}
                  onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--text-muted)'; }}
                >
                  <LogOut size={15} />
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={onOpenAuthModal}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                backgroundColor: 'var(--accent-orange)',
                color: '#000',
                border: 'none',
                borderRadius: '6px',
                padding: '8px 16px',
                fontSize: '13px',
                fontWeight: 700,
                cursor: 'pointer'
              }}
            >
              <LogIn size={15} />
              Sign In
            </button>
          )}
        </div>

        {/* Right: Network Status Indicators */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: health?.database_mode === 'POSTGRES' ? 'var(--accent-green)' : 'var(--accent-red)' }}>
            <Database size={14} />
            <span>Postgres: {health?.database_mode === 'POSTGRES' ? '5433 (Online)' : 'Offline'}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: health?.blockchain_mode === 'ON_CHAIN_EVM' ? 'var(--accent-orange)' : 'var(--text-muted)' }}>
            <Cpu size={14} />
            <span>EVM: {health?.blockchain_mode === 'ON_CHAIN_EVM' ? '8545 (Ganache)' : 'Simulated'}</span>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '0 24px', display: 'flex', gap: '28px' }}>
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onSelectTab(tab.id)}
              style={{
                background: 'none',
                border: 'none',
                padding: '12px 2px',
                fontSize: '13.5px',
                fontWeight: isActive ? 600 : 500,
                color: isActive ? 'var(--accent-orange)' : 'var(--text-muted)',
                borderBottom: isActive ? '2px solid var(--accent-orange)' : '2px solid transparent',
                borderRadius: 0,
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
    </header>
  );
}
