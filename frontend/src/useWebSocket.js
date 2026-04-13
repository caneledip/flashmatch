import { useEffect, useRef, useCallback } from 'react';

export function useWebSocket(onMessage) {
  const wsRef = useRef(null);
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  const connect = useCallback(() => {
    if (wsRef.current) return;
    const ws = new WebSocket(`ws://${window.location.host}/ws/session`);
    wsRef.current = ws;

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        onMessageRef.current(msg);
      } catch { /* ignore */ }
    };

    // Guard: only clear the ref if this specific WS is still the current one.
    // Without this, a stale onclose from a previous WS (closed by StrictMode cleanup)
    // will null out the ref for the NEW connection, breaking all subsequent sends.
    ws.onclose = () => {
      if (wsRef.current === ws) {
        wsRef.current = null;
      }
    };

    return ws;
  }, []);

  const send = useCallback((msg) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  useEffect(() => () => disconnect(), [disconnect]);

  return { connect, send, disconnect };
}
