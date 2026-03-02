#!/bin/bash

# Deployment script for Page Access Control System
# This will push changes to GitHub and trigger Railway auto-deploy

set -e

echo "🚀 Deploying Page Access Control System..."
echo ""

# Check if we're in a git repo
if [ ! -d .git ]; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Show current status
echo "📊 Current git status:"
git status --short
echo ""

# Check if there are any uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  Warning: You have uncommitted changes"
    echo "   All changes for page access control should already be committed"
    echo ""
    read -p "Do you want to continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled"
        exit 1
    fi
fi

# Show the commits that will be pushed
echo "📦 Commits to be pushed:"
git log origin/main..HEAD --oneline
echo ""

# Confirm deployment
read -p "Push to GitHub and trigger Railway deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 1
fi

# Push to GitHub
echo "⬆️  Pushing to GitHub..."
git push origin main

echo ""
echo "✅ Successfully pushed to GitHub!"
echo ""
echo "🚂 Railway will now automatically deploy your changes"
echo "   Monitor the deployment at: https://railway.app"
echo ""
echo "📝 Don't forget to run the database migration:"
echo "   1. Go to Railway dashboard"
echo "   2. Open your PostgreSQL database"
echo "   3. Connect and run:"
echo "      psql \$DATABASE_URL -f backend/migrations/add_page_access_control.sql"
echo ""
echo "   Or run it from your backend service terminal:"
echo "      python -c 'import asyncio; from app.db.session import engine; asyncio.run(engine.dispose())'"
echo "      # Then run the migration SQL"
echo ""
