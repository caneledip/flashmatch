import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api';

export default function DeckEdit() {
  const { id } = useParams();
  const isNew = !id;
  const navigate = useNavigate();

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isPublic, setIsPublic] = useState(false);
  const [cards, setCards] = useState([]);
  const [newTerm, setNewTerm] = useState('');
  const [newDef, setNewDef] = useState('');
  const [deckId, setDeckId] = useState(id || null);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!isNew) {
      api.getDeck(id).then((d) => {
        setTitle(d.title);
        setDescription(d.description || '');
        setIsPublic(d.is_public);
        setCards(d.flashcards || []);
      }).catch((e) => setError(e.message));
    }
  }, [id, isNew]);

  async function saveDeck(e) {
    e.preventDefault();
    setSaving(true);
    try {
      if (isNew) {
        const d = await api.createDeck({ title, description, is_public: isPublic });
        setDeckId(d.id);
        navigate(`/decks/${d.id}/edit`, { replace: true });
      } else {
        await api.updateDeck(deckId, { title, description, is_public: isPublic });
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function addCard(e) {
    e.preventDefault();
    if (!deckId) { setError('Save deck first'); return; }
    try {
      const card = await api.addCard(deckId, { term: newTerm, definition: newDef, position: cards.length });
      setCards((prev) => [...prev, card]);
      setNewTerm('');
      setNewDef('');
    } catch (e) {
      setError(e.message);
    }
  }

  async function removeCard(cardId) {
    try {
      await api.deleteCard(deckId, cardId);
      setCards((prev) => prev.filter((c) => c.id !== cardId));
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div style={styles.wrap}>
      <button onClick={() => navigate('/dashboard')} style={styles.back}>← Dashboard</button>
      <h2>{isNew ? 'New Deck' : 'Edit Deck'}</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}

      <form onSubmit={saveDeck}>
        <input style={styles.input} placeholder="Deck title" value={title}
          onChange={(e) => setTitle(e.target.value)} required />
        <textarea style={{ ...styles.input, height: 70 }} placeholder="Description (optional)"
          value={description} onChange={(e) => setDescription(e.target.value)} />
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <input type="checkbox" checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} />
          Make public
        </label>
        <button style={styles.btn} type="submit" disabled={saving}>
          {saving ? 'Saving…' : 'Save Deck'}
        </button>
      </form>

      {deckId && (
        <>
          <h3 style={{ marginTop: 32 }}>Flashcards ({cards.length})</h3>
          {cards.map((c, i) => (
            <div key={c.id} style={styles.cardRow}>
              <span style={{ flex: 1 }}><strong>{c.term}</strong> — {c.definition}</span>
              <button style={styles.btnDanger} onClick={() => removeCard(c.id)}>✕</button>
            </div>
          ))}
          <form onSubmit={addCard} style={{ marginTop: 16 }}>
            <input style={styles.input} placeholder="Term" value={newTerm}
              onChange={(e) => setNewTerm(e.target.value)} required />
            <input style={styles.input} placeholder="Definition" value={newDef}
              onChange={(e) => setNewDef(e.target.value)} required />
            <button style={styles.btn} type="submit">+ Add Card</button>
          </form>
        </>
      )}
    </div>
  );
}

const styles = {
  wrap: { maxWidth: 600, margin: '40px auto', fontFamily: 'sans-serif', padding: 24 },
  input: { display: 'block', width: '100%', padding: 10, marginBottom: 10, fontSize: 15, boxSizing: 'border-box', border: '1px solid #ccc', borderRadius: 6 },
  btn: { padding: '10px 20px', fontSize: 15, background: '#333', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' },
  btnDanger: { padding: '4px 10px', background: '#c00', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' },
  cardRow: { display: 'flex', alignItems: 'center', gap: 10, padding: '10px 0', borderBottom: '1px solid #eee' },
  back: { background: 'none', border: 'none', color: '#555', cursor: 'pointer', fontSize: 14, padding: 0, marginBottom: 16 },
};
