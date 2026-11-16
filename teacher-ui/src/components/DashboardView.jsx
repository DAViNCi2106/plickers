import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Play, Plus, BookOpen, Users, CheckCircle2,
  ChevronRight, BarChart2, Radio, RefreshCw, Zap,
  ChevronDown, Search, AlertCircle,
  Activity, Layers, Clock, FileText,
  HelpCircle, Award, LayoutGrid,
} from "lucide-react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { QuizModal } from "./QuizModal";
import { QuickQuizModal } from "./QuickQuizModal";

// ── Helpers ──────────────────────────────────────────────────────────────────

function getGreeting() {
  const h = new Date().getHours();
  if (h < 5)  return "Good night";
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  if (h < 20) return "Good evening";
  return "Good night";
}

function timeAgo(dateStr) {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const min = Math.floor(diff / 60000);
  const hr  = Math.floor(min / 60);
  const day = Math.floor(hr / 24);
  if (day > 0)  return `${day}d ago`;
  if (hr > 0)   return `${hr}h ago`;
  if (min > 0)  return `${min}m ago`;
  return "Just now";
}

function getStatusMeta(status) {
  const s = (status || "").toUpperCase();
  if (s === "ACTIVE")  return { label: "Live",      color: "#10b981", bg: "rgba(16,185,129,0.15)",  border: "rgba(16,185,129,0.4)",  pulse: true  };
  if (s === "PAUSED")  return { label: "Paused",    color: "#f59e0b", bg: "rgba(245,158,11,0.15)",  border: "rgba(245,158,11,0.4)",  pulse: false };
  if (s === "ENDED")   return { label: "Completed", color: "#6366f1", bg: "rgba(99,102,241,0.15)",  border: "rgba(99,102,241,0.4)",  pulse: false };
  return                      { label: "Pending",   color: "#64748b", bg: "rgba(100,116,139,0.1)", border: "rgba(100,116,139,0.3)", pulse: false };
}

// ── LiveClock ────────────────────────────────────────────────────────────────

function LiveClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  const time = now.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const date = now.toLocaleDateString("en-IN", { weekday: "long", month: "long", day: "numeric" });
  return (
    <div className="live-clock">
      <div className="live-clock-time">{time}</div>
      <div className="live-clock-date">{date}</div>
    </div>
  );
}

// ── AnimatedCounter ──────────────────────────────────────────────────────────

function AnimatedCounter({ target, duration = 900 }) {
  const [count, setCount] = useState(0);
  const frame = useRef(null);
  const start = useRef(null);
  useEffect(() => {
    if (target === 0) { setCount(0); return; }
    start.current = performance.now();
    const tick = (now) => {
      const pct  = Math.min((now - start.current) / duration, 1);
      const ease = 1 - Math.pow(1 - pct, 3);
      setCount(Math.floor(ease * target));
      if (pct < 1) frame.current = requestAnimationFrame(tick);
      else setCount(target);
    };
    frame.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame.current);
  }, [target, duration]);
  return <span>{count}</span>;
}

// ── StatCard ─────────────────────────────────────────────────────────────────
// Each card uses a distinct color to distinguish metric type at a glance.
// No glow on stat cards (R-13: glow reserved for max 1-2 key elements only).

function StatCard({ icon, label, value, color, sublabel, onClick }) {
  return (
    <div
      className={`dash-stat-card ${onClick ? "clickable" : ""}`}
      style={{ "--stat-color": color, cursor: onClick ? "pointer" : "default" }}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      <div className="dash-stat-icon">{icon}</div>
      <div>
        <div className="dash-stat-value"><AnimatedCounter target={value} /></div>
        <div className="dash-stat-label">{label}</div>
        {sublabel && <div className="dash-stat-sub">{sublabel}</div>}
      </div>
    </div>
  );
}

// ── QuizCard ─────────────────────────────────────────────────────────────────
// Subject color = semantic signal so teachers can scan by subject instantly (R-01 reason).
// No left-stripe decoration. No glow on quiz cards.

