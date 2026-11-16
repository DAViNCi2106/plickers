/**
 * src/components/RosterView.jsx
 * Class Roster Manager — view, edit, add, delete students and import/export via CSV.
 */
import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Users, Plus, Upload, Download, Search, Edit2, Trash2,
  Save, X, CheckCircle2, AlertCircle, Loader2, RefreshCw,
  CreditCard, ChevronUp, ChevronDown,
} from "lucide-react";
import { api } from "../api/client";

const initials = (f, l) =>
  ((f?.[0] || "").toUpperCase() + (l?.[0] || "").toUpperCase());
const PALETTE = ["#6366f1","#8b5cf6","#ec4899","#14b8a6","#f59e0b","#10b981","#3b82f6","#ef4444"];
const avatarColor = (id) => PALETTE[id % PALETTE.length];

const inputStyle = {
  background:"var(--bg-card)", border:"1px solid var(--border-subtle)",
  borderRadius:"var(--radius-sm)", padding:"6px 10px",
  color:"var(--text-primary)", fontSize:"13px", outline:"none", minWidth:"80px",
};
const labelSt = {
  display:"block", fontSize:"11px", fontWeight:600, color:"var(--text-muted)",
  marginBottom:"4px", textTransform:"uppercase", letterSpacing:"0.5px",
};

function Toast({ msg, type = "success", onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 3500); return () => clearTimeout(t); }, [onClose]);
  const col = type === "success" ? "#10b981" : type === "error" ? "#ef4444" : "#f59e0b";
  return (
    <div style={{ position:"fixed", bottom:"24px", right:"24px", zIndex:9999,
      display:"flex", alignItems:"center", gap:"10px",
      background:"var(--bg-elevated)", border:`1px solid ${col}`,
      borderLeft:`4px solid ${col}`, borderRadius:"var(--radius-md)",
      padding:"14px 20px", boxShadow:"0 8px 32px rgba(0,0,0,0.4)", maxWidth:"360px" }}>
      {type === "success" ? <CheckCircle2 size={18} color={col}/> : <AlertCircle size={18} color={col}/>}
      <span style={{ fontSize:"14px", color:"var(--text-primary)" }}>{msg}</span>
      <button onClick={onClose} style={{ background:"none", border:"none", cursor:"pointer", marginLeft:"auto", color:"var(--text-dim)" }}><X size={14}/></button>
    </div>
  );
}

function StudentRow({ student, card, onEdit, onDelete }) {
  return (
    <tr style={{ borderBottom:"1px solid var(--border-subtle)", transition:"background 0.15s" }}
      onMouseEnter={e => e.currentTarget.style.background="rgba(255,255,255,0.03)"}
      onMouseLeave={e => e.currentTarget.style.background="transparent"}>
      <td style={{ padding:"12px 16px" }}>
        <div style={{ display:"flex", alignItems:"center", gap:"12px" }}>
          <div style={{ width:"38px", height:"38px", borderRadius:"50%", background:avatarColor(student.id),
            display:"flex", alignItems:"center", justifyContent:"center",
            fontSize:"14px", fontWeight:700, color:"#fff", flexShrink:0,
            boxShadow:`0 2px 8px ${avatarColor(student.id)}55` }}>
            {initials(student.first_name, student.last_name)}
          </div>
          <span style={{ fontWeight:600, fontSize:"14px" }}>{student.first_name} {student.last_name}</span>
        </div>
      </td>
      <td style={{ padding:"12px 16px" }}>
        <code style={{ fontSize:"12px", color:"var(--primary)", background:"rgba(99,102,241,0.1)", padding:"3px 8px", borderRadius:"6px" }}>
          {student.student_code}
        </code>
      </td>
      <td style={{ padding:"12px 16px", color:"var(--text-muted)", fontSize:"13px" }}>
        {student.roll_number || <span style={{ color:"var(--text-dim)" }}>-</span>}
      </td>
      <td style={{ padding:"12px 16px", fontSize:"13px", color:"var(--text-muted)" }}>
        {student.email || <span style={{ color:"var(--text-dim)" }}>-</span>}
      </td>
      <td style={{ padding:"12px 16px" }}>
        {card ? (
          <span style={{ display:"inline-flex", alignItems:"center", gap:"5px", padding:"4px 10px",
            borderRadius:"20px", background:"rgba(16,185,129,0.1)", border:"1px solid rgba(16,185,129,0.3)",
            fontSize:"12px", fontWeight:700, color:"#10b981" }}>
            <CreditCard size={11}/> #{card.card_number}
          </span>
        ) : (
          <span style={{ display:"inline-flex", alignItems:"center", gap:"5px", padding:"4px 10px",
            borderRadius:"20px", background:"rgba(239,68,68,0.08)", border:"1px solid rgba(239,68,68,0.2)",
            fontSize:"12px", color:"#f87171" }}>No card</span>
        )}
      </td>
      <td style={{ padding:"12px 16px" }}>
        <div style={{ display:"flex", gap:"6px" }}>
          <button className="btn btn-outline btn-sm" onClick={onEdit} title="Edit" style={{ padding:"5px 10px" }}>
            <Edit2 size={13}/>
          </button>
          <button className="btn btn-outline btn-sm" onClick={onDelete} title="Delete"
            style={{ padding:"5px 10px", borderColor:"rgba(239,68,68,0.3)", color:"#f87171" }}>
            <Trash2 size={13}/>
          </button>
        </div>
      </td>
    </tr>
  );
}

