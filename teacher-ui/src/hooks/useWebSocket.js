/**
 * src/hooks/useWebSocket.js
 * =========================
 * Live real-time WebSocket connection to the quiz session.
 */

import { useState, useEffect, useRef, useCallback } from 'react';

export function useQuizWebSocket(sessionId, schoolId) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState(null);
  const [responses, setResponses] = useState({}); // student_id -> response object
  const [answerCounts, setAnswerCounts] = useState({ A: 0, B: 0, C: 0, D: 0 });
  const [stats, setStats] = useState({ total_students: 0, responses_received: 0 });
  const [error, setError] = useState(null);

  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const pingIntervalRef = useRef(null);

  const connect = useCallback(() => {
    if (!sessionId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Backend mount: /api/v1/schools/{school_id}/quiz-sessions/ws/quiz/{quiz_session_id}
    const schoolParam = schoolId || 1;
    const wsUrl = `${protocol}//${window.location.host}/api/v1/schools/${schoolParam}/quiz-sessions/ws/quiz/${sessionId}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        // Start ping heartbeat every 20s
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 20000);
      };

      ws.onmessage = (event) => {
        try {
          if (event.data === 'pong') return;
          const msg = JSON.parse(event.data);
          setLastEvent(msg);

          if (msg.event === 'response' && msg.data) {
            const data = msg.data;
            setResponses((prev) => ({
              ...prev,
              [data.student_id]: data,
            }));
            if (data.answer_counts) {
              setAnswerCounts(data.answer_counts);
            }
            if (data.responses_received !== undefined) {
              setStats({
                total_students: data.total_students,
                responses_received: data.responses_received,
              });
            }
          } else if (msg.event === 'dashboard' && msg.data) {
            if (msg.data.answer_counts) setAnswerCounts(msg.data.answer_counts);
            if (msg.data.responses) {
              const respMap = {};
              msg.data.responses.forEach((r) => {
                respMap[r.student_id] = r;
              });
              setResponses(respMap);
            }
          }
        } catch (err) {
          console.error('[WS PARSE ERROR]', err);
        }
      };

      ws.onerror = (err) => {
        console.warn('[WS ERROR]', err);
        setError('WebSocket error');
      };

      ws.onclose = () => {
        setIsConnected(false);
        clearInterval(pingIntervalRef.current);
        // Attempt reconnect after 3 seconds if still on active session
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 3000);
      };
    } catch (err) {
      console.error('[WS CONNECT FAILED]', err);
      setError(err.message);
    }
  }, [sessionId, schoolId]);

  useEffect(() => {
    connect();

    return () => {
      clearTimeout(reconnectTimeoutRef.current);
      clearInterval(pingIntervalRef.current);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const resetResponses = useCallback(() => {
    setResponses({});
    setAnswerCounts({ A: 0, B: 0, C: 0, D: 0 });
  }, []);

  return {
    isConnected,
    lastEvent,
    responses,
    setResponses,
    answerCounts,
    setAnswerCounts,
    stats,
    error,
    resetResponses,
  };
}
