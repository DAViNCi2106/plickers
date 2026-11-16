import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import { X, Plus, Trash2, CheckCircle2, Play, Loader2 } from 'lucide-react';
import { api } from '../api/client';

export function QuizModal({ isOpen, onClose, onCreated }) {
  const [title, setTitle] = useState('Science Practice Quiz');
  const [subject, setSubject] = useState('Science');
  const [grade, setGrade] = useState('Grade 8');
  const [questions, setQuestions] = useState([
    {
      question_text: 'What gas do plants absorb during photosynthesis?',
      option_a: 'Oxygen',
      option_b: 'Carbon Dioxide',
      option_c: 'Nitrogen',
      option_d: 'Hydrogen',
      correct_answer: 'B',
      marks: 1,
    },
    {
      question_text: 'Which organ pumps blood throughout the human body?',
      option_a: 'Lungs',
      option_b: 'Liver',
      option_c: 'Heart',
      option_d: 'Kidneys',
      correct_answer: 'C',
      marks: 1,
    }
  ]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleAddQuestion = () => {
    setQuestions([
      ...questions,
      {
        question_text: '',
        option_a: '',
        option_b: '',
        option_c: '',
        option_d: '',
        correct_answer: 'A',
        marks: 1,
      },
    ]);
  };

  const handleRemoveQuestion = (idx) => {
    if (questions.length <= 1) return;
    setQuestions(questions.filter((_, i) => i !== idx));
  };

  const handleQuestionChange = (idx, field, value) => {
    const updated = [...questions];
    updated[idx][field] = value;
    setQuestions(updated);
  };

  const handleSubmit = async (e, launchNow = false) => {
    if (e) e.preventDefault();
    if (!title.trim()) {
      setError('Please provide a quiz title.');
      return;
    }
    for (let i = 0; i < questions.length; i++) {
      const q = questions[i];
      if (!q.question_text || !q.option_a || !q.option_b || !q.option_c || !q.option_d) {
        setError(`Please fill in all options for Question #${i + 1}`);
        return;
      }
    }

    setSubmitting(true);
    setError(null);
    try {
      // 1. Create Question Set
      const qSet = await api.createQuestionSet({
        title,
        subject,
        grade,
        description: `Created via Teacher Portal for ${grade} ${subject}`,
      });

      // 2. Add Questions
      for (const q of questions) {
        await api.addQuestion(qSet.id, {
          question_text: q.question_text,
          option_a: q.option_a,
          option_b: q.option_b,
          option_c: q.option_c,
          option_d: q.option_d,
          correct_answer: q.correct_answer,
          marks: q.marks || 1,
        });
      }

      onCreated(qSet, launchNow);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to save question set');
    } finally {
      setSubmitting(false);
    }
  };

  return createPortal(
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-content animate-fade-in" style={{ maxWidth: '780px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <div>
            <h2 style={{ fontSize: '22px' }}>Create New Quiz</h2>
            <p style={{ fontSize: '13px' }}>Add questions with options A, B, C, D for classroom card scanning</p>
          </div>
          <button 
            id="close-quiz-modal-btn"
            className="btn btn-outline btn-sm" 
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </div>

        {error && (
          <div style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#f87171', padding: '12px', borderRadius: 'var(--radius-md)', marginBottom: '16px', fontSize: '14px' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '14px', marginBottom: '20px' }}>
            <div>
              <label className="form-label">Quiz Title</label>
              <input
                id="quiz-title-input"
                className="form-input"
                placeholder="e.g. Human Biology Chapter 4"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="form-label">Subject</label>
              <input
                className="form-input"
                placeholder="e.g. Science"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
              />
            </div>
            <div>
              <label className="form-label">Grade / Class</label>
              <input
                className="form-input"
                placeholder="e.g. Grade 8"
                value={grade}
                onChange={(e) => setGrade(e.target.value)}
              />
            </div>
          </div>

          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '20px', marginBottom: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '16px' }}>Questions ({questions.length})</h3>
              <button
                id="add-question-btn"
                type="button"
                className="btn btn-outline btn-sm"
                onClick={handleAddQuestion}
              >
                <Plus size={16} />
                <span>Add Question</span>
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {questions.map((q, idx) => (
                <div 
                  key={idx}
                  style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-md)',
                    padding: '18px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <span style={{ fontWeight: 700, fontSize: '14px', color: 'var(--primary)' }}>
                      Question #{idx + 1}
                    </span>
                    {questions.length > 1 && (
                      <button
                        type="button"
                        className="btn btn-outline btn-sm"
                        style={{ padding: '4px 8px', color: '#f87171' }}
                        onClick={() => handleRemoveQuestion(idx)}
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>

                  <div style={{ marginBottom: '14px' }}>
                    <input
                      className="form-input"
                      placeholder="Type question prompt here..."
                      value={q.question_text}
                      onChange={(e) => handleQuestionChange(idx, 'question_text', e.target.value)}
                      required
                    />
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '14px' }}>
                    <div>
                      <span style={{ fontSize: '12px', color: 'var(--color-a)', fontWeight: 700 }}>Option A:</span>
                      <input
                        className="form-input"
                        placeholder="Option A text"
                        value={q.option_a}
                        onChange={(e) => handleQuestionChange(idx, 'option_a', e.target.value)}
                        required
                      />
                    </div>
                    <div>
                      <span style={{ fontSize: '12px', color: 'var(--color-b)', fontWeight: 700 }}>Option B:</span>
                      <input
                        className="form-input"
                        placeholder="Option B text"
                        value={q.option_b}
                        onChange={(e) => handleQuestionChange(idx, 'option_b', e.target.value)}
                        required
                      />
                    </div>
                    <div>
                      <span style={{ fontSize: '12px', color: 'var(--color-c)', fontWeight: 700 }}>Option C:</span>
                      <input
                        className="form-input"
                        placeholder="Option C text"
                        value={q.option_c}
                        onChange={(e) => handleQuestionChange(idx, 'option_c', e.target.value)}
                        required
                      />
                    </div>
                    <div>
                      <span style={{ fontSize: '12px', color: 'var(--color-d)', fontWeight: 700 }}>Option D:</span>
                      <input
                        className="form-input"
                        placeholder="Option D text"
                        value={q.option_d}
                        onChange={(e) => handleQuestionChange(idx, 'option_d', e.target.value)}
                        required
                      />
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>Correct Answer:</span>
                    {['A', 'B', 'C', 'D'].map((opt) => (
                      <label key={opt} style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '14px', fontWeight: 600 }}>
                        <input
                          type="radio"
                          name={`correct_${idx}`}
                          value={opt}
                          checked={q.correct_answer === opt}
                          onChange={() => handleQuestionChange(idx, 'correct_answer', opt)}
                        />
                        <span>{opt}</span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', flexWrap: 'wrap' }}>
            <button type="button" className="btn btn-outline" onClick={onClose}>
              Cancel
            </button>
            <button 
              id="save-quiz-submit-btn"
              type="submit" 
              className="btn btn-outline" 
              disabled={submitting}
              onClick={(e) => handleSubmit(e, false)}
            >
              {submitting ? 'Saving...' : 'Save Quiz Set'}
            </button>
            <button 
              id="save-and-launch-quiz-btn"
              type="button" 
              className="btn btn-success" 
              disabled={submitting}
              onClick={(e) => handleSubmit(e, true)}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            >
              {submitting ? <Loader2 size={16} className="spin" /> : <Play size={15} fill="currentColor" />}
              <span>Save &amp; Launch Live</span>
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
}