function EditRow({ student, cardInfo, onSave, onCancel }) {
  const [form, setForm] = useState({
    first_name: student.first_name, last_name: student.last_name,
    roll_number: student.roll_number || "", email: student.email || "",
  });
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  return (
    <tr style={{ background:"rgba(99,102,241,0.06)", borderBottom:"1px solid var(--border-subtle)" }}>
      <td style={{ padding:"8px 12px" }}>
        <div style={{ display:"flex", alignItems:"center", gap:"10px" }}>
          <div style={{ width:"34px", height:"34px", borderRadius:"50%", background:avatarColor(student.id),
            display:"flex", alignItems:"center", justifyContent:"center",
            fontSize:"13px", fontWeight:700, color:"#fff", flexShrink:0 }}>
            {initials(form.first_name, form.last_name)}
          </div>
          <div style={{ display:"flex", gap:"6px", flex:1 }}>
            <input value={form.first_name} onChange={e => set("first_name", e.target.value)}
              placeholder="First name" style={{ ...inputStyle, flex:1 }}/>
            <input value={form.last_name} onChange={e => set("last_name", e.target.value)}
              placeholder="Last name" style={{ ...inputStyle, flex:1 }}/>
          </div>
        </div>
      </td>
      <td style={{ padding:"8px 12px" }}>
        <span style={{ fontSize:"12px", color:"var(--text-dim)", fontFamily:"monospace" }}>{student.student_code}</span>
      </td>
      <td style={{ padding:"8px 12px" }}>
        <input value={form.roll_number} onChange={e => set("roll_number", e.target.value)}
          placeholder="Roll #" type="number" style={{ ...inputStyle, width:"70px" }}/>
      </td>
      <td style={{ padding:"8px 12px" }}>
        <input value={form.email} onChange={e => set("email", e.target.value)}
          placeholder="email@school.com" type="email" style={{ ...inputStyle, width:"180px" }}/>
      </td>
      <td style={{ padding:"8px 12px" }}>
        <span style={{ display:"inline-flex", alignItems:"center", gap:"4px", padding:"4px 10px",
          borderRadius:"20px", background:"rgba(99,102,241,0.12)", border:"1px solid rgba(99,102,241,0.3)",
          fontSize:"12px", fontWeight:700, color:"#818cf8" }}>
          <CreditCard size={11}/> #{cardInfo?.card_number || "-"}
        </span>
      </td>
      <td style={{ padding:"8px 12px" }}>
        <div style={{ display:"flex", gap:"6px" }}>
          <button className="btn btn-success btn-sm" onClick={() => onSave(student.id, form)}>
            <Save size={13}/> Save
          </button>
          <button className="btn btn-outline btn-sm" onClick={onCancel}><X size={13}/> Cancel</button>
        </div>
      </td>
    </tr>
  );
}

