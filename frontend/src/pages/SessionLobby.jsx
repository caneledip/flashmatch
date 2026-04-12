import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { api, getToken } from '../api';
import { useWebSocket } from '../useWebSocket';

export default function SessionLobby() {
  const { state } = useLocation();
  const navigate = useNavigate();
  const pin = state?.pin;
  const [playerCount, setPlayerCount] = useState(0);
  const [players, setPlayers] = useState([]);
  const [error, setError] = useState('');

  const { connect, send, disconnect } = useWebSocket((msg) => {
    switch (msg.type) {
      case 'host_connected':
        setPlayerCount(msg.player_count);
        break;
      case 'player_joined':
        setPlayerCount(msg.player_count);
        setPlayers((prev) => [...prev, msg.display_name]);
        break;
      case 'question_start':
        navigate('/session/game', { state: { pin, question: msg } });
        break;
      case 'error':
        setError(msg.message);
        break;
    }
  });

  useEffect(() => {
    if (!pin) { navigate('/dashboard'); return; }
    const ws = connect();
    if (ws) {
      ws.onopen = () => {
        send({ type: 'host_connect', pin, token: getToken() });
      };
    }
    return () => disconnect();
  }, [pin]);

  async function startQuiz() {
    try {
      await api.startSession(pin);
    } catch (e) {
      setError(e.message);
    }
  }

  if (!pin) return null;

  return (
    <div style={styles.wrap}>
      <h2>Session Lobby</h2>
      <div style={styles.pinBox}>
        <div style={{ fontSize: 14, color: '#aaa' }}>Game PIN</div>
        <div style={{ fontSize: 56, fontWeight: 900, letterSpacing: 8 }}>{pin}</div>
      </div>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <p>Players joined: <strong>{playerCount}</strong></p>
      <ul style={{ textAlign: 'left', maxWidth: 300, margin: '0 auto 24px' }}>
        {players.map((p, i) => <li key={i}>{p}</li>)}
      </ul>
      <button style={styles.btn} onClick={startQuiz} disabled={playerCount === 0}>
        Start Quiz ▶
      </button>
    </div>
  );
}

const styles = {
  wrap: { maxWidth: 500, margin: '10vh auto', fontFamily: 'sans-serif', padding: 24, textAlign: 'center' },
  pinBox: { background: '#222', color: '#fff', borderRadius: 12, padding: '24px 40px', margin: '24px 0', display: 'inline-block' },
  btn: { padding: '14px 32px', fontSize: 18, background: '#1a7f37', color: '#fff', border: 'none', borderRadius: 8, cursor: 'pointer' },
};
