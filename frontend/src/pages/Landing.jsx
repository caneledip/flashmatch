import { useAuth } from '../AuthContext';
import { useNavigate } from 'react-router-dom';
import { useEffect } from 'react';

export default function Landing() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!loading && user) {
      if (user.role === 'admin') navigate('/admin');
      else if (user.role === 'host') navigate('/dashboard');
      else navigate('/join');
    }
  }, [user, loading, navigate]);

  if (loading) return <div style={styles.center}>Loading…</div>;

  return (
    <div style={styles.center}>
      <h1 style={{ fontSize: 48, margin: 0 }}>⚡ FlashMatch</h1>
      <p style={{ color: '#666', marginBottom: 32 }}>
        Real-time multiplayer vocabulary quiz game
      </p>
      <a href="/auth/google" style={styles.btn}>
        Sign in with Google
      </a>
      <br />
      <br />
      <a href="/join" style={{ color: '#555', fontSize: 14 }}>
        Join as guest →
      </a>
    </div>
  );
}

const styles = {
  center: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '100vh',
    fontFamily: 'sans-serif',
    background: '#f5f5f5',
  },
  btn: {
    background: '#4285F4',
    color: '#fff',
    padding: '14px 28px',
    borderRadius: 8,
    textDecoration: 'none',
    fontSize: 16,
    fontWeight: 600,
  },
};
