# 🎮 SvidNet Arena - Multiplayer Game Platform

A full-stack, production-ready multiplayer game platform featuring trivia, word games, and sports predictions with real-time gameplay, AI-generated content, and comprehensive social features.

**Domain**: svidnet.com

---

## ✨ Features

### 🎯 Game Modes

#### Trivia Games
- **5th Grade Mode**: Progressive difficulty trivia challenge
- **Jeopardy Mode**: Category-based with real-time buzzer system
- **Multiplayer Trivia**: Compete with up to 8 players in real-time

#### Word Games
- **Daily Wordle**: One puzzle per day, shared globally
- **Endless Wordle**: Unlimited puzzles with difficulty levels
- **Word Connections**: Group words into categories (NYT Connections style)

#### Sports Section
- Over/Under predictions
- Winner picks with confidence points
- Weekly leaderboards
- Optional betting currency system

### 🤖 AI-Powered Content
- **Gemini AI Integration**: Generate trivia questions on demand
- **Admin Review Workflow**: AI generates, admin approves
- **Category Suggestions**: AI-powered category recommendations
- **Quality Control**: Automatic question validation

### 👥 Social Features
- User profiles with stats and achievements
- Friends system
- Multiple leaderboards:
  - Global rankings
  - Friends-only
  - Per category
  - Per game mode
  - Weekly/monthly competitions
- ELO rating system
- Streak tracking

### 🎮 Multiplayer
- Create/join rooms with 4-6 digit codes
- Real-time WebSocket communication
- Live scoring and updates
- Spectator mode
- Host controls
- Turn-based gameplay

### 🛡️ Admin Panel
- Manage questions, categories, users
- Approve AI-generated content
- Bulk import via CSV
- User moderation
- Analytics dashboard

---

## 🏗️ Architecture

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15+
- **Cache**: Redis 7+
- **ORM**: SQLAlchemy (async)
- **Auth**: JWT tokens
- **Real-time**: WebSockets
- **AI**: Google Gemini API
- **Migrations**: Alembic

### Frontend
- **Framework**: React 18
- **Build Tool**: Vite
- **Styling**: TailwindCSS
- **State**: Zustand + React Query
- **Routing**: React Router v6
- **WebSocket**: Native WebSocket API
- **HTTP**: Axios with interceptors

### Infrastructure
- **Containerization**: Docker + Docker Compose
- **Reverse Proxy**: Nginx (production)
- **SSL**: Let's Encrypt (Certbot)
- **CI/CD**: GitHub Actions ready

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- (Optional) Python 3.11+, Node.js 18+, PostgreSQL, Redis

### 1. Clone & Configure

```bash
git clone <your-repo>
cd game-platform
cp backend/.env.example backend/.env
```

Edit `backend/.env`:
```bash
# Generate secure key
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Add your Gemini API key
GEMINI_API_KEY=your_api_key_here
```

### 2. Start with Docker

```bash
docker-compose up -d
```

### 3. Initialize Database

```bash
docker-compose exec backend alembic upgrade head
```

### 4. Access Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Admin Panel**: http://localhost:3000/admin

---

## 📁 Project Structure

```
game-platform/
├── backend/
│   ├── app/
│   │   ├── api/              # API routes & WebSocket
│   │   ├── core/             # Config, security, Redis
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   ├── db/               # Database setup
│   │   └── utils/            # Utilities
│   ├── tests/                # Backend tests
│   ├── alembic/              # DB migrations
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/            # Page components
│   │   ├── services/         # API & WebSocket clients
│   │   ├── hooks/            # Custom React hooks
│   │   ├── contexts/         # React contexts
│   │   └── utils/            # Utilities
│   └── package.json
│
├── docs/                     # Documentation
├── scripts/                  # Utility scripts
├── docker-compose.yml
├── database_schema.sql       # Complete DB schema
└── README.md
```

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed breakdown.

---

## 🗄️ Database

### Schema Highlights
- **30+ tables** with proper relationships
- **Automatic timestamps** via triggers
- **Comprehensive indexing** for performance
- **JSONB columns** for flexible game data
- **Materialized views** for leaderboards
- **Audit logging** for admin actions

See [database_schema.sql](database_schema.sql) for complete schema.

### Key Tables
- `users` & `user_profiles` - Authentication & stats
- `game_modes`, `game_rooms`, `game_sessions` - Game management
- `trivia_questions`, `trivia_answers` - Question bank
- `wordle_words`, `wordle_attempts` - Word games
- `sports_events`, `predictions` - Sports section
- `leaderboards`, `leaderboard_entries` - Rankings
- `ai_generated_questions` - AI content queue

---

## 🔐 Authentication

### Registration
```bash
POST /api/auth/register
{
  "username": "player1",
  "email": "player1@example.com",
  "password": "securepass123"
}
```

### Login
```bash
POST /api/auth/login
{
  "username": "player1",
  "password": "securepass123"
}
```

Returns:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### Protected Endpoints
Add header: `Authorization: Bearer {access_token}`

---

## 🎮 WebSocket API

### Connect to Game Room
```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/game/${roomCode}?token=${accessToken}`);
```

### Message Format
```javascript
// Client → Server
{
  "type": "answer",
  "data": {
    "answer_id": 123,
    "time_taken": 15
  }
}

// Server → Client
{
  "type": "score_update",
  "data": {
    "user_id": 1,
    "score": 500
  }
}
```

### Event Types
- `ready` - Mark player ready
- `answer` - Submit answer
- `buzz` - Jeopardy buzzer
- `chat` - Chat message
- `start_game` - Host starts game
- `score_update` - Live score broadcast
- `question_reveal` - New question
- `timer_start` - Countdown timer

---

## 🤖 AI Integration

### Generate Questions
```python
from app.services.ai_service import ai_service

