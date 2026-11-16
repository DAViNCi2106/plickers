import React, { useState } from 'react';
import { LogIn, KeyRound, AlertCircle, UserCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export function LoginView() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please enter your email and password.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err) {
      setError(err.message || 'Login failed. Please verify your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const fillDemoTeacher = () => {
    setEmail('anil.kumar@demohighschool.edu');
    setPassword('Teacher@1234');
    setError(null);
  };

  return (
    <div className="auth-wrapper">
      <div className="auth-card animate-fade-in">
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <div 
            style={{
              width: '52px',
              height: '52px',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-subtle)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '16px',
            }}
          >
            <KeyRound size={24} color="var(--primary)" />
          </div>
          <h2 style={{ fontSize: '24px', marginBottom: '6px' }}>Teacher Sign In</h2>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
            Access live polling, student response capture, and question analytics
          </p>
        </div>

        {error && (
          <div 
            style={{
              background: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: 'var(--radius-md)',
              padding: '12px 16px',
              marginBottom: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              color: '#f87171',
              fontSize: '14px',
            }}
            id="login-error-msg"
          >
            <AlertCircle size={18} style={{ flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="teacher-email">
              Teacher Email Address
            </label>
            <div style={{ position: 'relative' }}>
              <input
                id="teacher-email"
                type="email"
                className="form-input"
                placeholder="teacher@school.edu"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
              />
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: '28px' }}>
            <label className="form-label" htmlFor="teacher-password">
              Password
            </label>
            <input
              id="teacher-password"
              type="password"
              className="form-input"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button
            id="login-submit-btn"
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', padding: '13px' }}
            disabled={loading}
          >
            {loading ? (
              <span>Authenticating...</span>
            ) : (
              <>
                <LogIn size={17} />
                <span>Sign In to Teacher Portal</span>
              </>
            )}
          </button>
        </form>

        <div style={{ marginTop: '24px', paddingTop: '20px', borderTop: '1px solid var(--border-subtle)', textAlign: 'center' }}>
          <button
            id="demo-teacher-btn"
            type="button"
            className="btn btn-outline btn-sm"
            onClick={fillDemoTeacher}
            style={{ width: '100%' }}
          >
            <UserCheck size={14} color="var(--primary)" />
            <span>Fill Demo Teacher Credentials</span>
          </button>
        </div>
      </div>
    </div>
  );
}
