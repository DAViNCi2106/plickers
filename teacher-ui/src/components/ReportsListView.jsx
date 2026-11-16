import React, { useState, useEffect, useCallback } from 'react';
import {
  BarChart2, Search, Calendar, Users,
  ChevronRight, RefreshCw, FileText, CheckCircle2,
  ArrowLeft, TrendingUp, Target, Download,
  ChevronDown, ChevronUp, Trophy, Percent, User,
} from 'lucide-react';
import { api } from '../api/client';

// ── Palette for A/B/C/D ──────────────────────────────────────────
const ANSWER_PALETTE = {
  A: { bg: 'rgba(99,102,241,0.18)',  border: 'rgba(99,102,241,0.5)',  text: '#818cf8', solid: '#6366f1' },
  B: { bg: 'rgba(16,185,129,0.18)',  border: 'rgba(16,185,129,0.5)',  text: '#34d399', solid: '#10b981' },
  C: { bg: 'rgba(245,158,11,0.18)',  border: 'rgba(245,158,11,0.5)',  text: '#fbbf24', solid: '#f59e0b' },
  D: { bg: 'rgba(239,68,68,0.18)',   border: 'rgba(239,68,68,0.5)',   text: '#f87171', solid: '#ef4444' },
};

// ── Donut chart ──────────────────────────────────────────────────────
function DonutChart({ distribution = {}, total }) {
  const size = 140, r = 52, cx = 70, cy = 70;
  const circumference = 2 * Math.PI * r;
  let offset = 0;

  const segments = ['A', 'B', 'C', 'D'].map(key => {
    const count = distribution[key] || 0;
    const dash  = total > 0 ? (count / total) * circumference : 0;
    const seg   = { key, count, dash, offset };
    offset += dash;
    return seg;
  });

  return (
    <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} viewBox="0 0 140 140" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={22} />
        {segments.map(s => s.count > 0 && (
          <circle
            key={s.key} cx={cx} cy={cy} r={r} fill="none"
            stroke={ANSWER_PALETTE[s.key].solid}
            strokeWidth={22}
            strokeDasharray={`${s.dash} ${circumference - s.dash}`}
            strokeDashoffset={-s.offset}
          />
        ))}
      </svg>
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      }}>
        <span style={{ fontSize: 22, fontWeight: 800, color: '#e2e8f0' }}>{total}</span>
        <span style={{ fontSize: 10, color: '#64748b', marginTop: 1 }}>responses</span>
      </div>
    </div>
  );
}

