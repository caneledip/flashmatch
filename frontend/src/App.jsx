import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './AuthContext'
import Landing from './pages/Landing'
import Join from './pages/Join'
import Dashboard from './pages/Dashboard'
import DeckEdit from './pages/DeckEdit'
import SessionLobby from './pages/SessionLobby'
import SessionGame from './pages/SessionGame'
import Admin from './pages/Admin'

function NotFound() {
  return <h2 style={{ textAlign: 'center', marginTop: '10vh', fontFamily: 'sans-serif' }}>404 — Page not found</h2>
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/join" element={<Join />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/decks/new" element={<DeckEdit />} />
          <Route path="/decks/:id/edit" element={<DeckEdit />} />
          <Route path="/session/lobby" element={<SessionLobby />} />
          <Route path="/session/game" element={<SessionGame />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
