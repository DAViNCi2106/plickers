import React from 'react';
import {
  LayoutDashboard, Users, BarChart2, Radio,
  GraduationCap, LogOut, ChevronLeft, ChevronRight,
  Plus, HelpCircle, Sparkles, ArrowRight, Bell, Shield,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard',   icon: LayoutDashboard },
  { id: 'roster',    label: 'Class Roster', icon: Users },
  { id: 'results',   label: 'Reports',      icon: BarChart2 },
];

const PALETTE = ['#7c3aed', '#6366f1', '#8b5cf6', '#ec4899', '#14b8a6', '#f59e0b'];

export function Sidebar({
  currentView,
  onNavigate,
  onNavigateToAdmin,
  activeSession,
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onCloseMobile,
}) {
  const { user, logout } = useAuth();
  const initials = user?.full_name
    ? user.full_name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
    : (user?.email?.[0] || 'T').toUpperCase();
  const avatarColor = PALETTE[(user?.id || 0) % PALETTE.length];
  const teacherName = user?.full_name ? user.full_name.toUpperCase() : 'TEACHER';

  const handleNavClick = (viewId) => {
    onNavigate(viewId);
    if (onCloseMobile) onCloseMobile();
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          className="sidebar-mobile-backdrop"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      <aside className={`saas-sidebar ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
        {/* Brand */}
        <div className="sidebar-brand" onClick={() => handleNavClick('dashboard')}>
          <div className="sidebar-brand-icon">
            <GraduationCap size={collapsed ? 20 : 22} />
          </div>
          {!collapsed && (
            <div className="sidebar-brand-text">
              <span className="sidebar-brand-name">Plickers</span>
              <span className="sidebar-brand-edition">TEACHER PORTAL</span>
            </div>
          )}
        </div>

        {/* Collapse toggle */}
        <button
          className="sidebar-collapse-btn"
          onClick={onToggleCollapse}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>

        {/* Mobile close button */}
        <button
          className="sidebar-mobile-close-btn"
          onClick={onCloseMobile}
          aria-label="Close navigation menu"
        >
          <ChevronLeft size={18} />
        </button>

        {/* Teacher Profile Card */}
        <div className="sidebar-teacher-card" title={user?.full_name || 'Teacher'}>
          <div className="sidebar-avatar" style={{ background: avatarColor }}>
            {initials}
          </div>
          {!collapsed && (
            <div className="sidebar-teacher-meta">
              <div className="sidebar-teacher-name">{teacherName}</div>
              <div className="sidebar-teacher-role">
                {user?.role === 'SCHOOL_ADMIN' ? 'School Administrator' : user?.role === 'SUPER_ADMIN' ? 'Super Administrator' : 'Teacher'}
              </div>
            </div>
          )}
          {!collapsed && (
            <ArrowRight size={14} className="sidebar-teacher-arrow" />
          )}
        </div>

        {/* Live session alert */}
        {activeSession && (
          <button
            className="sidebar-live-alert"
            onClick={() => handleNavClick('live')}
            title="Return to Active Session"
          >
            <div className="sidebar-live-dot" />
            {!collapsed && (
              <div className="sidebar-live-text">
                <span className="sidebar-live-label">Session Live</span>
                <span className="sidebar-live-id">#{activeSession}</span>
              </div>
            )}
          </button>
        )}

        {/* Nav section */}
        <nav className="sidebar-nav">
          {NAV_ITEMS.map(item => {
            const Icon = item.icon;
            const isActive = currentView === item.id;
            return (
              <button
                key={item.id}
                id={`sidebar-nav-${item.id}`}
                className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
                onClick={() => handleNavClick(item.id)}
                title={collapsed ? item.label : undefined}
              >
                <Icon size={18} className="sidebar-nav-icon" />
                {!collapsed && <span className="sidebar-nav-text">{item.label}</span>}
              </button>
            );
          })}

          {activeSession && (
            <button
              id="sidebar-nav-live"
              className={`sidebar-nav-item ${currentView === 'live' ? 'active' : ''}`}
              onClick={() => handleNavClick('live')}
              title={collapsed ? 'Live Session' : undefined}
            >
              <Radio size={18} className="sidebar-nav-icon" />
              {!collapsed && <span className="sidebar-nav-text">Live Session</span>}
            </button>
          )}
        </nav>

        {/* Quick Action Button (+ New Quiz) */}
        {!collapsed && (
          <div className="sidebar-quick-cta">
            <button
              className="sidebar-cta-btn"
              onClick={() => handleNavClick('dashboard')}
              id="sidebar-quick-quiz-btn"
            >
              <Plus size={16} />
              <span>New Quiz</span>
            </button>
          </div>
        )}

        {/* Link to Separate Admin Portal */}
        <div style={{ padding: '10px 12px 6px' }}>
          <button
            type="button"
            className="sidebar-footer-link"
            onClick={onNavigateToAdmin}
            style={{
              background: 'rgba(99,102,241,0.08)',
              border: '1px solid rgba(99,102,241,0.25)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--primary)',
              fontWeight: 700,
              fontSize: '12px',
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '9px 12px',
              cursor: 'pointer',
            }}
            title="Go to Separate School Admin Dashboard (/admin)"
          >
            <Shield size={16} color="var(--primary)" />
            {!collapsed && <span>Admin Portal →</span>}
          </button>
        </div>

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Bottom secondary links */}
        <div className="sidebar-bottom-links">
          <button
            className="sidebar-footer-link"
            onClick={() => onNavigate('dashboard')}
            title={collapsed ? 'Support' : undefined}
          >
            <HelpCircle size={16} />
            {!collapsed && <span>Support</span>}
          </button>
          <button
            className="sidebar-footer-link"
            onClick={() => onNavigate('dashboard')}
            title={collapsed ? 'Updates' : undefined}
          >
            <Sparkles size={16} />
            {!collapsed && <span>Updates</span>}
          </button>
          <button
            className="sidebar-footer-link sidebar-logout"
            onClick={logout}
            title={collapsed ? 'Sign out' : undefined}
          >
            <LogOut size={16} />
            {!collapsed && <span>Log Out</span>}
            {!collapsed && <ArrowRight size={14} style={{ marginLeft: 'auto', opacity: 0.7 }} />}
          </button>
        </div>
      </aside>
    </>
  );
}
