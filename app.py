from flask import Flask, render_template, jsonify, request
import random
from datetime import datetime
from pymongo import MongoClient
import os

app = Flask(__name__)

# MongoDB Configuration
MONGO_URI = os.getenv('MONGO_URI', 'mongodb+srv://vgugan16:gugan2004@cluster0.qyh1fuo.mongodb.net/casino?retryWrites=true&w=majority')
DB_NAME = 'game_theory_db'
AI_COUNTER = 1

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    client.admin.command('ping')
    print("✓ MongoDB Connected Successfully")
except Exception as e:
    print(f"✗ MongoDB Connection Error: {e}")
    db = None

def get_players_collection():
    return db['players_stats'] if db is not None else None

def get_games_collection(game_id):
    return db[f'game_{game_id}'] if db is not None else None

def get_next_ai_sequence():
    global AI_COUNTER
    players_col = get_players_collection()
    
    # CHECK DB FOR EXISTING AI NAMES FIRST
    while True:
        ai_name = f"KyloBot{AI_COUNTER}"
        
        if players_col is not None:
            existing_ai = players_col.find_one({"username": ai_name})
            if existing_ai:  # AI EXISTS, MOVE TO NEXT
                print(f"⚠️ AI {ai_name} exists, trying next...")
                AI_COUNTER += 1
                continue
        
        # NEW AI - CREATE IT
        if db is not None and players_col is not None:
            players_col.update_one(
                {"username": ai_name},
                {"$setOnInsert": {
                    "username": ai_name,
                    "total_score": 0,
                    "rounds_played": 0,
                    "last_update_time": datetime.now(),
                    "is_bot": True,
                    "ai_id": AI_COUNTER
                }},
                upsert=True
            )
        
        print(f"🎲 NEW AI ASSIGNED: {ai_name} (#{AI_COUNTER})")
        AI_COUNTER += 1
        return ai_name

def get_game_collection(username, ai_name):
    game_id = f"{username}_vs_{ai_name}".replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")
    game_col = get_games_collection(game_id)
    
    if db is not None and game_col is not None:
        try:
            game_col.create_index([("game_id", 1), ("round_number", 1)], unique=True)
        except:
            pass
    
    return game_col, game_id

def store_game_move(game_col, game_id, round_num, player_name, player_dice, 
                    player_score, ai_name, ai_dice, ai_score, player_cumulative, ai_cumulative):
    if game_col is None:
        return
    
    move_record = {
        "game_id": game_id,
        "round_number": round_num,
        "timestamp": datetime.now(),
        "player": {"name": player_name, "dice": player_dice, "round_score": player_score, "cumulative_score": player_cumulative},
        "ai": {"name": ai_name, "dice": ai_dice, "round_score": ai_score, "cumulative_score": ai_cumulative},
        "payoff": {"player_wins": player_score > ai_score, "ai_wins": ai_score > player_score, "draw": player_score == ai_score}
    }
    
    try:
        game_col.replace_one({"game_id": game_id, "round_number": round_num}, move_record, upsert=True)
    except Exception as e:
        print(f"⚠ Save warning: {e}")

def get_leaderboard():
    if db is None:
        return []
    
    players_col = get_players_collection()
    if players_col is None:
        return []
        
    try:
        leaderboard = list(players_col.find(
            {},
            {"username": 1, "total_score": 1, "rounds_played": 1, "is_bot": 1}
        ).sort([("total_score", -1), ("last_update_time", 1)]).limit(20))
        
        for player in leaderboard:
            player['_id'] = str(player['_id'])
        return leaderboard
    except:
        return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/set-username', methods=['POST'])
def set_username():
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    data = request.json
    username = data.get('username', '').strip()
    
    if not username or len(username) < 2 or len(username) > 20:
        return jsonify({"error": "Username must be 2-20 characters"}), 400
    
    players_col = get_players_collection()
    if players_col is None:
        return jsonify({"error": "Database error"}), 500
        
    player_doc = players_col.find_one({"username": username})
    
    assigned_ai = get_next_ai_sequence()
    
    if not player_doc:
        players_col.insert_one({
            "username": username,
            "assigned_ai": assigned_ai,
            "total_score": 0,
            "rounds_played": 0,
            "last_update_time": datetime.now(),
            "is_bot": False
        })
        player_doc = {"rounds_played": 0}
    
    print(f"✅ Player '{username}' assigned to {assigned_ai}")
    return jsonify({
        "success": True,
        "username": username,
        "ai_name": assigned_ai,
        "rounds_played": player_doc.get('rounds_played', 0),
        "done": player_doc.get('rounds_played', 0) >= 10
    })

