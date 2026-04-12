import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../AuthContext';

export default function Dashboard() {
  const { user, logout } = useAuth();
  const [decks, setDecks] = useState([]);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    api.listDecks().then(setDecks).catch((e) => setError(e.message));
  }, []);

  async function handleDelete(id) {
    if (!confirm('Delete this deck?')) return;
    try {
      await api.deleteDeck(id);
      setDecks((prev) => prev.filter((d) => d.id !== id));
    } catch (e) {
      setError(e.message);
    }
  }

  async function createSession(deckId) {
    try {
      const session = await api.createSession({ deck_id: deckId, question_time_limit: 20 });
      navigate('/session/lobby', { state: { pin: session.pin } });
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div style={styles.wrap}>
      <div style={styles.header}>
        <h1>📚 My Decks</h1>
        <div>
          <span style={{ marginRight: 12 }}>Hi, {user?.display_name}</span>
          <button onClick={logout} style={styles.btnSm}>Logout</button>
        </div>
      </div>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <Link to="/decks/new"><button style={styles.btn}>+ New Deck</button></Link>
      <div style={{ marginTop: 24 }}>
        {decks.length === 0 && <p>No decks yet. Create one!</p>}
        {decks.map((deck) => (
          <div key={deck.id} style={styles.card}>
            <div>
              <strong>{deck.title}</strong>
              <span style={{ marginLeft: 8, color: '#888', fontSize: 13 }}>
                {deck.flashcards?.length ?? 0} cards
              </span>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button style={styles.btnSm} onClick={() => navigate(`/decks/${deck.id}/edit`)}>Edit</button>
              <button style={styles.btnSm} onClick={() => createSession(deck.id)}>▶ Start</button>
              <button style={{ ...styles.btnSm, background: '#c00' }} onClick={() => handleDelete(deck.id)}>Delete</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles = {
  wrap: { maxWidth: 700, margin: '40px auto', fontFamily: 'sans-serif', padding: 24 },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  btn: { padding: '10px 20px', fontSize: 15, background: '#333', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' },
  btnSm: { padding: '6px 14px', fontSize: 13, background: '#555', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' },
  card: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '14px 16px', marginBottom: 10, background: '#fff', borderRadius: 8, boxShadow: '0 1px 4px rgba(0,0,0,.1)' },
};