const SUBJECT_COLORS = {
  "Physics":                { accent: "#6366f1", bg: "rgba(99,102,241,0.1)"  },
  "Biology":                { accent: "#10b981", bg: "rgba(16,185,129,0.1)"  },
  "Chemistry":              { accent: "#f59e0b", bg: "rgba(245,158,11,0.1)"  },
  "Math":                   { accent: "#3b82f6", bg: "rgba(59,130,246,0.1)"  },
  "General Science & Math": { accent: "#8b5cf6", bg: "rgba(139,92,246,0.1)" },
  "Integrated Science":     { accent: "#06b6d4", bg: "rgba(6,182,212,0.1)"  },
  "History":                { accent: "#f97316", bg: "rgba(249,115,22,0.1)"  },
  "Geography":              { accent: "#84cc16", bg: "rgba(132,204,22,0.1)"  },
  "English":                { accent: "#ec4899", bg: "rgba(236,72,153,0.1)"  },
};

function QuizCard({ qs, launching, onLaunch }) {
  const theme = SUBJECT_COLORS[qs.subject] || { accent: "#6366f1", bg: "rgba(99,102,241,0.1)" };
  const qCount = qs.question_count ?? qs.questions?.length ?? 0;
  return (
    <div className="quiz-card" style={{ "--qa": theme.accent, "--qbg": theme.bg }}>
      <div className="quiz-card-header">
        <span className="quiz-subject-tag" style={{ color: theme.accent, background: theme.bg }}>
          {qs.subject || "Quiz"}
        </span>
        {qs.grade && <span className="quiz-grade-label">{qs.grade}</span>}
      </div>
      <h3 className="quiz-card-title">{qs.title}</h3>
      <p className="quiz-card-desc">
        {qs.description || "Ready for live card scanning in class."}
      </p>
      <div className="quiz-card-meta">
        <span className="quiz-meta-item"><HelpCircle size={12} /> {qCount} {qCount === 1 ? "question" : "questions"}</span>
        <span className="quiz-meta-item"><LayoutGrid size={12} /> A / B / C / D</span>
      </div>
      <div className="quiz-card-footer">
        <span className="quiz-id-label">Set #{qs.id}</span>
        <button
          id={`launch-quiz-btn-${qs.id}`}
          className="btn-launch"
          onClick={() => onLaunch(qs.id)}
          disabled={launching}
        >
          {launching ? <RefreshCw size={14} className="spin" /> : <Play size={14} fill="currentColor" />}
          Launch
        </button>
      </div>
    </div>
  );
}


// ── SessionRow ───────────────────────────────────────────────────────────────

