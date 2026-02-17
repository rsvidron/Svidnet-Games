# 🏗️ System Architecture

## Overview

SvidNet Arena is a modern, scalable full-stack multiplayer game platform built with FastAPI (Python) and React, using PostgreSQL for persistence and Redis for caching and real-time features.

---

## 🎯 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Browser    │  │   Mobile     │  │   Desktop    │         │
│  │   (React)    │  │   (Future)   │  │   (Future)   │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                  │
│         └──────────────────┴──────────────────┘                  │
│                            │                                     │
└────────────────────────────┼─────────────────────────────────────┘
                             │
                    ┌────────┴─────────┐
                    │   Load Balancer  │ (Nginx)
                    │   SSL Termination│
                    └────────┬─────────┘
                             │
┌────────────────────────────┼─────────────────────────────────────┐
│                     APPLICATION LAYER                            │
├────────────────────────────┼─────────────────────────────────────┤
│                            │                                     │
│  ┌─────────────────────────┴───────────────────────────────┐   │
│  │              FastAPI Application                         │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │  API Endpoints                                  │    │   │
│  │  │  - Auth (JWT)                                   │    │   │
│  │  │  - Users                                        │    │   │
│  │  │  - Trivia                                       │    │   │
│  │  │  - Games                                        │    │   │
│  │  │  - Wordle                                       │    │   │
│  │  │  - Sports                                       │    │   │
│  │  │  - Leaderboards                                 │    │   │
│  │  │  - Admin                                        │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │                                                          │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │  WebSocket Handlers                             │    │   │
│  │  │  - Game Rooms                                   │    │   │
│  │  │  - Connection Manager                           │    │   │
│  │  │  - Event Broadcasting                           │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  │                                                          │   │
│  │  ┌─────────────────────────────────────────────────┐    │   │
│  │  │  Service Layer                                  │    │   │
│  │  │  - Auth Service                                 │    │   │
│  │  │  - Game Engine                                  │    │   │
│  │  │  - Trivia Service                               │    │   │
│  │  │  - Wordle Service                               │    │   │
│  │  │  - Jeopardy Service                             │    │   │
│  │  │  - Sports Service                               │    │   │
│  │  │  - AI Service (Gemini)                          │    │   │
│  │  │  - Leaderboard Service                          │    │   │
│  │  │  - ELO Service                                  │    │   │
│  │  └─────────────────────────────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                            │                                     │
└────────────────────────────┼─────────────────────────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────────────┐
│                        DATA LAYER                                │
├────────────────────────────┼─────────────────────────────────────┤
│                            │                                     │
│  ┌────────────────┐    ┌───┴──────────┐    ┌───────────────┐   │
│  │   PostgreSQL   │    │    Redis     │    │ External APIs │   │
│  │                │    │              │    │               │   │
│  │ - Users        │    │ - Sessions   │    │ - Gemini AI   │   │
│  │ - Games        │    │ - Cache      │    │ - Sports Data │   │
│  │ - Trivia       │    │ - Game State │    │               │   │
│  │ - Leaderboards │    │ - PubSub     │    │               │   │
│  │ - Wordle       │    │ - Rate Limit │    │               │   │
│  │ - Sports       │    │              │    │               │   │
│  └────────────────┘    └──────────────┘    └───────────────┘   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📦 Component Breakdown

### Frontend (React)

```
React Application
├── Pages
│   ├── Home
│   ├── Game Modes
│   ├── Lobby
│   ├── Profile
│   ├── Leaderboard
│   ├── Friends
│   └── Admin Panel
│
├── Components
│   ├── Auth (Login, Register)
│   ├── Games
│   │   ├── Trivia (5th Grade, Jeopardy, Multiplayer)
│   │   ├── Wordle (Daily, Endless)
│   │   └── Sports (Predictions)
│   ├── Shared (Lobby, Scoreboard, Timer)
│   └── Admin
│
├── Services
│   ├── API Client (Axios)
│   ├── WebSocket Client
│   └── Auth Service
│
└── State Management
    ├── Context (Auth, Game, WebSocket)
    └── React Query (Data fetching)
```

### Backend (FastAPI)

