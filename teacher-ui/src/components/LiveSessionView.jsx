/**
 * src/components/LiveSessionView.jsx
 * =====================================
 * Live quiz dashboard with:
 *  - Real browser camera (getUserMedia) for ArUco card detection
 *  - Per-student named answer list (name + card# + answer + correct/wrong)
 *  - Real-time WebSocket feed for answer counts / progress
 *  - Controls: pause/resume/end session, manual question navigation
 */
import React, {
  useCallback, useEffect, useRef, useState,
} from 'react';
import {
  Camera, CameraOff, ChevronLeft, ChevronRight, Loader2, Pause,
  Play, Radio, Square, Users, CheckCircle2, XCircle, AlertCircle,
  RefreshCcw, Wifi, WifiOff, Maximize2, Minimize2, Minus, X, Upload,
} from 'lucide-react';
import { api } from '../api/client';

// ── constants ──────────────────────────────────────────────────────────────
const ANSWER_COLORS = { A: '#3b82f6', B: '#a855f7', C: '#f59e0b', D: '#ef4444' };
const ANSWER_BG     = { A: 'rgba(59,130,246,0.12)', B: 'rgba(168,85,247,0.12)', C: 'rgba(245,158,11,0.12)', D: 'rgba(239,68,68,0.12)' };
const DETECT_MS     = 1800; // ms between frame captures

