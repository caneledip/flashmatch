// Central API client. JWT is stored in module-level memory only (not localStorage).
let _token = null;

export function setToken(token) {
  _token = token;
}

export function getToken() {
  return _token;
}

export function clearToken() {
  _token = null;
}

function authHeaders() {
  return _token ? { Authorization: `Bearer ${_token}` } : {};
}

async function request(method, path, body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
  };
  if (body !== null) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}

// Auth
export const api = {
  // Users
  getMe: () => request('GET', '/users/me'),
  listUsers: () => request('GET', '/users/'),
  updateUserRole: (id, role) => request('PATCH', `/users/${id}/role`, { role }),
  deleteUser: (id) => request('DELETE', `/users/${id}`),

  // Decks
  listDecks: () => request('GET', '/decks/'),
  listPublicDecks: () => request('GET', '/decks/public'),
  getDeck: (id) => request('GET', `/decks/${id}`),
  createDeck: (data) => request('POST', '/decks/', data),
  updateDeck: (id, data) => request('PATCH', `/decks/${id}`, data),
  deleteDeck: (id) => request('DELETE', `/decks/${id}`),

  // Cards
  addCard: (deckId, data) => request('POST', `/decks/${deckId}/cards`, data),
  updateCard: (deckId, cardId, data) => request('PATCH', `/decks/${deckId}/cards/${cardId}`, data),
  deleteCard: (deckId, cardId) => request('DELETE', `/decks/${deckId}/cards/${cardId}`),

  // Sessions
  createSession: (data) => request('POST', '/sessions/', data),
  getSession: (pin) => request('GET', `/sessions/${pin}`),
  startSession: (pin) => request('POST', `/sessions/${pin}/start`),
};
