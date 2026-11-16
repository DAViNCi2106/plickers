import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Sidebar } from './components/Sidebar';
import { LoginView } from './components/LoginView';
import { DashboardView } from './components/DashboardView';
import { LiveSessionView } from './components/LiveSessionView';
import { ResultsView } from './components/ResultsView';
import { ReportsListView } from './components/ReportsListView';
import { RosterView } from './components/RosterView';
import { AdminPortalShell } from './components/AdminPortalShell';
import { ErrorBoundary } from './components/ErrorBoundary';
import { RefreshCw, Bell, Search, Menu, LayoutDashboard, Users, BarChart2, Radio, Shield } from 'lucide-react';

/**
 * Checks whether the current URL represents the dedicated admin chain.
 */
function isCurrentRouteAdmin() {
  const path = (window.location.pathname || '').toLowerCase();
  const hash = (window.location.hash || '').toLowerCase();
  return path.startsWith('/admin') || hash.startsWith('#/admin') || hash.startsWith('#admin');
}

/**
 * Standard Teacher Classroom Application
 */
function TeacherApp({ onNavigateToAdmin }) {
  const { isAuthenticated, loading } = useAuth();
  const [currentView, setCurrentView] = useState('dashboard');
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [selectedResultSessionId, setSelectedResultSessionId] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  if (loading) {
    return (
      <div className="saas-loading-screen">
        <RefreshCw size={32} color="var(--primary)" className="spin" />
        <p>Loading Teacher Portal...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginView />;
  }

  const handleStartSession = (sessionId) => {
    setActiveSessionId(sessionId);
    setCurrentView('live');
  };

  const handleEndSession = (sessionId) => {
    setActiveSessionId(null);
    setSelectedResultSessionId(sessionId);
    setCurrentView('results');
  };

  const handleOpenResults = (sessionId) => {
    setSelectedResultSessionId(sessionId);
    setCurrentView('results');
  };

  const handleNavigate = (view) => {
    setCurrentView(view);
    setMobileMenuOpen(false);
  };

  return (
    <div className="saas-shell">
      <Sidebar
        currentView={currentView}
        onNavigate={handleNavigate}
        onNavigateToAdmin={onNavigateToAdmin}
        activeSession={activeSessionId}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(c => !c)}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
      />

      <div className="saas-main">
        {/* Top bar */}
        <header className="saas-topbar">
          <div className="saas-topbar-left">
            <button
              className="saas-hamburger-btn"
              onClick={() => setMobileMenuOpen(o => !o)}
              aria-label="Toggle navigation menu"
              title="Menu"
            >
              <Menu size={20} />
            </button>
            <h1 className="saas-page-title">
              {currentView === 'dashboard' && 'Classroom Dashboard'}
              {currentView === 'roster' && 'Class Roster'}
              {currentView === 'live' && 'Live Session'}
              {currentView === 'results' && 'Reports & Analytics'}
            </h1>
          </div>

          <div className="saas-topbar-right">
            {/* Quick link to separate Admin Portal */}
            <button
              id="topbar-admin-portal-link"
              type="button"
              className="btn btn-outline btn-sm"
              onClick={onNavigateToAdmin}
              style={{
                display: 'flex', alignItems: 'center', gap: '6px',
                background: 'rgba(99,102,241,0.08)',
                borderColor: 'rgba(99,102,241,0.3)',
                color: 'var(--primary)',
                fontWeight: 700, fontSize: '12px', padding: '5px 12px',
              }}
              title="Open Separate School Admin Portal (/admin)"
            >
              <Shield size={14} /> Admin Portal (/admin)
            </button>

            <div className="saas-topbar-search">
              <Search size={15} className="saas-search-icon" />
              <input
                type="text"
                placeholder="Search anything..."
                className="saas-search-input"
              />
            </div>

            <button className="saas-topbar-bell" title="Notifications">
              <Bell size={18} />
              <span className="saas-bell-badge" />
            </button>

            <div className="saas-topbar-env">
              <span className="saas-env-dot" />
              <span>Live System</span>
            </div>
          </div>
        </header>

        {/* Content area */}
        <div className="saas-content">
          {currentView === 'dashboard' && (
            <DashboardView
              onStartSession={handleStartSession}
              onOpenResults={handleOpenResults}
            />
          )}

          {currentView === 'live' && activeSessionId && (
            <LiveSessionView
              session={{ id: activeSessionId }}
              onEnd={() => handleEndSession(activeSessionId)}
              onBack={() => { setActiveSessionId(null); setCurrentView('dashboard'); }}
            />
          )}

          {currentView === 'results' && selectedResultSessionId && (
            <ResultsView
              sessionId={selectedResultSessionId}
              onBack={() => setSelectedResultSessionId(null)}
            />
          )}

          {currentView === 'results' && !selectedResultSessionId && (
            <ReportsListView
              onSelectSession={(sessionId) => setSelectedResultSessionId(sessionId)}
            />
          )}

          {currentView === 'roster' && <RosterView />}
        </div>

        {/* Mobile / Tablet Bottom Navigation Bar */}
        <nav className="mobile-bottom-nav" aria-label="Mobile Navigation">
          <button
            className={`mobile-bottom-nav-item ${currentView === 'dashboard' ? 'active' : ''}`}
            onClick={() => handleNavigate('dashboard')}
          >
            <LayoutDashboard size={20} />
            <span>Dashboard</span>
          </button>
          <button
            className={`mobile-bottom-nav-item ${currentView === 'roster' ? 'active' : ''}`}
            onClick={() => handleNavigate('roster')}
          >
            <Users size={20} />
            <span>Roster</span>
          </button>
          <button
            className={`mobile-bottom-nav-item ${currentView === 'results' ? 'active' : ''}`}
            onClick={() => handleNavigate('results')}
          >
            <BarChart2 size={20} />
            <span>Reports</span>
          </button>
          {activeSessionId && (
            <button
              className={`mobile-bottom-nav-item live-pulse ${currentView === 'live' ? 'active' : ''}`}
              onClick={() => handleNavigate('live')}
            >
              <Radio size={20} color="#10b981" />
              <span style={{ color: '#10b981' }}>Live #{activeSessionId}</span>
            </button>
          )}
        </nav>
      </div>
    </div>
  );
}

/**
 * Root Application router switching between:
 *  - Teacher Portal (/)
 *  - Separate Admin Dashboard (/admin)
 */
function MainRouter() {
  const [route, setRoute] = useState(() => (isCurrentRouteAdmin() ? 'admin' : 'teacher'));

  useEffect(() => {
    const handleUrlChange = () => {
      setRoute(isCurrentRouteAdmin() ? 'admin' : 'teacher');
    };
    window.addEventListener('popstate', handleUrlChange);
    window.addEventListener('hashchange', handleUrlChange);
    return () => {
      window.removeEventListener('popstate', handleUrlChange);
      window.removeEventListener('hashchange', handleUrlChange);
    };
  }, []);

  const navigateToAdmin = () => {
    window.history.pushState(null, '', '/admin');
    setRoute('admin');
  };

  const navigateToTeacher = () => {
    window.history.pushState(null, '', '/');
    setRoute('teacher');
  };

  if (route === 'admin') {
    return <AdminPortalShell onNavigateToTeacher={navigateToTeacher} />;
  }

  return <TeacherApp onNavigateToAdmin={navigateToAdmin} />;
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <MainRouter />
      </AuthProvider>
    </ErrorBoundary>
  );
}
