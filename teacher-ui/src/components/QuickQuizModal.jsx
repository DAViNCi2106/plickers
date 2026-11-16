/**
 * src/components/QuickQuizModal.jsx
 * =====================================
 * Fast oral / dictated quiz builder:
 *  - Teacher dictates questions orally in class
 *  - Teacher configures options (A, B, C, D) and marks the correct answer
 *  - Supports setting the correct answer now OR leaving it to be set in the future / during live quiz
 *  - Quick question count presets (1, 3, 5, 10 questions)
 */
import React, { useState } from "react";
import { createPortal } from "react-dom";
import {
  X, Zap, Plus, Trash2, CheckCircle2, ChevronUp, ChevronDown,
  Loader2, Mic, Hash, Clock, Sparkles, ChevronRight, SlidersHorizontal,
} from "lucide-react";
import { api } from "../api/client";

const OPTS   = ["A", "B", "C", "D"];
const COLORS = { A: "#3b82f6", B: "#10b981", C: "#f59e0b", D: "#ef4444" };
const BG     = {
  A: "rgba(59,130,246,0.12)",
  B: "rgba(16,185,129,0.12)",
  C: "rgba(245,158,11,0.12)",
  D: "rgba(239,68,68,0.12)",
};

let _uid = 0;
const makeQ = (n, correct = null) => ({
  id: ++_uid,
  label: `Question ${n} (Oral / Dictated)`,
  option_a: "Option A",
  option_b: "Option B",
  option_c: "Option C",
  option_d: "Option D",
  correct_answer: correct, // null = decide in future / live session
  marks: 1,
  showCustomOptions: false,
});

