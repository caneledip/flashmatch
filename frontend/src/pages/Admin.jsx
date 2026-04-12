import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../AuthContext';

export default function Admin() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [decks, setDecks] = useState([]);
  const [tab, setTab] = useState('users');
  const [error, setError] = useState('');

  useEffect(() => {
    if (user && user.role !== 'admin') navigate('/');
  }, [user]);

  useEffect(() => {
    api.listUsers().then(setUsers).catch((e) => setError(e.message));
    api.listDecks().then(setDecks).catch((e) => setError(e.message));
  }, []);

  async function changeRole(id, role) {
    try {
      const updated = await api.updateUserRole(id, role);
      setUsers((prev) => prev.map((u) => (u.id === id ? updated : u)));
    } catch (e) {
      setError(e.message);
    }
  }

  async function deleteUser(id) {
    if (!confirm('Delete this user?')) return;
    try {
      await api.deleteUser(id);
      setUsers((prev) => prev.filter((u) => u.id !== id));
    } catch (e) {
      setError(e.message);
    }
  }

  async function deleteDeck(id) {
    if (!confirm('Delete this deck?')) return;
    try {
      await api.deleteDeck(id);
      setDecks((prev) => prev.filter((d) => d.id !== id));
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div style={styles.wrap}>
      <div style={styles.header}>
        <h1>🛠 Admin Dashboard</h1>
        <button onClick={logout} style={styles.btnSm}>Logout</button>
      </div>
      {error && <p style={{ color: 'red' }}>{error}</p>}

      <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
        <button style={tab === 'users' ? styles.tabActive : styles.tab} onClick={() => setTab('users')}>Users ({users.length})</button>
        <button style={tab === 'decks' ? styles.tabActive : styles.tab} onClick={() => setTab('decks')}>Decks ({decks.length})</button>
      </div>

      {tab === 'users' && users.map((u) => (
        <div key={u.id} style={styles.card}>
          <div>
            <strong>{u.display_name}</strong>
            <span style={{ marginLeft: 8, color: '#666', fontSize: 13 }}>{u.email}</span>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <select value={u.role} onChange={(e) => changeRole(u.id, e.target.value)} style={styles.select}>
              <option value="player">player</option>
              <option value="host">host</option>
              <option value="admin">admin</option>
            </select>
            <button style={{ ...styles.btnSm, background: '#c00' }} onClick={() => deleteUser(u.id)}>Delete</button>
          </div>
        </div>
      ))}

      {tab === 'decks' && decks.map((d) => (
        <div key={d.id} style={styles.card}>
          <div>
            <strong>{d.title}</strong>
            <span style={{ marginLeft: 8, color: '#888', fontSize: 13 }}>
              {d.flashcards?.length ?? 0} cards · {d.is_public ? 'Public' : 'Private'}
            </span>
          </div>
          <button style={{ ...styles.btnSm, background: '#c00' }} onClick={() => deleteDeck(d.id)}>Delete</button>
        </div>
      ))}
    </div>
  );
}

const styles = {
  wrap: { maxWidth: 760, margin: '40px auto', fontFamily: 'sans-serif', padding: 24 },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  card: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', marginBottom: 8, background: '#fff', borderRadius: 8, boxShadow: '0 1px 4px rgba(0,0,0,.1)' },
  btnSm: { padding: '6px 14px', fontSize: 13, background: '#555', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' },
  tab: { padding: '8px 18px', border: '1px solid #ccc', background: '#fff', borderRadius: 6, cursor: 'pointer' },
  tabActive: { padding: '8px 18px', border: '1px solid #333', background: '#333', color: '#fff', borderRadius: 6, cursor: 'pointer' },
  select: { padding: '4px 8px', borderRadius: 4, border: '1px solid #ccc' },
};
