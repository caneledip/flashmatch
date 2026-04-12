import { BrowserRouter, Routes, Route } from 'react-router-dom'

function Landing() {
  return (
    <div style={{ textAlign: 'center', marginTop: '10vh', fontFamily: 'sans-serif' }}>
      <h1>⚡ FlashMatch</h1>
      <p>Real-time multiplayer vocabulary flashcard quiz game</p>
      <a href="/auth/google">
        <button style={{ padding: '12px 24px', fontSize: '16px', cursor: 'pointer' }}>
          Login with Google
        </button>
      </a>
    </div>
  )
}

function NotFound() {
  return <h2 style={{ textAlign: 'center', marginTop: '10vh' }}>404 — Page not found</h2>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  )
}