// ── Horizontal bar per answer ───────────────────────────────────────
function AnswerBar({ letter, count, total }) {
  const p = ANSWER_PALETTE[letter];
  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 }}>
      <span style={{
        width: 26, height: 26, borderRadius: 6,
        background: p.bg, border: `1px solid ${p.border}`,
        color: p.text, fontWeight: 800, fontSize: 12,
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
      }}>{letter}</span>
      <div style={{ flex: 1, height: 6, background: 'rgba(255,255,255,0.07)', borderRadius: 99, overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${pct}%`, background: p.solid, borderRadius: 99 }} />
      </div>
      <span style={{ width: 28, textAlign: 'right', fontWeight: 700, color: p.text }}>{count}</span>
      <span style={{ width: 36, textAlign: 'right', color: '#475569', fontSize: 11 }}>{pct}%</span>
    </div>
  );
}

// ── Grade badge color ────────────────────────────────────────────────
function gradeBadge(pct) {
  if (pct >= 80) return { bg: 'rgba(16,185,129,0.15)',  color: '#34d399', border: 'rgba(16,185,129,0.35)' };
  if (pct >= 60) return { bg: 'rgba(99,102,241,0.15)',  color: '#818cf8', border: 'rgba(99,102,241,0.35)' };
  if (pct >= 40) return { bg: 'rgba(245,158,11,0.15)',  color: '#fbbf24', border: 'rgba(245,158,11,0.35)' };
  return          { bg: 'rgba(239,68,68,0.15)',   color: '#f87171', border: 'rgba(239,68,68,0.35)' };
}

// ── Small metric card ────────────────────────────────────────────────
function MiniStat({ icon: Icon, label, value, color }) {
  return (
    <div style={{
      background: 'rgba(255,255,255,0.04)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: 12, padding: '14px 16px',
      display: 'flex', alignItems: 'center', gap: 12, flex: 1, minWidth: 120,
    }}>
      <div style={{
        width: 36, height: 36, borderRadius: 9,
        background: `${color}22`,
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
      }}>
        <Icon size={16} color={color} />
      </div>
      <div>
        <div style={{ fontSize: 20, fontWeight: 800, color: '#e2e8f0', lineHeight: 1.1 }}>{value}</div>
        <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{label}</div>
      </div>
    </div>
  );
}

// ── Status badge ─────────────────────────────────────────────────────
function StatusBadge({ status }) {
  const s = (status || 'ENDED').toUpperCase();
  const isActive = s === 'ACTIVE';
  const isEnded  = s === 'ENDED';
  const style = {
    padding: '3px 10px', borderRadius: 6, fontSize: 11, fontWeight: 700,
    display: 'inline-flex', alignItems: 'center', gap: 5,
    ...(isActive
      ? { background: 'rgba(16,185,129,0.15)', color: '#34d399', border: '1px solid rgba(16,185,129,0.3)' }
      : isEnded
      ? { background: 'rgba(99,102,241,0.15)', color: '#818cf8', border: '1px solid rgba(99,102,241,0.3)' }
      : { background: 'rgba(100,116,139,0.15)', color: '#94a3b8', border: '1px solid rgba(100,116,139,0.3)' }),
  };
  return (
    <span style={style}>
      {isActive && (
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#34d399' }} />
      )}
      {s}
    </span>
  );
}

// ── Session detail / analytics panel ────────────────────────────────
function SessionDetail({ session, qMap, classMap, onBack }) {
  const [summary, setSummary]         = useState(null);
  const [scores,  setScores]          = useState([]);
  const [loading, setLoading]         = useState(true);
  const [scoreSort, setScoreSort]     = useState('desc');
  const [scoreSearch, setScoreSearch] = useState('');

  useEffect(() => {
    let alive = true;
    setLoading(true);
    Promise.all([
      api.getSessionSummary(session.id).catch(() => null),
      api.getSessionScores(session.id).catch(() => []),
    ]).then(([sum, sc]) => {
      if (!alive) return;
      setSummary(sum);
      setScores(Array.isArray(sc) ? sc : []);
      setLoading(false);
    });
    return () => { alive = false; };
  }, [session.id]);

  const qSet   = qMap[session.question_set_id];
  const cls    = classMap[session.class_id];
  const dateStr = session.created_at
    ? new Date(session.created_at).toLocaleDateString('en-IN', {
        day: 'numeric', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      })
    : '—';

  const sortedScores = [...scores]
    .filter(s => {
      if (!scoreSearch.trim()) return true;
      const q = scoreSearch.toLowerCase();
      return (s.student_name || '').toLowerCase().includes(q) ||
             (s.student_code || '').toLowerCase().includes(q);
    })
    .sort((a, b) => scoreSort === 'desc'
      ? (b.percentage ?? b.score ?? 0) - (a.percentage ?? a.score ?? 0)
      : (a.percentage ?? a.score ?? 0) - (b.percentage ?? b.score ?? 0)
    );

  const exportCSV = () => {
    const header = 'Student,Code,Score,Total,Percentage,Correct,Wrong\n';
    const rows = sortedScores.map(s =>
      `"${s.student_name || ''}","${s.student_code || ''}",${s.score ?? 0},${s.total_questions ?? 0},${s.percentage ?? 0},${s.correct_answers ?? 0},${s.wrong_answers ?? 0}`
    ).join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = `session-${session.id}-scores.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  const dist  = summary?.answer_distribution || {};
  const total = summary?.total_responses || 0;

  return (
    <div>
      {/* Header bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        <button className="btn btn-secondary btn-sm" onClick={onBack} style={{ gap: 6 }}>
          <ArrowLeft size={14} /> Back
        </button>
        <div style={{ flex: 1 }}>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: 'var(--text-main)' }}>
            {qSet?.title || `Session #${session.id}`}
          </h3>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--text-dim)' }}>
            {cls?.name || '—'} · {dateStr}
          </p>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={exportCSV} style={{ gap: 6 }}>
          <Download size={14} /> Export CSV
        </button>
      </div>

      {loading ? (
        <div className="saas-loading-screen" style={{ minHeight: 280 }}>
          <RefreshCw size={22} color="var(--primary)" className="spin" />
          <p>Loading analytics…</p>
        </div>
      ) : (
        <>
          {/* Metric mini-cards */}
          {summary && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 20 }}>
              <MiniStat icon={Users}    label="Students"        value={summary.students_participated ?? 0}           color="#6366f1" />
              <MiniStat icon={Target}   label="Accuracy"        value={`${summary.accuracy_rate ?? 0}%`}            color="#10b981" />
              <MiniStat icon={Percent}  label="Avg score"       value={`${summary.average_score_percentage ?? 0}%`} color="#f59e0b" />
              <MiniStat icon={FileText} label="Total responses" value={summary.total_responses ?? 0}                color="#8b5cf6" />
            </div>
          )}

          {/* Distribution panel */}
          {summary && (
            <div style={{
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: 14, padding: '16px 20px',
              marginBottom: 20, display: 'flex', gap: 24,
              alignItems: 'center', flexWrap: 'wrap',
            }}>
              <DonutChart distribution={dist} total={total} />
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10, minWidth: 200 }}>
                <p style={{ margin: '0 0 4px', fontSize: 11, fontWeight: 700, color: '#94a3b8', letterSpacing: '0.06em' }}>
                  ANSWER DISTRIBUTION
                </p>
                {['A','B','C','D'].map(k =>
                  <AnswerBar key={k} letter={k} count={dist[k] || 0} total={total} />
                )}
              </div>
            </div>
          )}

          {/* Score table */}
          <div style={{
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 14, overflow: 'hidden',
          }}>
            <div style={{
              padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.07)',
              display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
            }}>
              <Trophy size={15} color="#f59e0b" />
              <span style={{ fontSize: 13, fontWeight: 700, color: '#e2e8f0', flex: 1 }}>Student Scores</span>
              <div className="roster-search-wrapper" style={{ maxWidth: 200 }}>
                <Search size={13} className="roster-search-icon" />
                <input
                  className="roster-search-input"
                  type="text"
                  placeholder="Search students…"
                  value={scoreSearch}
                  onChange={e => setScoreSearch(e.target.value)}
                  style={{ fontSize: 12, padding: '5px 8px 5px 28px' }}
                />
              </div>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setScoreSort(s => s === 'desc' ? 'asc' : 'desc')}
                style={{ gap: 4, fontSize: 11, padding: '4px 10px' }}
              >
                {scoreSort === 'desc' ? <ChevronDown size={13} /> : <ChevronUp size={13} />}
                {scoreSort === 'desc' ? 'Highest first' : 'Lowest first'}
              </button>
            </div>

            {sortedScores.length === 0 ? (
              <div className="saas-empty-page" style={{ minHeight: 140 }}>
                <User size={28} color="var(--text-dim)" />
                <p>No scores recorded for this session yet.</p>
              </div>
            ) : (
              <div className="roster-table-container">
                <table className="roster-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Student</th>
                      <th>Code</th>
                      <th style={{ textAlign: 'center' }}>Correct</th>
                      <th style={{ textAlign: 'center' }}>Total Q</th>
                      <th style={{ textAlign: 'right' }}>Score %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedScores.map((s, idx) => {
                      const pct   = Math.round(s.percentage ?? 0);
                      const badge = gradeBadge(pct);
                      return (
                        <tr key={s.student_id || idx}>
                          <td style={{ color: '#475569', fontSize: 12 }}>{idx + 1}</td>
                          <td>
                            <div style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: 13 }}>
                              {s.student_name || `Student #${s.student_id}`}
                            </div>
                          </td>
                          <td><span className="student-code-chip">{s.student_code || '—'}</span></td>
                          <td style={{ textAlign: 'center', fontWeight: 700, color: '#34d399' }}>
                            {s.correct_answers ?? '—'}
                          </td>
                          <td style={{ textAlign: 'center', color: '#64748b', fontSize: 12 }}>
                            {s.total_questions ?? '—'}
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <span style={{
                              padding: '3px 10px', borderRadius: 6,
                              fontSize: 12, fontWeight: 700,
                              background: badge.bg, color: badge.color,
                              border: `1px solid ${badge.border}`,
                            }}>{pct}%</span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────
export function ReportsListView({ onSelectSession }) {
  const [sessions, setSessions]         = useState([]);
  const [questionSets, setQuestionSets] = useState([]);
  const [classes, setClasses]           = useState([]);
  const [searchQuery, setSearchQuery]   = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [loading, setLoading]           = useState(true);
  const [selectedSession, setSelected]  = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [sessList, qSets, clsList] = await Promise.all([
        api.getQuizSessions().catch(() => []),
        api.getQuestionSets().catch(() => []),
        api.getClasses().catch(() => []),
      ]);
      setSessions(Array.isArray(sessList) ? sessList : []);
      setQuestionSets(Array.isArray(qSets) ? qSets : []);
      setClasses(Array.isArray(clsList) ? clsList : []);
    } catch (err) {
      console.error('Failed to load reports data', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const qMap = React.useMemo(() => {
    const m = {}; questionSets.forEach(q => { m[q.id] = q; }); return m;
  }, [questionSets]);

  const classMap = React.useMemo(() => {
    const m = {}; classes.forEach(c => { m[c.id] = c; }); return m;
  }, [classes]);

  const sorted = React.useMemo(() =>
    [...sessions].sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0)),
  [sessions]);

  const filtered = React.useMemo(() => {
    let list = sorted;
    if (statusFilter !== 'ALL')
      list = list.filter(s => (s.status || '').toUpperCase() === statusFilter);
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(s => {
        const title = qMap[s.question_set_id]?.title || '';
        const cls   = classMap[s.class_id]?.name || '';
        return title.toLowerCase().includes(q) || cls.toLowerCase().includes(q) || String(s.id).includes(q);
      });
    }
    return list;
  }, [sorted, statusFilter, searchQuery, qMap, classMap]);

  const completedCount = sorted.filter(s => (s.status || '').toUpperCase() === 'ENDED').length;
  const activeCount    = sorted.filter(s => (s.status || '').toUpperCase() === 'ACTIVE').length;

  if (selectedSession) {
    return (
      <div className="reports-list-container">
        <SessionDetail
          session={selectedSession}
          qMap={qMap}
          classMap={classMap}
          onBack={() => setSelected(null)}
        />
      </div>
    );
  }

  return (
    <div className="reports-list-container">
      {/* Header */}
      <div className="reports-header-row">
        <div>
          <h2 className="reports-title">Session Reports &amp; Analytics</h2>
          <p className="reports-subtitle">
            Review per-student scores, answer distributions, and participation across all your quizzes.
          </p>
        </div>
        <button className="btn btn-secondary" onClick={loadData} title="Refresh" style={{ gap: 6 }}>
          <RefreshCw size={15} className={loading ? 'spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Summary stat cards */}
      <div className="dash-stats-grid" style={{ marginBottom: 24 }}>
        <div className="dash-stat-card" style={{ '--stat-color': '#6366f1' }}>
          <div className="dash-stat-icon"><FileText size={20} /></div>
          <div>
            <div className="dash-stat-value">{sorted.length}</div>
            <div className="dash-stat-label">Total Sessions</div>
            <div className="dash-stat-sub">All time</div>
          </div>
        </div>
        <div className="dash-stat-card" style={{ '--stat-color': '#10b981' }}>
          <div className="dash-stat-icon"><CheckCircle2 size={20} /></div>
          <div>
            <div className="dash-stat-value">{completedCount}</div>
            <div className="dash-stat-label">Completed</div>
            <div className="dash-stat-sub">With full reports</div>
          </div>
        </div>
        <div className="dash-stat-card" style={{ '--stat-color': '#f59e0b' }}>
          <div className="dash-stat-icon"><Users size={20} /></div>
          <div>
            <div className="dash-stat-value">{classes.length}</div>
            <div className="dash-stat-label">Classes</div>
            <div className="dash-stat-sub">Active grade levels</div>
          </div>
        </div>
        {activeCount > 0 && (
          <div className="dash-stat-card" style={{ '--stat-color': '#34d399' }}>
            <div className="dash-stat-icon"><TrendingUp size={20} /></div>
            <div>
              <div className="dash-stat-value">{activeCount}</div>
              <div className="dash-stat-label">Live Now</div>
              <div className="dash-stat-sub">In progress</div>
            </div>
          </div>
        )}
      </div>

      {/* Toolbar */}
      <div className="roster-toolbar" style={{ marginBottom: 16, gap: 10 }}>
        <div className="roster-search-wrapper" style={{ flex: 1 }}>
          <Search size={15} className="roster-search-icon" />
          <input
            type="text"
            className="roster-search-input"
            placeholder="Search by quiz name, class, or session ID…"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {['ALL', 'ENDED', 'ACTIVE'].map(f => (
            <button
              key={f}
              className={`btn btn-sm ${statusFilter === f ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setStatusFilter(f)}
              style={{ fontSize: 11, padding: '5px 12px' }}
            >
              {f === 'ALL' ? 'All' : f === 'ENDED' ? 'Completed' : 'Live'}
            </button>
          ))}
        </div>
      </div>

      {/* Session list */}
      {loading ? (
        <div className="saas-loading-screen" style={{ minHeight: 260 }}>
          <RefreshCw size={24} color="var(--primary)" className="spin" />
          <p>Loading session reports…</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="saas-empty-page" style={{ minHeight: 240, border: '1px dashed var(--border-subtle)', borderRadius: 'var(--radius-md)' }}>
          <BarChart2 size={36} color="var(--text-dim)" />
          <p>{
            searchQuery || statusFilter !== 'ALL'
              ? 'No sessions match your filters.'
              : 'No quiz sessions yet. Start a session from the Live tab.'
          }</p>
        </div>
      ) : (
        <div className="roster-table-container">
          <table className="roster-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Quiz Topic</th>
                <th>Class</th>
                <th>Date</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Analytics</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(sess => {
                const qSet = qMap[sess.question_set_id];
                const cls  = classMap[sess.class_id];
                const dateStr = sess.created_at
                  ? new Date(sess.created_at).toLocaleDateString('en-IN', {
                      day: 'numeric', month: 'short', year: 'numeric',
                      hour: '2-digit', minute: '2-digit',
                    })
                  : '—';
                return (
                  <tr
                    key={sess.id}
                    className="report-row"
                    style={{ cursor: 'pointer' }}
                    onClick={() => setSelected(sess)}
                  >
                    <td>
                      <span className="student-code-chip" style={{ background: 'rgba(99,102,241,0.1)', color: '#818cf8' }}>
                        #{sess.id}
                      </span>
                    </td>
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: 13 }}>
                        {qSet?.title || `Question Set #${sess.question_set_id || 'Quick'}`}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>
                        {qSet?.subject || 'Class Assessment'}
                      </div>
                    </td>
                    <td style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                      {cls?.name || `Class #${sess.class_id || '—'}`}
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, color: 'var(--text-dim)' }}>
                        <Calendar size={12} />{dateStr}
                      </div>
                    </td>
                    <td><StatusBadge status={sess.status} /></td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="btn btn-sm btn-primary"
                        onClick={e => { e.stopPropagation(); setSelected(sess); }}
                        style={{ gap: 5 }}
                      >
                        <BarChart2 size={13} /> View <ChevronRight size={13} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
