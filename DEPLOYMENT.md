# 🚀 Deployment Guide

## Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional but recommended)

---

## Option 1: Docker Compose (Recommended for Development)

### 1. Clone the repository
```bash
git clone <your-repo>
cd game-platform
```

### 2. Create environment file
```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set:
- `SECRET_KEY`: Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- `GEMINI_API_KEY`: Your Google Gemini API key

### 3. Start all services
```bash
docker-compose up -d
```

This will start:
- PostgreSQL on port 5432
- Redis on port 6379
- Backend API on port 8000
- Frontend on port 3000

### 4. Initialize database
```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Seed initial data (optional)
docker-compose exec backend python scripts/seed_database.py
```

### 5. Access the application
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Option 2: Manual Setup

### Backend Setup

1. **Create virtual environment**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Setup PostgreSQL**
```bash
# Create database
createdb gamedb

# Or using psql
psql -U postgres
CREATE DATABASE gamedb;
CREATE USER gameuser WITH PASSWORD 'gamepass';
GRANT ALL PRIVILEGES ON DATABASE gamedb TO gameuser;
\q
```

4. **Setup Redis**
```bash
# Start Redis (if not running)
redis-server
```

5. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your settings
```

6. **Run migrations**
```bash
alembic upgrade head
```

7. **Start backend**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

1. **Install dependencies**
```bash
cd frontend
npm install
```

2. **Configure environment**
```bash
# Create .env file
echo "VITE_API_URL=http://localhost:8000" > .env
```

3. **Start frontend**
```bash
npm run dev
```

---

## Production Deployment

### 1. VPS/Cloud Server (DigitalOcean, AWS EC2, etc.)

#### A. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose -y

# Install Nginx
sudo apt install nginx -y
```

#### B. Clone and Configure

```bash
# Clone repository
git clone <your-repo> /var/www/game-platform
cd /var/www/game-platform

# Set environment variables
cp backend/.env.example backend/.env
nano backend/.env
# Set production values (strong SECRET_KEY, secure passwords, etc.)
```

#### C. Nginx Configuration

Create `/etc/nginx/sites-available/game-platform`:

```nginx
server {
    listen 80;
    server_name svidnet.com www.svidnet.com;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/game-platform /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### D. SSL with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d svidnet.com -d www.svidnet.com
```

#### E. Start Application

```bash
# Production docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

### 2. Platform-as-a-Service (Heroku, Railway, Render)

#### Railway Deployment

1. Create `railway.json`:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "numReplicas": 1,
    "restartPolicyType": "ON_FAILURE"
  }
}
```

2. Add environment variables in Railway dashboard
3. Deploy via GitHub integration

#### Render Deployment

Create `render.yaml`:
```yaml
services:
  - type: web
    name: game-platform-api
    env: python
    buildCommand: "pip install -r backend/requirements.txt"
    startCommand: "cd backend && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT"
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: gamedb
          property: connectionString
      - key: REDIS_URL
        fromService:
          name: redis
          type: redis
          property: connectionString

  - type: web
    name: game-platform-frontend
    env: node
    buildCommand: "cd frontend && npm install && npm run build"
    startCommand: "cd frontend && npm run preview"

databases:
  - name: gamedb
    plan: starter

  - name: redis
    plan: starter
```

### 3. Kubernetes (Advanced)

Create Kubernetes manifests in `k8s/` directory:

- `deployment.yaml` - Application deployments
- `service.yaml` - Services
- `ingress.yaml` - Ingress controller
- `configmap.yaml` - Configuration
- `secrets.yaml` - Secrets

Deploy:
```bash
kubectl apply -f k8s/
```

---

## Database Migrations

### Create new migration
```bash
cd backend
alembic revision --autogenerate -m "Description of changes"
```

### Apply migrations
```bash
alembic upgrade head
```

### Rollback
```bash
alembic downgrade -1
```

---

## Performance Optimization

### 1. Database
- Enable connection pooling (already configured in SQLAlchemy)
- Add indexes for frequently queried columns
- Use materialized views for leaderboards
- Set up read replicas for scaling

### 2. Redis
- Use Redis for:
  - Session storage
  - Leaderboard caching
  - Active game room data
  - Rate limiting

### 3. Frontend
- Enable code splitting
- Use lazy loading for routes
- Optimize images
- Enable gzip compression in Nginx

### 4. Backend
- Use async/await throughout
- Implement pagination for large datasets
- Cache expensive queries
- Use background tasks for heavy operations (Celery)

---

## Monitoring & Logging

### Application Monitoring

1. **Sentry** for error tracking
```bash
pip install sentry-sdk
```

2. **Prometheus + Grafana** for metrics
```bash
pip install prometheus-fastapi-instrumentator
```

3. **ELK Stack** for logs

### Health Checks

Backend health endpoint: `GET /health`

Monitor:
- Database connectivity
- Redis connectivity
- API response times
- WebSocket connections

---

## Backup Strategy

### Database Backups

```bash
# Automated daily backup
0 2 * * * pg_dump -U gameuser gamedb | gzip > /backups/gamedb_$(date +\%Y\%m\%d).sql.gz
```

### Redis Snapshots

Configure in `redis.conf`:
```
save 900 1
save 300 10
save 60 10000
```

---

## Scaling Strategy

### Horizontal Scaling

1. **Load Balancer** - Distribute traffic across multiple backend instances
2. **Database Replication** - Primary + read replicas
3. **Redis Cluster** - Distribute cache across nodes
4. **CDN** - CloudFlare/AWS CloudFront for static assets

### Vertical Scaling

- Upgrade server resources (CPU, RAM)
- Optimize database queries
- Increase connection pool sizes

---

## Security Checklist

- [ ] Use HTTPS (SSL certificate)
- [ ] Strong SECRET_KEY in production
- [ ] Secure database passwords
- [ ] Enable CORS only for trusted origins
- [ ] Implement rate limiting
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (using ORM)
- [ ] XSS protection
- [ ] CSRF tokens for forms
- [ ] Regular security updates
- [ ] Firewall configuration
- [ ] Backup encryption

---

## Troubleshooting

### Backend won't start
```bash
# Check logs
docker-compose logs backend

# Verify database connection
docker-compose exec backend python -c "from app.db.session import engine; print(engine.connect())"
```

### WebSocket not connecting
- Check CORS settings
- Verify WebSocket URL in frontend
- Check Nginx WebSocket proxy configuration

### Database migrations failing
```bash
# Reset migrations (development only!)
docker-compose exec backend alembic downgrade base
docker-compose exec backend alembic upgrade head
```

---

## Environment Variables Reference

### Backend
```
DATABASE_URL - PostgreSQL connection string
REDIS_URL - Redis connection string
SECRET_KEY - JWT secret (generate strong key)
GEMINI_API_KEY - Google Gemini API key
ENVIRONMENT - development/staging/production
DEBUG - True/False
CORS_ORIGINS - Comma-separated allowed origins
```

### Frontend
```
VITE_API_URL - Backend API URL
```

---

## CI/CD Pipeline (GitHub Actions Example)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /var/www/game-platform
            git pull origin main
            docker-compose down
            docker-compose up -d --build
```

---

## Support & Maintenance

- Monitor error logs daily
- Review performance metrics weekly
- Update dependencies monthly
- Backup database daily
- Test disaster recovery quarterly