// ══════════════════════════════════════════════════════════════════════════════
// ══════════════════════════════════════════════════════════════════════════════
//  CameraWindow — Dedicated Floating / PiP Classroom Camera Window
//  Shows 100% of the camera field of view uncropped with live card detection
// ══════════════════════════════════════════════════════════════════════════════
function CameraWindow({
  active,
  sessionId,
  currentQuestion,
  submittedForQ,
  onDetections,
  isOpen = true,
  onClose,
}) {
  const videoRef     = useRef(null);
  const canvasRef    = useRef(null);
  const timerRef     = useRef(null);
  const streamRef    = useRef(null);
  const fileInputRef = useRef(null);

  const [camState, setCamState]             = useState('idle'); // idle | starting | live | error | denied
  const [lastDetections, setLastDetections] = useState([]);
  const [frameCount, setFrameCount]         = useState(0);
  const [photoScanning, setPhotoScanning]   = useState(false);
  const [scanMessage, setScanMessage]       = useState(null);
  const [isExpanded, setIsExpanded]         = useState(false);
  const [isMinimized, setIsMinimized]       = useState(false);
  const [cameras, setCameras]               = useState([]);   // available video devices
  const [selectedDeviceId, setSelectedDeviceId] = useState(''); // chosen camera
  const [errorDetail, setErrorDetail]       = useState('');

  // ── enumerate available cameras ────────────────────────────────────────
  const enumerateCameras = useCallback(async () => {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(d => d.kind === 'videoinput');
      setCameras(videoDevices);
      // Pick the environment-facing camera (rear cam) if available
      const envCam = videoDevices.find(d => /back|rear|environment/i.test(d.label));
      if (envCam && !selectedDeviceId) setSelectedDeviceId(envCam.deviceId);
    } catch (err) {
      // silently ignore
    }
  }, [selectedDeviceId]);

  // ── start camera ───────────────────────────────────────────────────────
  const startCamera = useCallback(async (deviceId) => {
    setCamState('starting');
    setErrorDetail('');
    try {
      // Build video constraints — prefer the chosen device, fall back to environment facing
      const videoConstraints = deviceId
        ? { deviceId: { exact: deviceId }, width: { ideal: 1920 }, height: { ideal: 1080 } }
        : { width: { ideal: 1920 }, height: { ideal: 1080 }, facingMode: { ideal: 'environment' } };

      const stream = await navigator.mediaDevices.getUserMedia({ video: videoConstraints, audio: false });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => {});
      }
      setCamState('live');
      // After permission is granted, refresh the camera list with real labels
      await enumerateCameras();
    } catch (err) {
      console.error('Camera access error:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setCamState('denied');
        setErrorDetail('Camera permission was denied. Please click the camera icon in your browser address bar and choose Allow, then click Retry.');
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setCamState('error');
        setErrorDetail('No camera found on this device. Connect a webcam or use Upload Photo.');
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        setCamState('error');
        setErrorDetail('Camera is in use by another app. Close other apps using the camera and retry.');
      } else {
        setCamState('error');
        setErrorDetail(err.message || 'Could not access camera.');
      }
    }
  }, [enumerateCameras]);

  // ── Auto-start camera when window opens ────────────────────────────────
  useEffect(() => {
    if (isOpen && camState === 'idle') {
      // Small delay so the window renders first, then auto-request
      const t = setTimeout(() => startCamera(selectedDeviceId), 400);
      return () => clearTimeout(t);
    }
  }, [isOpen]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Enumerate cameras on mount (labels may be empty until permission) ──
  useEffect(() => {
    enumerateCameras();
    // Also listen for device changes (user plugs in / out webcam)
    navigator.mediaDevices?.addEventListener?.('devicechange', enumerateCameras);
    return () => navigator.mediaDevices?.removeEventListener?.('devicechange', enumerateCameras);
  }, [enumerateCameras]);

  // ── stop camera ────────────────────────────────────────────────────────
  const stopCamera = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setLastDetections([]);
    setCamState('idle');
  }, []);

  // ── single frame/photo scanner function ───────────────────────────────
  const processFrameB64 = async (frame_b64, label = 'Snapshot') => {
    setPhotoScanning(true);
    setScanMessage(`Scanning ${label}...`);
    try {
      const result = await api.detectFrame(frame_b64);
      const dets = result?.detections || [];
      setLastDetections(dets);
      setFrameCount((c) => c + 1);
      onDetections(dets);
      setScanMessage(`Detected ${dets.length} card${dets.length === 1 ? '' : 's'}!`);
      setTimeout(() => setScanMessage(null), 3500);
    } catch (err) {
      setScanMessage(`Scan error: ${err.message || 'Failed to detect'}`);
      setTimeout(() => setScanMessage(null), 3500);
    } finally {
      setPhotoScanning(false);
    }
  };

  // ── snap photo from live camera ────────────────────────────────────────
  const snapRoomPhoto = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || !video.videoWidth) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    const frame_b64 = canvas.toDataURL('image/jpeg', 0.92);
    processFrameB64(frame_b64, 'Room Photo');
  };

  // ── handle file upload of room photo ──────────────────────────────────
  const handleUploadRoomPhoto = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const img = new Image();
      img.onload = () => {
        const canvas = canvasRef.current || document.createElement('canvas');
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0);
        const frame_b64 = canvas.toDataURL('image/jpeg', 0.90);
        processFrameB64(frame_b64, file.name);
      };
      img.src = event.target.result;
    };
    reader.readAsDataURL(file);
    e.target.value = '';
  };

  // ── continuous auto-detection loop ─────────────────────────────────────
  useEffect(() => {
    if (camState !== 'live') return;

    const capture = async () => {
      const video  = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas || !video.videoWidth) return;

      canvas.width  = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext('2d').drawImage(video, 0, 0);

      const frame_b64 = canvas.toDataURL('image/jpeg', 0.65);
      try {
        const result = await api.detectFrame(frame_b64);
        const dets = result?.detections || [];
        setLastDetections(dets);
        setFrameCount((c) => c + 1);
        onDetections(dets);
      } catch (err) {
        // silent loop
      }
    };

    timerRef.current = setInterval(capture, DETECT_MS);
    return () => clearInterval(timerRef.current);
  }, [camState, onDetections]);

  // cleanup on unmount
  useEffect(() => () => stopCamera(), [stopCamera]);

  if (!isOpen) return null;

  // ── Minimized Pill view ────────────────────────────────────────────────
  if (isMinimized) {
    return (
      <div
        className="classroom-camera-pill"
        onClick={() => setIsMinimized(false)}
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '28px',
          padding: '10px 18px',
          background: '#0d1322',
          border: '1px solid rgba(124, 58, 237, 0.45)',
          borderRadius: '9999px',
          boxShadow: '0 12px 32px rgba(0,0,0,0.45)',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          cursor: 'pointer',
          zIndex: 1000,
          color: '#fff',
          transition: 'all 0.2s ease',
        }}
        title="Click to expand camera preview window"
      >
        <span style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          background: camState === 'live' ? '#10b981' : '#94a3b8',
          boxShadow: camState === 'live' ? '0 0 8px #10b981' : 'none',
        }} />
        <Camera size={16} color="#8b5cf6" />
        <span style={{ fontSize: '13px', fontWeight: 600 }}>Classroom Camera</span>
        {lastDetections.length > 0 && (
          <span style={{
            fontSize: '11px',
            fontWeight: 700,
            background: 'rgba(124,58,237,0.3)',
            color: '#c4b5fd',
            padding: '2px 8px',
            borderRadius: '9999px',
          }}>
            {lastDetections.length} cards
          </span>
        )}
        <Maximize2 size={13} color="#94a3b8" style={{ marginLeft: '4px' }} />
      </div>
    );
  }

  // ── Full Camera Window view ───────────────────────────────────────────
  return (
    <aside
      aria-label="Classroom Camera Window"
      className="classroom-camera-floating-window"
      style={{
        position: 'fixed',
        bottom: '24px',
        right: '28px',
        width: isExpanded ? '640px' : '420px',
        maxWidth: 'calc(100vw - 48px)',
        background: '#0d1322',
        border: '1px solid rgba(255, 255, 255, 0.16)',
        borderRadius: '16px',
        boxShadow: '0 24px 60px rgba(0,0,0,0.55), 0 0 0 1px rgba(124,58,237,0.25)',
        zIndex: 1000,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        transition: 'width 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
      }}
    >
      {/* Window Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '10px 14px',
        background: 'rgba(255, 255, 255, 0.04)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        color: '#fff',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: camState === 'live' ? '#10b981' : '#94a3b8',
            boxShadow: camState === 'live' ? '0 0 8px #10b981' : 'none',
          }} />
          <Camera size={15} color="#8b5cf6" />
          <span style={{ fontSize: '13px', fontWeight: 700, letterSpacing: '-0.01em' }}>
            Camera Window
          </span>
          {camState === 'live' && (
            <span style={{ fontSize: '11px', color: '#94a3b8' }}>
              · {lastDetections.length} cards
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {/* Resize toggle */}
          <button
            onClick={() => setIsExpanded((e) => !e)}
            style={{
              background: 'none',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: '4px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
            }}
            title={isExpanded ? 'Normal size (420px)' : 'Expand size (640px)'}
          >
            {isExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>

          {/* Minimize to pill */}
          <button
            onClick={() => setIsMinimized(true)}
            style={{
              background: 'none',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: '4px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
            }}
            title="Minimize to corner pill"
          >
            <Minus size={14} />
          </button>

          {/* Close window */}
          <button
            onClick={() => {
              stopCamera();
              if (onClose) onClose();
            }}
            style={{
              background: 'none',
              border: 'none',
              color: '#f87171',
              cursor: 'pointer',
              padding: '4px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
            }}
            title="Close camera window"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {scanMessage && (
        <div style={{
          padding: '6px 14px',
          background: 'rgba(124,58,237,0.2)',
          borderBottom: '1px solid rgba(124,58,237,0.3)',
          color: '#c4b5fd',
          fontSize: '12px',
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
        }}>
          {photoScanning ? <Loader2 size={12} className="spin" /> : <CheckCircle2 size={12} color="#10b981" />}
          {scanMessage}
        </div>
      )}

      {/* Video stream container — strictly preserves 16:9 aspect ratio with ZERO cropping */}
      <div style={{
        position: 'relative',
        background: '#040711',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: '100%',
        aspectRatio: '16 / 9',
        overflow: 'hidden',
      }}>
        <canvas ref={canvasRef} style={{ display: 'none' }} />

        {camState === 'idle' && (
          <div style={{ textAlign: 'center', padding: '28px 20px', color: '#94a3b8' }}>
            <div style={{
              width: 56, height: 56, borderRadius: '50%',
              background: 'rgba(124,58,237,0.15)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 12px',
            }}>
              <Camera size={26} color="#8b5cf6" />
            </div>
            <p style={{ margin: '0 0 4px', fontSize: '14px', fontWeight: 700, color: '#e2e8f0' }}>Ready to scan</p>
            <p style={{ margin: '0 0 16px', fontSize: '12px', color: '#64748b' }}>Click below to start your classroom camera</p>
            <button
              className="btn btn-success btn-sm"
              onClick={() => startCamera(selectedDeviceId)}
              style={{ fontSize: '13px', padding: '8px 20px', fontWeight: 600, gap: '6px' }}
            >
              <Camera size={14} /> Start Camera
            </button>
            <p style={{ margin: '12px 0 0', fontSize: '11px', color: '#475569' }}>
              Your browser will ask to allow camera access — click <strong style={{color:'#a78bfa'}}>Allow</strong>
            </p>
          </div>
        )}

        {(camState === 'error' || camState === 'denied') && (
          <div style={{ textAlign: 'center', padding: '24px 20px', color: '#f87171' }}>
            <div style={{
              width: 48, height: 48, borderRadius: '50%',
              background: 'rgba(248,113,113,0.12)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 10px',
            }}>
              <AlertCircle size={24} />
            </div>
            <p style={{ margin: '0 0 6px', fontSize: '13px', fontWeight: 700 }}>
              {camState === 'denied' ? 'Camera Access Denied' : 'Camera Error'}
            </p>
            {errorDetail && (
              <p style={{ margin: '0 0 14px', fontSize: '11px', color: '#94a3b8', lineHeight: 1.5 }}>
                {errorDetail}
              </p>
            )}
            {camState === 'denied' && (
              <div style={{
                background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.25)',
                borderRadius: '8px', padding: '10px 12px', marginBottom: '14px', textAlign: 'left',
              }}>
                <p style={{ margin: '0 0 4px', fontSize: '11px', fontWeight: 700, color: '#fbbf24' }}>How to enable:</p>
                <ol style={{ margin: 0, paddingLeft: '16px', fontSize: '11px', color: '#94a3b8', lineHeight: 1.7 }}>
                  <li>Click the 🔒 or 📷 icon in your browser address bar</li>
                  <li>Set Camera to <strong style={{color:'#fbbf24'}}>Allow</strong></li>
                  <li>Reload the page, then click Retry</li>
                </ol>
              </div>
            )}
            <button
              className="btn btn-outline btn-sm"
              onClick={() => startCamera(selectedDeviceId)}
              style={{ fontSize: '12px', borderColor: '#f87171', color: '#f87171' }}
            >
              Retry
            </button>
          </div>
        )}

        {camState === 'starting' && (
          <div style={{ textAlign: 'center', padding: '28px 20px', color: '#94a3b8' }}>
            <Loader2 size={36} className="spin" color="#8b5cf6" style={{ margin: '0 auto 12px' }} />
            <p style={{ margin: '0 0 4px', fontSize: '13px', fontWeight: 600, color: '#e2e8f0' }}>Requesting camera access…</p>
            <p style={{ margin: 0, fontSize: '11px', color: '#64748b' }}>Allow the permission prompt in your browser</p>
          </div>
        )}

        <video
          ref={videoRef}
          muted
          playsInline
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            background: '#040711',
            display: camState === 'live' ? 'block' : 'none',
          }}
        />

        {/* Live detection badges on video feed */}
        {camState === 'live' && lastDetections.length > 0 && (
          <div style={{
            position: 'absolute',
            top: '8px',
            right: '8px',
            display: 'flex',
            flexDirection: 'column',
            gap: '4px',
            maxWidth: '180px',
            maxHeight: '80%',
            overflowY: 'auto',
          }}>
            {lastDetections.map((d) => (
              <div
                key={d.card_id}
                style={{
                  background: 'rgba(15, 23, 42, 0.85)',
                  border: `1px solid ${ANSWER_COLORS[d.answer] || '#7c3aed'}`,
                  borderRadius: '6px',
                  padding: '3px 8px',
                  fontSize: '11px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  color: '#fff',
                  backdropFilter: 'blur(4px)',
                }}
              >
                <span style={{ fontWeight: 800, color: ANSWER_COLORS[d.answer], minWidth: '16px' }}>
                  {d.answer}
                </span>
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {d.student_name}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Camera Device Selector */}
      {cameras.length > 1 && (
        <div style={{
          padding: '6px 14px',
          background: 'rgba(255,255,255,0.03)',
          borderTop: '1px solid rgba(255,255,255,0.07)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}>
          <Camera size={12} color="#8b5cf6" style={{ flexShrink: 0 }} />
          <select
            value={selectedDeviceId}
            onChange={(e) => {
              setSelectedDeviceId(e.target.value);
              stopCamera();
              setTimeout(() => startCamera(e.target.value), 200);
            }}
            style={{
              flex: 1,
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: '6px',
              color: '#e2e8f0',
              fontSize: '11px',
              padding: '4px 8px',
              cursor: 'pointer',
              outline: 'none',
            }}
            title="Switch camera"
          >
            {cameras.map((cam, i) => (
              <option key={cam.deviceId} value={cam.deviceId}>
                {cam.label || `Camera ${i + 1}`}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Bottom Controls inside Window */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '10px 14px',
        background: 'rgba(255, 255, 255, 0.03)',
        borderTop: '1px solid rgba(255, 255, 255, 0.08)',
        gap: '8px',
      }}>
        {/* Upload file button */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          style={{ display: 'none' }}
          onChange={handleUploadRoomPhoto}
        />
        <button
          className="btn btn-outline btn-sm"
          onClick={() => fileInputRef.current?.click()}
          disabled={photoScanning}
          title="Upload a classroom photo taken from your phone"
          style={{
            fontSize: '12px',
            padding: '6px 12px',
            borderColor: 'rgba(255,255,255,0.2)',
            color: '#fff',
            background: 'rgba(255,255,255,0.05)',
          }}
        >
          {photoScanning ? <Loader2 size={12} className="spin" /> : <Upload size={12} />}
          Upload Photo
        </button>

        {camState === 'live' ? (
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              className="btn btn-primary btn-sm"
              onClick={snapRoomPhoto}
              disabled={photoScanning}
              style={{ fontSize: '12px', padding: '6px 14px' }}
              title="Snap high-resolution photo from camera"
            >
              📸 Snap Photo
            </button>
            <button
              className="btn btn-outline btn-sm"
              onClick={stopCamera}
              style={{ fontSize: '12px', padding: '6px 10px', borderColor: '#f87171', color: '#f87171' }}
              title="Pause camera"
            >
              <CameraOff size={12} />
            </button>
          </div>
        ) : (
          <button
            className="btn btn-success btn-sm"
            onClick={startCamera}
            disabled={camState === 'starting'}
            style={{ fontSize: '12px', padding: '6px 14px' }}
          >
            <Camera size={12} /> Open Live Cam
          </button>
        )}
      </div>
    </aside>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
//  StudentAnswerPanel — per-student named answers for current question
// ══════════════════════════════════════════════════════════════════════════════
function StudentAnswerPanel({ students, currentQuestion, sessionResponses, liveDetections }) {
  if (!currentQuestion) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-dim)', fontSize: '14px' }}>
        No active question
      </div>
    );
  }

  const correctAnswer = currentQuestion.correct_answer;

  // Build map: card_id → latest detection
  const detectionMap = {};
  liveDetections.forEach((d) => { detectionMap[d.card_id] = d; });

  // Build rows combining DB students with live detections
  const detectedNotInRoster = [];
  const seenCardIds = new Set();

  const rosterRows = students.map((stu) => {
    const cardId = stu.card_number || stu.card_id;
    if (cardId) seenCardIds.add(cardId);
    const det = cardId ? detectionMap[cardId] : null;
    const resp = sessionResponses.find(
      (r) => r.student_id === stu.id && r.question_id === currentQuestion.id
    );
    const answer = resp?.answer || det?.answer || null;
    const isCorrect = answer && answer.toUpperCase() === correctAnswer?.toUpperCase();
    const confidence = det?.confidence;
    return { stu, cardId, answer, isCorrect, confidence, source: resp ? 'stored' : det ? 'live' : null };
  });

  // Detections for cards not in DB roster
  Object.values(detectionMap).forEach((d) => {
    if (!seenCardIds.has(d.card_id)) {
      detectedNotInRoster.push(d);
    }
  });

  const hasKey    = Boolean(correctAnswer);
  const answered  = rosterRows.filter((r) => r.answer).length;
  const correct   = hasKey ? rosterRows.filter((r) => r.isCorrect).length : 0;
  const wrong     = hasKey ? answered - correct : 0;
  const total     = rosterRows.length + detectedNotInRoster.length;

  return (
    <div>
      {/* summary bar */}
      <div style={{ display: 'flex', gap: '16px', marginBottom: '12px', flexWrap: 'wrap' }}>
        <Stat label="Answered" value={`${answered}/${total}`} color="#6ee7b7" />
        {hasKey ? (
          <>
            <Stat label="Correct" value={correct} color="#6ee7b7" />
            <Stat label="Wrong" value={wrong} color="#f87171" />
            <Stat label="Correct Key" value={correctAnswer} color={ANSWER_COLORS[correctAnswer]} />
          </>
        ) : (
          <>
            <Stat label="Recorded" value={answered} color="#818cf8" />
            <Stat label="Answer Key" value="Pending" color="#f59e0b" />
          </>
        )}
      </div>

      {/* roster rows */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '420px', overflowY: 'auto' }}>
        {rosterRows.map(({ stu, cardId, answer, isCorrect, confidence, source }) => (
          <StudentRow
            key={stu.id}
            name={`${stu.first_name} ${stu.last_name}`}
            cardId={cardId}
            answer={answer}
            isCorrect={isCorrect}
            correctAnswer={correctAnswer}
            confidence={confidence}
            source={source}
          />
        ))}
        {/* un-rostered detections */}
        {detectedNotInRoster.map((d) => (
          <StudentRow
            key={`det-${d.card_id}`}
            name={d.student_name || `Card #${d.card_id}`}
            cardId={d.card_id}
            answer={d.answer}
            isCorrect={d.answer?.toUpperCase() === correctAnswer?.toUpperCase()}
            correctAnswer={correctAnswer}
            confidence={d.confidence}
            source="live"
            unrostered
          />
        ))}
        {total === 0 && (
          <div style={{ textAlign: 'center', padding: '24px', color: 'var(--text-dim)', fontSize: '13px' }}>
            No students found. Point camera at student cards.
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value, color }) {
  return (
    <div style={{ flex: 1, minWidth: '60px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', padding: '8px 12px', border: '1px solid var(--border-subtle)' }}>
      <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>{label}</div>
      <div style={{ fontSize: '18px', fontWeight: 800, color }}>{value}</div>
    </div>
  );
}

function StudentRow({ name, cardId, answer, isCorrect, correctAnswer, confidence, source, unrostered }) {
  const hasKey = Boolean(correctAnswer);
  const bg = answer
    ? hasKey
      ? isCorrect
        ? 'rgba(16,185,129,0.06)'
        : 'rgba(239,68,68,0.06)'
      : 'rgba(99,102,241,0.06)'
    : 'transparent';

  const borderColor = answer
    ? hasKey
      ? isCorrect
        ? 'rgba(16,185,129,0.25)'
        : 'rgba(239,68,68,0.25)'
      : 'rgba(99,102,241,0.25)'
    : 'var(--border-subtle)';

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '28px 1fr 44px 44px auto',
      alignItems: 'center',
      gap: '8px',
      padding: '8px 12px',
      borderRadius: 'var(--radius-sm)',
      border: `1px solid ${borderColor}`,
      background: bg,
      opacity: unrostered ? 0.75 : 1,
    }}>
      {/* card# */}
      <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--primary)', textAlign: 'center' }}>
        {cardId ? `#${cardId}` : '-'}
      </span>

      {/* name */}
      <span style={{ fontSize: '14px', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {name}
        {unrostered && <span style={{ fontSize: '10px', color: '#f59e0b', marginLeft: '4px' }}>(not in roster)</span>}
      </span>

      {/* answer badge */}
      {answer ? (
        <span style={{
          width: '34px', height: '34px',
          borderRadius: '8px',
          background: ANSWER_BG[answer] || 'rgba(100,100,100,0.1)',
          border: `2px solid ${ANSWER_COLORS[answer] || '#555'}`,
          color: ANSWER_COLORS[answer] || '#aaa',
          fontWeight: 800, fontSize: '15px',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          {answer}
        </span>
      ) : (
        <span style={{ width: '34px', height: '34px', borderRadius: '8px', border: '2px dashed var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)', fontSize: '11px' }}>
          -
        </span>
      )}

      {/* correct/wrong or recorded pending */}
      {answer ? (
        hasKey ? (
          isCorrect
            ? <CheckCircle2 size={18} color="#10b981" />
            : <XCircle size={18} color="#ef4444" />
        ) : (
          <CheckCircle2 size={16} color="#818cf8" title="Response recorded. Answer key pending." />
        )
      ) : <span style={{ width: '18px' }} />}

      {/* source + confidence */}
      <span style={{ fontSize: '11px', color: 'var(--text-dim)', textAlign: 'right', minWidth: '70px', display: 'inline-flex', alignItems: 'center', justifyContent: 'flex-end', gap: '4px' }}>
        {source === 'live' && confidence != null ? (
          <>
            <Camera size={11} color="var(--primary)" />
            <span>{confidence.toFixed(0)}%</span>
          </>
        ) : source === 'stored' ? (
          <span style={{ color: 'var(--success)', fontWeight: 600 }}>Saved</span>
        ) : ''}
      </span>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
//  AnswerBar — visual A/B/C/D count bar
// ══════════════════════════════════════════════════════════════════════════════
function AnswerBar({ counts, total }) {
  const opts = ['A', 'B', 'C', 'D'];
  return (
    <div style={{ display: 'flex', gap: '8px', height: '56px', alignItems: 'flex-end' }}>
      {opts.map((opt) => {
        const n   = counts?.[opt] || 0;
        const pct = total > 0 ? (n / total) * 100 : 0;
        return (
          <div key={opt} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px' }}>
            <span style={{ fontSize: '12px', fontWeight: 700, color: ANSWER_COLORS[opt] }}>{n}</span>
            <div style={{ width: '100%', height: `${Math.max(pct, 4)}%`, background: ANSWER_COLORS[opt], borderRadius: '4px 4px 0 0', minHeight: '4px', maxHeight: '36px', transition: 'height 0.4s ease' }} />
            <span style={{ fontSize: '11px', fontWeight: 700, color: ANSWER_COLORS[opt] }}>{opt}</span>
          </div>
        );
      })}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
//  Main LiveSessionView
// ══════════════════════════════════════════════════════════════════════════════
export function LiveSessionView({ session, onEnd, onBack }) {
  const [questions, setQuestions]           = useState([]);
  const [students, setStudents]             = useState([]);
  const [currentQIdx, setCurrentQIdx]       = useState(0);
  const [sessionStatus, setSessionStatus]   = useState(session?.status || 'pending');
  const [dashboard, setDashboard]           = useState(null);
  const [wsConnected, setWsConnected]       = useState(false);
  const [sessionResponses, setSessionResponses] = useState([]);
  const [liveDetections, setLiveDetections] = useState([]);
  const [loading, setLoading]               = useState(true);
  const [error, setError]                   = useState(null);
  const [activeTab, setActiveTab]           = useState('camera'); // 'camera' | 'students'
  const [camWindowOpen, setCamWindowOpen]   = useState(true);

  const wsRef            = useRef(null);
  const autoSubmittedRef = useRef(new Set()); // track `${question_id}:${card_id}` already submitted

  const sessionId    = session?.id;
  const currentQ     = questions[currentQIdx] || null;

  // ── Load questions + students ─────────────────────────────────────────
  useEffect(() => {
    if (!sessionId) return;

    const loadData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [sess, db] = await Promise.all([
          api.getQuizSession(sessionId),
          api.getQuizDashboard(sessionId).catch(() => null),
        ]);

        const qsId = sess?.question_set_id || session?.question_set_id;
        const classId = sess?.class_id || session?.class_id;

        const [qs, stuList] = await Promise.all([
          qsId ? api.getQuestionSet(qsId).catch(() => null) : Promise.resolve(null),
          classId ? api.getStudents({ class_id: classId }).catch(() => []) : api.getStudents().catch(() => []),
        ]);

        let loadedQuestions = qs?.questions || [];
        if ((!loadedQuestions || loadedQuestions.length === 0) && qsId) {
          try {
            loadedQuestions = await api.getQuestions(qsId);
          } catch (e) {
            console.warn("Falling back to getQuestions:", e);
          }
        }

        setQuestions(loadedQuestions || []);
        setStudents(Array.isArray(stuList) ? stuList : []);
        setSessionStatus((sess?.status || 'pending').toLowerCase());
        setDashboard(db);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [sessionId]);

  // ── WebSocket for real-time events ───────────────────────────────────
  useEffect(() => {
    if (!sessionId) return;
    const token = api.getToken();
    const wsUrl = `/ws/quiz/${sessionId}?token=${encodeURIComponent(token || '')}`;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}${wsUrl}`);
    wsRef.current = ws;

    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);
    ws.onerror = () => setWsConnected(false);
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.event === 'response') {
          setDashboard((prev) => ({
            ...(prev || {}),
            responses_received: msg.data.responses_received,
            total_students: msg.data.total_students,
            answer_counts: msg.data.answer_counts,
          }));
          // Add to sessionResponses for the student panel
          setSessionResponses((prev) => [
            ...prev.filter(
              (r) => !(r.student_id === msg.data.student_id && r.question_id === currentQ?.id)
            ),
            {
              student_id: msg.data.student_id,
              question_id: currentQ?.id,
              answer: msg.data.answer,
              is_correct: msg.data.is_correct,
            },
          ]);
        } else if (msg.event === 'session_ended') {
          setSessionStatus('ended');
        }
      } catch (_) {}
    };

    return () => ws.close();
  }, [sessionId]);

  // ── Auto-submit detections for current question ───────────────────────
  const handleDetections = useCallback(
    (detections) => {
      setLiveDetections(detections);
      if (!currentQ || (sessionStatus || '').toLowerCase() !== 'active') return;

      detections.forEach(async (d) => {
        const key = `${currentQ.id}:${d.card_id}`;
        if (autoSubmittedRef.current.has(key)) return;
        autoSubmittedRef.current.add(key);

        try {
          await api.submitScannerResponse({
            quiz_session_id: sessionId,
            question_id: currentQ.id,
            marker_id: d.card_id,
            rotation: d.rotation || 0,
            answer: d.answer,
            detected_at: new Date().toISOString(),
          });
        } catch (err) {
          // 409 duplicate — clear key so next question won't be blocked
          if (err?.status !== 409) {
            autoSubmittedRef.current.delete(key);
          }
        }
      });
    },
    [currentQ, sessionId, sessionStatus]
  );

  // ── Session controls ──────────────────────────────────────────────────
  const handleStart = async () => {
    try {
      await api.startQuizSession(sessionId);
      setSessionStatus('active');
    } catch (err) { alert(err.message); }
  };

  const handlePause = async () => {
    try {
      await api.pauseQuizSession(sessionId);
      setSessionStatus('paused');
    } catch (err) { alert(err.message); }
  };

  const handleResume = async () => {
    try {
      await api.resumeQuizSession(sessionId);
      setSessionStatus('active');
    } catch (err) { alert(err.message); }
  };

  const handleEnd = async () => {
    if (!window.confirm('End this quiz session?')) return;
    try {
      await api.endQuizSession(sessionId);
      setSessionStatus('ended');
      onEnd?.();   // → goes to Results view
    } catch (err) { alert(err.message); }
  };

  const nextQuestion = () => {
    setCurrentQIdx((i) => Math.min(i + 1, questions.length - 1));
    setLiveDetections([]);
  };

  const prevQuestion = () => {
    setCurrentQIdx((i) => Math.max(i - 1, 0));
    setLiveDetections([]);
  };

  // ── Set or change correct answer on the fly (for dictated questions or future reveal) ──
  const handleSetCorrectAnswer = async (opt) => {
    if (!currentQ) return;
    const qsId = currentQ.question_set_id || session?.question_set_id;
    if (!qsId) return;

    // Toggle: if clicking current answer, clear it (null); otherwise set to opt
    const newAnswer = currentQ.correct_answer === opt ? null : opt;

    try {
      await api.updateQuestion(qsId, currentQ.id, {
        correct_answer: newAnswer,
      });

      // Update question in local state
      setQuestions((prev) =>
        prev.map((q) => (q.id === currentQ.id ? { ...q, correct_answer: newAnswer } : q))
      );

      // Recalculate local responses is_correct
      setSessionResponses((prev) =>
        prev.map((r) => {
          if (r.question_id === currentQ.id) {
            return {
              ...r,
              is_correct: newAnswer ? r.answer?.toUpperCase() === newAnswer.toUpperCase() : false,
            };
          }
          return r;
        })
      );
    } catch (err) {
      console.error('Failed to update question answer key:', err);
      alert('Could not update answer key: ' + (err.message || err));
    }
  };

  // ── Loading / Error ───────────────────────────────────────────────────
  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh', flexDirection: 'column', gap: '16px' }}>
        <Loader2 size={40} className="spin" />
        <p>Loading quiz session…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh', flexDirection: 'column', gap: '16px' }}>
        <AlertCircle size={40} color="#f87171" />
        <p style={{ color: '#f87171' }}>{error}</p>
        <p style={{ fontSize: '13px', color: 'var(--text-dim)' }}>Session may have ended or doesn't exist.</p>
        <button className="btn btn-outline btn-sm" onClick={onBack || onEnd}>← Back to Dashboard</button>
      </div>
    );
  }

  const answeredCount  = dashboard?.responses_received || 0;
  const totalStudents  = dashboard?.total_students || students.length || 1;
  const answerCounts   = dashboard?.answer_counts || {};
  const progressPct    = Math.round((answeredCount / totalStudents) * 100);

  return (
    <div className="live-session-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '20px', minHeight: 'calc(100vh - 120px)' }}>

      {/* ── Left column: camera + question nav ── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

        {/* Status / control bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {/* status chip */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '8px 16px', borderRadius: '100px',
            background: sessionStatus === 'active' ? 'rgba(16,185,129,0.15)'
              : sessionStatus === 'paused' ? 'rgba(245,158,11,0.15)'
              : 'rgba(100,100,120,0.15)',
            border: `1px solid ${sessionStatus === 'active' ? 'rgba(16,185,129,0.4)' : sessionStatus === 'paused' ? 'rgba(245,158,11,0.4)' : 'rgba(100,100,120,0.3)'}`,
          }}>
            <Radio size={14} color={sessionStatus === 'active' ? '#10b981' : sessionStatus === 'paused' ? '#f59e0b' : '#666'} />
            <span style={{ fontWeight: 700, fontSize: '13px', textTransform: 'capitalize' }}>{sessionStatus}</span>
          </div>

          {/* WS indicator */}
          {wsConnected
            ? <Wifi size={16} color="#10b981" title="WebSocket connected" />
            : <WifiOff size={16} color="#666" title="WebSocket disconnected" />
          }

          <span style={{ fontSize: '13px', color: 'var(--text-muted)', marginLeft: '4px' }}>
            Session #{sessionId}
          </span>

          {/* spacer */}
          <div style={{ flex: 1 }} />

          {/* controls */}
          {sessionStatus === 'pending' && (
            <button id="start-session-btn" className="btn btn-success btn-sm" onClick={handleStart}>
              <Play size={14} /> Start Quiz
            </button>
          )}
          {sessionStatus === 'active' && (
            <button id="pause-session-btn" className="btn btn-outline btn-sm" onClick={handlePause}>
              <Pause size={14} /> Pause
            </button>
          )}
          {sessionStatus === 'paused' && (
            <button id="resume-session-btn" className="btn btn-success btn-sm" onClick={handleResume}>
              <Play size={14} /> Resume
            </button>
          )}
          {(sessionStatus === 'active' || sessionStatus === 'paused') && (
            <button id="end-session-btn" className="btn btn-danger btn-sm" onClick={handleEnd}>
              <Square size={14} /> End
            </button>
          )}
          <button
            className="btn btn-outline btn-sm"
            onClick={() => setCamWindowOpen((o) => !o)}
            style={{
              borderColor: camWindowOpen ? 'var(--primary)' : 'var(--border-subtle)',
              color: camWindowOpen ? 'var(--primary)' : 'inherit',
              background: camWindowOpen ? 'rgba(124, 58, 237, 0.08)' : 'transparent',
              fontWeight: 600,
            }}
            title="Toggle camera window"
          >
            <Camera size={14} />
            {camWindowOpen ? 'Cam Window Open' : 'Open Cam Window'}
          </button>
          <button className="btn btn-outline btn-sm" onClick={onBack || onEnd}>← Dashboard</button>
        </div>

        {/* Floating / PiP Camera Window */}
        <CameraWindow
          isOpen={camWindowOpen}
          onClose={() => setCamWindowOpen(false)}
          active={sessionStatus === 'active'}
          sessionId={sessionId}
          currentQuestion={currentQ}
          submittedForQ={autoSubmittedRef.current}
          onDetections={handleDetections}
        />

        {/* Question navigator */}
        {questions.length > 0 && (
          <div style={{ background: 'var(--bg-elevated)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-subtle)', padding: '20px' }}>
            {/* nav controls */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <button
                className="btn btn-outline btn-sm"
                onClick={prevQuestion}
                disabled={currentQIdx === 0}
                id="prev-question-btn"
              >
                <ChevronLeft size={16} />
              </button>
              <span style={{ fontWeight: 700, flex: 1, textAlign: 'center', fontSize: '14px' }}>
                Q{currentQIdx + 1} of {questions.length}
              </span>
              <button
                className="btn btn-outline btn-sm"
                onClick={nextQuestion}
                disabled={currentQIdx >= questions.length - 1}
                id="next-question-btn"
              >
                <ChevronRight size={16} />
              </button>
            </div>

            {/* question card */}
            {currentQ && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
                  <p style={{ fontWeight: 600, fontSize: '16px', margin: 0 }}>
                    {currentQ.question_text || `Question ${currentQIdx + 1} (Oral / Dictated)`}
                  </p>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {currentQ.correct_answer ? (
                      <span style={{
                        fontSize: '12px', fontWeight: 700,
                        color: ANSWER_COLORS[currentQ.correct_answer],
                        background: ANSWER_BG[currentQ.correct_answer],
                        padding: '4px 10px', borderRadius: 'var(--radius-sm)',
                        border: `1px solid ${ANSWER_COLORS[currentQ.correct_answer]}44`,
                        display: 'flex', alignItems: 'center', gap: '6px'
                      }}>
                        <CheckCircle2 size={13} />
                        Key: Option {currentQ.correct_answer} (click to change)
                      </span>
                    ) : (
                      <span style={{
                        fontSize: '12px', fontWeight: 600,
                        color: '#f59e0b',
                        background: 'rgba(245,158,11,0.12)',
                        padding: '4px 10px', borderRadius: 'var(--radius-sm)',
                        border: '1px solid rgba(245,158,11,0.3)',
                        display: 'flex', alignItems: 'center', gap: '6px'
                      }}>
                        🎤 Oral: Key Pending (Click option A-D to set/reveal)
                      </span>
                    )}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  {['A', 'B', 'C', 'D'].map((opt) => {
                    const text = currentQ[`option_${opt.toLowerCase()}`] || `Option ${opt}`;
                    const isCorrect = opt === currentQ.correct_answer?.toUpperCase();
                    return (
                      <div
                        key={opt}
                        onClick={() => handleSetCorrectAnswer(opt)}
                        title={isCorrect ? `Option ${opt} is correct key. Click to unset.` : `Click to set Option ${opt} as correct answer`}
                        style={{
                          display: 'flex', alignItems: 'center', gap: '10px',
                          padding: '10px 14px',
                          borderRadius: 'var(--radius-md)',
                          border: `2px solid ${isCorrect ? ANSWER_COLORS[opt] : 'var(--border-subtle)'}`,
                          background: isCorrect ? ANSWER_BG[opt] : 'transparent',
                          cursor: 'pointer',
                          transition: 'all 0.15s ease',
                          boxShadow: isCorrect ? `0 2px 10px ${ANSWER_COLORS[opt]}25` : 'none',
                        }}
                      >
                        <span style={{
                          fontWeight: 800, fontSize: '15px', color: isCorrect ? '#fff' : ANSWER_COLORS[opt],
                          background: isCorrect ? ANSWER_COLORS[opt] : 'transparent',
                          width: '28px', height: '28px', borderRadius: '6px',
                          display: 'flex', alignItems: 'center', justifyContent: 'center'
                        }}>
                          {opt}
                        </span>
                        <span style={{ fontSize: '13px', flex: 1, fontWeight: isCorrect ? 600 : 400 }}>{text}</span>
                        {isCorrect ? (
                          <CheckCircle2 size={18} color={ANSWER_COLORS[opt]} />
                        ) : (
                          <span style={{ fontSize: '11px', color: 'var(--text-dim)', opacity: 0.7 }}>Set Key</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* dot bar for all questions */}
            <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginTop: '14px' }}>
              {questions.map((q, idx) => (
                <button
                  key={q.id}
                  onClick={() => { setCurrentQIdx(idx); setLiveDetections([]); }}
                  style={{
                    width: '28px', height: '28px',
                    borderRadius: '6px',
                    border: `2px solid ${idx === currentQIdx ? 'var(--primary)' : 'var(--border-subtle)'}`,
                    background: idx === currentQIdx ? 'var(--primary)' : 'transparent',
                    color: idx === currentQIdx ? '#fff' : 'var(--text-muted)',
                    fontSize: '12px', fontWeight: 700, cursor: 'pointer',
                  }}
                >
                  {idx + 1}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Progress bar */}
        <div style={{ background: 'var(--bg-elevated)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-subtle)', padding: '16px 20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '13px' }}>
            <span style={{ fontWeight: 600 }}>
              <Users size={14} style={{ verticalAlign: 'middle', marginRight: '4px' }} />
              Responses
            </span>
            <span style={{ color: 'var(--text-muted)' }}>{answeredCount} / {totalStudents}</span>
          </div>
          <div style={{ height: '8px', background: 'var(--bg-card)', borderRadius: '100px', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${progressPct}%`, background: 'linear-gradient(90deg, var(--primary), #818cf8)', borderRadius: '100px', transition: 'width 0.5s ease' }} />
          </div>
          <div style={{ marginTop: '12px' }}>
            <AnswerBar counts={answerCounts} total={answeredCount} />
          </div>
        </div>
      </div>

      {/* ── Right column: student answers ── */}
      <div style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0' }}>
        <div style={{ background: 'var(--bg-elevated)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-subtle)', overflow: 'hidden', flex: 1 }}>
          {/* tabs */}
          <div style={{ display: 'flex', borderBottom: '1px solid var(--border-subtle)' }}>
            {[
              { id: 'students', label: 'Student Answers', icon: <Users size={14} /> },
              { id: 'camera', label: 'Live Detections', icon: <Camera size={14} /> },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  flex: 1,
                  padding: '12px 8px',
                  background: activeTab === tab.id ? 'var(--bg-card)' : 'transparent',
                  borderBottom: activeTab === tab.id ? '2px solid var(--primary)' : '2px solid transparent',
                  color: activeTab === tab.id ? 'var(--primary)' : 'var(--text-dim)',
                  fontWeight: activeTab === tab.id ? 700 : 500,
                  fontSize: '13px',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                  cursor: 'pointer', border: 'none',
                  borderBottom: activeTab === tab.id ? '2px solid var(--primary)' : '2px solid transparent',
                  transition: 'all 0.2s',
                }}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>

          <div style={{ padding: '16px' }}>
            {activeTab === 'students' ? (
              <StudentAnswerPanel
                students={students}
                currentQuestion={currentQ}
                sessionResponses={sessionResponses}
                liveDetections={liveDetections}
              />
            ) : (
              <div>
                {liveDetections.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--text-dim)', fontSize: '13px' }}>
                    <Camera size={32} style={{ marginBottom: '8px', opacity: 0.4 }} />
                    <p>No cards detected yet.<br />Open the camera and point it at student cards.</p>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {liveDetections.map((d) => (
                      <div
                        key={d.card_id}
                        style={{
                          display: 'flex', alignItems: 'center', gap: '10px',
                          padding: '10px 14px',
                          borderRadius: 'var(--radius-md)',
                          background: ANSWER_BG[d.answer] || 'var(--bg-card)',
                          border: `1px solid ${ANSWER_COLORS[d.answer] || 'var(--border-subtle)'}`,
                        }}
                      >
                        <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--primary)', minWidth: '30px' }}>
                          #{d.card_id}
                        </span>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontWeight: 600, fontSize: '14px' }}>{d.student_name}</div>
                          {d.student_code && <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>{d.student_code}</div>}
                        </div>
                        <div style={{
                          width: '36px', height: '36px',
                          borderRadius: '8px',
                          background: ANSWER_BG[d.answer],
                          border: `2px solid ${ANSWER_COLORS[d.answer]}`,
                          color: ANSWER_COLORS[d.answer],
                          fontWeight: 800, fontSize: '16px',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          boxShadow: `0 0 8px ${ANSWER_COLORS[d.answer]}66`,
                        }}>
                          {d.answer}
                        </div>
                        <div style={{ textAlign: 'right', fontSize: '11px', color: 'var(--text-dim)' }}>
                          <div>{d.confidence?.toFixed(0)}%</div>
                          <div style={{ color: '#6ee7b7' }}>live</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