function SessionRow({ sess, onStartSession, onOpenResults, index }) {
  const meta = getStatusMeta(sess.status);
  const started = sess.started_at ? new Date(sess.started_at) : null;
  const ended   = sess.ended_at   ? new Date(sess.ended_at)   : null;
  const sUpper  = (sess.status || "").toUpperCase();
  const isLive  = sUpper === "ACTIVE" || sUpper === "PAUSED";
  const duration = started && ended
    ? Math.round((ended - started) / 60000) + " min"
    : started ? "In progress" : "Not started";

  return (
    <div className="session-row" style={{ animationDelay: `${index * 45}ms` }}>
      <span className="session-id-badge">#{sess.id}</span>

      <div className="session-quiz-info">
        <div className="session-quiz-title">
          {sess.question_set?.title || `Quiz Set #${sess.question_set_id}`}
        </div>
        <div className="session-quiz-sub">
          {sess.class_?.name || "-"} · {duration}
        </div>
      </div>

      <div className="session-date-col">
        {started ? (
          <>
            <div className="session-date-main">
              {started.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
            </div>
            <div className="session-date-time">
              {started.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
            </div>
          </>
        ) : <span className="session-date-main" style={{ color: "var(--text-dim)" }}>Pending</span>}
      </div>

      <span
        className="status-pill"
        style={{ color: meta.color, background: meta.bg, border: `1px solid ${meta.border}` }}
      >
        {meta.pulse && <span className="status-dot-live" style={{ background: meta.color }} />}
        {meta.label}
      </span>

      <div style={{ textAlign: "right" }}>
        {isLive ? (
          <button className="btn btn-success btn-sm" onClick={() => onStartSession(sess.id)}>
            <Radio size={13} /> Enter Live
          </button>
        ) : (
          <button
            id={`view-matrix-btn-${sess.id}`}
            className="btn btn-outline btn-sm"
            onClick={() => onOpenResults(sess.id)}
          >
            <BarChart2 size={13} /> View Report
          </button>
        )}
      </div>
    </div>
  );
}

// ── ActivityFeed ─────────────────────────────────────────────────────────────
// Only real events from real session/quiz data. No fabricated entries (R-38).
// Dots: solid color only, no glow (R-13: glow reserved for max 1-2 key elements).

function ActivityFeed({ sessions, questionSets }) {
  const items = React.useMemo(() => {
    const feed = [];
    sessions.slice(0, 6).forEach((s) => {
      const title = s.question_set?.title || `Quiz #${s.question_set_id}`;
      const time  = s.ended_at || s.started_at || s.created_at;
      const st = (s.status || "").toUpperCase();
      if (st === "ACTIVE") {
        feed.push({ color: "#10b981", label: "Started live", title, time });
      } else if (st === "ENDED") {
        feed.push({ color: "#6366f1", label: "Completed",    title, time });
      } else {
        feed.push({ color: "#64748b", label: "Pending",      title, time });
      }
    });
    questionSets.slice(0, 3).forEach((qs) => {
      feed.push({ color: "#f59e0b", label: "Created", title: qs.title, time: qs.created_at });
    });
    return feed
      .filter(f => f.time)
      .sort((a, b) => new Date(b.time) - new Date(a.time))
      .slice(0, 8);
  }, [sessions, questionSets]);

  if (items.length === 0) {
    return (
      <div className="sidebar-empty">
        <Clock size={20} color="var(--text-dim)" />
        <p>No activity yet. Launch a quiz to see history here.</p>
      </div>
    );
  }

  return (
    <div className="activity-list">
      {items.map((item, i) => (
        <div key={i} className="activity-item" style={{ animationDelay: `${i * 40}ms` }}>
          <div className="activity-dot" style={{ background: item.color }} />
          <div className="activity-body">
            <div className="activity-label">{item.label}</div>
            <div className="activity-title">{item.title}</div>
            <div className="activity-time">{timeAgo(item.time)}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── SessionBarChart ───────────────────────────────────────────────────────────
// Shows real session counts per day over the last 7 days (R-17: no fabricated values).
// Only renders when at least one day has real session data.

function SessionBarChart({ sessions }) {
  const data = React.useMemo(() => {
    const ended = sessions.filter(s => (s.status || "").toUpperCase() === "ENDED" && s.started_at);
    if (ended.length === 0) return [];

    const buckets = {};
    const today = new Date();
    for (let i = 6; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(today.getDate() - i);
      const key = d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
      buckets[key] = 0;
    }
    ended.forEach(s => {
      const key = new Date(s.started_at).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
      if (key in buckets) buckets[key]++;
    });

    return Object.entries(buckets).map(([label, value]) => ({ label, value }));
  }, [sessions]);

  const hasData = data.some(d => d.value > 0);
  if (!hasData) return null;

  const max = Math.max(...data.map(d => d.value), 1);

  return (
    <div className="sidebar-section">
      <div className="sidebar-section-label">Sessions this week</div>
      <div className="mini-bars">
        {data.map((d, i) => (
          <div key={i} className="mini-bar-col" title={`${d.label}: ${d.value} session${d.value !== 1 ? "s" : ""}` }>
            <div
              className="mini-bar-fill"
              style={{ height: `${Math.max((d.value / max) * 56, d.value > 0 ? 4 : 0)}px`, animationDelay: `${i * 60}ms` }}
            />
            <div className="mini-bar-label">{d.label.split(" ")[0]}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── EmptyState ───────────────────────────────────────────────────────────────

function EmptyState({ icon, title, subtitle, action }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">{icon}</div>
      <h3 className="empty-title">{title}</h3>
      <p className="empty-sub">{subtitle}</p>
      {action}
    </div>
  );
}

// ── DashboardView ─────────────────────────────────────────────────────────────

export function DashboardView({ onStartSession, onOpenResults }) {
  const { user } = useAuth();
  const [questionSets, setQuestionSets] = useState([]);
  const [classes, setClasses]           = useState([]);
  const [sessions, setSessions]         = useState([]);
  const [loading, setLoading]           = useState(true);
  const [refreshing, setRefreshing]     = useState(false);
  const [error, setError]               = useState(null);
  const [isQuizModalOpen, setIsQuizModalOpen]   = useState(false);
  const [isQuickQuizOpen, setIsQuickQuizOpen]   = useState(false);
  const [searchQuery, setSearchQuery]   = useState("");
  const [sessionFilter, setSessionFilter] = useState("all");
  const [launching, setLaunching]       = useState(false);
  const [launchError, setLaunchError]   = useState(null);
  const [selectedClass, setSelectedClass] = useState("");

  const greeting = getGreeting();

  const fetchData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true); else setLoading(true);
    setError(null);
    try {
      const [qs, cls, sess] = await Promise.all([
        api.getQuestionSets().catch(() => []),
        api.getClasses().catch(() => []),
        api.getQuizSessions().catch(() => []),
      ]);
      setQuestionSets(qs);
      setClasses(cls);
      setSessions(sess);
      if (cls.length > 0 && !selectedClass) setSelectedClass(cls[0].id.toString());
    } catch (err) {
      setError("Could not load dashboard data. Check that the server is running.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [selectedClass]);

  useEffect(() => { fetchData(); }, []);

  const handleLaunchQuiz = async (qSetId) => {
    setLaunching(true);
    setLaunchError(null);
    try {
      const session = await api.createQuizSession({
        question_set_id: Number(qSetId),
        class_id: selectedClass ? Number(selectedClass) : null,
      });
      await api.startQuizSession(session.id);
      onStartSession(session.id);
    } catch (err) {
      setLaunchError(err.message || "Failed to start quiz session.");
    } finally {
      setLaunching(false);
    }
  };

  const handleQuickQuizCreated = async (result) => {
    try {
      const session = await api.createQuizSession({
        question_set_id: result.question_set_id,
        class_id: selectedClass ? Number(selectedClass) : null,
      });
      await api.startQuizSession(session.id);
      await fetchData(true);
      onStartSession(session.id);
    } catch (err) {
      alert("Quiz created but failed to launch: " + (err.message || err));
    }
  };

  const handleQuizCreated = async (qSet, launchNow = false) => {
    await fetchData(true);
    if (launchNow && qSet?.id) {
      await handleLaunchQuiz(qSet.id);
    }
  };

  const filteredQuizzes = React.useMemo(() => {
    if (!searchQuery) return questionSets;
    const q = searchQuery.toLowerCase();
    return questionSets.filter(qs =>
      qs.title.toLowerCase().includes(q) ||
      (qs.subject || "").toLowerCase().includes(q) ||
      (qs.grade || "").toLowerCase().includes(q)
    );
  }, [questionSets, searchQuery]);

  const filteredSessions = React.useMemo(() => {
    if (sessionFilter === "active") return sessions.filter(s => {
      const st = (s.status || "").toUpperCase();
      return st === "ACTIVE" || st === "PAUSED";
    });
    if (sessionFilter === "ended") return sessions.filter(s => (s.status || "").toUpperCase() === "ENDED");
    return sessions;
  }, [sessions, sessionFilter]);

  const liveSession = sessions.find(s => {
    const st = (s.status || "").toUpperCase();
    return st === "ACTIVE" || st === "PAUSED";
  });
  const completedCount = sessions.filter(s => (s.status || "").toUpperCase() === "ENDED").length;
  const firstName      = user?.full_name?.split(" ")[0] || "Teacher";

  if (loading) {
    return (
      <div className="dash-loading">
        <div className="dash-loading-inner">
          <div className="spinner-ring" />
        </div>
        <p className="dash-loading-text">Loading your classroom...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dash-loading">
        <div className="dash-loading-inner">
          <AlertCircle size={32} color="var(--danger)" />
        </div>
        <p className="dash-loading-text" style={{ color: "var(--danger)" }}>{error}</p>
        <button className="btn btn-outline" style={{ marginTop: "16px" }} onClick={() => fetchData()}>
          <RefreshCw size={15} /> Try again
        </button>
      </div>
    );
  }

  return (
    <div className="main-container animate-fade-in">

      {/* ── HERO ─────────────────────────────────────────────────────────── */}
      <div className="dash-hero">
        <div className="dash-hero-left">
          <p className="dash-greeting-text">{greeting}</p>
          <h1 className="dash-hero-name">{firstName}</h1>
          <p className="dash-hero-sub">
            {questionSets.length > 0
              ? `${questionSets.length} quiz ${questionSets.length === 1 ? "set" : "sets"} ready to launch${sessions.length > 0 ? `, ${sessions.length} session${sessions.length === 1 ? "" : "s"} on record` : ""}.`
              : "Create your first quiz set to get started."}
          </p>
          <div className="dash-hero-btns">
            <button id="quick-quiz-btn" className="btn-hero-quick" onClick={() => setIsQuickQuizOpen(true)}>
              <Zap size={16} /> Quick Quiz
            </button>
            <button id="create-quiz-btn" className="btn-hero-primary" onClick={() => setIsQuizModalOpen(true)}>
              <Plus size={16} /> New Quiz Set
            </button>
            <button
              id="refresh-dashboard-btn"
              className="btn-hero-ghost"
              onClick={() => fetchData(true)}
              disabled={refreshing}
            >
              <RefreshCw size={15} className={refreshing ? "spin" : ""} />
              {refreshing ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </div>
        <div className="dash-hero-right">
          <LiveClock />
          <div className="dash-mini-stats">
            <button
              id="mini-stat-quizzes"
              type="button"
              className="dash-mini-stat"
              style={{ cursor: "pointer", border: "1px solid var(--border-subtle)", background: "transparent" }}
              onClick={() => document.getElementById("available-quizzes-section")?.scrollIntoView({ behavior: "smooth" })}
              title="Jump to Available Quizzes"
            >
              <BookOpen size={13} /> {questionSets.length} {questionSets.length === 1 ? "Quiz" : "Quizzes"}
            </button>
            <button
              id="mini-stat-classes"
              type="button"
              className="dash-mini-stat"
              style={{ cursor: "pointer", border: "1px solid var(--border-subtle)", background: "transparent" }}
              onClick={() => document.getElementById("classroom-section")?.scrollIntoView({ behavior: "smooth" })}
              title="Jump to Target Classroom"
            >
              <Users size={13} /> {classes.length} {classes.length === 1 ? "Class" : "Classes"}
            </button>
            <button
              id="mini-stat-completed"
              type="button"
              className="dash-mini-stat"
              style={{ cursor: "pointer", border: "1px solid var(--border-subtle)", background: "transparent" }}
              onClick={() => {
                setSessionFilter("ended");
                document.getElementById("quiz-sessions-section")?.scrollIntoView({ behavior: "smooth" });
              }}
              title="Filter to Completed Sessions"
            >
              <CheckCircle2 size={13} /> {completedCount} Done
            </button>
          </div>
        </div>
      </div>

      {/* ── LIVE SESSION BANNER ──────────────────────────────────────────────── */}
      {liveSession && (
        <div className="live-banner animate-fade-in">
          <div className="live-banner-indicator" />
          <div>
            <div className="live-banner-title">
              Session #{liveSession.id} is live right now
            </div>
            <div className="live-banner-sub">
              {liveSession.question_set?.title || `Quiz #${liveSession.question_set_id}`}
              {liveSession.class_?.name && ` · ${liveSession.class_.name}`}
            </div>
          </div>
          <button
            className="btn btn-success"
            style={{ marginLeft: "auto", flexShrink: 0 }}
            onClick={() => onStartSession(liveSession.id)}
          >
            <Radio size={14} /> Return to session
          </button>
        </div>
      )}

      {/* ── STAT CARDS ─────────────────────────────────────────────────────── */}
      <div className="dash-stats-grid">
        <StatCard
          icon={<BookOpen size={20} />}
          label="Question Sets"
          value={questionSets.length}
          color="#6366f1"
          sublabel="Ready to launch"
          onClick={() => document.getElementById("available-quizzes-section")?.scrollIntoView({ behavior: "smooth" })}
        />
        <StatCard
          icon={<Users size={20} />}
          label="Assigned Classes"
          value={classes.length}
          color="#10b981"
          sublabel="Active classrooms"
          onClick={() => document.getElementById("classroom-section")?.scrollIntoView({ behavior: "smooth" })}
        />
        <StatCard
          icon={<Radio size={20} />}
          label="Total Sessions"
          value={sessions.length}
          color="#f59e0b"
          sublabel="All time"
          onClick={() => {
            setSessionFilter("all");
            document.getElementById("quiz-sessions-section")?.scrollIntoView({ behavior: "smooth" });
          }}
        />
        <StatCard
          icon={<CheckCircle2 size={20} />}
          label="Completed"
          value={completedCount}
          color="#3b82f6"
          sublabel="With full reports"
          onClick={() => {
            setSessionFilter("ended");
            document.getElementById("quiz-sessions-section")?.scrollIntoView({ behavior: "smooth" });
          }}
        />
      </div>

      {/* ── MAIN 2-COL LAYOUT ──────────────────────────────────────────────── */}
      <div className="dash-main-grid">

        {/* ── LEFT COLUMN ────────────────────────────────────────────────── */}
        <div style={{ minWidth: 0 }}>

          {launchError && (
            <div className="error-toast animate-fade-in">
              <AlertCircle size={15} />
              <span>{launchError}</span>
              <button onClick={() => setLaunchError(null)} style={{ marginLeft: "auto", background: "none", border: "none", color: "inherit", cursor: "pointer", fontSize: "16px" }}>×</button>
            </div>
          )}

          {/* Class Selector */}
          <div id="classroom-section" className="class-bar">
            <div className="class-bar-label"><Users size={15} color="var(--primary)" /> Target Classroom</div>
            <div className="class-bar-select-wrap">
              <select
                id="class-selector"
                className="form-select class-select"
                value={selectedClass}
                onChange={(e) => setSelectedClass(e.target.value)}
              >
                {classes.length > 0 ? (
                  classes.map((c) => (
                    <option key={c.id} value={c.id}>{c.name} {c.grade ? `(${c.grade})` : ""}</option>
                  ))
                ) : (
                  <>
                    <option value="1">Grade 10 (10)</option>
                    <option value="2">Grade 11 (11)</option>
                  </>
                )}
              </select>
              <ChevronDown size={14} className="select-chevron" />
            </div>
          </div>

          {/* Quiz Search + List */}
          <div id="available-quizzes-section" className="section-header">
            <div>
              <h2 className="section-title">Available Quizzes</h2>
              <p className="section-sub">Select any quiz to launch live card-scanning on projector</p>
            </div>
            <div className="search-box">
              <Search size={13} className="search-ico" />
              <input
                id="quiz-search-input"
                className="search-inp"
                placeholder="Search by title, subject or grade..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>

          {filteredQuizzes.length === 0 ? (
            <EmptyState
              icon={<BookOpen size={44} color="var(--text-dim)" />}
              title={searchQuery ? "No quizzes matched your search" : "No Quizzes Yet"}
              subtitle={searchQuery ? "Try a different keyword." : "Create your first question set to get started."}
              action={!searchQuery && (
                <button className="btn btn-primary" onClick={() => setIsQuizModalOpen(true)}>
                  <Plus size={15} /> Create Your First Quiz
                </button>
              )}
            />
          ) : (
            <div className="quiz-grid">
              {filteredQuizzes.map((qs) => (
                <QuizCard key={qs.id} qs={qs} launching={launching} onLaunch={handleLaunchQuiz} />
              ))}
            </div>
          )}

          {/* Sessions */}
          <div id="quiz-sessions-section" className="section-header" style={{ marginTop: "44px" }}>
            <div>
              <h2 className="section-title">Quiz Sessions</h2>
              <p className="section-sub">Review student responses, scores, and question-by-question analysis</p>
            </div>
            <div className="filter-tabs">
              {[
                { id: "all",    label: "All" },
                { id: "active", label: "Live" },
                { id: "ended",  label: "Completed" },
              ].map(tab => (
                <button
                  key={tab.id}
                  className={`filter-tab ${sessionFilter === tab.id ? "active" : ""}`}
                  onClick={() => setSessionFilter(tab.id)}
                >
                  {tab.label}
                  {tab.id === "active" && liveSession && <span className="tab-live-dot" />}
                </button>
              ))}
            </div>
          </div>

          {filteredSessions.length === 0 ? (
            <EmptyState
              icon={<Activity size={40} color="var(--text-dim)" />}
              title={sessionFilter === "active"
                ? "No live sessions right now"
                : sessionFilter === "ended"
                ? "No completed sessions yet"
                : "No sessions yet"}
              subtitle={sessionFilter === "active"
                ? "Launch a quiz above to start a live session."
                : "Launch a quiz to start collecting student responses."}
            />
          ) : (
            <div className="sessions-list">
              <div className="sessions-list-head">
                <span>ID</span><span>Quiz / Class</span><span>Date</span><span>Status</span><span style={{ textAlign: "right" }}>Action</span>
              </div>
              {filteredSessions.map((sess, i) => (
                <SessionRow key={sess.id} sess={sess} index={i} onStartSession={onStartSession} onOpenResults={onOpenResults} />
              ))}
            </div>
          )}
        </div>

        {/* ── RIGHT SIDEBAR ──────────────────────────────────────────────────── */}
        <div className="dash-sidebar">

          {/* Session chart — only when real data exists */}
          {sessions.length >= 2 && (
            <div className="sidebar-card">
              <SessionBarChart sessions={sessions} />
            </div>
          )}

          {/* Activity feed — only real events */}
          <div className="sidebar-card">
            <div className="sidebar-section-label">
              <Clock size={13} />
              Recent activity
            </div>
            <ActivityFeed sessions={sessions} questionSets={questionSets} />
          </div>

          {/* Quick actions */}
          <div className="sidebar-card">
            <div className="sidebar-section-label">
              <FileText size={13} />
              Quick actions
            </div>
            <div className="quick-actions">
              <button className="quick-action" onClick={() => setIsQuickQuizOpen(true)}>
                <div className="qa-icon" style={{ background: "rgba(245,158,11,0.12)", color: "#f59e0b" }}><Zap size={16} /></div>
                <div className="qa-body">
                  <div className="qa-title">Quick Quiz</div>
                  <div className="qa-sub">Build and launch in one step</div>
                </div>
                <ChevronRight size={14} className="qa-arrow" />
              </button>
              <button className="quick-action" onClick={() => setIsQuizModalOpen(true)}>
                <div className="qa-icon" style={{ background: "rgba(99,102,241,0.12)", color: "#6366f1" }}><Plus size={16} /></div>
                <div className="qa-body">
                  <div className="qa-title">New Quiz Set</div>
                  <div className="qa-sub">Build a full question set</div>
                </div>
                <ChevronRight size={14} className="qa-arrow" />
              </button>
              {liveSession && (
                <button className="quick-action" onClick={() => onStartSession(liveSession.id)}>
                  <div className="qa-icon" style={{ background: "rgba(16,185,129,0.12)", color: "#10b981" }}><Radio size={16} /></div>
                  <div className="qa-body">
                    <div className="qa-title">Resume live session</div>
                    <div className="qa-sub">Session #{liveSession.id} is running</div>
                  </div>
                  <ChevronRight size={14} className="qa-arrow" />
                </button>
              )}
            </div>
          </div>

          {/* Class list with keyboard navigation (R-32) */}
          {classes.length > 0 && (
            <div className="sidebar-card">
              <div className="sidebar-section-label"><Layers size={13} /> Your classes</div>
              <div className="class-chips">
                {classes.map((cls) => (
                  <div
                    key={cls.id}
                    className={`class-chip ${selectedClass === cls.id.toString() ? "selected" : ""}`}
                    onClick={() => setSelectedClass(cls.id.toString())}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && setSelectedClass(cls.id.toString())}
                  >
                    <div className="class-chip-badge">{cls.grade || cls.name.charAt(0)}</div>
                    <div>
                      <div className="class-chip-name">{cls.name}</div>
                      <div className="class-chip-sub">{sessions.filter(s => s.class_id === cls.id).length} sessions</div>
                    </div>
                    {selectedClass === cls.id.toString() && <CheckCircle2 size={13} color="#10b981" style={{ marginLeft: "auto" }} />}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Results shortcut — only when completed sessions exist */}
          {completedCount > 0 && (
            <div className="sidebar-card sidebar-results-card">
              <div className="sidebar-section-label">
                <Award size={13} />
                Session results
              </div>
              <p className="sidebar-results-text">
                {completedCount} completed {completedCount === 1 ? "session has" : "sessions have"} full response reports ready.
              </p>
              <button
                className="btn btn-outline btn-sm"
                style={{ width: "100%", marginTop: "10px" }}
                onClick={() => setSessionFilter("ended")}
              >
                <BarChart2 size={13} /> View completed sessions
              </button>
            </div>
          )}
        </div>
      </div>

      <QuizModal isOpen={isQuizModalOpen} onClose={() => setIsQuizModalOpen(false)} onCreated={handleQuizCreated} />
      <QuickQuizModal isOpen={isQuickQuizOpen} onClose={() => setIsQuickQuizOpen(false)} onCreated={handleQuickQuizCreated} />
    </div>
  );
}
