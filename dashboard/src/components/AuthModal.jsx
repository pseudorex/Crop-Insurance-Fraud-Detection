import React, { useState } from 'react';
import { Lock, Shield, ShieldCheck, User, Key, Building2, Mail, CheckCircle2, AlertCircle, X, ArrowRight, LogIn, UserPlus } from 'lucide-react';
import { loginInsurer, registerInsurer } from '../api';

const QUICK_ACCOUNTS = [
  { id: 'adjuster3', name: 'Insurer 3 (Great Plains Corp)', user: 'adjuster3', pass: 'AdjusterPass123!', badge: 'ADJUSTER', role: 'adjuster', sub: 'Insurer 3' },
  { id: 'admin3', name: 'Insurer 3 (Great Plains Corp)', user: 'admin3', pass: 'AdminPass123!', badge: 'ADMIN', role: 'admin', sub: 'Insurer 3' },
  { id: 'auditor1', name: 'Individual Auditor (Dr. Aris Thorne)', user: 'auditor1', pass: 'AuditorPass123!', badge: 'INDIVIDUAL AUDITOR', role: 'auditor', sub: 'Independent / Individual' },
  { id: 'admin2', name: 'Insurer 2 (Midwest Mutual)', user: 'admin2', pass: 'AdminPass123!', badge: 'ADMIN', role: 'admin', sub: 'Insurer 2' },
  { id: 'adjuster2', name: 'Insurer 2 (Midwest Mutual)', user: 'adjuster2', pass: 'AdjusterPass123!', badge: 'ADJUSTER', role: 'adjuster', sub: 'Insurer 2' },
  { id: 'adjuster1', name: 'Insurer 1 (Alliance Agri)', user: 'adjuster1', pass: 'AdjusterPass123!', badge: 'ADJUSTER', role: 'adjuster', sub: 'Insurer 1' },
  { id: 'admin1', name: 'Insurer 1 (Alliance Agri)', user: 'admin1', pass: 'AdminPass123!', badge: 'ADMIN', role: 'admin', sub: 'Insurer 1' },
];

const PRESET_INSURERS = [
  { id: 'insurer1', name: 'Insurer 1 (Alliance Agri)' },
  { id: 'insurer2', name: 'Insurer 2 (Midwest Mutual)' },
  { id: 'insurer3', name: 'Insurer 3 (Great Plains Corp)' },
  { id: 'insurer4', name: 'Insurer 4 (National Crop)' },
  { id: 'insurer5', name: 'Insurer 5 (Pioneer Harvest)' },
  { id: 'insurer6', name: 'Insurer 6 (Frontier Farm)' },
];

