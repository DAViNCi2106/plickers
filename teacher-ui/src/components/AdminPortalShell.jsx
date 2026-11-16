/**
 * src/components/AdminPortalShell.jsx
 * ===================================
 * Dedicated, standalone interface for the School Administration Console.
 * Accessible via /admin (or #/admin).
 * Provides distinct governance layout, role protection, and sign-out.
 */
import React from 'react';
import { Shield, LogOut, ArrowLeft, GraduationCap, Lock, AlertTriangle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { AdminDashboardView } from './AdminDashboardView';
import { AdminLoginView } from './AdminLoginView';

export function AdminPortalShell({ onNavigateToTeacher }) {
  const { isAuthenticated, user, logout } = useAuth();

  // If not authenticated, render dedicated Admin Login View
  if (!isAuthenticated) {
    return <AdminLoginView onNavigateToTeacher={onNavigateToTeacher} />;
  }

  // Access check: only SCHOOL_ADMIN or SUPER_ADMIN
  const isAdmin = user?.role === 'SCHOOL_ADMIN' || user?.role === 'SUPER_ADMIN';
  if (!isAdmin) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg-base)',
        padding: '20px',
      }}>
        <div style={{
          maxWidth: '500px',
          background: 'var(--bg-elevated)',
          border: '1px solid rgba(239, 68, 68, 0.4)',
          borderRadius: 'var(--radius-lg)',
          padding: '36px',
          textAlign: 'center',
          boxShadow: '0 20px 40px rgba(0,0,0,0.4)',
        }}>
          <div style={{
            width: '56px', height: '56px', borderRadius: '16px',
            background: 'rgba(239,68,68,0.15)', color: '#ef4444',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            marginBottom: '16px',
          }}>
            <Lock size={28} />
          </div>
          <h2 style={{ fontSize: '22px', fontWeight: 800, margin: '0 0 8px' }}>
            Administrator Access Restricted
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)', margin: '0 0 20px', lineHeight: '1.5' }}>
            You are currently signed in as <strong>{user?.username || user?.email}</strong> (Role: <span style={{ color: '#10b981' }}>{user?.role}</span>).
            This dashboard is restricted to designated School Administrators only.
          </p>
          <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
            <button
              className="btn btn-primary"
              onClick={onNavigateToTeacher}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <GraduationCap size={16} /> Open Teacher Classroom Portal
            </button>
            <button
              className="btn btn-outline"
              onClick={logout}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <LogOut size={16} /> Sign Out
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Admin Authenticated View
  return (
    <div className="admin-portal-app" style={{
      minHeight: '100vh',
      background: 'var(--bg-base)',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* ── Dedicated Admin Header ── */}
      <header style={{
        background: 'var(--bg-elevated)',
        borderBottom: '1px solid rgba(99,102,241,0.25)',
        padding: '14px 28px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '12px',
        position: 'sticky',
        top: 0,
        zIndex: 50,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '38px', height: '38px', borderRadius: '10px',
            background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 4px 10px rgba(99,102,241,0.3)',
          }}>
            <Shield size={20} color="#fff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '16px', fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '-0.3px' }}>
                Plickers Admin Console
              </span>
              <span style={{ fontSize: '10px', fontWeight: 800, padding: '1px 6px', borderRadius: '100px', background: 'rgba(99,102,241,0.2)', color: '#818cf8', border: '1px solid rgba(99,102,241,0.4)' }}>
                GOVERNANCE
              </span>
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
              School ID: {user?.school_id || 1} &middot; Dedicated Admin Interface
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Admin user info pill */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '6px 12px', borderRadius: '100px',
            background: 'var(--bg-card)', border: '1px solid var(--border-subtle)',
            fontSize: '12px',
          }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981' }} />
            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
              {user?.full_name || user?.username}
            </span>
            <span style={{ color: 'var(--text-dim)', fontSize: '11px' }}>
              ({user?.role === 'SUPER_ADMIN' ? 'Super Admin' : 'School Admin'})
            </span>
          </div>

          {/* Quick link to Teacher Portal */}
          <button
            type="button"
            className="btn btn-outline btn-sm"
            onClick={onNavigateToTeacher}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}
            title="Open Teacher Classroom Portal"
          >
            <GraduationCap size={15} color="#10b981" />
            <span>Teacher Portal</span>
          </button>

          {/* Sign Out */}
          <button
            type="button"
            className="btn btn-outline btn-sm"
            onClick={logout}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#ef4444' }}
            title="Sign Out of Admin Console"
          >
            <LogOut size={14} />
            <span>Sign Out</span>
          </button>
        </div>
      </header>

      {/* ── Main Admin Content ── */}
      <main style={{ flex: 1, padding: '24px 28px', maxWidth: '1440px', width: '100%', margin: '0 auto' }}>
        <AdminDashboardView onSwitchToTeacherPortal={onNavigateToTeacher} />
      </main>
    </div>
  );
}

