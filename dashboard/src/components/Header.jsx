import React from 'react';
import { ShieldCheck, Database, Cpu, Layers } from 'lucide-react';

export default function Header({ currentInsurer, onSelectInsurer, activeTab, onSelectTab, health }) {
  const insurers = [
    { id: 'insurer1', name: 'Insurer 1 (Alliance Agri)' },
    { id: 'insurer2', name: 'Insurer 2 (Midwest Mutual)' },
    { id: 'insurer3', name: 'Insurer 3 (Great Plains Corp)' },
    { id: 'insurer4', name: 'Insurer 4 (National Crop)' },
    { id: 'insurer5', name: 'Insurer 5 (Pioneer Harvest)' },
    { id: 'insurer6', name: 'Insurer 6 (Frontier Farm)' },
  ];

  const tabs = [
    { id: 'intake', label: 'Claim Intake' },
    { id: 'claims', label: 'Claims Ledger' },
    { id: 'auditor', label: 'Auditor & Tamper' },
    { id: 'network', label: 'Models & Network' },
  ];

  return (
    <header style={{ borderBottom: '1px solid var(--border)', backgroundColor: '#181818', position: 'sticky', top: 0, zIndex: 100 }}>
      {/* Top Banner */}
      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '12px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '20px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '34px', height: '34px', borderRadius: '6px', backgroundColor: 'var(--accent-orange-subtle)', color: 'var(--accent-orange)', border: '1px solid rgba(255, 161, 22, 0.3)' }}>
            <ShieldCheck size={20} />
          </div>
          <div>
            <h1 style={{ fontSize: '16px', fontWeight: '700', letterSpacing: '-0.3px', color: '#fff' }}>Crop Insurance Fraud Consortium</h1>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Federated DP-ML & Solidity Ethereum Audit Ledger</p>
          </div>
        </div>

        {/* Center: Insurer Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 500 }}>Active Insurer:</span>
          <select
            value={currentInsurer}
            onChange={(e) => onSelectInsurer(e.target.value)}
            style={{ width: '250px', fontWeight: '600', backgroundColor: '#222', borderColor: '#404040' }}
          >
            {insurers.map((ins) => (
              <option key={ins.id} value={ins.id}>{ins.name}</option>
            ))}
          </select>
        </div>

        {/* Right: Network Status Indicators */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '12px' }}>
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