```
FastAPI Application
├── API Layer
│   ├── REST Endpoints
│   │   ├── /api/auth
│   │   ├── /api/users
│   │   ├── /api/trivia
│   │   ├── /api/games
│   │   ├── /api/wordle
│   │   ├── /api/sports
│   │   ├── /api/leaderboards
│   │   ├── /api/friends
│   │   └── /api/admin
│   │
│   └── WebSocket Endpoints
│       ├── /ws/game/{room_code}
│       └── /ws/lobby
│
├── Service Layer (Business Logic)
│   ├── AuthService
│   ├── GameEngine
│   ├── TriviaService
│   ├── WordleService
│   ├── JeopardyService
│   ├── SportsService
│   ├── AIService (Gemini)
│   ├── LeaderboardService
│   └── ELOService
│
├── Data Layer
│   ├── SQLAlchemy Models
│   ├── Pydantic Schemas
│   └── Database Session
│
└── Core
    ├── Configuration
    ├── Security (JWT)
    └── Redis Client
```

---

## 🔄 Data Flow

### Authentication Flow

```
1. User submits credentials
   ↓
2. Frontend → POST /api/auth/login
   ↓
3. Backend validates credentials
   ↓
4. Backend generates JWT tokens (access + refresh)
   ↓
5. Frontend stores tokens in localStorage
   ↓
6. Frontend includes token in all requests
   ↓
7. Backend middleware validates token
```

### Multiplayer Game Flow

```
1. Host creates room
   Frontend → POST /api/games/rooms
   Backend creates room in DB + Redis
   Backend returns room_code
   ↓
2. Players join via room code
   Frontend → GET /api/games/rooms/{code}
   ↓
3. WebSocket connection established
   Frontend → WS /ws/game/{room_code}?token={jwt}
   Backend validates token
   Backend adds to ConnectionManager
   ↓
4. Real-time game events
   Player action (buzz, answer) → WebSocket message
   Backend validates action
   Backend updates game state (Redis)
   Backend broadcasts to all players
   ↓
5. Game completion
   Backend calculates scores
   Backend updates user stats (DB)
   Backend updates ELO ratings
   Backend broadcasts final results
```

### AI Question Generation Flow

```
1. Admin triggers generation
   Frontend → POST /api/admin/ai/generate
   ↓
2. Backend calls Gemini API
   Backend → Google Gemini
   Gemini generates questions
   ↓
3. Backend stores in ai_generated_questions table
   Status: 'pending'
   ↓
4. Admin reviews in admin panel
   Frontend → GET /api/admin/questions/pending
   ↓
5. Admin approves/rejects
   Frontend → POST /api/admin/questions/{id}/approve
   ↓
6. If approved:
   Backend moves to trivia_questions table
   Backend sets is_approved = True
```

---

## 🗄️ Database Architecture

### Entity Relationships

```
User ─────┬─────< UserProfile
          ├─────< GameSession
          ├─────< Friendship
          ├─────< Notification
          └─────< UserAnswer

GameRoom ──┬────< GameParticipant
           └────< GameSession

GameMode ──┬────< GameRoom
           └────< GameSession

Category ──┬────< TriviaQuestion
           └────< AIGeneratedQuestion

TriviaQuestion ─┬──< TriviaAnswer
                └──< UserAnswer

GameSession ────< UserAnswer

SportsEvent ────< Prediction

Leaderboard ────< LeaderboardEntry
```

### Indexing Strategy

- **Primary Keys**: All tables
- **Foreign Keys**: All relationships
- **Lookup Fields**: username, email, room_code
- **Query Optimization**:
  - `game_sessions(user_id, completed, started_at DESC)`
  - `leaderboard_entries(leaderboard_id, rank ASC)`
  - `trivia_questions(category_id, is_approved)`

---

## ⚡ Caching Strategy

### Redis Usage

```
Key Pattern                    TTL      Purpose
──────────────────────────────────────────────────────────
game_session:{id}              1h       Active game state
room:{code}                    2h       Room metadata
leaderboard:{type}             5m       Cached rankings
user_stats:{id}                10m      User statistics
rate_limit:{ip}:{endpoint}     1m       API rate limiting
ws_connections:{room_code}     -        Active connections
```

### Cache Invalidation

- **Write-through**: Update cache on DB write
- **TTL-based**: Automatic expiration
- **Event-based**: Invalidate on specific events
  - User profile update → Invalidate user_stats
  - Game completion → Invalidate leaderboards
  - Room close → Invalidate room data

---

## 🔐 Security Architecture

### Authentication

```
┌──────────────┐
│   Client     │
└──────┬───────┘
       │ 1. Login credentials
       ↓
┌──────────────────────────┐
│   FastAPI Auth Endpoint  │
│   - Validate credentials │
│   - Hash password check  │
└──────┬───────────────────┘
       │ 2. Generate JWT
       ↓
┌──────────────────────┐
│   JWT Token          │
│   - access_token     │
│   - refresh_token    │
│   - Expiration       │
└──────┬───────────────┘
       │ 3. Return tokens
       ↓
┌──────────────┐
│   Client     │
│   Stores in  │
│   localStorage│
└──────────────┘
```

