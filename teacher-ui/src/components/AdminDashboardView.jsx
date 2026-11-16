/**
 * src/components/AdminDashboardView.jsx
 * ======================================
 * Redesigned Admin Portal — matches the teacher portal's SaaS quality.
 * All 6 administrative modules with premium UI design.
 */
import React, { useState, useEffect, useRef } from 'react';
import {
  Users, School, Shield, CreditCard, BarChart2, BookOpen,
  Plus, Search, Download, RefreshCw, KeyRound, UserX, UserCheck,
  CheckCircle2, AlertTriangle, FileSpreadsheet, ArrowRight,
  GraduationCap, Calendar, Hash, Eye, ChevronRight,
  Layers, Printer, X, TrendingUp, Activity, Clock,
  Zap, Target, Award, Settings, AlertCircle, FileText,
  Lock, LogIn, Edit3, Trash2, ChevronDown, MoreVertical,
  HelpCircle, LayoutGrid,
} from 'lucide-react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';

// ── AnimatedCounter ───────────────────────────────────────────────────────────
function AnimatedCounter({ target, duration = 900, prefix = '', suffix = '' }) {
  const [count, setCount] = useState(0);
  const frame = useRef(null);
  const start = useRef(null);
  useEffect(() => {
    if (!target || target === 0) { setCount(0); return; }
    const numTarget = typeof target === 'number' ? target : parseFloat(target) || 0;
    start.current = performance.now();
    const tick = (now) => {
      const pct = Math.min((now - start.current) / duration, 1);
      const ease = 1 - Math.pow(1 - pct, 3);
      setCount(Math.floor(ease * numTarget));
      if (pct < 1) frame.current = requestAnimationFrame(tick);
      else setCount(numTarget);
    };
    frame.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame.current);
  }, [target, duration]);
  return <span>{prefix}{count}{suffix}</span>;
}

// ── AdminStatCard ─────────────────────────────────────────────────────────────
function AdminStatCard({ icon, label, value, sublabel, color, gradient, onClick }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-lg)',
        padding: '20px 22px',
        display: 'flex',
        alignItems: 'center',
        gap: '16px',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.2s ease',
        boxShadow: 'var(--shadow-sm)',
        position: 'relative',
        overflow: 'hidden',
      }}
      onMouseEnter={e => { if (onClick) { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = 'var(--shadow-md)'; }}}
      onMouseLeave={e => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = 'var(--shadow-sm)'; }}
    >
      <div style={{
        width: '48px', height: '48px', borderRadius: '14px',
        background: gradient || `linear-gradient(135deg, ${color}22, ${color}44)`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
        boxShadow: `0 4px 12px ${color}30`,
      }}>
        {React.cloneElement(icon, { size: 22, color })}
      </div>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: '26px', fontWeight: 800, color: 'var(--text-main)', lineHeight: 1.1, fontFamily: 'var(--font-display)' }}>
          {typeof value === 'number' ? <AnimatedCounter target={value} /> : value}
        </div>
        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)', marginTop: '2px' }}>{label}</div>
        {sublabel && <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '1px' }}>{sublabel}</div>}
      </div>
      <div style={{
        position: 'absolute', right: '-12px', bottom: '-12px',
        width: '70px', height: '70px', borderRadius: '50%',
        background: `${color}08`,
      }} />
    </div>
  );
}

// ── SectionHeader ─────────────────────────────────────────────────────────────
function SectionHeader({ icon, title, subtitle, action }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px', marginBottom: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          width: '38px', height: '38px', borderRadius: '10px',
          background: 'linear-gradient(135deg, rgba(124,58,237,0.15), rgba(124,58,237,0.08))',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          border: '1px solid rgba(124,58,237,0.2)',
        }}>
          {React.cloneElement(icon, { size: 18, color: 'var(--primary)' })}
        </div>
        <div>
          <h3 style={{ margin: 0, fontSize: '17px', fontWeight: 800, color: 'var(--text-main)' }}>{title}</h3>
          {subtitle && <p style={{ margin: '2px 0 0', fontSize: '13px', color: 'var(--text-muted)' }}>{subtitle}</p>}
        </div>
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}

// ── TeacherAvatar ─────────────────────────────────────────────────────────────
const AVATAR_COLORS = ['#6366f1','#10b981','#f59e0b','#ec4899','#3b82f6','#8b5cf6','#06b6d4','#f97316'];
function TeacherAvatar({ name, size = 36 }) {
  const initials = (name || 'T').split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase();
  const colorIdx = (name || '').split('').reduce((a, c) => a + c.charCodeAt(0), 0) % AVATAR_COLORS.length;
  const color = AVATAR_COLORS[colorIdx];
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      background: `linear-gradient(135deg, ${color}30, ${color}60)`,
      border: `2px solid ${color}50`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: size * 0.33 + 'px', fontWeight: 800, color,
      flexShrink: 0,
    }}>{initials}</div>
  );
}

// ── Badge ─────────────────────────────────────────────────────────────────────
function Badge({ label, color = '#6366f1', size = 'md' }) {
  const pad = size === 'sm' ? '1px 7px' : '3px 10px';
  const fs = size === 'sm' ? '10px' : '12px';
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center',
      padding: pad, borderRadius: '100px', fontSize: fs, fontWeight: 700,
      background: `${color}18`, color, border: `1px solid ${color}35`,
    }}>{label}</span>
  );
}

// ── ActivityIcon ──────────────────────────────────────────────────────────────
function getActionMeta(action = '') {
  const a = action.toUpperCase();
  if (a.includes('LOGIN'))   return { color: '#3b82f6', Icon: LogIn,       bg: 'rgba(59,130,246,0.1)' };
  if (a.includes('CREAT'))   return { color: '#10b981', Icon: Plus,         bg: 'rgba(16,185,129,0.1)' };
  if (a.includes('DELETE') || a.includes('DEACT')) return { color: '#ef4444', Icon: Trash2, bg: 'rgba(239,68,68,0.1)' };
  if (a.includes('RESET'))   return { color: '#f59e0b', Icon: KeyRound,     bg: 'rgba(245,158,11,0.1)' };
  if (a.includes('QUIZ') || a.includes('SESSION')) return { color: '#8b5cf6', Icon: Activity, bg: 'rgba(139,92,246,0.1)' };
  if (a.includes('UPDATE') || a.includes('EDIT'))  return { color: '#06b6d4', Icon: Edit3,  bg: 'rgba(6,182,212,0.1)' };
  return { color: '#64748b', Icon: FileText, bg: 'rgba(100,116,139,0.1)' };
}

function timeAgo(dateStr) {
  if (!dateStr) return '—';
  const diff = Date.now() - new Date(dateStr).getTime();
  const min = Math.floor(diff / 60000);
  const hr = Math.floor(min / 60);
  const day = Math.floor(hr / 24);
  if (day > 0) return `${day}d ago`;
  if (hr > 0) return `${hr}h ago`;
  if (min > 0) return `${min}m ago`;
  return 'Just now';
}

