import { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { getToken } from '../api';
import { useWebSocket } from '../useWebSocket';

export default function SessionGame() {
  const { state } = useLocation();
  const navigate = useNavigate();
  const pin = state?.pin;
  const initialQuestion = state?.question;

  const [question, setQuestion] = useState(initialQuestion);
  const [timeLeft, setTimeLeft] = useState(initialQuestion?.time_limit ?? 20);
  const [answeredCount, setAnsweredCount] = useState(0);
  const [totalPlayers, setTotalPlayers] = useState(0);
  const [feedback, setFeedback] = useState(null);
  const [leaderboard, setLeaderboard] = useState(null);
  const [finished, setFinished] = useState(false);
  const [error, setError] = useState('');
  const timerRef = useRef(null);

  const { connect, send, disconnect } = useWebSocket((msg) => {
    switch (msg.type) {
      case 'host_connected':
        break;
      case 'question_start':
        setQuestion(msg);
        setTimeLeft(msg.time_limit);
        setAnsweredCount(0);
        setFeedback(null);
        setLeaderboard(null);
        startTimer(msg.time_limit);
        break;
      case 'answer_received':
        setAnsweredCount(msg.answered_count);
        setTotalPlayers(msg.total);
        break;
      case 'question_end':
        clearInterval(timerRef.current);
        setFeedback(msg);
        break;
      case 'leaderboard':
        setLeaderboard(msg.rankings);
        break;
      case 'session_finished':
        setFinished(true);
        setLeaderboard(msg.final_rankings);
        clearInterval(timerRef.current);
        break;
      case 'error':
        setError(msg.message);
        break;
    }
  });

  function startTimer(seconds) {
    clearInterval(timerRef.current);
    setTimeLeft(seconds);
    timerRef.current = setInterval(() => {
      setTimeLeft((t) => {
        if (t <= 1) { clearInterval(timerRef.current); return 0; }
        return t - 1;
      });
    }, 1000);
  }

  useEffect(() => {
    if (!pin) { navigate('/dashboard'); return; }
    const ws = connect();
    if (ws) {
      ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'host_connect', pin, token: getToken() }));
      };
    }
    if (initialQuestion) startTimer(initialQuestion.time_limit);
    return () => { clearInterval(timerRef.current); disconnect(); };
  }, [pin]);

  function nextQuestion() {
    send({ type: 'next_question', pin });
  }

  function endSession() {
    send({ type: 'end_session', pin });
  }

  if (!pin) return null;

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
        <button style={{ ...styles.btn, marginTop: 24 }} onClick={() => navigate('/dashboard')}>
          Back to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div style={styles.wrap}>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {question && (
        <>
          <div style={styles.timer}>{timeLeft}s</div>
          <h3>Question {question.index + 1}</h3>
          <p style={{ fontSize: 28, fontWeight: 700 }}>{question.term}</p>
          <p style={{ color: '#666' }}>Answered: {answeredCount} / {totalPlayers}</p>
        </>
      )}
      {feedback && (
        <div style={{ marginTop: 16 }}>
          <p>✓ Correct answer: <strong>{feedback.correct_answer}</strong></p>
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
          <div style={{ marginTop: 20, display: 'flex', gap: 12, justifyContent: 'center' }}>
            <button style={styles.btn} onClick={nextQuestion}>Next Question →</button>
            <button style={{ ...styles.btn, background: '#c00' }} onClick={endSession}>End Session</button>
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  wrap: { maxWidth: 580, margin: '40px auto', fontFamily: 'sans-serif', padding: 24, textAlign: 'center' },
  timer: { fontSize: 48, fontWeight: 900, color: '#c00' },
  btn: { padding: '12px 24px', fontSize: 15, background: '#333', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' },
  row: { display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid #eee', maxWidth: 360, margin: '0 auto' },
};
