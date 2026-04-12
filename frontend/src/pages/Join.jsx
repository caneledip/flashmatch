import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useWebSocket } from '../useWebSocket';

export default function Join() {
  const [pin, setPin] = useState('');
  const [name, setName] = useState('');
  const [joined, setJoined] = useState(false);
  const [playerCount, setPlayerCount] = useState(0);
  const [question, setQuestion] = useState(null);
  const [answer, setAnswer] = useState('');
  const [feedback, setFeedback] = useState(null);
  const [leaderboard, setLeaderboard] = useState(null);
  const [finished, setFinished] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const { connect, send, disconnect } = useWebSocket((msg) => {
    switch (msg.type) {
      case 'player_joined':
        setPlayerCount(msg.player_count);
        break;
      case 'question_start':
        setQuestion(msg);
        setFeedback(null);
        setAnswer('');
        setLeaderboard(null);
        break;
      case 'answer_received':
        break;
      case 'question_end':
        setFeedback(msg);
        break;
      case 'leaderboard':
        setLeaderboard(msg.rankings);
        break;
      case 'session_finished':
        setFinished(true);
        setLeaderboard(msg.final_rankings);
        disconnect();
        break;
      case 'error':
        setError(msg.message);
        break;
    }
  });

  function joinSession(e) {
    e.preventDefault();
    if (!pin || !name) return;
    setError('');
    const ws = connect();
    if (!ws) return;
    ws.onopen = () => {
      send({ type: 'join_session', pin, display_name: name });
      setJoined(true);
    };
  }

  function submitAnswer(e) {
    e.preventDefault();
    send({ type: 'submit_answer', pin, answer });
  }

  if (finished) {
    return (
      <div style={styles.wrap}>
        <h2>🏆 Final Scoreboard</h2>
        {leaderboard?.map((p) => (
          <div key={p.display_name} style={styles.row}>
            <span>#{p.rank} {p.display_name}</span>
            <strong>{p.score} pts</strong>
          </div>
        ))}
      </div>
    );
  }

  if (!joined) {
    return (
      <div style={styles.wrap}>
        <h2>Join a Game</h2>
        {error && <p style={{ color: 'red' }}>{error}</p>}
        <form onSubmit={joinSession}>
          <input style={styles.input} placeholder="6-digit PIN" value={pin} maxLength={6}
            onChange={(e) => setPin(e.target.value)} />
          <input style={styles.input} placeholder="Your name" value={name}
            onChange={(e) => setName(e.target.value)} />
          <button style={styles.btn} type="submit">Join</button>
        </form>
      </div>
    );
  }

  if (!question) {
    return (
      <div style={styles.wrap}>
        <h2>Waiting for host to start…</h2>
        <p>Players joined: {playerCount}</p>
      </div>
    );
  }

  return (
    <div style={styles.wrap}>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <h3>Question {question.index + 1}</h3>
      <p style={{ fontSize: 28, fontWeight: 700 }}>{question.term}</p>

      {feedback ? (
        <div>
          <p>Correct answer: <strong>{feedback.correct_answer}</strong></p>
          {leaderboard && (
            <>
              <h4>Leaderboard</h4>
              {leaderboard.map((p) => (
                <div key={p.display_name} style={styles.row}>
                  <span>#{p.rank} {p.display_name}</span>
                  <strong>{p.score} pts</strong>
                </div>
              ))}
            </>
          )}
        </div>
      ) : (
        <form onSubmit={submitAnswer}>
          <input style={styles.input} placeholder="Type the definition…" value={answer}
            onChange={(e) => setAnswer(e.target.value)} />
          <button style={styles.btn} type="submit">Submit</button>
        </form>
      )}
    </div>
  );
}

const styles = {
  wrap: { maxWidth: 480, margin: '10vh auto', fontFamily: 'sans-serif', padding: 24 },
  input: { display: 'block', width: '100%', padding: 10, marginBottom: 12, fontSize: 16, boxSizing: 'border-box' },
  btn: { padding: '10px 24px', fontSize: 16, background: '#333', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' },
  row: { display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #eee' },
};
