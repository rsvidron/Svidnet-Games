# 🎮 Project Structure

```
game-platform/
│
├── backend/                          # FastAPI Backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app entry point
│   │   │
│   │   ├── api/                      # API routes
│   │   │   ├── __init__.py
│   │   │   ├── deps.py               # Dependencies (auth, db)
│   │   │   ├── endpoints/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py           # Login, register, JWT
│   │   │   │   ├── users.py          # User profile, stats
│   │   │   │   ├── trivia.py         # Trivia questions, categories
│   │   │   │   ├── games.py          # Game sessions, rooms
│   │   │   │   ├── wordle.py         # Wordle endpoints
│   │   │   │   ├── sports.py         # Sports predictions
│   │   │   │   ├── leaderboards.py   # Leaderboard endpoints
│   │   │   │   ├── friends.py        # Friends system
│   │   │   │   └── admin.py          # Admin panel endpoints
│   │   │   │
│   │   │   └── websockets/
│   │   │       ├── __init__.py
│   │   │       ├── manager.py        # WebSocket connection manager
│   │   │       ├── game_rooms.py     # Multiplayer game rooms
│   │   │       └── events.py         # WebSocket event handlers
│   │   │
│   │   ├── core/                     # Core configuration
│   │   │   ├── __init__.py
│   │   │   ├── config.py             # Settings (env vars)
│   │   │   ├── security.py           # JWT, password hashing
│   │   │   └── redis.py              # Redis connection
│   │   │
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── user.py               # User, UserProfile
│   │   │   ├── game.py               # GameMode, GameRoom, GameSession
│   │   │   ├── trivia.py             # TriviaQuestion, TriviaAnswer, Category
│   │   │   ├── wordle.py             # WordleWord, WordleAttempt
│   │   │   ├── sports.py             # SportsEvent, Prediction
│   │   │   ├── leaderboard.py        # Leaderboard, LeaderboardEntry
│   │   │   └── ai.py                 # AIGeneratedQuestion
│   │   │
│   │   ├── schemas/                  # Pydantic schemas (request/response)
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── auth.py
│   │   │   ├── game.py
│   │   │   ├── trivia.py
│   │   │   ├── wordle.py
│   │   │   ├── sports.py
│   │   │   └── leaderboard.py
│   │   │
│   │   ├── services/                 # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py       # Authentication logic
│   │   │   ├── game_engine.py        # Core game logic
│   │   │   ├── trivia_service.py     # Trivia game logic
│   │   │   ├── wordle_service.py     # Wordle game logic
│   │   │   ├── jeopardy_service.py   # Jeopardy game logic
│   │   │   ├── sports_service.py     # Sports prediction logic
│   │   │   ├── leaderboard_service.py # Leaderboard calculations
│   │   │   ├── ai_service.py         # Gemini AI integration
│   │   │   ├── elo_service.py        # ELO rating calculations
│   │   │   └── notification_service.py
│   │   │
│   │   ├── db/                       # Database
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # SQLAlchemy base
│   │   │   └── session.py            # Database session
│   │   │
│   │   └── utils/                    # Utilities
│   │       ├── __init__.py
│   │       ├── validators.py         # Input validators
│   │       ├── rate_limiter.py       # API rate limiting
│   │       └── helpers.py            # Helper functions
│   │
│   ├── tests/                        # Backend tests
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_games.py
│   │   └── test_websockets.py
│   │
│   ├── alembic/                      # Database migrations
│   │   ├── versions/
│   │   ├── env.py
│   │   └── script.py.mako
│   │
│   ├── requirements.txt              # Python dependencies
│   ├── requirements-dev.txt          # Dev dependencies
│   ├── .env.example                  # Environment variables template
│   ├── alembic.ini                   # Alembic config
│   └── Dockerfile                    # Docker image for backend
│
├── frontend/                         # React Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── auth/
│   │   │   │   ├── Login.jsx
│   │   │   │   ├── Register.jsx
│   │   │   │   └── ProtectedRoute.jsx
│   │   │   │
│   │   │   ├── games/
│   │   │   │   ├── trivia/
│   │   │   │   │   ├── FifthGradeMode.jsx
│   │   │   │   │   ├── JeopardyBoard.jsx
│   │   │   │   │   ├── QuestionCard.jsx
│   │   │   │   │   └── TriviaRoom.jsx
│   │   │   │   │
│   │   │   │   ├── wordle/
│   │   │   │   │   ├── WordleGrid.jsx
│   │   │   │   │   ├── Keyboard.jsx
│   │   │   │   │   └── DailyWordle.jsx
│   │   │   │   │
│   │   │   │   ├── sports/
│   │   │   │   │   ├── PredictionCard.jsx
│   │   │   │   │   └── SportsDashboard.jsx
│   │   │   │   │
│   │   │   │   └── shared/
│   │   │   │       ├── GameLobby.jsx
│   │   │   │       ├── JoinRoom.jsx
│   │   │   │       ├── Scoreboard.jsx
│   │   │   │       └── Timer.jsx
│   │   │   │
│   │   │   ├── admin/
│   │   │   │   ├── Dashboard.jsx
│   │   │   │   ├── QuestionManager.jsx
│   │   │   │   ├── AIQuestionReview.jsx
│   │   │   │   ├── UserManager.jsx
│   │   │   │   └── CategoryManager.jsx
│   │   │   │
│   │   │   ├── common/
│   │   │   │   ├── Button.jsx
│   │   │   │   ├── Modal.jsx
│   │   │   │   ├── LoadingSpinner.jsx
│   │   │   │   └── Avatar.jsx
│   │   │   │
│   │   │   └── layout/
│   │   │       ├── Navbar.jsx
│   │   │       ├── Sidebar.jsx
│   │   │       └── Footer.jsx
│   │   │
│   │   ├── pages/
│   │   │   ├── Home.jsx
│   │   │   ├── Profile.jsx
│   │   │   ├── Leaderboard.jsx
│   │   │   ├── Friends.jsx
│   │   │   ├── GameModes.jsx
│   │   │   └── AdminPanel.jsx
│   │   │
│   │   ├── services/
│   │   │   ├── api.js               # Axios instance
│   │   │   ├── authService.js       # Auth API calls
│   │   │   ├── gameService.js       # Game API calls
│   │   │   ├── websocketService.js  # WebSocket client
│   │   │   └── storageService.js    # LocalStorage wrapper
│   │   │
│   │   ├── hooks/
│   │   │   ├── useAuth.js
│   │   │   ├── useWebSocket.js
│   │   │   ├── useGame.js
│   │   │   └── useLeaderboard.js
│   │   │
│   │   ├── contexts/
│   │   │   ├── AuthContext.jsx
│   │   │   ├── GameContext.jsx
│   │   │   └── WebSocketContext.jsx
│   │   │
│   │   ├── utils/
│   │   │   ├── constants.js
│   │   │   ├── helpers.js
│   │   │   └── validators.js
│   │   │
│   │   ├── assets/
│   │   │   ├── images/
│   │   │   └── styles/
│   │   │       └── globals.css
│   │   │
│   │   ├── App.jsx                  # Main app component
│   │   ├── main.jsx                 # Entry point
│   │   └── router.jsx               # React Router config
│   │
│   ├── public/
│   │   ├── index.html
│   │   └── favicon.ico
│   │
│   ├── package.json
│   ├── vite.config.js               # Vite bundler config
│   ├── tailwind.config.js           # Tailwind CSS config
│   ├── .env.example
│   └── Dockerfile
│
├── docs/                             # Documentation
│   ├── API.md                        # API documentation
│   ├── ARCHITECTURE.md               # System architecture
│   ├── DEPLOYMENT.md                 # Deployment guide
│   └── GAME_RULES.md                 # Game rules & logic
│
├── scripts/                          # Utility scripts
│   ├── seed_database.py              # Seed initial data
│   ├── generate_wordle_words.py      # Generate word lists
│   └── backup_db.sh                  # Database backup
│
├── docker-compose.yml                # Docker compose for local dev
├── .gitignore
└── README.md
```

