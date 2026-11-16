/**
 * src/components/AdminLoginView.jsx
 * =================================
 * Dedicated login portal for School Administrators and Super Administrators.
 * Enforces role verification: non-admin accounts (e.g. teachers) are blocked with an explicit error.
 */
import React, { useState } from 'react';
import { Shield, KeyRound, AlertCircle, ArrowLeft, UserCheck, Lock } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export function AdminLoginView({ onNavigateToTeacher }) {
  const { login, logout } = useAuth();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!identifier || !password) {
      setError('Please enter your Administrator ID/Email and password.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await login(identifier, password);
      const userRole = res.user?.role;
      if (userRole !== 'SCHOOL_ADMIN' && userRole !== 'SUPER_ADMIN') {
        logout();
        setError(`Access Denied: Account "${res.user?.username || identifier}" does not have Administrator privileges. Please use the Teacher Classroom Portal.`);
      }
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify your administrator credentials.');
    } finally {
      setLoading(false);
    }
  };

  const fillDemoAdmin = () => {
    setIdentifier('schooladmin');
    setPassword('SchoolAdmin@1234');
    setError(null);
  };

  return (
    <div className="auth-wrapper" style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'radial-gradient(circle at 50% 20%, rgba(99, 102, 241, 0.15), transparent 70%), var(--bg-base)',
      padding: '20px',
    }}>
      <div className="auth-card animate-fade-in" style={{
        maxWidth: '460px',
        width: '100%',
        background: 'var(--bg-elevated)',
        border: '1px solid rgba(99, 102, 241, 0.3)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: '0 20px 40px -15px rgba(0,0,0,0.5), 0 0 30px rgba(99, 102, 241, 0.15)',
        padding: '36px',
      }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '26px' }}>
          <div style={{
            width: '60px',
            height: '60px',
            borderRadius: '16px',
            background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '16px',
            boxShadow: '0 8px 20px rgba(99,102,241,0.4)',
          }}>
            <Shield size={30} color="#fff" />
          </div>
          <div style={{ display: 'inline-block', padding: '3px 10px', borderRadius: '100px', background: 'rgba(99,102,241,0.15)', color: '#818cf8', fontSize: '11px', fontWeight: 800, letterSpacing: '0.5px', marginBottom: '8px' }}>
            RESTRICTED ACCESS
          </div>
          <h2 style={{ fontSize: '24px', fontWeight: 800, margin: '0 0 6px' }}>
            School Administration
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: 0 }}>
            Sign in with an Administrator ID to manage faculty, rosters, ArUco cards, and governance.
          </p>
        </div>

        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: 'var(--radius-md)',
            padding: '12px 16px',
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '10px',
            color: '#f87171',
            fontSize: '13px',
            lineHeight: '1.4',
          }}>
            <AlertCircle size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group" style={{ marginBottom: '16px' }}>
            <label className="form-label" htmlFor="admin-id" style={{ fontSize: '12px', fontWeight: 700 }}>
              Administrator Username or Email
            </label>
            <input
              id="admin-id"
              type="text"
              className="form-input"
              placeholder="e.g. schooladmin or admin@school.edu"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              required
              autoFocus
            />
          </div>

          <div className="form-group" style={{ marginBottom: '24px' }}>
            <label className="form-label" htmlFor="admin-password" style={{ fontSize: '12px', fontWeight: 700 }}>
              Administrator Password
            </label>
            <input
              id="admin-password"
              type="password"
              className="form-input"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button
            id="admin-login-submit-btn"
            type="submit"
            className="btn btn-primary"
            style={{
              width: '100%',
              padding: '13px',
              fontWeight: 800,
              fontSize: '14px',
              background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
              border: 'none',
              boxShadow: '0 4px 14px rgba(99,102,241,0.4)',
            }}
            disabled={loading}
          >
            {loading ? (
              <span>Verifying Credentials...</span>
            ) : (
              <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                <Lock size={16} /> Sign In to Admin Console
              </span>
            )}
          </button>
        </form>

        {/* Demo Admin Fill */}
        <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid var(--border-subtle)', textAlign: 'center' }}>
          <button
            type="button"
            className="btn btn-outline btn-sm"
            onClick={fillDemoAdmin}
            style={{ width: '100%', fontSize: '12px', color: 'var(--primary)' }}
          >
            <UserCheck size={14} />
            <span>Fill Demo Admin Credentials (schooladmin)</span>
          </button>
        </div>

        {/* Link back to Teacher Portal */}
        <div style={{ marginTop: '16px', textAlign: 'center' }}>
          <button
            type="button"
            onClick={onNavigateToTeacher}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--text-dim)',
              fontSize: '12px',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <ArrowLeft size={13} /> Return to Teacher Classroom Portal
          </button>
        </div>
      </div>
    </div>
  );
}

