import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, Download, Award, BarChart2, CheckCircle2, 
  XCircle, Users, RefreshCw, FileSpreadsheet 
} from 'lucide-react';
import { api } from '../api/client';

export function ResultsView({ sessionId, onBack }) {
  const [session, setSession] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [students, setStudents] = useState([]);
  const [scores, setScores] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadResults() {
      setLoading(true);
      try {
        const sess = await api.getQuizSession(sessionId);
        setSession(sess);

        const [qs, stuList, scoreList, dash] = await Promise.all([
          sess.question_set_id ? api.getQuestionSet(sess.question_set_id) : Promise.resolve(null),
          api.getStudents({ class_id: sess.class_id, section_id: sess.section_id }).catch(() => []),
          api.getSessionScores(sessionId).catch(() => []),
          api.getQuizDashboard(sessionId).catch(() => null),
        ]);

        let qList = qs?.questions || [];
        if ((!qList || qList.length === 0) && sess?.question_set_id) {
          try {
            qList = await api.getQuestions(sess.question_set_id);
          } catch (e) {
            console.warn('Falling back to getQuestions in ResultsView:', e);
          }
        }
        if (qList?.length) setQuestions(qList);
        if (stuList?.length) setStudents(stuList);
        if (scoreList) setScores(scoreList);
        if (dash) setDashboard(dash);
      } catch (err) {
        console.error('Failed to load session report', err);
      } finally {
        setLoading(false);
      }
    }

    loadResults();
  }, [sessionId]);

  // Build matrix lookup: (student_id, question_id) -> response
  const matrix = React.useMemo(() => {
    const map = {};
    if (dashboard?.responses) {
      dashboard.responses.forEach((r) => {
        if (!map[r.student_id]) map[r.student_id] = {};
        map[r.student_id][r.question_id] = r;
      });
    }
    return map;
  }, [dashboard]);

  // Merge student list with their responses & scores
  const studentRows = React.useMemo(() => {
    let list = Array.isArray(students) && students.length > 0 ? students : [];
    if (list.length === 0 && Array.isArray(scores) && scores.length > 0) {
      list = scores.map((s) => ({
        id: s.student_id,
        first_name: `Student`,
        last_name: `#${s.student_id}`,
        student_code: `STU${s.student_id}`,
        roll_number: String(s.student_id),
      }));
    }
    return list.filter(Boolean).map((stu) => {
      const studentId = stu.id;
      const scoreObj = scores.find((s) => s.student_id === studentId);
      const studentResponses = matrix[studentId] || {};

      let totalCorrect = 0;
      let totalMarks = 0;

      questions.forEach((q) => {
        const resp = studentResponses[q.id];
        if (resp && resp.is_correct) {
          totalCorrect++;
          totalMarks += (resp.marks_obtained || q.marks || 1);
        }
      });

      const maxPossibleMarks = questions.reduce((sum, q) => sum + (q.marks || 1), 0) || 1;
      const percentage = scoreObj ? scoreObj.percentage : Math.round((totalMarks / maxPossibleMarks) * 100);

      return {
        id: studentId,
        name: stu.first_name ? `${stu.first_name} ${stu.last_name}` : (stu.user?.full_name || stu.student_code || `Student ${studentId}`),
        rollNumber: stu.roll_number || stu.student_code || `--`,
        cardId: stu.assigned_card?.card_number || stu.id,
        responses: studentResponses,
        totalCorrect: scoreObj ? scoreObj.correct_answers : totalCorrect,
        totalMarks: scoreObj ? scoreObj.score : totalMarks,
        percentage,
      };
    });
  }, [students, scores, matrix, questions]);

  // Overall Statistics
  const stats = React.useMemo(() => {
    if (studentRows.length === 0) return { avg: 0, high: 0, low: 0, passCount: 0 };
    const pcts = studentRows.map((r) => r.percentage);
    const sum = pcts.reduce((a, b) => a + b, 0);
    return {
      avg: Math.round(sum / pcts.length),
      high: Math.max(...pcts),
      low: Math.min(...pcts),
      passCount: pcts.filter((p) => p >= 50).length,
    };
  }, [studentRows]);

  // Export to CSV
  const handleExportCSV = () => {
    const headers = ['Card ID', 'Student Name', 'Roll Number'];
    questions.forEach((q, i) => headers.push(`Q${i + 1} (${q.correct_answer})`));
    headers.push('Total Correct', 'Total Score', 'Percentage (%)');

    const csvRows = [headers.join(',')];

    studentRows.forEach((r) => {
      const row = [
        r.cardId,
        `"${r.name}"`,
        `"${r.rollNumber}"`,
      ];
      questions.forEach((q) => {
        const resp = r.responses[q.id];
        row.push(resp ? resp.answer : '-');
      });
      row.push(r.totalCorrect, r.totalMarks, `${r.percentage}%`);
      csvRows.push(row.join(','));
    });

    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `Plickers_Quiz_Session_${sessionId}_Report.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) {
    return (
      <div className="main-container" style={{ textAlign: 'center', padding: '100px 0' }}>
        <RefreshCw size={36} className="pulse-dot" style={{ margin: '0 auto 16px' }} />
        <h2>Generating Question Matrix Gradebook...</h2>
      </div>
    );
  }

  return (
    <div className="main-container animate-fade-in">
      {/* ── Top Bar ────────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '28px', flexWrap: 'wrap', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button 
            id="back-to-dashboard-btn"
            className="btn btn-outline" 
            onClick={onBack}
          >
            <ArrowLeft size={16} />
            <span>Back to Reports</span>
          </button>
          <div>
            <h1 style={{ fontSize: '26px', margin: 0 }}>
              Session Report: {session?.question_set?.title || `Quiz #${sessionId}`}
            </h1>
            <p style={{ fontSize: '13px' }}>
              Final question-by-question student responses and gradebook
            </p>
          </div>
        </div>

        <button
          id="export-csv-btn"
          className="btn btn-success"
          onClick={handleExportCSV}
          title="Download question matrix as CSV/Excel"
        >
          <FileSpreadsheet size={16} />
          <span>Export Matrix (CSV / Excel)</span>
        </button>
      </div>

      {/* ── Summary KPI Cards ──────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '20px', marginBottom: '32px' }}>
        <div className="glass-panel" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 700 }}>
            Class Average
          </div>
          <div style={{ fontSize: '36px', fontWeight: 800, color: 'var(--primary)', marginTop: '4px' }}>
            {stats.avg}%
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Overall Mastery</div>
        </div>

        <div className="glass-panel" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 700 }}>
            Highest Score
          </div>
          <div style={{ fontSize: '36px', fontWeight: 800, color: 'var(--success)', marginTop: '4px' }}>
            {stats.high}%
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Top Performer</div>
        </div>

        <div className="glass-panel" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 700 }}>
            Students Evaluated
          </div>
          <div style={{ fontSize: '36px', fontWeight: 800, color: '#fff', marginTop: '4px' }}>
            {studentRows.length}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>100% Finalized</div>
        </div>

        <div className="glass-panel" style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-dim)', textTransform: 'uppercase', fontWeight: 700 }}>
            Passing Rate
          </div>
          <div style={{ fontSize: '36px', fontWeight: 800, color: '#38bdf8', marginTop: '4px' }}>
            {studentRows.length > 0 ? Math.round((stats.passCount / studentRows.length) * 100) : 0}%
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>≥ 50% Threshold</div>
        </div>
      </div>

      {/* ── Per-Question Student Matrix ────────────────────────────────────── */}
      <div className="glass-panel" style={{ padding: '0', overflow: 'hidden' }}>
        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 style={{ fontSize: '18px' }}>Per-Question Student Response Matrix</h2>
            <p style={{ fontSize: '13px' }}>
              Green = Correct • Red = Incorrect • Dash (-) = No card detected before lock
            </p>
          </div>
          <span className="brand-badge">{questions.length} Total Questions</span>
        </div>

        <div className="table-responsive">
          <table className="matrix-table" id="gradebook-matrix-table">
            <thead>
              <tr>
                <th style={{ width: '80px' }}>Card #</th>
                <th>Student Name</th>
                <th>Roll No</th>
                {questions.map((q, idx) => (
                  <th key={q.id} style={{ textAlign: 'center' }} title={q.question_text}>
                    Q{idx + 1}
                    <div style={{ fontSize: '10px', color: 'var(--primary)' }}>
                      [{q.correct_answer}]
                    </div>
                  </th>
                ))}
                <th style={{ textAlign: 'center' }}>Correct</th>
                <th style={{ textAlign: 'center' }}>Score</th>
                <th style={{ textAlign: 'center' }}>%</th>
              </tr>
            </thead>
            <tbody>
              {studentRows.map((stu) => (
                <tr key={stu.id}>
                  <td>
                    <span style={{ fontWeight: 700, fontFamily: 'monospace', color: 'var(--text-dim)' }}>
                      #{stu.cardId}
                    </span>
                  </td>
                  <td style={{ fontWeight: 600, color: '#fff' }}>{stu.name}</td>
                  <td style={{ color: 'var(--text-muted)' }}>{stu.rollNumber}</td>

                  {/* Individual Question Cells */}
                  {questions.map((q) => {
                    const resp = stu.responses[q.id];
                    if (!resp) {
                      return (
                        <td key={q.id} style={{ textAlign: 'center', color: 'var(--text-dim)' }}>
                          -
                        </td>
                      );
                    }
                    const isCorrect = resp.is_correct;
                    return (
                      <td 
                        key={q.id} 
                        style={{ textAlign: 'center' }}
                        className={isCorrect ? 'cell-correct' : 'cell-incorrect'}
                        title={`Answered ${resp.answer} (${isCorrect ? 'Correct' : 'Incorrect'})`}
                      >
                        {resp.answer}
                      </td>
                    );
                  })}

                  <td style={{ textAlign: 'center', fontWeight: 700 }}>
                    {stu.totalCorrect} / {questions.length}
                  </td>
                  <td style={{ textAlign: 'center', fontWeight: 700, color: 'var(--primary)' }}>
                    {stu.totalMarks}
                  </td>
                  <td style={{ textAlign: 'center', fontWeight: 800 }}>
                    <span 
                      style={{
                        padding: '3px 8px',
                        borderRadius: 'var(--radius-full)',
                        background: stu.percentage >= 60 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                        color: stu.percentage >= 60 ? '#34d399' : '#f87171',
                      }}
                    >
                      {stu.percentage}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