## 📦 Key Technology Stack

### Backend
- **FastAPI** - Modern async web framework
- **SQLAlchemy** - ORM for PostgreSQL
- **Alembic** - Database migrations
- **Redis** - Caching & real-time sessions
- **WebSockets** - Real-time multiplayer
- **JWT** - Authentication
- **Pydantic** - Data validation
- **Google Gemini API** - AI question generation

### Frontend
- **React** - UI framework
- **Vite** - Fast build tool
- **TailwindCSS** - Styling
- **React Router** - Navigation
- **Axios** - HTTP client
- **WebSocket** - Real-time updates
- **Context API** - State management

### Infrastructure
- **PostgreSQL** - Primary database
- **Redis** - Cache & sessions
- **Docker** - Containerization
- **Nginx** - Reverse proxy (production)

## 🗂️ Database Schema Highlights

### Core Tables
1. **users** - User authentication & basic info
2. **user_profiles** - Stats, ELO, achievements
3. **friendships** - Friend connections
4. **game_modes** - Available game types
5. **game_rooms** - Multiplayer sessions
6. **game_sessions** - Individual game records
7. **trivia_questions** - Question bank
8. **wordle_words** - Word lists
9. **sports_events** - Sports games for predictions
10. **leaderboards** - Rankings & competitions

### Special Features
- **Audit logging** for admin actions
- **AI question approval workflow**
- **Flexible JSONB fields** for game-specific data
- **Automatic triggers** for profile creation & timestamps
- **Materialized views** for leaderboards
- **Proper indexes** for performance