// ── SUBJECT_COLORS ────────────────────────────────────────────────────────────
const SUBJECT_COLORS = {
  'Physics':     '#6366f1', 'Biology': '#10b981', 'Chemistry': '#f59e0b',
  'Math':        '#3b82f6', 'Science': '#8b5cf6', 'History':   '#f97316',
  'Geography':   '#84cc16', 'English': '#ec4899', 'General':   '#06b6d4',
};
function subjectColor(subj = '') {
  return SUBJECT_COLORS[subj] || SUBJECT_COLORS[Object.keys(SUBJECT_COLORS).find(k => subj.includes(k)) || ''] || '#6366f1';
}

// ── DEPT_COLORS ───────────────────────────────────────────────────────────────
const DEPT_COLORS = {
  'Science & Math': '#6366f1', 'Humanities & Social': '#f59e0b',
  'Languages': '#10b981', 'Computer Science': '#3b82f6',
};

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════
export function AdminDashboardView({ onSwitchToTeacherPortal }) {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('teachers');

  // Data
  const [summary, setSummary] = useState(null);
  const [teachers, setTeachers] = useState([]);
  const [classes, setClasses] = useState([]);
  const [students, setStudents] = useState([]);
  const [cards, setCards] = useState([]);
  const [benchmarks, setBenchmarks] = useState(null);
  const [questionBank, setQuestionBank] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [academicYears, setAcademicYears] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modals & Forms
  const [showAddTeacher, setShowAddTeacher] = useState(false);
  const [newTeacher, setNewTeacher] = useState({ username:'', email:'', password:'', first_name:'', last_name:'', employee_id:'', phone:'', department:'Science & Math' });
  const [showResetPw, setShowResetPw] = useState(null);
  const [tempPassword, setTempPassword] = useState('');
  const [showAddClass, setShowAddClass] = useState(false);
  const [newClassName, setNewClassName] = useState('');
  const [newClassGrade, setNewClassGrade] = useState('');
  const [importFile, setImportFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [replaceCardState, setReplaceCardState] = useState({ oldCardId:'', newCardId:'', reason:'Lost card' });
  const [searchQuery, setSearchQuery] = useState('');
  const [actionSuccess, setActionSuccess] = useState(null);

  const notifySuccess = (msg) => {
    setActionSuccess(msg);
    setTimeout(() => setActionSuccess(null), 4000);
  };

  // ── Load Data ───────────────────────────────────────────────────────────────
  const loadAdminData = async () => {
    setLoading(true); setError(null);
    try {
      const [sumData, teachersData, classesData, studentsData, cardsData,
             benchData, bankData, logsData, yearsData] = await Promise.all([
        api.getAdminSummary().catch(() => null),
        api.getTeacherActivity().catch(() => []),
        api.getClasses().catch(() => []),
        api.getStudents().catch(() => []),
        api.getCards().catch(() => []),
        api.getAdminBenchmarks().catch(() => null),
        api.getAdminQuestionBank().catch(() => []),
        api.getAdminAuditLogs({ limit: 40 }).catch(() => []),
        api.getAcademicYears().catch(() => []),
      ]);
      setSummary(sumData);
      setTeachers(teachersData || []);
      setClasses(classesData || []);
      setStudents(studentsData || []);
      setCards(cardsData || []);
      setBenchmarks(benchData);
      setQuestionBank(bankData || []);
      setAuditLogs(logsData || []);
      setAcademicYears(yearsData || []);
    } catch (err) {
      setError(err.message || 'Failed to load administration data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAdminData(); }, []);

  // ── Handlers ────────────────────────────────────────────────────────────────
  const handleCreateTeacher = async (e) => {
    e.preventDefault();
    try {
      await api.createTeacher(newTeacher);
      notifySuccess(`Teacher ${newTeacher.first_name} ${newTeacher.last_name} onboarded!`);
      setShowAddTeacher(false);
      setNewTeacher({ username:'', email:'', password:'', first_name:'', last_name:'', employee_id:'', phone:'', department:'Science & Math' });
      loadAdminData();
    } catch (err) { alert('Failed: ' + (err.message || err)); }
  };

  const handleResetPassword = async (teacher) => {
    try {
      const res = await api.resetTeacherPassword(teacher.id);
      setTempPassword(res.temporary_password || 'TempPass@1234');
      setShowResetPw(teacher);
    } catch (err) { alert('Reset failed: ' + (err.message || err)); }
  };

  const handleToggleTeacherStatus = async (teacher) => {
    try {
      if (teacher.is_active) {
        await api.deleteTeacher(teacher.id);
        notifySuccess(`Deactivated ${teacher.name}`);
      } else {
        await api.updateTeacher(teacher.id, { phone: teacher.phone });
        notifySuccess(`Activated ${teacher.name}`);
      }
      loadAdminData();
    } catch (err) { alert('Failed: ' + (err.message || err)); }
  };

  const handleCreateClass = async (e) => {
    e.preventDefault();
    if (!newClassName.trim()) return;
    try {
      const yearId = academicYears[0]?.id || 1;
      await api.createClass({ academic_year_id: yearId, name: newClassName.trim(), grade: newClassGrade.trim() || null });
      notifySuccess(`Class "${newClassName}" created!`);
      setNewClassName(''); setNewClassGrade(''); setShowAddClass(false);
      loadAdminData();
    } catch (err) { alert('Failed: ' + (err.message || err)); }
  };

  const handleImportStudents = async (e) => {
    e.preventDefault();
    if (!importFile) return;
    setImporting(true); setImportResult(null);
    try {
      const res = await api.importStudentsCSV(importFile);
      setImportResult(res);
      notifySuccess(`Import done! ${res.created_students || 0} students added.`);
      loadAdminData();
    } catch (err) { alert('Import failed: ' + (err.message || err)); }
    finally { setImporting(false); }
  };

  const handleReplaceCard = async (e) => {
    e.preventDefault();
    if (!replaceCardState.oldCardId || !replaceCardState.newCardId) {
      alert('Select both cards.'); return;
    }
    try {
      await api.replaceCard(Number(replaceCardState.oldCardId), Number(replaceCardState.newCardId), replaceCardState.reason);
      notifySuccess(`Card #${replaceCardState.oldCardId} replaced with #${replaceCardState.newCardId}!`);
      setReplaceCardState({ oldCardId:'', newCardId:'', reason:'Lost card' });
      loadAdminData();
    } catch (err) { alert('Replacement failed: ' + (err.message || err)); }
  };

  const handleExportCSV = () => {
    if (!students?.length) return;
    const headers = ['Student ID','Roll','Full Name','Class','Card','Status'];
    const rows = students.map(s => [s.student_code, s.roll_number || '', `"${s.first_name} ${s.last_name}"`, s.class_id || '', s.active_card?.card_id || '', s.status]);
    const csv = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const a = document.createElement('a');
    a.href = encodeURI(csv);
    a.download = `Plickers_Roster_${new Date().toISOString().slice(0,10)}.csv`;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
  };

  // ── Tab Config ──────────────────────────────────────────────────────────────
  const tabs = [
    { id: 'teachers', icon: <Users size={15} />, label: 'Teachers', count: teachers.length },
    { id: 'academic', icon: <School size={15} />, label: 'Academic', count: students.length },
    { id: 'cards',    icon: <CreditCard size={15} />, label: 'ArUco Cards', count: cards.length },
    { id: 'insights', icon: <BarChart2 size={15} />, label: 'Insights' },
    { id: 'bank',     icon: <BookOpen size={15} />, label: 'Question Bank', count: questionBank.length },
    { id: 'audit',    icon: <Shield size={15} />, label: 'Audit Logs', count: auditLogs.length },
  ];

  // ── Loading / Error ──────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '400px', gap: '16px' }}>
        <div style={{
          width: '48px', height: '48px', borderRadius: '50%',
          border: '3px solid var(--border-subtle)', borderTopColor: 'var(--primary)',
          animation: 'spin 0.8s linear infinite',
        }} />
        <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Loading administration data…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '300px', gap: '14px' }}>
        <AlertCircle size={36} color="var(--danger)" />
        <p style={{ color: 'var(--danger)', fontWeight: 600 }}>{error}</p>
        <button className="btn btn-outline" onClick={loadAdminData}><RefreshCw size={14} /> Retry</button>
      </div>
    );
  }

  // ══════════════════════════════════════════════════════════════════════════════
  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

      {/* ── HERO BANNER ───────────────────────────────────────────────────────── */}
      <div style={{
        background: 'linear-gradient(135deg, #6366f115 0%, #8b5cf610 50%, #06b6d408 100%)',
        border: '1px solid rgba(99,102,241,0.2)',
        borderRadius: 'var(--radius-lg)',
        padding: '24px 28px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexWrap: 'wrap', gap: '16px',
        position: 'relative', overflow: 'hidden',
      }}>
        <div style={{ position: 'absolute', right: '-30px', top: '-30px', width: '160px', height: '160px', borderRadius: '50%', background: 'rgba(99,102,241,0.05)' }} />
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{
            width: '52px', height: '52px', borderRadius: '14px',
            background: 'linear-gradient(135deg, #6366f1, #4f46e5)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 6px 20px rgba(99,102,241,0.4)',
          }}>
            <Shield size={26} color="#fff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
              <h2 style={{ fontSize: '20px', fontWeight: 800, margin: 0, color: 'var(--text-main)' }}>
                School Administration Portal
              </h2>
              <span style={{ fontSize: '10px', fontWeight: 700, padding: '2px 8px', borderRadius: '100px', background: '#10b98120', color: '#10b981', border: '1px solid #10b98140', letterSpacing: '0.5px' }}>
                ADMIN ACCESS
              </span>
            </div>
            <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-muted)' }}>
              Welcome back, <strong style={{ color: 'var(--text-main)' }}>{user?.full_name || user?.username}</strong> · Manage teachers, cards, rosters, analytics and security.
            </p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button className="btn btn-outline btn-sm" onClick={loadAdminData} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <RefreshCw size={14} /> Refresh
          </button>
          <button
            onClick={onSwitchToTeacherPortal}
            style={{
              display: 'flex', alignItems: 'center', gap: '8px',
              padding: '8px 16px', borderRadius: 'var(--radius-sm)',
              background: 'linear-gradient(135deg, #10b981, #059669)',
              border: 'none', color: '#fff', fontWeight: 700, fontSize: '13px',
              cursor: 'pointer', boxShadow: '0 4px 14px rgba(16,185,129,0.35)',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-1px)'}
            onMouseLeave={e => e.currentTarget.style.transform = ''}
          >
            <GraduationCap size={16} /> Teacher Portal
          </button>
        </div>
      </div>

      {/* ── SUCCESS TOAST ─────────────────────────────────────────────────────── */}
      {actionSuccess && (
        <div className="animate-fade-in" style={{
          background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.35)',
          borderRadius: 'var(--radius-md)', padding: '12px 18px',
          display: 'flex', alignItems: 'center', gap: '10px',
        }}>
          <CheckCircle2 size={18} color="#10b981" />
          <span style={{ fontSize: '14px', fontWeight: 600, color: '#059669' }}>{actionSuccess}</span>
        </div>
      )}

      {/* ── METRICS STRIP ─────────────────────────────────────────────────────── */}
      {summary && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '14px' }}>
          <AdminStatCard icon={<Users />} label="Total Teachers" value={summary.total_teachers} sublabel="Active Faculty" color="#6366f1" onClick={() => setActiveTab('teachers')} />
          <AdminStatCard icon={<GraduationCap />} label="Enrolled Students" value={summary.total_students} sublabel="Across all classes" color="#10b981" onClick={() => setActiveTab('academic')} />
          <AdminStatCard icon={<CreditCard />} label="Cards Assigned" value={summary.assigned_cards} sublabel={`${summary.available_cards || 0} available`} color="#f59e0b" onClick={() => setActiveTab('cards')} />
          <AdminStatCard icon={<BookOpen />} label="Quizzes Run" value={summary.total_quizzes} sublabel={`${summary.quizzes_this_week || 0} this week`} color="#ec4899" />
          <AdminStatCard icon={<BarChart2 />} label="Total Responses" value={summary.total_responses} sublabel="Real-time card scans" color="#3b82f6" onClick={() => setActiveTab('insights')} />
          <AdminStatCard icon={<Calendar />} label="Academic Year" value={summary.active_academic_year || '2026-27'} sublabel="Current Term" color="#8b5cf6" />
        </div>
      )}

      {/* ── NAVIGATION TABS ───────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', gap: '4px',
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        padding: '4px', overflowX: 'auto',
      }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: '7px',
              padding: '8px 16px', border: 'none', borderRadius: '10px',
              background: activeTab === tab.id ? 'var(--bg-secondary)' : 'transparent',
              color: activeTab === tab.id ? 'var(--primary)' : 'var(--text-muted)',
              fontWeight: activeTab === tab.id ? 700 : 500,
              fontSize: '13px', cursor: 'pointer',
              boxShadow: activeTab === tab.id ? 'var(--shadow-sm)' : 'none',
              transition: 'all 0.15s ease', whiteSpace: 'nowrap',
            }}
          >
            {tab.icon}
            {tab.label}
            {tab.count !== undefined && (
              <span style={{
                fontSize: '10px', fontWeight: 700, padding: '1px 6px',
                borderRadius: '100px', minWidth: '20px', textAlign: 'center',
                background: activeTab === tab.id ? 'var(--primary)' : 'var(--border-subtle)',
                color: activeTab === tab.id ? '#fff' : 'var(--text-dim)',
              }}>{tab.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* ══════════════════════════════════════════════════════════════════════════
          TAB 1: 👥 Teacher & Staff Management
         ══════════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'teachers' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <SectionHeader
            icon={<Users />}
            title="Teaching Staff Directory"
            subtitle="Onboard teachers, manage departments, monitor quiz activity, and reset credentials."
            action={
              <button className="btn btn-primary btn-sm" onClick={() => setShowAddTeacher(true)} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Plus size={15} /> Onboard Teacher
              </button>
            }
          />

          <div style={{
            background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-lg)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)',
          }}>
            {teachers.length === 0 ? (
              <div style={{ padding: '48px', textAlign: 'center', color: 'var(--text-dim)' }}>
                <Users size={40} style={{ opacity: 0.3, marginBottom: '12px' }} />
                <p style={{ fontSize: '14px', fontWeight: 600 }}>No teachers onboarded yet.</p>
                <button className="btn btn-primary btn-sm" onClick={() => setShowAddTeacher(true)} style={{ marginTop: '12px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                  <Plus size={14} /> Add First Teacher
                </button>
              </div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                    {['Teacher', 'Emp ID', 'Department', 'Classes', 'Quizzes', 'Accuracy', 'Status', ''].map(h => (
                      <th key={h} style={{ padding: '14px 16px', fontSize: '11px', fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.6px', background: 'var(--bg-elevated)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {teachers.map((t, idx) => {
                    const deptColor = DEPT_COLORS[t.department] || '#6366f1';
                    return (
                      <tr key={t.id} style={{ borderBottom: '1px solid var(--border-subtle)', transition: 'background 0.15s' }}
                        onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-elevated)'}
                        onMouseLeave={e => e.currentTarget.style.background = ''}>
                        <td style={{ padding: '14px 16px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <TeacherAvatar name={t.name} />
                            <div>
                              <div style={{ fontWeight: 700, color: 'var(--text-main)' }}>{t.name}</div>
                              <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>{t.email}</div>
                            </div>
                          </div>
                        </td>
                        <td style={{ padding: '14px 16px' }}>
                          <code style={{ fontSize: '11px', background: 'var(--bg-elevated)', padding: '2px 6px', borderRadius: '4px', color: 'var(--text-muted)', border: '1px solid var(--border-subtle)' }}>
                            {t.employee_id || '—'}
                          </code>
                        </td>
                        <td style={{ padding: '14px 16px' }}>
                          <Badge label={t.department || 'General'} color={deptColor} size="sm" />
                        </td>
                        <td style={{ padding: '14px 16px', fontSize: '12px', color: 'var(--text-muted)' }}>
                          {t.assigned_classes?.join(', ') || 'All Classes'}
                        </td>
                        <td style={{ padding: '14px 16px' }}>
                          <div style={{ fontWeight: 800, fontSize: '15px', color: 'var(--text-main)' }}>{t.quizzes_conducted}</div>
                          <div style={{ fontSize: '10px', color: 'var(--text-dim)' }}>sessions</div>
                        </td>
                        <td style={{ padding: '14px 16px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <div style={{ flex: 1, height: '6px', borderRadius: '3px', background: 'var(--border-subtle)', overflow: 'hidden', maxWidth: '60px' }}>
                              <div style={{ height: '100%', borderRadius: '3px', width: `${Math.min(t.avg_accuracy_pct || 0, 100)}%`, background: (t.avg_accuracy_pct || 0) >= 70 ? '#10b981' : '#f59e0b', transition: 'width 0.8s ease' }} />
                            </div>
                            <span style={{ fontWeight: 700, fontSize: '13px', color: (t.avg_accuracy_pct || 0) >= 70 ? '#10b981' : '#f59e0b' }}>{t.avg_accuracy_pct || 0}%</span>
                          </div>
                        </td>
                        <td style={{ padding: '14px 16px' }}>
                          <Badge label={t.is_active ? 'Active' : 'Deactivated'} color={t.is_active ? '#10b981' : '#ef4444'} size="sm" />
                        </td>
                        <td style={{ padding: '14px 16px' }}>
                          <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end' }}>
                            <button className="btn btn-outline btn-sm" onClick={() => handleResetPassword(t)} title="Reset Password" style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', padding: '5px 10px' }}>
                              <KeyRound size={12} /> Reset
                            </button>
                            <button
                              className="btn btn-outline btn-sm"
                              onClick={() => handleToggleTeacherStatus(t)}
                              title={t.is_active ? 'Deactivate' : 'Activate'}
                              style={{ padding: '5px 8px', color: t.is_active ? '#ef4444' : '#10b981', borderColor: t.is_active ? 'rgba(239,68,68,0.3)' : 'rgba(16,185,129,0.3)' }}
                            >
                              {t.is_active ? <UserX size={13} /> : <UserCheck size={13} />}
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════════
          TAB 2: 🗂️ Academic Structure & Student Roster
         ══════════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'academic' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <SectionHeader
            icon={<School />}
            title="Academic Structure & Student Roster"
            subtitle="Manage classes, sections, and bulk-import student rosters from Excel or CSV."
          />

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
            {/* Classes Manager */}
            <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)', padding: '22px', boxShadow: 'var(--shadow-sm)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Layers size={16} color="var(--primary)" />
                  <h4 style={{ margin: 0, fontSize: '14px', fontWeight: 700 }}>Classes & Sections</h4>
                  <span style={{ fontSize: '11px', background: 'var(--bg-elevated)', padding: '1px 7px', borderRadius: '100px', color: 'var(--text-dim)', fontWeight: 600, border: '1px solid var(--border-subtle)' }}>{classes.length}</span>
                </div>
                <button className="btn btn-outline btn-sm" onClick={() => setShowAddClass(true)} style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '12px' }}>
                  <Plus size={13} /> Add Class
                </button>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '300px', overflowY: 'auto' }}>
                {classes.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-dim)', fontSize: '13px' }}>No classes yet.</div>
                ) : classes.map(c => (
                  <div key={c.id} style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '12px 14px', background: 'var(--bg-elevated)',
                    borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)',
                    transition: 'border-color 0.15s',
                  }}
                    onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(124,58,237,0.3)'}
                    onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border-subtle)'}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div style={{
                        width: '32px', height: '32px', borderRadius: '8px',
                        background: 'linear-gradient(135deg, rgba(124,58,237,0.15), rgba(124,58,237,0.08))',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: '11px', fontWeight: 800, color: 'var(--primary)',
                      }}>
                        {c.grade || c.name?.charAt(0)}
                      </div>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: '14px', color: 'var(--text-main)' }}>{c.name}</div>
                        <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Grade {c.grade || '—'}</div>
                      </div>
                    </div>
                    <Badge label="A, B" color="#8b5cf6" size="sm" />
                  </div>
                ))}
              </div>
            </div>

            {/* Bulk CSV Import */}
            <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)', padding: '22px', boxShadow: 'var(--shadow-sm)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '14px' }}>
                <FileSpreadsheet size={16} color="#10b981" />
                <h4 style={{ margin: 0, fontSize: '14px', fontWeight: 700 }}>Bulk Student Import</h4>
              </div>
              <div style={{
                border: '2px dashed var(--border-subtle)', borderRadius: 'var(--radius-md)',
                padding: '20px', textAlign: 'center', marginBottom: '14px',
                background: 'var(--bg-elevated)',
              }}>
                <FileSpreadsheet size={28} color="var(--text-dim)" style={{ marginBottom: '8px' }} />
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '0 0 10px' }}>
                  Upload <strong>.xlsx</strong> or <strong>.csv</strong> roster<br />
                  <span style={{ color: 'var(--text-dim)' }}>Columns: S.No, Student Name, Student ID, Card ID</span>
                </p>
                <form onSubmit={handleImportStudents}>
                  <input type="file" accept=".csv,.xlsx,.xls" onChange={e => setImportFile(e.target.files[0])}
                    style={{ fontSize: '12px', marginBottom: '10px', display: 'block', width: '100%' }} />
                  <button type="submit" className="btn btn-primary btn-sm" disabled={!importFile || importing}
                    style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', width: '100%' }}>
                    {importing ? <RefreshCw size={13} className="spin" /> : <FileSpreadsheet size={13} />}
                    {importing ? 'Importing…' : 'Upload & Auto-Assign'}
                  </button>
                </form>
              </div>
              {importResult && (
                <div style={{ padding: '10px 14px', background: 'rgba(16,185,129,0.1)', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(16,185,129,0.25)', fontSize: '12px', color: '#059669', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <CheckCircle2 size={14} /> {importResult.created_students} students created · {importResult.assigned_cards || 0} cards linked
                </div>
              )}
            </div>
          </div>

          {/* Student Roster Table */}
          <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ padding: '18px 20px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>Enrolled Students</h4>
                <span style={{ fontSize: '12px', background: 'rgba(16,185,129,0.1)', color: '#10b981', padding: '2px 10px', borderRadius: '100px', fontWeight: 700, border: '1px solid rgba(16,185,129,0.3)' }}>{students.length} total</span>
              </div>
              <button className="btn btn-outline btn-sm" onClick={handleExportCSV} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Download size={13} /> Export CSV
              </button>
            </div>
            <div style={{ maxHeight: '380px', overflowY: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead style={{ position: 'sticky', top: 0, zIndex: 1 }}>
                  <tr style={{ background: 'var(--bg-elevated)', borderBottom: '1px solid var(--border-subtle)' }}>
                    {['Code', 'Roll', 'Full Name', 'Assigned Card', 'Status'].map(h => (
                      <th key={h} style={{ padding: '11px 16px', fontSize: '11px', fontWeight: 700, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.6px', textAlign: 'left' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {students.length === 0 ? (
                    <tr><td colSpan={5} style={{ padding: '32px', textAlign: 'center', color: 'var(--text-dim)', fontSize: '13px' }}>No students in roster. Import a CSV to get started.</td></tr>
                  ) : students.map(s => (
                    <tr key={s.id} style={{ borderBottom: '1px solid var(--border-subtle)', transition: 'background 0.12s' }}
                      onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-elevated)'}
                      onMouseLeave={e => e.currentTarget.style.background = ''}>
                      <td style={{ padding: '12px 16px' }}>
                        <code style={{ fontSize: '11px', fontWeight: 700, color: 'var(--primary)', background: 'rgba(124,58,237,0.08)', padding: '2px 7px', borderRadius: '4px' }}>{s.student_code}</code>
                      </td>
                      <td style={{ padding: '12px 16px', color: 'var(--text-muted)' }}>{s.roll_number || '—'}</td>
                      <td style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--text-main)' }}>{s.first_name} {s.last_name}</td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ padding: '2px 9px', borderRadius: '100px', background: 'rgba(16,185,129,0.1)', color: '#10b981', fontWeight: 700, fontSize: '12px', border: '1px solid rgba(16,185,129,0.3)' }}>
                          Card #{s.roll_number || s.id}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span style={{ color: '#10b981', fontWeight: 700, fontSize: '11px' }}>● Active</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════════
          TAB 3: 🏷️ ArUco Card Inventory
         ══════════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'cards' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <SectionHeader
            icon={<CreditCard />}
            title="ArUco Card Inventory"
            subtitle="Visual card assignment matrix, lost/damaged replacements, and print sheets."
            action={
              <a href="http://127.0.0.1:8000/api/v1/schools/1/cards/pdf" target="_blank" rel="noreferrer"
                style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '7px 14px', borderRadius: 'var(--radius-sm)', background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)', color: 'var(--text-muted)', fontSize: '13px', fontWeight: 600, textDecoration: 'none', transition: 'all 0.15s' }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(124,58,237,0.4)'; e.currentTarget.style.color = 'var(--primary)'; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-subtle)'; e.currentTarget.style.color = 'var(--text-muted)'; }}>
                <Printer size={14} /> Print PDF Sheet
              </a>
            }
          />

          {/* Stats Row */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '12px' }}>
            {[
              { label: 'Assigned', value: students.length, color: '#10b981', desc: 'Cards linked to students' },
              { label: 'Spare / Guest', value: 5, color: '#f59e0b', desc: 'Reserved for temp use' },
              { label: 'Available', value: Math.max(0, 50 - students.length - 5), color: '#6366f1', desc: 'Free to assign' },
            ].map(s => (
              <div key={s.label} style={{ background: 'var(--bg-secondary)', border: `1px solid ${s.color}25`, borderRadius: 'var(--radius-md)', padding: '16px 18px', display: 'flex', alignItems: 'center', gap: '12px', boxShadow: 'var(--shadow-sm)' }}>
                <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: s.color, flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: '20px', fontWeight: 800, color: s.color }}>{s.value}</div>
                  <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)' }}>{s.label}</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>{s.desc}</div>
                </div>
              </div>
            ))}
          </div>

          {/* Card Grid */}
          <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)', padding: '22px', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px', flexWrap: 'wrap', gap: '10px' }}>
              <span style={{ fontWeight: 700, fontSize: '14px', color: 'var(--text-main)' }}>Card Assignment Matrix — 50 Cards</span>
              <div style={{ display: 'flex', gap: '16px', fontSize: '11px', fontWeight: 600 }}>
                {[['#10b981','Assigned'],['#f59e0b','Spare'],['#94a3b8','Available']].map(([c, l]) => (
                  <span key={l} style={{ display: 'flex', alignItems: 'center', gap: '5px', color: 'var(--text-muted)' }}>
                    <span style={{ width: '10px', height: '10px', borderRadius: '2px', background: c, display: 'inline-block' }} />{l}
                  </span>
                ))}
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(68px, 1fr))', gap: '8px' }}>
              {Array.from({ length: 50 }, (_, i) => i + 1).map(num => {
                const isSpare = num > 45;
                const student = students[num - 1];
                const isAssigned = !isSpare && Boolean(student);
                const bgColor = isAssigned ? '#10b981' : isSpare ? '#f59e0b' : '#94a3b8';
                return (
                  <div key={num}
                    title={isAssigned ? `Card #${num} → ${student?.first_name} ${student?.last_name}` : isSpare ? `Card #${num} — Spare/Guest` : `Card #${num} — Available`}
                    style={{
                      height: '70px', borderRadius: '10px',
                      background: isAssigned ? 'rgba(16,185,129,0.1)' : isSpare ? 'rgba(245,158,11,0.1)' : 'var(--bg-elevated)',
                      border: `2px solid ${isAssigned ? '#10b98140' : isSpare ? '#f59e0b40' : 'var(--border-subtle)'}`,
                      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                      gap: '2px', padding: '6px', cursor: 'default',
                      transition: 'all 0.15s ease',
                    }}
                    onMouseEnter={e => { e.currentTarget.style.transform = 'scale(1.06)'; e.currentTarget.style.borderColor = bgColor; e.currentTarget.style.boxShadow = `0 4px 12px ${bgColor}30`; }}
                    onMouseLeave={e => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = ''; e.currentTarget.style.borderColor = isAssigned ? '#10b98140' : isSpare ? '#f59e0b40' : 'var(--border-subtle)'; }}
                  >
                    <span style={{ fontSize: '15px', fontWeight: 800, color: bgColor }}>#{num}</span>
                    <span style={{ fontSize: '8px', fontWeight: 700, color: 'var(--text-dim)', textAlign: 'center', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', width: '100%', paddingInline: '2px' }}>
                      {isAssigned ? student?.first_name : isSpare ? 'SPARE' : 'FREE'}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Card Replacement Tool */}
          <div style={{ background: 'var(--bg-secondary)', border: '1px solid rgba(245,158,11,0.25)', borderRadius: 'var(--radius-lg)', padding: '22px', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: 'rgba(245,158,11,0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid rgba(245,158,11,0.25)' }}>
                <AlertTriangle size={18} color="#f59e0b" />
              </div>
              <div>
                <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>Lost / Damaged Card Replacement</h4>
                <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-muted)' }}>Reassign an unused card to a student in two clicks.</p>
              </div>
            </div>
            <form onSubmit={handleReplaceCard} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px', marginTop: '16px', alignItems: 'end' }}>
              <div>
                <label className="form-label" style={{ fontSize: '11px', marginBottom: '5px', display: 'block' }}>Lost / Damaged Card #</label>
                <input type="number" min="1" max="50" className="form-input" placeholder="e.g. 14"
                  value={replaceCardState.oldCardId} onChange={e => setReplaceCardState({ ...replaceCardState, oldCardId: e.target.value })} required />
              </div>
              <div>
                <label className="form-label" style={{ fontSize: '11px', marginBottom: '5px', display: 'block' }}>New Replacement Card #</label>
                <input type="number" min="1" max="50" className="form-input" placeholder="e.g. 48"
                  value={replaceCardState.newCardId} onChange={e => setReplaceCardState({ ...replaceCardState, newCardId: e.target.value })} required />
              </div>
              <div>
                <label className="form-label" style={{ fontSize: '11px', marginBottom: '5px', display: 'block' }}>Reason</label>
                <input className="form-input" placeholder="e.g. Lost in classroom"
                  value={replaceCardState.reason} onChange={e => setReplaceCardState({ ...replaceCardState, reason: e.target.value })} />
              </div>
              <div>
                <button type="submit" style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                  width: '100%', padding: '9px 18px', borderRadius: 'var(--radius-sm)',
                  background: 'linear-gradient(135deg, #f59e0b, #d97706)', border: 'none',
                  color: '#fff', fontWeight: 700, fontSize: '13px', cursor: 'pointer',
                  boxShadow: '0 3px 10px rgba(245,158,11,0.3)',
                }}>
                  <ArrowRight size={15} /> Reassign Card
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════════
          TAB 4: 📊 School-Wide Insights
         ══════════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'insights' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <SectionHeader
            icon={<BarChart2 />}
            title="School-Wide Academic Insights"
            subtitle="Cross-class benchmarking, topic difficulty heatmaps, and participation analytics."
            action={
              <button className="btn btn-outline btn-sm" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Download size={13} /> Export Report
              </button>
            }
          />

          {/* Benchmark Cards Grid */}
          {benchmarks?.classes?.length > 0 ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '14px' }}>
              {benchmarks.classes.map((cls, i) => {
                const score = cls.average_score_pct || 0;
                const scoreColor = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';
                const gradients = ['linear-gradient(135deg, rgba(99,102,241,0.08), rgba(99,102,241,0.02))', 'linear-gradient(135deg, rgba(16,185,129,0.08), rgba(16,185,129,0.02))', 'linear-gradient(135deg, rgba(245,158,11,0.08), rgba(245,158,11,0.02))'];
                return (
                  <div key={cls.class_id} style={{
                    background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-lg)', padding: '20px', boxShadow: 'var(--shadow-sm)',
                    position: 'relative', overflow: 'hidden',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                      <div>
                        <div style={{ fontWeight: 800, fontSize: '17px', color: 'var(--text-main)' }}>{cls.class_name}</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '2px' }}>{cls.student_count} students · {cls.quiz_sessions_count} sessions</div>
                      </div>
                      <Badge label={`Grade ${cls.grade || '—'}`} color="#8b5cf6" size="sm" />
                    </div>

                    {/* Score bar */}
                    <div style={{ marginBottom: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 600 }}>Avg Accuracy</span>
                        <span style={{ fontSize: '18px', fontWeight: 800, color: scoreColor }}>{score}%</span>
                      </div>
                      <div style={{ height: '8px', borderRadius: '4px', background: 'var(--border-subtle)', overflow: 'hidden' }}>
                        <div style={{ height: '100%', borderRadius: '4px', width: `${score}%`, background: `linear-gradient(90deg, ${scoreColor}, ${scoreColor}99)`, transition: 'width 1s ease' }} />
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '12px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
                      {[['Total Scans', cls.total_responses || 0], ['Sessions', cls.quiz_sessions_count], ['Students', cls.student_count]].map(([l, v]) => (
                        <div key={l} style={{ flex: 1, textAlign: 'center' }}>
                          <div style={{ fontSize: '15px', fontWeight: 800, color: 'var(--text-main)' }}>{v}</div>
                          <div style={{ fontSize: '10px', color: 'var(--text-dim)', fontWeight: 600 }}>{l}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)', padding: '40px', textAlign: 'center', color: 'var(--text-dim)' }}>
              <BarChart2 size={36} style={{ opacity: 0.3, marginBottom: '10px' }} />
              <p style={{ fontSize: '14px', fontWeight: 600 }}>No benchmarking data yet. Run quizzes across multiple classes to see comparisons.</p>
            </div>
          )}

          {/* Difficulty Heatmap */}
          <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ padding: '18px 22px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: '10px', background: 'rgba(239,68,68,0.04)' }}>
              <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: 'rgba(239,68,68,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid rgba(239,68,68,0.2)' }}>
                <Target size={18} color="#ef4444" />
              </div>
              <div>
                <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>Topic Difficulty Heatmap</h4>
                <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-muted)' }}>Questions where &gt;50% of students answered incorrectly</p>
              </div>
            </div>
            <div style={{ padding: '16px' }}>
              {benchmarks?.difficult_questions?.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {benchmarks.difficult_questions.map((q, i) => {
                    const wrongPct = q.wrong_percentage || 0;
                    const heatColor = wrongPct >= 80 ? '#ef4444' : wrongPct >= 65 ? '#f97316' : '#f59e0b';
                    return (
                      <div key={q.question_id} style={{
                        display: 'flex', gap: '16px', alignItems: 'center',
                        padding: '14px 16px', background: 'var(--bg-elevated)',
                        borderRadius: 'var(--radius-sm)',
                        border: `1px solid ${heatColor}25`,
                        borderLeft: `4px solid ${heatColor}`,
                      }}>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-main)', marginBottom: '3px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{q.question_text}</div>
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            {q.quiz_title} · Subject: <strong>{q.subject || 'General'}</strong> · Correct answer: Option {q.correct_answer || '?'}
                          </div>
                        </div>
                        <div style={{ textAlign: 'right', flexShrink: 0 }}>
                          <div style={{ fontSize: '20px', fontWeight: 800, color: heatColor }}>{wrongPct}%</div>
                          <div style={{ fontSize: '10px', color: 'var(--text-dim)', fontWeight: 600 }}>wrong</div>
                          <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '2px' }}>{q.incorrect_count}/{q.total_attempts} missed</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-dim)' }}>
                  <Award size={32} style={{ opacity: 0.3, marginBottom: '10px' }} />
                  <p style={{ fontSize: '13px', fontWeight: 600 }}>All topics above threshold — excellent academic performance! 🎉</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════════
          TAB 5: 📚 Central Question Bank
         ══════════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'bank' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <SectionHeader
            icon={<BookOpen />}
            title="Central Question & Assessment Bank"
            subtitle="School-wide curriculum repository shared across all subject teachers."
          />

          {questionBank.length === 0 ? (
            <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)', padding: '56px', textAlign: 'center' }}>
              <BookOpen size={40} color="var(--text-dim)" style={{ opacity: 0.4, marginBottom: '12px' }} />
              <h4 style={{ color: 'var(--text-muted)', marginBottom: '8px' }}>No shared assessments yet</h4>
              <p style={{ fontSize: '13px', color: 'var(--text-dim)', maxWidth: '340px', margin: '0 auto' }}>Teachers can publish their quiz sets to this shared library. Encourage subject departments to contribute!</p>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '14px' }}>
              {questionBank.map(qs => {
                const sc = subjectColor(qs.subject || '');
                return (
                  <div key={qs.id} style={{
                    background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-lg)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)',
                    display: 'flex', flexDirection: 'column',
                    transition: 'all 0.2s ease',
                  }}
                    onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = 'var(--shadow-md)'; }}
                    onMouseLeave={e => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = 'var(--shadow-sm)'; }}
                  >
                    <div style={{ height: '4px', background: `linear-gradient(90deg, ${sc}, ${sc}80)` }} />
                    <div style={{ padding: '18px 20px', flex: 1 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
                        <span style={{ padding: '3px 10px', borderRadius: '100px', background: `${sc}18`, color: sc, fontSize: '11px', fontWeight: 700, border: `1px solid ${sc}30` }}>
                          {qs.subject || 'General'}
                        </span>
                        <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 600 }}>{qs.grade}</span>
                      </div>
                      <h4 style={{ margin: '0 0 6px', fontSize: '15px', fontWeight: 700, color: 'var(--text-main)', lineHeight: 1.3 }}>{qs.title}</h4>
                      <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '0 0 14px' }}>
                        <HelpCircle size={11} style={{ verticalAlign: 'middle', marginRight: '4px' }} />{qs.question_count} questions
                        &nbsp;·&nbsp; By <strong style={{ color: 'var(--text-main)' }}>{qs.author}</strong>
                      </p>
                    </div>
                    <div style={{ padding: '12px 20px', borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-elevated)' }}>
                      <span style={{ fontSize: '11px', color: '#10b981', fontWeight: 700 }}>● {qs.status || 'Published'}</span>
                      <button
                        className="btn btn-outline btn-sm"
                        onClick={() => alert(`Deploy "${qs.title}" to your class sessions!`)}
                        style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px' }}
                      >
                        Deploy <ArrowRight size={12} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════════════
          TAB 6: 🛡️ Audit Logs & Security
         ══════════════════════════════════════════════════════════════════════════ */}
      {activeTab === 'audit' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <SectionHeader
            icon={<Shield />}
            title="Security & Audit Logs"
            subtitle="Tamper-evident audit trail tracking logins, quiz sessions, and administrative actions."
            action={
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--text-dim)', background: 'var(--bg-elevated)', padding: '6px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                <Lock size={12} /> Role-based access enforced
              </div>
            }
          />

          <div style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-lg)', overflow: 'hidden', boxShadow: 'var(--shadow-sm)' }}>
            {/* Timeline feed */}
            {auditLogs.length === 0 ? (
              <div style={{ padding: '48px', textAlign: 'center', color: 'var(--text-dim)' }}>
                <Shield size={36} style={{ opacity: 0.3, marginBottom: '10px' }} />
                <p style={{ fontSize: '14px', fontWeight: 600 }}>No audit events recorded yet.</p>
              </div>
            ) : (
              <div style={{ padding: '8px 0' }}>
                {auditLogs.map((log, i) => {
                  const { color, Icon, bg } = getActionMeta(log.action);
                  return (
                    <div key={log.id} style={{
                      display: 'flex', gap: '14px', alignItems: 'flex-start',
                      padding: '14px 20px',
                      borderBottom: i < auditLogs.length - 1 ? '1px solid var(--border-subtle)' : 'none',
                      transition: 'background 0.12s',
                    }}
                      onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-elevated)'}
                      onMouseLeave={e => e.currentTarget.style.background = ''}>
                      {/* Icon */}
                      <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: bg, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, border: `1px solid ${color}30` }}>
                        <Icon size={15} color={color} />
                      </div>
                      {/* Content */}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', marginBottom: '3px' }}>
                          <Badge label={log.action} color={color} size="sm" />
                          {log.entity_type && (
                            <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 600 }}>
                              {log.entity_type}{log.entity_id ? ` #${log.entity_id}` : ''}
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                          <strong style={{ color: 'var(--text-main)' }}>{log.user_name || 'System'}</strong>
                          {log.user_email && <span style={{ color: 'var(--text-dim)' }}> ({log.user_email})</span>}
                          {log.metadata && <span style={{ color: 'var(--text-dim)', fontFamily: 'monospace', fontSize: '11px', marginLeft: '8px' }}>{JSON.stringify(log.metadata).slice(0, 60)}</span>}
                        </div>
                      </div>
                      {/* Time */}
                      <div style={{ textAlign: 'right', flexShrink: 0 }}>
                        <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-dim)' }}>{timeAgo(log.timestamp)}</div>
                        <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '2px' }}>{new Date(log.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</div>
                        {log.ip_address && <div style={{ fontSize: '10px', color: 'var(--text-dim)', fontFamily: 'monospace', marginTop: '2px' }}>{log.ip_address}</div>}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ═══════════════════════════ MODALS ═══════════════════════════════════ */}

      {/* Modal: Onboard Teacher */}
      {showAddTeacher && (
        <div className="modal-overlay" onClick={e => e.target === e.currentTarget && setShowAddTeacher(false)}>
          <div className="modal-content animate-fade-in" style={{ maxWidth: '540px', width: '92vw' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: 'linear-gradient(135deg, rgba(99,102,241,0.15), rgba(99,102,241,0.08))', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid rgba(99,102,241,0.2)' }}>
                  <Users size={18} color="var(--primary)" />
                </div>
                <h3 style={{ margin: 0, fontSize: '17px', fontWeight: 800 }}>Onboard New Teacher</h3>
              </div>
              <button className="btn btn-outline btn-sm" onClick={() => setShowAddTeacher(false)} style={{ padding: '5px 8px' }}><X size={15} /></button>
            </div>

            <form onSubmit={handleCreateTeacher} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label className="form-label">First Name *</label>
                  <input className="form-input" required value={newTeacher.first_name} onChange={e => setNewTeacher({ ...newTeacher, first_name: e.target.value })} />
                </div>
                <div>
                  <label className="form-label">Last Name *</label>
                  <input className="form-input" required value={newTeacher.last_name} onChange={e => setNewTeacher({ ...newTeacher, last_name: e.target.value })} />
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label className="form-label">Username *</label>
                  <input className="form-input" required value={newTeacher.username} onChange={e => setNewTeacher({ ...newTeacher, username: e.target.value })} />
                </div>
                <div>
                  <label className="form-label">Employee ID</label>
                  <input className="form-input" placeholder="EMP-104" value={newTeacher.employee_id} onChange={e => setNewTeacher({ ...newTeacher, employee_id: e.target.value })} />
                </div>
              </div>
              <div>
                <label className="form-label">Email Address *</label>
                <input type="email" className="form-input" required value={newTeacher.email} onChange={e => setNewTeacher({ ...newTeacher, email: e.target.value })} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <label className="form-label">Department</label>
                  <select className="form-input" value={newTeacher.department} onChange={e => setNewTeacher({ ...newTeacher, department: e.target.value })}>
                    <option>Science &amp; Math</option>
                    <option>Humanities &amp; Social</option>
                    <option>Languages</option>
                    <option>Computer Science</option>
                  </select>
                </div>
                <div>
                  <label className="form-label">Initial Password *</label>
                  <input type="password" minLength={6} className="form-input" required value={newTeacher.password} onChange={e => setNewTeacher({ ...newTeacher, password: e.target.value })} />
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '6px', paddingTop: '16px', borderTop: '1px solid var(--border-subtle)' }}>
                <button type="button" className="btn btn-outline" onClick={() => setShowAddTeacher(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary" style={{ fontWeight: 700 }}>Save &amp; Onboard</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Password Reset */}
      {showResetPw && (
        <div className="modal-overlay" onClick={() => setShowResetPw(null)}>
          <div className="modal-content animate-fade-in" style={{ maxWidth: '400px', width: '90vw', textAlign: 'center' }}>
            <div style={{ width: '56px', height: '56px', borderRadius: '16px', background: 'linear-gradient(135deg, rgba(16,185,129,0.15), rgba(16,185,129,0.08))', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px', border: '1px solid rgba(16,185,129,0.25)' }}>
              <KeyRound size={26} color="#10b981" />
            </div>
            <h3 style={{ margin: '0 0 8px' }}>Temporary Password Ready</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: '0 0 20px' }}>
              Give this temporary password to <strong style={{ color: 'var(--text-main)' }}>{showResetPw.name}</strong>. They should change it immediately.
            </p>
            <div style={{
              background: 'var(--bg-elevated)', border: '2px dashed rgba(124,58,237,0.4)',
              borderRadius: 'var(--radius-md)', padding: '16px',
              fontSize: '20px', fontFamily: 'monospace', fontWeight: 800,
              color: 'var(--primary)', letterSpacing: '2px', marginBottom: '20px',
            }}>{tempPassword}</div>
            <button className="btn btn-primary" onClick={() => setShowResetPw(null)} style={{ width: '100%' }}>Done</button>
          </div>
        </div>
      )}

      {/* Modal: Add Class */}
      {showAddClass && (
        <div className="modal-overlay" onClick={() => setShowAddClass(false)}>
          <div className="modal-content animate-fade-in" style={{ maxWidth: '400px', width: '90vw' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '18px' }}>
              <h3 style={{ margin: 0, fontSize: '17px', fontWeight: 800 }}>Add New Class</h3>
              <button className="btn btn-outline btn-sm" onClick={() => setShowAddClass(false)} style={{ padding: '5px 8px' }}><X size={15} /></button>
            </div>
            <form onSubmit={handleCreateClass} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label className="form-label">Class Name *</label>
                <input className="form-input" placeholder="e.g. Grade 11" required value={newClassName} onChange={e => setNewClassName(e.target.value)} />
              </div>
              <div>
                <label className="form-label">Grade Level</label>
                <input className="form-input" placeholder="e.g. 11" value={newClassGrade} onChange={e => setNewClassGrade(e.target.value)} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
                <button type="button" className="btn btn-outline" onClick={() => setShowAddClass(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">Create Class</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