function AddStudentForm({ existingCount, usedCards, onAdd, onCancel }) {
  const nextCode = `STU${String(existingCount + 1).padStart(3, "0")}`;
  const [form, setForm] = useState({
    first_name:"", last_name:"", student_code:nextCode,
    roll_number:"", email:"", card_number:"",
  });
  const [loading, setLoading] = useState(false);
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const conflict = usedCards.includes(Number(form.card_number)) && form.card_number;
  const submit = async () => {
    if (!form.first_name || !form.last_name) return;
    setLoading(true);
    await onAdd(form);
    setLoading(false);
  };
  return (
    <div style={{ margin:"16px 0", background:"rgba(99,102,241,0.06)", border:"1px solid rgba(99,102,241,0.25)", borderRadius:"var(--radius-md)", padding:"20px 24px" }}>
      <h4 style={{ margin:"0 0 16px", fontSize:"14px", fontWeight:700, color:"var(--primary)", display:"flex", alignItems:"center", gap:"6px" }}>
        <Plus size={14}/> Add New Student
      </h4>
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 130px 90px 1fr 140px", gap:"12px", alignItems:"start" }}>
        <div><label style={labelSt}>First Name *</label>
          <input value={form.first_name} onChange={e => set("first_name", e.target.value)} placeholder="e.g. Priya" style={{ ...inputStyle, width:"100%" }} autoFocus/></div>
        <div><label style={labelSt}>Last Name *</label>
          <input value={form.last_name} onChange={e => set("last_name", e.target.value)} placeholder="e.g. Sharma" style={{ ...inputStyle, width:"100%" }}/></div>
        <div><label style={labelSt}>Student Code</label>
          <input value={form.student_code} onChange={e => set("student_code", e.target.value)} placeholder="STU051" style={{ ...inputStyle, width:"100%" }}/></div>
        <div><label style={labelSt}>Roll #</label>
          <input value={form.roll_number} onChange={e => set("roll_number", e.target.value)} placeholder="51" type="number" style={{ ...inputStyle, width:"100%" }}/></div>
        <div><label style={labelSt}>Email (optional)</label>
          <input value={form.email} onChange={e => set("email", e.target.value)} placeholder="student@school.com" type="email" style={{ ...inputStyle, width:"100%" }}/></div>
        <div><label style={labelSt}>Card # (1-249)</label>
          <input value={form.card_number} onChange={e => set("card_number", e.target.value)} placeholder="e.g. 51" type="number" min="1" max="249"
            style={{ ...inputStyle, width:"100%", borderColor:conflict ? "#ef4444" : undefined }}/>
          {conflict && <span style={{ fontSize:"11px", color:"#ef4444", display:"block", marginTop:"2px" }}>Already assigned</span>}
        </div>
      </div>
      <div style={{ marginTop:"16px", display:"flex", gap:"10px" }}>
        <button className="btn btn-primary btn-sm" onClick={submit} disabled={loading || !form.first_name || !form.last_name || conflict}>
          {loading ? <Loader2 size={14} className="spin"/> : <Plus size={14}/>} Add Student
        </button>
        <button className="btn btn-outline btn-sm" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

function CSVImportModal({ onClose, onDone }) {
  const fileRef = useRef();
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const handleFile = (f) => {
    if (!f) return;
    if (!f.name.match(/\.(csv|xlsx|xls)$/i)) { setError("Only .csv, .xlsx or .xls accepted"); return; }
    setFile(f); setError(null); setResult(null);
  };
  const doImport = async () => {
    if (!file) return;
    setLoading(true); setError(null);
    try { const res = await api.importStudentsCSV(file); setResult(res); }
    catch (err) { setError(err.message || "Import failed"); }
    finally { setLoading(false); }
  };
  const dlTemplate = () => {
    const csv = "S.No,Student Name,Student ID,Card ID\n1,Priya Sharma,STU051,51\n2,Arjun Patel,STU052,52\n";
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type:"text/csv" }));
    a.download = "plickers_template.csv"; a.click();
  };
  return (
    <div style={{ position:"fixed", inset:0, zIndex:1000, background:"rgba(0,0,0,0.7)",
      display:"flex", alignItems:"center", justifyContent:"center", backdropFilter:"blur(4px)" }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={{ background:"var(--bg-card)", borderRadius:"var(--radius-lg)", border:"1px solid var(--border-subtle)",
        width:"560px", padding:"32px", boxShadow:"0 24px 80px rgba(0,0,0,0.6)" }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"24px" }}>
          <div>
            <h3 style={{ margin:0, fontSize:"18px", fontWeight:800, display:"flex", alignItems:"center", gap:"8px" }}>
              <Upload size={18} color="var(--primary)"/> Import Students from CSV
            </h3>
            <p style={{ margin:"4px 0 0", fontSize:"13px", color:"var(--text-muted)" }}>Bulk-add students from a spreadsheet</p>
          </div>
          <button onClick={onClose} style={{ background:"none", border:"none", cursor:"pointer", color:"var(--text-dim)" }}><X size={20}/></button>
        </div>
        <div style={{ background:"rgba(99,102,241,0.08)", border:"1px solid rgba(99,102,241,0.2)", borderRadius:"var(--radius-sm)", padding:"12px 16px", marginBottom:"20px", display:"flex", alignItems:"center", justifyContent:"space-between" }}>
          <div>
            <p style={{ margin:0, fontSize:"13px", fontWeight:600 }}>Download Template (.csv / .xlsx)</p>
            <p style={{ margin:"2px 0 0", fontSize:"12px", color:"var(--text-muted)" }}>Supports "Student Name", "Roll No". Unique Plicker Cards are automatically allotted!</p>
          </div>
          <button className="btn btn-outline btn-sm" onClick={dlTemplate}><Download size={13}/> Template</button>
        </div>
        <div style={{ border:`2px dashed ${dragOver ? "var(--primary)" : "var(--border-subtle)"}`,
          borderRadius:"var(--radius-md)", padding:"40px 20px", textAlign:"center", cursor:"pointer",
          transition:"all 0.2s", background:dragOver ? "rgba(99,102,241,0.05)" : "transparent", marginBottom:"20px" }}
          onDragOver={e => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={e => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files[0]); }}
          onClick={() => fileRef.current?.click()}>
          <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls" style={{ display:"none" }} onChange={e => handleFile(e.target.files[0])}/>
          {file ? (
            <div><CheckCircle2 size={32} color="#10b981" style={{ marginBottom:"8px" }}/>
              <p style={{ margin:0, fontWeight:700, fontSize:"15px" }}>{file.name}</p>
              <p style={{ margin:"4px 0 0", fontSize:"12px", color:"var(--text-muted)" }}>{(file.size/1024).toFixed(1)} KB</p>
            </div>
          ) : (
            <div><Upload size={32} color="var(--text-dim)" style={{ marginBottom:"8px" }}/>
              <p style={{ margin:0, fontWeight:600 }}>Drop file here or click to browse</p>
              <p style={{ margin:"4px 0 0", fontSize:"12px", color:"var(--text-muted)" }}>Supports .csv, .xlsx, .xls</p>
            </div>
          )}
        </div>
        {error && (
          <div style={{ padding:"12px 16px", background:"rgba(239,68,68,0.1)", border:"1px solid rgba(239,68,68,0.3)", borderRadius:"var(--radius-sm)", marginBottom:"16px", display:"flex", gap:"8px", alignItems:"center" }}>
            <AlertCircle size={16} color="#ef4444"/>
            <span style={{ fontSize:"13px", color:"#ef4444" }}>{error}</span>
          </div>
        )}
        {result && (
          <div style={{ padding:"16px", background:"rgba(16,185,129,0.08)", border:"1px solid rgba(16,185,129,0.3)", borderRadius:"var(--radius-sm)", marginBottom:"16px" }}>
            <p style={{ margin:0, fontWeight:700, color:"#10b981", fontSize:"15px" }}>Import Complete!</p>
            <div style={{ display:"flex", gap:"24px", marginTop:"8px", fontSize:"13px" }}>
              <span>Successful: <strong>{result.successful}</strong></span>
              <span>Failed: <strong>{result.failed}</strong></span>
              <span>Skipped: <strong>{result.skipped}</strong></span>
            </div>
            {result.errors?.length > 0 && (
              <ul style={{ margin:"8px 0 0", padding:"0 0 0 16px", fontSize:"12px", color:"#f87171" }}>
                {result.errors.slice(0,5).map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            )}
          </div>
        )}
        <div style={{ display:"flex", gap:"10px", justifyContent:"flex-end" }}>
          <button className="btn btn-outline" onClick={onClose}>{result ? "Close" : "Cancel"}</button>
          {!result && (
            <button className="btn btn-primary" onClick={doImport} disabled={!file || loading}>
              {loading ? <Loader2 size={15} className="spin"/> : <Upload size={15}/>}
              {loading ? "Importing..." : "Import Students"}
            </button>
          )}
          {result && (
            <button className="btn btn-success" onClick={() => { onDone(); onClose(); }}>
              <RefreshCw size={15}/> Refresh Roster
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export function RosterView() {
  const [students, setStudents]   = useState([]);
  const [cards, setCards]         = useState([]);
  const [cardMap, setCardMap]     = useState({});
  const [loading, setLoading]     = useState(true);
  const [saving, setSaving]       = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [showAdd, setShowAdd]     = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [toast, setToast]         = useState(null);
  const [search, setSearch]       = useState("");
  const [sortKey, setSortKey]     = useState("student_code");
  const [sortDir, setSortDir]     = useState("asc");
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [deleting, setDeleting]   = useState(null);

  const showToast = (msg, type = "success") => setToast({ msg, type });

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [stuList, cardList] = await Promise.all([api.getStudents(), api.getCards()]);
      let assignments = [];
      try { assignments = await api.getCardAssignments(); } catch {}
      setStudents(stuList); setCards(cardList);
      const map = {};
      assignments.forEach(a => { if (a.is_active) map[a.student_id] = a.card; });
      if (assignments.length === 0 && cardList.length > 0) {
        stuList.forEach((s, idx) => {
          const c = cardList.find(c => c.card_number === idx+1 || c.marker_id === idx+1);
          if (c) map[s.id] = c;
        });
      }
      setCardMap(map);
    } catch (err) { showToast("Failed to load: " + err.message, "error"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const filtered = students
    .filter(s => {
      const q = search.toLowerCase();
      return s.first_name.toLowerCase().includes(q) || s.last_name.toLowerCase().includes(q) ||
        s.student_code.toLowerCase().includes(q) || (s.email||"").toLowerCase().includes(q) ||
        String(s.roll_number||"").includes(q);
    })
    .sort((a, b) => {
      let va = a[sortKey]??"", vb = b[sortKey]??"";
      if (typeof va==="string") va=va.toLowerCase();
      if (typeof vb==="string") vb=vb.toLowerCase();
      return va < vb ? (sortDir==="asc"?-1:1) : va > vb ? (sortDir==="asc"?1:-1) : 0;
    });

  const toggleSort = (key) => {
    if (sortKey===key) setSortDir(d => d==="asc"?"desc":"asc");
    else { setSortKey(key); setSortDir("asc"); }
  };

  const SortIcon = ({ col }) => sortKey!==col
    ? <ChevronUp size={12} style={{ opacity:0.2 }}/>
    : sortDir==="asc" ? <ChevronUp size={12} color="var(--primary)"/> : <ChevronDown size={12} color="var(--primary)"/>;

  const handleSave = async (studentId, form) => {
    setSaving(studentId);
    try {
      const payload = {
        first_name: form.first_name, last_name: form.last_name,
        ...(form.roll_number ? { roll_number: Number(form.roll_number) } : {}),
        ...(form.email ? { email: form.email } : {}),
      };
      const updated = await api.updateStudent(studentId, payload);
      setStudents(prev => prev.map(s => s.id===studentId ? { ...s, ...updated } : s));
      setEditingId(null);
      showToast(`Updated ${form.first_name} ${form.last_name}`);
    } catch (err) { showToast("Save failed: " + err.message, "error"); }
    finally { setSaving(null); }
  };

  const handleAdd = async (form) => {
    try {
      const payload = {
        first_name: form.first_name, last_name: form.last_name,
        student_code: form.student_code,
        ...(form.roll_number ? { roll_number: Number(form.roll_number) } : {}),
        ...(form.email ? { email: form.email } : {}),
      };
      const newStu = await api.createStudent(payload);
      if (form.card_number) {
        const num = Number(form.card_number);
        try {
          let card = cards.find(c => c.card_number===num);
          if (!card) card = await api.createCard(num);
          await api.assignCard(card.id, newStu.id);
          setCardMap(prev => ({ ...prev, [newStu.id]: card }));
        } catch (err) { showToast("Student added but card failed: "+err.message, "warning"); }
      }
      setStudents(prev => [...prev, newStu]);
      setShowAdd(false);
      showToast(`Added ${newStu.first_name} ${newStu.last_name}`);
    } catch (err) { showToast("Failed: "+err.message, "error"); }
  };

  const handleDelete = async (studentId) => {
    setDeleting(studentId);
    try {
      await api.deleteStudent(studentId);
      setStudents(prev => prev.filter(s => s.id!==studentId));
      setConfirmDelete(null);
      showToast("Student removed");
    } catch (err) { showToast("Delete failed: "+err.message, "error"); }
    finally { setDeleting(null); }
  };

  const exportCSV = () => {
    const header = "S.No,Student Name,Student ID,Card ID,Roll No,Email";
    const rows = students.map((s, i) => {
      const c = cardMap[s.id];
      return `${i+1},"${s.first_name} ${s.last_name}",${s.student_code},${c?.card_number||""},${s.roll_number||""},${s.email||""}`;
    });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([[header,...rows].join("\n")], { type:"text/csv" }));
    a.download = `plickers_roster_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    showToast("Exported CSV");
  };

  const usedCardNums = Object.values(cardMap).map(c => c?.card_number).filter(Boolean);

  if (loading) return (
    <div style={{ display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", height:"60vh", gap:"16px" }}>
      <Loader2 size={40} className="spin" color="var(--primary)"/>
      <p style={{ color:"var(--text-muted)" }}>Loading class roster...</p>
    </div>
  );

  return (
    <div style={{ padding:"24px 28px", maxWidth:"1200px", margin:"0 auto" }}>
      {/* Header */}
      <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", marginBottom:"24px", flexWrap:"wrap", gap:"12px" }}>
        <div>
          <h1 style={{ margin:0, fontSize:"24px", fontWeight:800, display:"flex", alignItems:"center", gap:"10px" }}>
            <Users size={26} color="var(--primary)"/> Class Roster
          </h1>
          <p style={{ margin:"4px 0 0", color:"var(--text-muted)", fontSize:"14px" }}>
            {students.length} students enrolled &middot; {Object.keys(cardMap).length} cards assigned
          </p>
        </div>
        <div style={{ display:"flex", gap:"10px", flexWrap:"wrap" }}>
          <button className="btn btn-outline btn-sm" onClick={loadData}><RefreshCw size={14}/> Refresh</button>
          <a
            href="http://127.0.0.1:8000/api/v1/cards/pdf"
            target="_blank"
            rel="noreferrer"
            className="btn btn-outline btn-sm"
            style={{ textDecoration: 'none', borderColor: '#10b981', color: '#10b981', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
            title="Download printable cards PDF to distribute to students"
          >
            <Download size={14}/> Printable Cards PDF
          </a>
          <button className="btn btn-outline btn-sm" onClick={exportCSV}><Download size={14}/> Export CSV</button>
          <button className="btn btn-outline btn-sm" onClick={() => setShowImport(true)}><Upload size={14}/> Import Excel/CSV</button>
          <button className="btn btn-primary btn-sm" onClick={() => { setShowAdd(true); setEditingId(null); }}>
            <Plus size={14}/> Add Student
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="roster-stats-grid" style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit, minmax(180px, 1fr))", gap:"14px", marginBottom:"24px" }}>
        {[
          { label:"Total Students", value:students.length, color:"var(--primary)" },
          { label:"Cards Assigned", value:Object.keys(cardMap).length, color:"#10b981" },
          { label:"Without Cards", value:students.length - Object.keys(cardMap).length, color:"#f59e0b" },
          { label:"Active Cards", value:cards.filter(c => c.status==="active").length, color:"#6366f1" },
        ].map(stat => (
          <div key={stat.label} style={{ background:"var(--bg-card)", borderRadius:"var(--radius-md)", border:"1px solid var(--border-subtle)", padding:"16px 20px" }}>
            <div style={{ fontSize:"11px", color:"var(--text-muted)", fontWeight:600, textTransform:"uppercase", letterSpacing:"0.5px" }}>{stat.label}</div>
            <div style={{ fontSize:"28px", fontWeight:800, color:stat.color, marginTop:"4px" }}>{stat.value}</div>
          </div>
        ))}
      </div>

      {/* Search */}
      <div style={{ display:"flex", gap:"12px", marginBottom:"16px", alignItems:"center", flexWrap:"wrap" }}>
        <div style={{ position:"relative", flex:1, minWidth:"200px" }}>
          <Search size={15} style={{ position:"absolute", left:"12px", top:"50%", transform:"translateY(-50%)", color:"var(--text-dim)" }}/>
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search by name, code, email or roll number..."
            style={{ ...inputStyle, paddingLeft:"36px", width:"100%", fontSize:"14px", padding:"10px 12px 10px 36px" }}/>
        </div>
        {search && <button className="btn btn-outline btn-sm" onClick={() => setSearch("")}><X size={13}/> Clear</button>}
        <span style={{ fontSize:"13px", color:"var(--text-muted)", whiteSpace:"nowrap" }}>{filtered.length} / {students.length}</span>
      </div>

      {/* Add form */}
      {showAdd && (
        <AddStudentForm existingCount={students.length} usedCards={usedCardNums}
          onAdd={handleAdd} onCancel={() => setShowAdd(false)}/>
      )}

      {/* Table */}
      <div className="table-responsive" style={{ background:"var(--bg-card)", borderRadius:"var(--radius-lg)", border:"1px solid var(--border-subtle)", overflowX:"auto", position:"relative" }}>
        {confirmDelete && (
          <div style={{ position:"absolute", inset:0, zIndex:100, background:"rgba(0,0,0,0.6)", display:"flex", alignItems:"center", justifyContent:"center" }}>
            <div style={{ background:"var(--bg-elevated)", borderRadius:"var(--radius-md)", border:"1px solid var(--border-subtle)", padding:"28px", maxWidth:"360px", textAlign:"center" }}>
              <AlertCircle size={36} color="#ef4444" style={{ marginBottom:"12px" }}/>
              <h3 style={{ margin:"0 0 8px" }}>Delete Student?</h3>
              <p style={{ margin:"0 0 20px", color:"var(--text-muted)", fontSize:"14px" }}>
                Remove <strong>{confirmDelete.first_name} {confirmDelete.last_name}</strong>? This cannot be undone.
              </p>
              <div style={{ display:"flex", gap:"10px", justifyContent:"center" }}>
                <button className="btn btn-outline" onClick={() => setConfirmDelete(null)}>Cancel</button>
                <button className="btn btn-danger" onClick={() => handleDelete(confirmDelete.id)} disabled={deleting===confirmDelete.id}>
                  {deleting===confirmDelete.id ? <Loader2 size={14} className="spin"/> : <Trash2 size={14}/>} Delete
                </button>
              </div>
            </div>
          </div>
        )}
        <table style={{ width:"100%", borderCollapse:"collapse" }}>
          <thead>
            <tr style={{ borderBottom:"1px solid var(--border-subtle)", background:"var(--bg-elevated)" }}>
              {[{key:"first_name",label:"Student Name"},{key:"student_code",label:"Code"},{key:"roll_number",label:"Roll #"},{key:"email",label:"Email"},{key:null,label:"Card"},{key:null,label:"Actions"}].map(col => (
                <th key={col.label} onClick={() => col.key && toggleSort(col.key)}
                  style={{ padding:"12px 16px", textAlign:"left", fontSize:"11px", fontWeight:700, textTransform:"uppercase", letterSpacing:"0.6px", color:"var(--text-muted)", cursor:col.key?"pointer":"default", userSelect:"none", whiteSpace:"nowrap" }}>
                  <span style={{ display:"flex", alignItems:"center", gap:"4px" }}>
                    {col.label}{col.key && <SortIcon col={col.key}/>}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ padding:"60px 20px", textAlign:"center", color:"var(--text-dim)" }}>
                  <Users size={36} style={{ opacity:0.3, display:"block", margin:"0 auto 12px" }}/>
                  <p style={{ margin:0, fontSize:"15px" }}>
                    {search ? "No students match your search" : "No students yet. Add a student or import from CSV"}
                  </p>
                </td>
              </tr>
            ) : (
              filtered.map(student =>
                editingId === student.id ? (
                  <EditRow key={student.id} student={student} cardInfo={cardMap[student.id]}
                    onSave={handleSave} onCancel={() => setEditingId(null)}/>
                ) : (
                  <StudentRow key={student.id} student={student} card={cardMap[student.id]}
                    onEdit={() => { setEditingId(student.id); setShowAdd(false); }}
                    onDelete={() => setConfirmDelete(student)}/>
                )
              )
            )}
          </tbody>
        </table>
      </div>

      {showImport && <CSVImportModal onClose={() => setShowImport(false)} onDone={loadData}/>}
      {toast && <Toast msg={toast.msg} type={toast.type} onClose={() => setToast(null)}/>}
    </div>
  );
}
