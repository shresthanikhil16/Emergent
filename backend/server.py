from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Game Models
class Player(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    current_level: int = Field(default=1)
    score: int = Field(default=0)
    lives: int = Field(default=3)
    difficulty_level: float = Field(default=1.0)  # AI difficulty multiplier
    total_deaths: int = Field(default=0)
    total_play_time: float = Field(default=0.0)  # in seconds
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class PlayerCreate(BaseModel):
    name: str

class GameSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    player_id: str
    level: int
    score: int
    deaths: int
    completion_time: float  # in seconds
    difficulty_level: float
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class GameSessionCreate(BaseModel):
    player_id: str
    level: int
    score: int
    deaths: int
    completion_time: float
    difficulty_level: float
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)

class PlayerPerformance(BaseModel):
    player_id: str
    avg_completion_time: float
    avg_deaths_per_level: float
    success_rate: float
    difficulty_progression: float
    suggested_difficulty: float

class GameState(BaseModel):
    player_id: str
    current_level: int
    score: int
    lives: int
    mario_position: Dict[str, float]
    enemies: List[Dict[str, Any]]
    power_ups: List[Dict[str, Any]]
    difficulty_settings: Dict[str, Any]

# AI Difficulty Calculation Functions
def calculate_difficulty_adjustment(sessions: List[GameSession]) -> float:
    """Calculate AI difficulty adjustment based on player performance"""
    if not sessions:
        return 1.0
    
    recent_sessions = sessions[-5:]  # Last 5 sessions
    
    avg_deaths = sum(s.deaths for s in recent_sessions) / len(recent_sessions)
    avg_completion_time = sum(s.completion_time for s in recent_sessions) / len(recent_sessions)
    
    # If player is dying too much, reduce difficulty
    if avg_deaths > 3:
        return max(0.5, recent_sessions[-1].difficulty_level - 0.2)
    
    # If player is completing levels too quickly with few deaths, increase difficulty
    if avg_deaths < 1 and avg_completion_time < 30:
        return min(2.0, recent_sessions[-1].difficulty_level + 0.3)
    
    # Moderate adjustment based on performance
    performance_score = (1 / max(avg_deaths, 0.1)) * (60 / max(avg_completion_time, 1))
    
    if performance_score > 2:
        return min(2.0, recent_sessions[-1].difficulty_level + 0.1)
    elif performance_score < 0.5:
        return max(0.5, recent_sessions[-1].difficulty_level - 0.1)
    
    return recent_sessions[-1].difficulty_level

def generate_level_config(level: int, difficulty: float) -> Dict[str, Any]:
    """Generate level configuration based on difficulty"""
    base_enemy_count = 3 + (level - 1)
    base_enemy_speed = 1.0
    base_jump_gaps = 2
    
    return {
        "enemy_count": int(base_enemy_count * difficulty),
        "enemy_speed": base_enemy_speed * difficulty,
        "jump_gaps": int(base_jump_gaps * difficulty),
        "platform_spacing": max(100, 150 - (difficulty * 30)),
        "power_up_frequency": max(0.3, 1.0 - (difficulty * 0.3)),
        "level_length": 800 + (level * 200)
    }

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Mario AI Game API"}

@api_router.post("/player", response_model=Player)
async def create_player(player_data: PlayerCreate):
    """Create a new player"""
    player = Player(**player_data.dict())
    await db.players.insert_one(player.dict())
    return player

@api_router.get("/player/{player_id}", response_model=Player)
async def get_player(player_id: str):
    """Get player by ID"""
    player_data = await db.players.find_one({"id": player_id})
    if not player_data:
        raise HTTPException(status_code=404, detail="Player not found")
    return Player(**player_data)

@api_router.put("/player/{player_id}", response_model=Player)
async def update_player(player_id: str, updates: Dict[str, Any]):
    """Update player data"""
    updates["updated_at"] = datetime.utcnow()
    result = await db.players.update_one({"id": player_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Player not found")
    
    player_data = await db.players.find_one({"id": player_id})
    return Player(**player_data)

@api_router.post("/game-session", response_model=GameSession)
async def create_game_session(session_data: GameSessionCreate):
    """Record a game session"""
    session = GameSession(**session_data.dict())
    await db.game_sessions.insert_one(session.dict())
    
    # Update player stats
    player_data = await db.players.find_one({"id": session_data.player_id})
    if player_data:
        updates = {
            "total_deaths": player_data.get("total_deaths", 0) + session_data.deaths,
            "total_play_time": player_data.get("total_play_time", 0) + session_data.completion_time,
            "updated_at": datetime.utcnow()
        }
        await db.players.update_one({"id": session_data.player_id}, {"$set": updates})
    
    return session

@api_router.get("/player/{player_id}/performance", response_model=PlayerPerformance)
async def get_player_performance(player_id: str):
    """Get player performance analytics"""
    sessions_cursor = db.game_sessions.find({"player_id": player_id}).sort("created_at", -1)
    sessions_data = await sessions_cursor.to_list(20)  # Last 20 sessions
    
    if not sessions_data:
        return PlayerPerformance(
            player_id=player_id,
            avg_completion_time=60.0,
            avg_deaths_per_level=2.0,
            success_rate=0.5,
            difficulty_progression=1.0,
            suggested_difficulty=1.0
        )
    
    sessions = [GameSession(**session) for session in sessions_data]
    
    avg_completion_time = sum(s.completion_time for s in sessions) / len(sessions)
    avg_deaths = sum(s.deaths for s in sessions) / len(sessions)
    success_rate = len([s for s in sessions if s.deaths < 3]) / len(sessions)
    
    suggested_difficulty = calculate_difficulty_adjustment(sessions)
    
    return PlayerPerformance(
        player_id=player_id,
        avg_completion_time=avg_completion_time,
        avg_deaths_per_level=avg_deaths,
        success_rate=success_rate,
        difficulty_progression=sessions[-1].difficulty_level if sessions else 1.0,
        suggested_difficulty=suggested_difficulty
    )

@api_router.get("/level/{level_number}/config")
async def get_level_config(level_number: int, player_id: str):
    """Get level configuration with AI difficulty adjustment"""
    # Get player's current difficulty level
    player_data = await db.players.find_one({"id": player_id})
    difficulty = player_data.get("difficulty_level", 1.0) if player_data else 1.0
    
    # Get recent performance to adjust difficulty
    performance = await get_player_performance(player_id)
    adjusted_difficulty = performance.suggested_difficulty
    
    # Update player's difficulty level
    if player_data:
        await db.players.update_one(
            {"id": player_id}, 
            {"$set": {"difficulty_level": adjusted_difficulty}}
        )
    
    # Generate level configuration
    config = generate_level_config(level_number, adjusted_difficulty)
    config["difficulty_level"] = adjusted_difficulty
    
    return config

@api_router.post("/game-state")
async def save_game_state(game_state: GameState):
    """Save current game state"""
    await db.game_states.replace_one(
        {"player_id": game_state.player_id}, 
        game_state.dict(), 
        upsert=True
    )
    return {"status": "saved"}

@api_router.get("/game-state/{player_id}")
async def get_game_state(player_id: str):
    """Get saved game state"""
    state = await db.game_states.find_one({"player_id": player_id})
    if not state:
        raise HTTPException(status_code=404, detail="Game state not found")
    
    # Remove MongoDB _id field for JSON serialization
    if "_id" in state:
        del state["_id"]
    
    return state

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()