function QuestionCard({ q, idx, total, onChange, onDelete, onMove }) {
  const set = (k, v) => onChange(q.id, { ...q, [k]: v });
  const optKey = { A: "option_a", B: "option_b", C: "option_c", D: "option_d" };

  const handleSelectAnswer = (opt) => {
    // If already selected, clicking it again unselects it (sets to null / future)
    set("correct_answer", q.correct_answer === opt ? null : opt);
  };

  return (
    <div
      style={{
        background: "var(--bg-elevated)",
        border: `1px solid ${q.correct_answer ? COLORS[q.correct_answer] + "55" : "var(--border-subtle)"}`,
        borderRadius: "var(--radius-md)",
        padding: "16px 18px",
        marginBottom: "12px",
        transition: "border-color 0.2s, box-shadow 0.2s",
        boxShadow: q.correct_answer ? `0 2px 8px ${COLORS[q.correct_answer]}15` : "none",
      }}
    >
      {/* Header row */}
      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "12px" }}>
        <span
          style={{
            width: "32px",
            height: "32px",
            borderRadius: "var(--radius-sm)",
            background: q.correct_answer ? BG[q.correct_answer] : "var(--bg-card)",
            border: `1px solid ${q.correct_answer ? COLORS[q.correct_answer] : "var(--border-subtle)"}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "13px",
            fontWeight: 800,
            color: q.correct_answer ? COLORS[q.correct_answer] : "var(--primary)",
            flexShrink: 0,
          }}
        >
          Q{idx + 1}
        </span>

        <input
          value={q.label}
          onChange={(e) => set("label", e.target.value)}
          placeholder={`Question ${idx + 1} note (e.g. Oral Prompt / Chapter Topic)`}
          style={{
            flex: 1,
            background: "var(--bg-card)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-sm)",
            padding: "8px 12px",
            color: "var(--text-primary)",
            fontSize: "13px",
            fontWeight: 600,
            outline: "none",
          }}
        />

        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          <Hash size={12} color="var(--text-muted)" />
          <input
            type="number"
            min={1}
            max={10}
            value={q.marks}
            onChange={(e) => set("marks", Math.max(1, Number(e.target.value)))}
            style={{
              width: "48px",
              background: "var(--bg-card)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-sm)",
              padding: "6px 4px",
              color: "var(--text-primary)",
              fontSize: "13px",
              fontWeight: 700,
              textAlign: "center",
              outline: "none",
            }}
            title="Marks / Points"
          />
          <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>pts</span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
          <button
            type="button"
            onClick={() => onMove(idx, -1)}
            disabled={idx === 0}
            style={{
              background: "none",
              border: "none",
              cursor: idx === 0 ? "default" : "pointer",
              color: idx === 0 ? "var(--text-dim)" : "var(--text-muted)",
              padding: "2px",
            }}
          >
            <ChevronUp size={14} />
          </button>
          <button
            type="button"
            onClick={() => onMove(idx, 1)}
            disabled={idx === total - 1}
            style={{
              background: "none",
              border: "none",
              cursor: idx === total - 1 ? "default" : "pointer",
              color: idx === total - 1 ? "var(--text-dim)" : "var(--text-muted)",
              padding: "2px",
            }}
          >
            <ChevronDown size={14} />
          </button>
        </div>

        {total > 1 && (
          <button
            type="button"
            onClick={() => onDelete(q.id)}
            style={{ background: "none", border: "none", cursor: "pointer", color: "#f87171", padding: "4px" }}
            title="Remove Question"
          >
            <Trash2 size={16} />
          </button>
        )}
      </div>

      {/* Answer Key Selection */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "10px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)", marginRight: "4px" }}>
            Correct Answer:
          </span>

          {OPTS.map((opt) => {
            const isCorrect = q.correct_answer === opt;
            return (
              <button
                key={opt}
                type="button"
                onClick={() => handleSelectAnswer(opt)}
                title={`Mark ${opt} as correct answer (click again to unset)`}
                style={{
                  width: "44px",
                  height: "36px",
                  borderRadius: "var(--radius-sm)",
                  border: `2px solid ${isCorrect ? COLORS[opt] : "var(--border-subtle)"}`,
                  background: isCorrect ? COLORS[opt] : "var(--bg-card)",
                  color: isCorrect ? "#fff" : "var(--text-primary)",
                  fontWeight: 800,
                  fontSize: "14px",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  transition: "all 0.15s ease",
                  boxShadow: isCorrect ? `0 2px 8px ${COLORS[opt]}55` : "none",
                }}
              >
                {opt}
              </button>
            );
          })}

          <button
            type="button"
            onClick={() => set("correct_answer", null)}
            style={{
              padding: "6px 12px",
              borderRadius: "var(--radius-sm)",
              border: `1px dashed ${!q.correct_answer ? "#f59e0b" : "var(--border-subtle)"}`,
              background: !q.correct_answer ? "rgba(245,158,11,0.12)" : "transparent",
              color: !q.correct_answer ? "#f59e0b" : "var(--text-dim)",
              fontSize: "12px",
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
            title="Leave answer key undecided for now. You can reveal or set it live in class."
          >
            <Clock size={13} />
            {!q.correct_answer ? "Set Later (Decide in Future)" : "Decide Later"}
          </button>
        </div>

        <button
          type="button"
          onClick={() => set("showCustomOptions", !q.showCustomOptions)}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "var(--text-dim)",
            fontSize: "11px",
            display: "flex",
            alignItems: "center",
            gap: "4px",
            textDecoration: "underline",
          }}
        >
          <SlidersHorizontal size={11} />
          {q.showCustomOptions ? "Hide Option Labels" : "Customize Option Labels (Optional)"}
        </button>
      </div>

      {/* Optional custom option text inputs */}
      {q.showCustomOptions && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginTop: "12px", paddingTop: "12px", borderTop: "1px dashed var(--border-subtle)" }}>
          {OPTS.map((opt) => (
            <div key={opt} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <span style={{ fontSize: "12px", fontWeight: 700, color: COLORS[opt], width: "16px" }}>{opt}:</span>
              <input
                value={q[optKey[opt]]}
                onChange={(e) => set(optKey[opt], e.target.value)}
                placeholder={`Option ${opt}`}
                style={{
                  flex: 1,
                  background: "var(--bg-card)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "var(--radius-sm)",
                  padding: "5px 8px",
                  fontSize: "12px",
                  color: "var(--text-primary)",
                  outline: "none",
                }}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function QuickQuizModal({ isOpen, onClose, onCreated }) {
  const getInitialTitle = () => {
    const now = new Date();
    return `Oral Quiz · ${now.toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;
  };

  const [title, setTitle]         = useState(getInitialTitle);
  const [subject, setSubject]     = useState("General");
  const [grade, setGrade]         = useState("Class 10");
  const [questions, setQuestions] = useState([makeQ(1), makeQ(2), makeQ(3)]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError]         = useState(null);

  if (!isOpen) return null;

  // Set number of questions using presets (1, 3, 5, 10)
  const setPresetCount = (count) => {
    setQuestions((prev) => {
      if (prev.length === count) return prev;
      if (prev.length < count) {
        const next = [...prev];
        for (let i = prev.length + 1; i <= count; i++) {
          next.push(makeQ(i));
        }
        return next;
      }
      return prev.slice(0, count);
    });
  };

  const addQuestion = () => {
    setQuestions((prev) => [...prev, makeQ(prev.length + 1)]);
    setTimeout(() => {
      const el = document.getElementById("qq-questions-list");
      if (el) el.scrollTop = el.scrollHeight;
    }, 50);
  };

  const updateQuestion = (id, updated) =>
    setQuestions((prev) => prev.map((q) => (q.id === id ? updated : q)));

  const deleteQuestion = (id) =>
    setQuestions((prev) => (prev.length <= 1 ? prev : prev.filter((q) => q.id !== id)));

  const moveQuestion = (idx, dir) => {
    setQuestions((prev) => {
      const arr = [...prev];
      const t = idx + dir;
      if (t < 0 || t >= arr.length) return arr;
      [arr[idx], arr[t]] = [arr[t], arr[idx]];
      return arr;
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim()) {
      setError("Please enter a quiz title.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const result = await api.quickCreateQuiz({
        title: title.trim(),
        subject: subject.trim() || null,
        grade: grade.trim() || null,
        questions: questions.map((q, idx) => ({
          correct_answer: q.correct_answer || null, // null allowed if deciding in future
          label: q.label || `Question ${idx + 1} (Oral / Dictated)`,
          question_text: q.label || `Question ${idx + 1} (Oral / Dictated)`,
          marks: q.marks || 1,
          option_a: q.option_a || "Option A",
          option_b: q.option_b || "Option B",
          option_c: q.option_c || "Option C",
          option_d: q.option_d || "Option D",
        })),
      });

      onCreated(result);
      onClose();
    } catch (err) {
      setError(err.message || "Failed to create quiz");
    } finally {
      setSubmitting(false);
    }
  };

  const totalMarks = questions.reduce((s, q) => s + (Number(q.marks) || 1), 0);
  const answersWithKey = questions.filter((q) => q.correct_answer).length;
  const answersPending = questions.length - answersWithKey;

  return createPortal(
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div
        className="modal-content animate-fade-in"
        style={{ maxWidth: "800px", width: "95vw", maxHeight: "90vh", display: "flex", flexDirection: "column" }}
        id="quick-quiz-modal"
      >
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px", flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                width: "42px",
                height: "42px",
                borderRadius: "var(--radius-md)",
                background: "linear-gradient(135deg, #f59e0b, #d97706)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Mic size={22} color="#fff" />
            </div>
            <div>
              <h2 style={{ fontSize: "19px", margin: 0, display: "flex", alignItems: "center", gap: "8px" }}>
                Dictated / Oral Quick Quiz
                <span style={{ fontSize: "11px", fontWeight: 700, padding: "2px 8px", background: "rgba(245,158,11,0.15)", color: "#f59e0b", borderRadius: "100px" }}>
                  Instant
                </span>
              </h2>
              <p style={{ fontSize: "12px", margin: 0, color: "var(--text-muted)" }}>
                Dictate questions verbally. Choose answer keys now or reveal/set them anytime during live polling.
              </p>
            </div>
          </div>
          <button id="close-quick-quiz-btn" className="btn btn-outline btn-sm" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {error && (
          <div
            style={{
              background: "rgba(239,68,68,0.15)",
              color: "#f87171",
              padding: "10px 14px",
              borderRadius: "var(--radius-md)",
              marginBottom: "14px",
              fontSize: "13px",
              flexShrink: 0,
            }}
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", flex: 1, overflow: "hidden", gap: 0 }}>
          {/* Quick Preset Selector & Title Bar */}
          <div style={{ background: "var(--bg-card)", padding: "12px 16px", borderRadius: "var(--radius-md)", border: "1px solid var(--border-subtle)", marginBottom: "14px", flexShrink: 0 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px", marginBottom: "12px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontSize: "12px", fontWeight: 700, color: "var(--text-muted)" }}>Questions:</span>
                {[1, 3, 5, 10].map((num) => (
                  <button
                    key={num}
                    type="button"
                    onClick={() => setPresetCount(num)}
                    style={{
                      padding: "4px 10px",
                      borderRadius: "var(--radius-sm)",
                      border: `1px solid ${questions.length === num ? "var(--primary)" : "var(--border-subtle)"}`,
                      background: questions.length === num ? "var(--primary)" : "transparent",
                      color: questions.length === num ? "#fff" : "var(--text-primary)",
                      fontSize: "12px",
                      fontWeight: 700,
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                  >
                    {num} Q
                  </button>
                ))}
              </div>

              <div style={{ fontSize: "12px", color: "var(--text-dim)" }}>
                💡 Tip: Click A, B, C, or D for correct key, or leave as <em>Set Later</em>
              </div>
            </div>

            {/* Quiz Info fields */}
            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: "10px" }}>
              <div>
                <label className="form-label" htmlFor="qq-title" style={{ fontSize: "11px", marginBottom: "3px" }}>
                  Quiz Title
                </label>
                <input
                  id="qq-title"
                  className="form-input"
                  style={{ fontSize: "13px", padding: "6px 10px" }}
                  placeholder="e.g. Oral Chapter 5 Polling"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="form-label" style={{ fontSize: "11px", marginBottom: "3px" }}>
                  Subject
                </label>
                <input
                  className="form-input"
                  style={{ fontSize: "13px", padding: "6px 10px" }}
                  placeholder="e.g. Science"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                />
              </div>
              <div>
                <label className="form-label" style={{ fontSize: "11px", marginBottom: "3px" }}>
                  Grade / Section
                </label>
                <input
                  className="form-input"
                  style={{ fontSize: "13px", padding: "6px 10px" }}
                  placeholder="e.g. Grade 10"
                  value={grade}
                  onChange={(e) => setGrade(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Questions list — scrollable */}
          <div id="qq-questions-list" style={{ flex: 1, overflowY: "auto", paddingRight: "4px", minHeight: "180px" }}>
            {questions.map((q, idx) => (
              <QuestionCard
                key={q.id}
                q={q}
                idx={idx}
                total={questions.length}
                onChange={updateQuestion}
                onDelete={deleteQuestion}
                onMove={moveQuestion}
              />
            ))}

            <button
              type="button"
              onClick={addQuestion}
              style={{
                width: "100%",
                padding: "12px",
                background: "transparent",
                border: "2px dashed var(--border-subtle)",
                borderRadius: "var(--radius-md)",
                color: "var(--primary)",
                fontSize: "13px",
                fontWeight: 600,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                transition: "all 0.2s",
                marginBottom: "8px",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(99,102,241,0.06)";
                e.currentTarget.style.borderColor = "var(--primary)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "transparent";
                e.currentTarget.style.borderColor = "var(--border-subtle)";
              }}
            >
              <Plus size={16} /> Add Another Dictated Question
            </button>
          </div>

          {/* Footer */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginTop: "14px",
              paddingTop: "14px",
              borderTop: "1px solid var(--border-subtle)",
              flexShrink: 0,
              flexWrap: "wrap",
              gap: "10px",
            }}
          >
            <div style={{ fontSize: "12px", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
              <span>
                <strong style={{ color: "var(--text-primary)" }}>{questions.length}</strong> questions ({totalMarks} pts)
              </span>
              {answersWithKey > 0 && (
                <span style={{ color: "#10b981", fontWeight: 600 }}>
                  ✓ {answersWithKey} key{answersWithKey > 1 ? "s" : ""} set
                </span>
              )}
              {answersPending > 0 && (
                <span style={{ color: "#f59e0b", fontWeight: 600 }}>
                  ⏳ {answersPending} to decide in live quiz
                </span>
              )}
            </div>

            <div style={{ display: "flex", gap: "10px" }}>
              <button type="button" className="btn btn-outline btn-sm" onClick={onClose}>
                Cancel
              </button>
              <button
                id="quick-quiz-submit-btn"
                type="submit"
                className="btn btn-success"
                disabled={submitting || !title.trim()}
                style={{
                  background: "linear-gradient(135deg, #f59e0b, #d97706)",
                  boxShadow: "0 4px 12px rgba(245,158,11,0.3)",
                  border: "none",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  fontWeight: 700,
                }}
              >
                {submitting ? (
                  <>
                    <Loader2 size={16} className="spin" /> Creating...
                  </>
                ) : (
                  <>
                    <Zap size={16} /> Launch Live Polling Now!
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
}
