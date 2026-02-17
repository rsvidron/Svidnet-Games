#!/bin/bash

# Setup script for SvidNet Arena Game Platform
# Run this to set up your development environment

set -e

echo "🎮 SvidNet Arena - Development Setup"
echo "===================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose found"
echo ""

# Create .env file if it doesn't exist
if [ ! -f backend/.env ]; then
    echo "📝 Creating backend/.env file..."
    cp backend/.env.example backend/.env

    # Generate SECRET_KEY
    if command -v python3 &> /dev/null; then
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
        sed -i.bak "s/your-super-secret-key-change-this-in-production/$SECRET_KEY/" backend/.env
        rm backend/.env.bak 2>/dev/null || true
        echo "   ✅ Generated SECRET_KEY"
    else
        echo "   ⚠️  Please manually set SECRET_KEY in backend/.env"
    fi

    echo ""
    echo "⚠️  IMPORTANT: Edit backend/.env and set your GEMINI_API_KEY"
    echo "   Get your API key from: https://makersuite.google.com/app/apikey"
    echo ""
    read -p "Press Enter when you've added your GEMINI_API_KEY..."
else
    echo "✅ backend/.env already exists"
fi

# Create frontend .env
if [ ! -f frontend/.env ]; then
    echo "📝 Creating frontend/.env file..."
    echo "VITE_API_URL=http://localhost:8000" > frontend/.env
    echo "   ✅ Created frontend/.env"
fi

echo ""
echo "🐳 Starting Docker containers..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

echo ""
echo "🗄️  Running database migrations..."
docker-compose exec -T backend alembic upgrade head

echo ""
echo "🌱 Seeding database with sample data..."
cat << 'EOF' | docker-compose exec -T backend python
from app.db.session import SessionLocal
from app.models.user import User, UserProfile
from app.models.trivia import Category
from app.core.security import get_password_hash

db = SessionLocal()

# Create admin user
admin = User(
    username="admin",
    email="admin@svidnet.com",
    hashed_password=get_password_hash("admin123"),
    role="admin",
    is_active=True,
    is_verified=True
)
db.add(admin)
db.commit()

# Create test user
user = User(
    username="player1",
    email="player1@svidnet.com",
    hashed_password=get_password_hash("password123"),
    role="user",
    is_active=True,
    is_verified=True
)
db.add(user)
db.commit()

print("✅ Created users: admin (password: admin123), player1 (password: password123)")

# Create sample categories
categories = [
    {"name": "Science", "description": "General science questions", "difficulty_level": "medium"},
    {"name": "History", "description": "World history trivia", "difficulty_level": "medium"},
    {"name": "Sports", "description": "Sports knowledge", "difficulty_level": "easy"},
    {"name": "Geography", "description": "World geography", "difficulty_level": "hard"},
    {"name": "Pop Culture", "description": "Movies, music, and entertainment", "difficulty_level": "easy"}
]

for cat_data in categories:
    cat = Category(**cat_data, is_active=True)
    db.add(cat)

db.commit()
print("✅ Created sample categories")

db.close()
EOF

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎮 Your game platform is ready!"
echo ""
echo "Access points:"
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo ""
echo "Test credentials:"
echo "  Admin:  admin / admin123"
echo "  User:   player1 / password123"
echo ""
echo "Useful commands:"
echo "  docker-compose logs -f         # View logs"
echo "  docker-compose down            # Stop all services"
echo "  docker-compose restart         # Restart services"
echo ""
echo "Happy coding! 🚀"
