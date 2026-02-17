# 🎓 5th Grade Trivia Game - Setup Guide

## Game Features

✅ **AI-Generated Questions** using Google Gemini API
✅ **Multiple Categories**: General, Science, Math, History, Geography
✅ **Flexible Game Length**: 5-20 questions per game
✅ **Real-Time Scoring**: Points, accuracy tracking, and timers
✅ **Kid-Friendly**: Age-appropriate questions and explanations
✅ **Leaderboards**: Track best scores and fastest times
✅ **Fallback Questions**: Works even without API key

---

## How to Play

1. **Access the Game:**
   ```
   https://svidnet-games-production.up.railway.app/trivia
   ```

2. **Select Options:**
   - Choose a category (General, Science, Math, History, Geography)
   - Pick number of questions (5, 10, 15, or 20)
   - Click "Start Game"

3. **Answer Questions:**
   - Read the question carefully
   - Click your answer (A, B, C, or D)
   - See instant feedback with explanations
   - Click "Next Question" to continue

4. **View Results:**
   - Final score (10 points per correct answer)
   - Accuracy percentage
   - Total time taken
   - Option to play again

---

## Setting Up Gemini AI (Optional)

The game works with fallback questions by default, but for unlimited AI-generated questions:

### 1. Get Gemini API Key

1. Go to: https://makersuite.google.com/app/apikey
2. Click **"Create API Key"**
3. Select a Google Cloud project (or create new one)
4. Copy your API key (starts with `AIza...`)

### 2. Add to Railway Environment Variables

In Railway Dashboard:
1. Go to your service → **Variables** tab
2. Click **"+ New Variable"**
3. Add:
   ```
   GEMINI_API_KEY=AIzaSy...your_key_here
   ```
4. Railway will auto-redeploy with AI question generation enabled

---

## API Endpoints

### Start a New Game
```http
POST /api/trivia/start
Content-Type: application/json

{
  "category": "science",
  "difficulty": "5th_grade",
  "num_questions": 10
}
```

**Response:**
```json
{
  "game_id": 1,
  "category": "science",
  "total_questions": 10,
  "first_question": {
    "question": "What is the largest planet?",
    "options": ["Earth", "Jupiter", "Saturn", "Mars"],
    "category": "science"
  },
  "current_index": 0
}
```

### Submit an Answer
```http
POST /api/trivia/games/{game_id}/answer
Content-Type: application/json

{
  "selected_answer": 1,
  "time_taken_seconds": 15
}
```

**Response:**
```json
{
  "is_correct": true,
  "correct_answer": 1,
  "explanation": "Jupiter is the largest planet!",
  "current_score": 10,
  "correct_count": 1,
  "wrong_count": 0,
  "next_question": { ... },
  "game_completed": false
}
```

### Get Game Stats
```http
GET /api/trivia/games/{game_id}/stats
```

### Get Leaderboard
```http
GET /api/trivia/leaderboard/{category}?limit=10
```

**Response:**
```json
{
  "category": "science",
  "entries": [
    {
      "rank": 1,
      "username": "player1",
      "best_score": 100,
      "best_accuracy": 100,
      "total_games": 5,
      "fastest_time": 120
    }
  ],
  "user_rank": 3,
  "total_players": 25
}
```

---

## Database Schema

### TriviaGame
- `id`: Game identifier
- `user_id`: Player ID
- `category`: Question category
- `total_questions`: Number of questions
- `questions_data`: JSON array of questions
- `score`: Current score (10 points per correct)
- `correct_answers`: Count of correct answers
- `time_started`: Game start timestamp
- `time_completed`: Game end timestamp
- `is_completed`: Boolean completion status

### TriviaAnswer
- Individual answers with timing and correctness

### TriviaLeaderboard
- Best scores per category per user
- Accuracy percentages
- Fastest completion times
- Total games played

---

## Fallback Questions

Without a Gemini API key, the game uses 10 pre-loaded questions covering:
- Science (planets, plants, gases)
- Geography (continents, oceans, capitals)
- Math (multiplication, percentages, geometry)
- History (US Presidents)

These ensure the game is always playable!

---

## Future Enhancements

🎯 **Planned Features:**
- Multiplayer trivia battles
- Daily challenges
- Achievement system
- Custom difficulty levels
- Question reporting/flagging
- Parent/teacher dashboard
- Progress tracking over time

---

## Troubleshooting

### "Failed to generate trivia questions"
- **Without API key**: Falls back to default questions automatically
- **With API key**: Check that key is valid and not rate-limited

### Game not loading
- Ensure you're on `/trivia` endpoint
- Check browser console for errors
- Verify Railway deployment is running

### Questions too hard/easy
- Currently optimized for 5th grade (ages 10-11)
- Future updates will add difficulty settings

---

## Support

Found a bug? Have suggestions?
- Create an issue on GitHub
- Contact: support@svidnet.com

Enjoy learning! 🎓✨