export default function AuthModal({ isOpen, onClose, onAuthSuccess, currentUser }) {
  const [tab, setTab] = useState('login'); // 'login' | 'register'
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Register Form State
  const [regData, setRegData] = useState({
    insurer_id: 'insurer1',
    username: '',
    email: '',
    password: '',
    role: 'admin' // 'admin' | 'adjuster'
  });

  if (!isOpen) return null;

  const handleLogin = async (e, customUser, customPass) => {
    if (e) e.preventDefault();
    const u = customUser || username;
    const p = customPass || password;

    if (!u || !p) {
      setError('Please provide both username and password.');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const data = await loginInsurer(u, p);
      setSuccessMsg(`Welcome, ${data.user.insurer_name} (${data.user.username})!`);
      setTimeout(() => {
        onAuthSuccess(data.user);
        if (onClose) onClose();
      }, 500);
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = (acc) => {
    setUsername(acc.user);
    setPassword(acc.pass);
    handleLogin(null, acc.user, acc.pass);
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!regData.username.trim() || !regData.password) {
      setError('Username and password are required.');
      return;
    }
    if (regData.password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    let finalRole = regData.role === 'adjuster' ? 'adjuster' : 'admin';
    let finalInsurerId = regData.insurer_id;
    let finalInsurerName = PRESET_INSURERS.find(i => i.id === regData.insurer_id)?.name || regData.insurer_id;

    setLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const data = await registerInsurer({
        insurer_id: finalInsurerId,
        insurer_name: finalInsurerName,
        username: regData.username.trim(),
        email: regData.email.trim() || null,
        password: regData.password,
        role: finalRole
      });
      setSuccessMsg(`Registration complete! Welcome, ${data.user.insurer_name} (${data.user.username}).`);
      setTimeout(() => {
        onAuthSuccess(data.user);
        if (onClose) onClose();
      }, 500);
    } catch (err) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(4px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px'
    }}>
      <div style={{
        backgroundColor: '#1e1e1e',
        borderRadius: '12px',
        border: '1px solid var(--border)',
        width: '100%',
        maxWidth: '620px',
        boxShadow: '0 20px 40px rgba(0,0,0,0.6)',
        overflow: 'hidden',
        position: 'relative'
      }}>
        {/* Modal Header */}
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'linear-gradient(180deg, #252525 0%, #1e1e1e 100%)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '38px',
              height: '38px',
              borderRadius: '8px',
              backgroundColor: 'var(--accent-orange-subtle)',
              color: 'var(--accent-orange)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid rgba(255, 161, 22, 0.3)'
            }}>
              <Lock size={20} />
            </div>
            <div>
              <h2 style={{ fontSize: '17px', fontWeight: '700', color: '#fff', margin: 0 }}>
                Consortium Access & Authentication
              </h2>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '2px 0 0 0' }}>
                Role-Based Access Control &bull; Multi-Tenant Database Isolation &bull; Individual Auditor Verification
              </p>
            </div>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              title="Close"
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                padding: '6px',
                borderRadius: '6px'
              }}
            >
              <X size={18} />
            </button>
          )}
        </div>

        {/* Tab Switcher */}
        <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', backgroundColor: '#181818' }}>
          <button
            type="button"
            onClick={() => { setTab('login'); setError(null); setSuccessMsg(null); }}
            style={{
              flex: 1,
              padding: '12px',
              background: tab === 'login' ? '#1e1e1e' : 'transparent',
              color: tab === 'login' ? 'var(--accent-orange)' : 'var(--text-muted)',
              border: 'none',
              borderBottom: tab === 'login' ? '2px solid var(--accent-orange)' : '2px solid transparent',
              fontWeight: 600,
              fontSize: '13px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px'
            }}
          >
            <LogIn size={15} />
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setTab('register'); setError(null); setSuccessMsg(null); }}
            style={{
              flex: 1,
              padding: '12px',
              background: tab === 'register' ? '#1e1e1e' : 'transparent',
              color: tab === 'register' ? 'var(--accent-orange)' : 'var(--text-muted)',
              border: 'none',
              borderBottom: tab === 'register' ? '2px solid var(--accent-orange)' : '2px solid transparent',
              fontWeight: 600,
              fontSize: '13px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px'
            }}
          >
            <UserPlus size={15} />
            Register New Account
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: '24px' }}>
          {error && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#ef4444',
              padding: '10px 14px',
              borderRadius: '6px',
              fontSize: '13px',
              marginBottom: '18px'
            }}>
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              backgroundColor: 'rgba(34, 197, 94, 0.1)',
              border: '1px solid rgba(34, 197, 94, 0.3)',
              color: '#22c55e',
              padding: '10px 14px',
              borderRadius: '6px',
              fontSize: '13px',
              marginBottom: '18px'
            }}>
              <CheckCircle2 size={16} style={{ flexShrink: 0 }} />
              <span>{successMsg}</span>
            </div>
          )}

          {tab === 'login' ? (
            <div>
              {/* Quick Login Bar */}
              <div style={{ marginBottom: '20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontSize: '11.5px', textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-muted)', fontWeight: 600 }}>
                    1-Click Demo Login (Pre-Seeded Roles):
                  </span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(136px, 1fr))', gap: '8px' }}>
                  {QUICK_ACCOUNTS.map((acc) => {
                    const badgeColor = acc.role === 'adjuster' ? '#60a5fa' : acc.role === 'admin' ? 'var(--accent-green)' : 'var(--accent-orange)';
                    return (
                      <button
                        key={acc.id}
                        type="button"
                        disabled={loading}
                        onClick={() => handleQuickLogin(acc)}
                        style={{
                          padding: '8px 10px',
                          backgroundColor: '#282828',
                          border: '1px solid #383838',
                          borderRadius: '6px',
                          color: '#ddd',
                          fontSize: '11px',
                          cursor: 'pointer',
                          textAlign: 'left',
                          transition: 'all 0.15s ease'
                        }}
                        onMouseEnter={(e) => { e.currentTarget.style.borderColor = badgeColor; e.currentTarget.style.color = '#fff'; }}
                        onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#383838'; e.currentTarget.style.color = '#ddd'; }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <span style={{
                            fontSize: '9.5px',
                            fontWeight: 800,
                            color: badgeColor,
                            backgroundColor: `${badgeColor}15`,
                            padding: '1px 5px',
                            borderRadius: '3px'
                          }}>
                            {acc.badge}
                          </span>
                          <span style={{ fontSize: '9px', color: 'var(--text-muted)' }}>{acc.sub}</span>
                        </div>
                        <div style={{ fontSize: '12px', fontWeight: 700, color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {acc.user}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Standard Login Form */}
              <form onSubmit={handleLogin}>
                <div style={{ marginBottom: '14px' }}>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#ccc', marginBottom: '6px' }}>
                    Username or Email
                  </label>
                  <div style={{ position: 'relative' }}>
                    <User size={15} style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-muted)' }} />
                    <input
                      type="text"
                      placeholder="e.g. adjuster3, admin3, auditor1"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '10px 12px 10px 36px',
                        backgroundColor: '#141414',
                        border: '1px solid #383838',
                        borderRadius: '6px',
                        color: '#fff',
                        fontSize: '13px'
                      }}
                      disabled={loading}
                    />
                  </div>
                </div>

                <div style={{ marginBottom: '20px' }}>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#ccc', marginBottom: '6px' }}>
                    Password
                  </label>
                  <div style={{ position: 'relative' }}>
                    <Key size={15} style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-muted)' }} />
                    <input
                      type="password"
                      placeholder="e.g. AdjusterPass123! or demo123"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '10px 12px 10px 36px',
                        backgroundColor: '#141414',
                        border: '1px solid #383838',
                        borderRadius: '6px',
                        color: '#fff',
                        fontSize: '13px'
                      }}
                      disabled={loading}
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  style={{
                    width: '100%',
                    padding: '12px',
                    backgroundColor: 'var(--accent-orange)',
                    color: '#000',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '14px',
                    fontWeight: 700,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px'
                  }}
                >
                  {loading ? 'Authenticating...' : 'Sign In & Access Dashboard'}
                  <ArrowRight size={16} />
                </button>
              </form>
            </div>
          ) : (
            /* Register New Insurer Account Form */
            <form onSubmit={handleRegister}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px', marginBottom: '14px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#ccc', marginBottom: '6px' }}>
                    Consortium Organization
                  </label>
                  <select
                    value={regData.insurer_id}
                    onChange={(e) => setRegData((prev) => ({ ...prev, insurer_id: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '10px',
                      backgroundColor: '#141414',
                      border: '1px solid #383838',
                      borderRadius: '6px',
                      color: '#fff',
                      fontSize: '13px'
                    }}
                    disabled={loading}
                  >
                    {PRESET_INSURERS.map((ins) => (
                      <option key={ins.id} value={ins.id}>{ins.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#ccc', marginBottom: '6px' }}>
                    Role & Permissions
                  </label>
                  <select
                    value={regData.role}
                    onChange={(e) => setRegData((prev) => ({ ...prev, role: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '10px',
                      backgroundColor: '#141414',
                      border: '1px solid #383838',
                      borderRadius: '6px',
                      color: '#fff',
                      fontSize: '13px'
                    }}
                    disabled={loading}
                  >
                    <option value="admin">Insurer Admin (Full Ledger & Audit for own insurer)</option>
                    <option value="adjuster">Intake Officer / Adjuster (Submit Claims)</option>
                  </select>
                </div>
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#ccc', marginBottom: '6px' }}>
                  Username
                </label>
                <div style={{ position: 'relative' }}>
                  <User size={15} style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-muted)' }} />
                  <input
                    type="text"
                    placeholder="e.g. admin_midwest, officer_john"
                    value={regData.username}
                    onChange={(e) => setRegData((prev) => ({ ...prev, username: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '10px 12px 10px 36px',
                      backgroundColor: '#141414',
                      border: '1px solid #383838',
                      borderRadius: '6px',
                      color: '#fff',
                      fontSize: '13px'
                    }}
                    disabled={loading}
                    required
                  />
                </div>
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#ccc', marginBottom: '6px' }}>
                  Email Address (Optional)
                </label>
                <div style={{ position: 'relative' }}>
                  <Mail size={15} style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-muted)' }} />
                  <input
                    type="email"
                    placeholder="officer@consortium.org"
                    value={regData.email}
                    onChange={(e) => setRegData((prev) => ({ ...prev, email: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '10px 12px 10px 36px',
                      backgroundColor: '#141414',
                      border: '1px solid #383838',
                      borderRadius: '6px',
                      color: '#fff',
                      fontSize: '13px'
                    }}
                    disabled={loading}
                  />
                </div>
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#ccc', marginBottom: '6px' }}>
                  Password (Stored Bcrypt / Argon2id Hashed)
                </label>
                <div style={{ position: 'relative' }}>
                  <Key size={15} style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-muted)' }} />
                  <input
                    type="password"
                    placeholder="Minimum 6 characters"
                    value={regData.password}
                    onChange={(e) => setRegData((prev) => ({ ...prev, password: e.target.value }))}
                    style={{
                      width: '100%',
                      padding: '10px 12px 10px 36px',
                      backgroundColor: '#141414',
                      border: '1px solid #383838',
                      borderRadius: '6px',
                      color: '#fff',
                      fontSize: '13px'
                    }}
                    disabled={loading}
                    required
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '12px',
                  backgroundColor: 'var(--accent-orange)',
                  color: '#000',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '14px',
                  fontWeight: 700,
                  cursor: loading ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '8px'
                }}
              >
                {loading ? 'Registering Account...' : 'Register Insurer Account'}
                <ArrowRight size={16} />
              </button>
            </form>
          )}

          {/* Cryptographic Protection Footer */}
          <div style={{
            marginTop: '20px',
            paddingTop: '16px',
            borderTop: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '11px',
            color: 'var(--text-muted)'
          }}>
            <Shield size={14} color="var(--accent-green)" />
            <span>Multi-Tenant PostgreSQL isolation &bull; RFC 9106 Argon2id password hashing</span>
          </div>
        </div>
      </div>
    </div>
  );
}
