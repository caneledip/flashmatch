# FlashMatch

Real-time multiplayer vocabulary flashcard quiz game. Hosts create decks and run live quiz sessions; players join with a 6-digit PIN and compete on a live leaderboard.

---

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- A Google Cloud project with OAuth 2.0 credentials

---

## Installation

### 1. Clone the repository

```bash
git clone <repo-url>
cd flashmatch
```

### 2. Configure Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → **APIs & Services** → **Credentials**
2. Create an **OAuth 2.0 Client ID** (Web application)
3. Add the following under **Authorized JavaScript origins**:
   ```
   http://localhost
   ```
4. Add the following under **Authorized redirect URIs**:
   ```
   http://localhost/auth/callback
   ```
5. Copy your **Client ID** and **Client Secret** into `.env`:

```env
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
```

> If your OAuth app is in **Testing** mode, add every user's Google account under **OAuth consent screen → Test users**.

### 3. Start the stack

```bash
docker compose up --build
```

All services start automatically. The app is available at **http://localhost** once all containers are healthy (about 30 seconds on first run).

To run in the background:

```bash
docker compose up --build -d
```

### 4. First-time admin setup

The first user to sign in is created with the `host` role. To grant admin access, run:

```bash
docker exec flashmatch-user-db-1 psql -U user_admin -d userdb -c \
  "UPDATE users SET role='admin' WHERE email='your@email.com';"
```

Then sign out and back in to refresh your session token.

### Stopping the app

```bash
docker compose down
```

To also delete all data (databases, Redis):

```bash
docker compose down -v
```

---

## Usage — Normal User (Host)

Every Google account that signs in gets **host** role by default, which allows creating decks and running sessions.

### Sign in

1. Go to **http://localhost**
2. Click **Sign in with Google**
3. You are redirected to the **Dashboard**

### Create a deck

1. From the Dashboard, click **+ New Deck**
2. Enter a title and optional description
3. Toggle **Make public** if you want other hosts to see it
4. Click **Save Deck**
5. Add flashcards using the **Term** and **Definition** fields, then click **+ Add Card**
6. Repeat for all cards (minimum 1 to start a session)

### Run a quiz session

1. From the Dashboard, click **▶ Start** next to a deck
2. A lobby screen opens showing a **6-digit PIN**
3. Share the PIN with players — they join at **http://localhost/join**
4. Watch the player list update in real time as people join
5. Click **Start Quiz** when ready

### During the quiz

- Each question shows a **term** — players type the matching definition
- The timer counts down (20 seconds per question)
- The answer count updates live as players submit
- When all players answer (or the timer expires), the correct answer and leaderboard appear
- Click **Next Question →** to advance
- Click **End Session** at any time to close the session and show final rankings

### Join as a player

1. Go to **http://localhost/join**
2. Enter the **6-digit PIN** and your **display name**
3. Wait for the host to start — questions appear automatically
4. Type the definition and hit **Submit** before the timer runs out
5. See your score and rank after each question

---

## Usage — Admin

Admins have all host permissions plus user and deck management.

### Access the admin dashboard

Go to **http://localhost/admin** (only visible to admin accounts).

### Manage users

- View all registered users with their roles
- Change any user's role using the dropdown:
  - `player` — can only join sessions
  - `host` — can create decks and run sessions
  - `admin` — full access
- Delete any user account

### Manage decks

- View all decks (public and private) across all users
- Delete any deck

---

## Architecture overview

```
Browser
  └── http://localhost (Nginx)
        ├── /auth/*      → User Service   (FastAPI :8000)
        ├── /users/*     → User Service
        ├── /decks/*     → Deck Service   (FastAPI :8001)
        ├── /sessions/*  → Quiz Service   (FastAPI :8002)
        ├── /ws/*        → Quiz Service   (WebSocket)
        └── /            → Frontend       (React + Vite :5173)

Databases
  ├── user-db   PostgreSQL  (users, oauth_accounts)
  ├── deck-db   PostgreSQL  (decks, flashcards)
  └── redis     Redis       (active sessions, leaderboard state)
```

Only port 80 (Nginx) is exposed to the host machine. All other services communicate on an internal Docker network.

---

## Environment variables

| Variable | Description |
|---|---|
| `GOOGLE_CLIENT_ID` | OAuth 2.0 client ID from Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | OAuth 2.0 client secret |
| `GOOGLE_REDIRECT_URI` | Must match the URI registered in Google Cloud Console |
| `JWT_SECRET` | Secret key for signing JWTs — change in production |
| `JWT_EXPIRE_MINUTES` | Token lifetime in minutes (default 1440 = 24 h) |
| `USER_DB_URL` | Async PostgreSQL connection string for user service |
| `DECK_DB_URL` | Async PostgreSQL connection string for deck service |
| `REDIS_URL` | Redis connection string for quiz session service |
