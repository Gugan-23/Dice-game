# Game Theory Dice Game - MongoDB Implementation

## Overview
This Flask app implements a dice rolling game with MongoDB for persistent storage. The game tracks payoff matrices for each player vs AI matchup across 10 rounds.

## MongoDB Collections Structure

### 1. **`players_stats` Collection**
Stores player statistics and metadata.

**Schema:**
```json
{
  "_id": ObjectId,
  "username": "string (unique)",
  "total_score": "number",
  "rounds_played": "number",
  "is_bot": "boolean",
  "last_update_time": "datetime"
}
```

**Example:**
```json
{
  "username": "john_doe",
  "total_score": 58,
  "rounds_played": 10,
  "is_bot": false,
  "last_update_time": "2026-02-11T10:30:45.123Z"
}
```

### 2. **`game_{game_id}` Collections** (Payoff Matrix)
One collection per game (player vs AI). Stores all moves and payoffs for that game.

**Naming Convention:** `game_username_vs_KyloBotAI`

**Schema:**
```json
{
  "_id": ObjectId,
  "game_id": "string",
  "round_number": "number (1-10)",
  "timestamp": "datetime",
  "player": {
    "name": "string",
    "dice": [number, number, number],
    "round_score": "number",
    "cumulative_score": "number"
  },
  "ai": {
    "name": "string",
    "dice": [number, number, number],
    "round_score": "number",
    "cumulative_score": "number"
  },
  "payoff": {
    "player_wins": "boolean",
    "ai_wins": "boolean",
    "draw": "boolean"
  }
}
```

**Example Move Record:**
```json
{
  "game_id": "john_doe_vs_KyloBotAI",
  "round_number": 1,
  "timestamp": "2026-02-11T10:30:45.123Z",
  "player": {
    "name": "john_doe",
    "dice": [4, 5, 3],
    "round_score": 12,
    "cumulative_score": 12
  },
  "ai": {
    "name": "KyloBot (AI)",
    "dice": [6, 2, 1],
    "round_score": 9,
    "cumulative_score": 9
  },
  "payoff": {
    "player_wins": true,
    "ai_wins": false,
    "draw": false
  }
}
```

## Setup Instructions

### 1. Install MongoDB
- **Local:** [Download MongoDB](https://www.mongodb.com/try/download/community)
- **Cloud:** Use [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) (free tier available)

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure MongoDB Connection
Edit `.env` file:
```
# Local MongoDB
MONGO_URI=mongodb://localhost:27017/

# MongoDB Atlas (Cloud)
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
```

### 4. Run the Application
```bash
python app.py
```

The app will automatically:
- Connect to MongoDB
- Create the `game_theory_db` database
- Create `players_stats` collection
- Initialize AI player ("KyloBot (AI)")
- Create game-specific collections as players register

## API Endpoints

### `POST /roll`
Roll dice and record move in payoff matrix.

**Request:**
```json
{
  "username": "john_doe"
}
```

**Response:**
```json
{
  "player_dice": [4, 5, 3],
  "player_total": 12,
  "cumulative_score": 58,
  "rounds_played": 10,
  "bot_dice": [6, 2, 1],
  "bot_total": 9,
  "bot_cumulative": 45,
  "leaderboard": [...]
}
```

### `GET /leaderboard`
Fetch top 3 players.

**Response:**
```json
[
  {
    "username": "john_doe",
    "total_score": 58,
    "rounds_played": 10,
    "is_bot": false
  },
  ...
]
```

### `GET /game-history/<username>`
Fetch complete payoff matrix for a player's game.

**Response:**
```json
{
  "game_id": "john_doe_vs_KyloBotAI",
  "player": "john_doe",
  "ai": "KyloBot (AI)",
  "total_rounds": 10,
  "moves": [
    {
      "game_id": "john_doe_vs_KyloBotAI",
      "round_number": 1,
      "timestamp": "2026-02-11T10:30:45.123Z",
      "player": {...},
      "ai": {...},
      "payoff": {...}
    },
    ...
  ]
}
```

## Key Changes from Original Code

1. **Persistent Storage:** Replaced in-memory `users_data` dict with MongoDB
2. **Payoff Matrix:** Each game has a dedicated collection storing all 10 rounds with detailed payoff information
3. **Game Collections:** Separate `game_{player}_vs_{AI}` collections for tracking matchup history
4. **Indexes:** Created indexes on username, game_id, round_number, and timestamp for efficient queries
5. **Game History:** New endpoint to retrieve complete game payoff matrix
6. **Better Error Handling:** MongoDB connection checks and error messages

## Game Flow

```
Player Registers
    ↓
Players_stats collection: Create user document
    ↓
Player Rolls Dice
    ↓
Game_{username}_vs_AI collection: Insert move record with payoff data
    ↓
Update players_stats: Increment score and rounds
    ↓
Return: Dice, scores, and leaderboard
    ↓
After 10 Rounds: Complete game history available in game collection
```

## Querying the Database

### View all players
```javascript
db.players_stats.find()
```

### View game history for a player
```javascript
db.game_john_doe_vs_KyloBotAI.find().sort({round_number: 1})
```

### Get player's final score
```javascript
db.players_stats.findOne({username: "john_doe"})
```

### Analyze payoff matrix (e.g., count wins)
```javascript
db.game_john_doe_vs_KyloBotAI.aggregate([
  {$group: {
    _id: null,
    player_wins: {$sum: {$cond: ["$payoff.player_wins", 1, 0]}},
    ai_wins: {$sum: {$cond: ["$payoff.ai_wins", 1, 0]}},
    draws: {$sum: {$cond: ["$payoff.draw", 1, 0]}}
  }}
])
```

## Requirements
- Python 3.8+
- MongoDB 4.0+
- Flask 3.0.0
- PyMongo 4.6.1
# Dice-game
# Dice-game