### Request Authorization

```
Every API Request
       ↓
┌──────────────────────┐
│ Middleware           │
│ - Extract token      │
│ - Verify signature   │
│ - Check expiration   │
└──────┬───────────────┘
       │
       ├─ Valid → Continue to endpoint
       └─ Invalid → 401 Unauthorized
```

### Security Layers

1. **Transport**: HTTPS/TLS
2. **Authentication**: JWT tokens
3. **Authorization**: Role-based (user/admin)
4. **Input Validation**: Pydantic schemas
5. **SQL Injection**: ORM (SQLAlchemy)
6. **XSS**: React auto-escaping
7. **CSRF**: Token validation
8. **Rate Limiting**: Redis-based

---

## 🌐 WebSocket Architecture

### Connection Management

```python
class ConnectionManager:
    active_connections: Dict[user_id, WebSocket]
    room_connections: Dict[room_code, Set[user_id]]
    user_rooms: Dict[user_id, room_code]

    Methods:
    - connect(user_id, websocket)
    - disconnect(user_id)
    - join_room(user_id, room_code)
    - leave_room(user_id, room_code)
    - send_personal_message(message, user_id)
    - broadcast_to_room(room_code, message)
    - broadcast_to_all(message)
```

### Event Flow

```
Client Event → WebSocket → Server Handler
                              ↓
                       Validate Event
                              ↓
                       Update State (Redis)
                              ↓
                       Broadcast to Room
                              ↓
                    All Clients Receive Update
```

---

## 📊 Scalability Considerations

### Horizontal Scaling

```
                Load Balancer
                     │
        ┌────────────┼────────────┐
        ↓            ↓            ↓
   Backend 1    Backend 2    Backend 3
        │            │            │
        └────────────┴────────────┘
                     │
        ┌────────────┴────────────┐
        ↓                         ↓
   PostgreSQL                  Redis
   (Primary + Replicas)        (Cluster)
```

### Bottleneck Mitigation

1. **Database**
   - Read replicas for queries
   - Connection pooling
   - Query optimization
   - Materialized views

2. **Cache**
   - Redis cluster mode
   - Pub/Sub for events
   - Separate cache per service

3. **WebSocket**
   - Sticky sessions
   - Redis adapter for multi-server
   - Connection limits per server

4. **API**
   - Stateless design
   - Rate limiting
   - Async operations
   - Background tasks (Celery)

---

## 🔄 Deployment Architecture

### Development

```
Docker Compose
├── postgres:15
├── redis:7
├── backend (FastAPI)
└── frontend (Vite dev server)
```

### Production

```
                    ┌─────────────┐
                    │   Nginx     │
                    │   (SSL)     │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        ↓                                     ↓
┌───────────────┐                   ┌──────────────┐
│  Frontend     │                   │   Backend    │
│  (Static)     │                   │   (Uvicorn)  │
│  CDN/S3       │                   │   Gunicorn   │
└───────────────┘                   └──────┬───────┘
                                           │
                        ┌──────────────────┴─────────────┐
                        ↓                                ↓
                 ┌─────────────┐               ┌──────────────┐
                 │ PostgreSQL  │               │    Redis     │
                 │ (RDS/Managed)│               │  (Managed)   │
                 └─────────────┘               └──────────────┘
```

---

## 🧪 Testing Strategy

### Backend Tests

```
tests/
├── unit/
│   ├── test_auth_service.py
│   ├── test_game_engine.py
│   └── test_ai_service.py
├── integration/
│   ├── test_api_endpoints.py
│   └── test_websocket.py
└── e2e/
    └── test_game_flow.py
```

### Frontend Tests

```
src/__tests__/
├── components/
├── services/
└── integration/
```

---

## 📈 Monitoring & Observability

### Metrics to Track

- **Application**
  - Request rate
  - Response time
  - Error rate
  - Active users
  - WebSocket connections

- **Database**
  - Query time
  - Connection pool usage
  - Slow queries
  - Deadlocks

- **Cache**
  - Hit rate
  - Memory usage
  - Eviction rate

### Logging

```
Application Logs → Structured JSON
                         ↓
                   Log Aggregator
                   (ELK/Datadog)
                         ↓
                   Dashboards & Alerts
```

---

This architecture supports:
- ✅ High availability
- ✅ Horizontal scalability
- ✅ Real-time features
- ✅ Sub-second response times
- ✅ Thousands of concurrent users
- ✅ Clean separation of concerns
- ✅ Easy maintenance & updates