questions = await ai_service.generate_trivia_questions(
    category="Science",
    difficulty="medium",
    count=5
)
```

### Admin Workflow
1. Admin triggers AI generation
2. Questions saved to `ai_generated_questions` table with `status='pending'`
3. Admin reviews in admin panel
4. Approved questions moved to `trivia_questions` table
5. Rejected questions marked `status='rejected'`

### Customization
Edit `backend/app/services/ai_service.py` to adjust:
- Prompt engineering
- Response parsing
- Quality validation
- Category suggestions

---

## 📊 API Endpoints

### Authentication
- `POST /api/auth/register` - Register user
- `POST /api/auth/login` - Login
- `POST /api/auth/refresh` - Refresh token
- `GET /api/auth/me` - Get current user

### Users
- `GET /api/users/profile` - Get user profile
- `PUT /api/users/profile` - Update profile
- `GET /api/users/{id}/stats` - Get user stats

### Trivia
- `GET /api/trivia/questions` - List questions
- `POST /api/trivia/questions` - Create question
- `GET /api/trivia/categories` - List categories

### Games
- `POST /api/games/rooms` - Create game room
- `GET /api/games/rooms/{code}` - Get room details
- `POST /api/games/sessions` - Start game session

### Leaderboards
- `GET /api/leaderboards/global` - Global rankings
- `GET /api/leaderboards/friends` - Friends rankings

### Admin
- `GET /api/admin/questions/pending` - Pending AI questions
- `POST /api/admin/questions/{id}/approve` - Approve question
- `POST /api/admin/ai/generate` - Trigger AI generation

Full API docs: http://localhost:8000/docs

---

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

### E2E Tests
```bash
npm run test:e2e
```

---

## 📈 Performance

### Caching Strategy
- **Redis** for:
  - Game session state (1 hour TTL)
  - Leaderboards (5 min TTL)
  - Active rooms (2 hour TTL)
  - User sessions

### Database Optimization
- Indexes on all foreign keys
- Composite indexes for common queries
- Connection pooling (10 connections + 20 overflow)
- Query result caching

### Frontend Optimization
- Code splitting by route
- Lazy loading components
- Image optimization
- TailwindCSS purging

---

## 🔒 Security

### Implemented
- ✅ JWT authentication with refresh tokens
- ✅ Password hashing (bcrypt)
- ✅ CORS protection
- ✅ SQL injection prevention (ORM)
- ✅ Rate limiting
- ✅ Input validation (Pydantic)
- ✅ XSS protection
- ✅ HTTPS ready
- ✅ Secure WebSocket connections

### Environment Variables
Never commit:
- `SECRET_KEY`
- `DATABASE_URL` with credentials
- `GEMINI_API_KEY`
- `REDIS_PASSWORD`

---

## 📦 Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive guide including:
- Local development setup
- Docker deployment
- VPS/Cloud deployment (AWS, DigitalOcean)
- Platform-as-a-Service (Heroku, Railway, Render)
- Kubernetes setup
- CI/CD pipeline
- SSL configuration
- Monitoring & logging
- Backup strategy

### Quick Production Deploy

```bash
# On server
git clone <repo>
cd game-platform
cp backend/.env.example backend/.env
# Edit .env with production values

# Start with Docker
docker-compose -f docker-compose.prod.yml up -d

# Setup Nginx + SSL
sudo certbot --nginx -d svidnet.com
```

---

## 🎨 Branding

**Recommended Brand**: **SvidNet Arena**

**Tagline**: "Where Smart Players Compete"

See [BRAND_NAMES.md](BRAND_NAMES.md) for:
- 10+ brand name options
- Logo concepts
- Color schemes
- Domain strategies
- Brand voice guidelines

---

## 🛣️ Roadmap

### Phase 1: MVP (Current)
- [x] Core authentication
- [x] Basic trivia game
- [x] Multiplayer rooms
- [x] WebSocket infrastructure
- [x] AI integration
- [x] Admin panel skeleton

### Phase 2: Enhancement
- [ ] Complete all game modes
- [ ] Mobile app (React Native)
- [ ] Advanced analytics
- [ ] Tournament system
- [ ] In-app purchases
- [ ] Push notifications

### Phase 3: Scale
- [ ] Microservices architecture
- [ ] GraphQL API
- [ ] Machine learning recommendations
- [ ] Video/voice chat
- [ ] Streaming integration (Twitch)
- [ ] Esports features

---

## 🤝 Contributing

### Development Workflow
1. Fork repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

### Code Style
- **Backend**: Follow PEP 8
- **Frontend**: ESLint config provided
- **Commits**: Conventional Commits format

---

## 📄 License

This project is proprietary. All rights reserved.

---

## 🙏 Acknowledgments

- **FastAPI** - Modern Python web framework
- **React** - UI library
- **Google Gemini** - AI integration
- **PostgreSQL** - Robust database
- **Redis** - Fast caching
- **TailwindCSS** - Utility-first CSS

---

## 📞 Support

- **Email**: support@svidnet.com
- **Discord**: [Join our community](#)
- **Documentation**: [docs.svidnet.com](#)
- **Issues**: GitHub Issues

---

## 🚀 Get Started Now!

```bash
# Clone
git clone <your-repo>

# Start
cd game-platform
docker-compose up -d

# Play
open http://localhost:3000
```

**Let the games begin! 🎮**