@app.route('/roll', methods=['POST'])
def roll():
    if db is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    data = request.json
    username = data.get('username')
    if not username:
        return jsonify({"error": "Username required"}), 400

    players_col = get_players_collection()
    if players_col is None:
        return jsonify({"error": "Database error"}), 500
        
    player_doc = players_col.find_one({"username": username})
    if not player_doc:
        return jsonify({"error": "Player not found"}), 404
    
    rounds_played = player_doc.get('rounds_played', 0)
    if rounds_played >= 10:
        return jsonify({"error": "You have completed your 10 rounds!", "done": True}), 200

    current_ai = player_doc['assigned_ai']
    game_col, game_id = get_game_collection(username, current_ai)
    
    player_dice = [random.randint(1, 6) for _ in range(3)]
    player_round_score = sum(player_dice)
    ai_dice = [random.randint(1, 6) for _ in range(3)]
    ai_round_score = sum(ai_dice)
    
    new_player_total = player_doc.get('total_score', 0) + player_round_score
    new_player_rounds = rounds_played + 1
    
    players_col.update_one(
        {"username": username},
        {"$set": {
            "total_score": new_player_total,
            "rounds_played": new_player_rounds,
            "assigned_ai": current_ai,
            "last_update_time": datetime.now()
        }}
    )
    
    ai_doc = players_col.find_one({"username": current_ai})
    new_ai_total = (ai_doc.get('total_score', 0) if ai_doc else 0) + ai_round_score
    new_ai_rounds = (ai_doc.get('rounds_played', 0) if ai_doc else 0) + 1
    
    players_col.update_one(
        {"username": current_ai},
        {"$set": {
            "total_score": new_ai_total,
            "rounds_played": new_ai_rounds,
            "last_update_time": datetime.now()
        }},
        upsert=True
    )
    
    store_game_move(game_col, game_id, new_player_rounds, username, player_dice, 
                   player_round_score, current_ai, ai_dice, ai_round_score, new_player_total, new_ai_total)

    return jsonify({
        "player_dice": player_dice,
        "player_total": player_round_score,
        "cumulative_score": new_player_total,
        "rounds_played": new_player_rounds,
        "ai_name": current_ai,
        "bot_dice": ai_dice,
        "bot_total": ai_round_score,
        "bot_cumulative": new_ai_total,
        "leaderboard": get_leaderboard()
    })

@app.route('/leaderboard', methods=['GET'])
def fetch_leaderboard():
    return jsonify(get_leaderboard())

@app.route('/ai-stats/<username>')
def get_ai_stats(username):
    if db is None:
        return jsonify({"ai_rounds_played": 0, "ai_previous_dice": [], "ai_wins": 0, "ai_total_score": 0})
    
    players_col = get_players_collection()
    if players_col is None:
        return jsonify({"ai_rounds_played": 0, "ai_previous_dice": [], "ai_wins": 0, "ai_total_score": 0})
        
    player_doc = players_col.find_one({"username": username})
    if not player_doc:
        return jsonify({"ai_rounds_played": 0, "ai_previous_dice": [], "ai_wins": 0, "ai_total_score": 0})
    
    current_ai = player_doc['assigned_ai']
    game_col, game_id = get_game_collection(username, current_ai)
    
    ai_dice_history = []
    ai_wins = 0
    if game_col is not None:
        all_rounds = list(game_col.find({"game_id": game_id}, {"_id": 0, "ai": 1, "payoff": 1}).sort("round_number", 1))
        ai_dice_history = [r['ai']['dice'] for r in all_rounds[-5:]]
        ai_wins = sum(1 for r in all_rounds if r.get('payoff', {}).get('ai_wins', False))
    
    ai_doc = players_col.find_one({"username": current_ai})
    ai_total_score = ai_doc.get('total_score', 0) if ai_doc else 0
    
    return jsonify({
        "ai_name": current_ai,
        "ai_rounds_played": len(ai_dice_history),
        "ai_previous_dice": ai_dice_history,
        "ai_wins": ai_wins,
        "ai_total_score": ai_total_score
    })
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
