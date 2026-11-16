import React from 'react';
import { GraduationCap, LogOut, User, LayoutDashboard, Users, Radio } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export function Navbar({ onNavigate, currentView, activeSession }) {
  const { user, logout } = useAuth();

  return (
    <header className="navbar">
      <div className="navbar-top">
        <div 
          className="nav-brand" 
          onClick={() => onNavigate('dashboard')}
          id="nav-brand-logo"
        >
          <div className="brand-icon">
            <GraduationCap size={22} />
          </div>
          <div>
            <div className="brand-title">Plickers Live</div>
            <span className="brand-badge">Teacher Portal</span>
          </div>
        </div>

        <div className="nav-actions">
          {activeSession && currentView !== 'live' && (
            <button 
              id="nav-resume-session-btn"
              className="btn btn-success btn-sm"
              onClick={() => onNavigate('live')}
            >
              <Radio size={14} /> Active Quiz Running
            </button>
          )}

          {user && (
            <>
              <div className="user-profile-badge" id="user-profile-info">
                <User size={16} className="text-muted" />
                <div>
                  <strong>{user.full_name || user.email}</strong>
                  <span style={{ color: 'var(--text-dim)', marginLeft: '6px', fontSize: '12px' }}>
                    ({user.role})
                  </span>
                </div>
              </div>

              <button
                id="logout-btn"
                className="btn btn-outline btn-sm"
                onClick={logout}
                title="Log Out"
              >
                <LogOut size={16} />
                <span>Logout</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Tab nav */}
      <nav style={{ display: 'flex', gap: '4px', padding: '0 24px 0', borderTop: '1px solid var(--border-subtle)' }}>
        {[
          { id: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={15} /> },
          { id: 'roster',    label: 'Class Roster', icon: <Users size={15} /> },
        ].map(tab => (
          <button
            key={tab.id}
            id={`nav-tab-${tab.id}`}
            onClick={() => onNavigate(tab.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: '7px',
              padding: '10px 16px',
              background: 'none', border: 'none', cursor: 'pointer',
              fontSize: '13px', fontWeight: currentView === tab.id ? 700 : 500,
              color: currentView === tab.id ? 'var(--primary)' : 'var(--text-muted)',
              borderBottom: currentView === tab.id ? '2px solid var(--primary)' : '2px solid transparent',
              transition: 'all 0.15s ease',
              marginBottom: '-1px',
            }}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </nav>
    </header>
  );
}
