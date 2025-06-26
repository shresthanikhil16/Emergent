import React, { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Game constants
const GAME_CONFIG = {
  CANVAS_WIDTH: 800,
  CANVAS_HEIGHT: 600,
  GRAVITY: 0.5,
  JUMP_FORCE: -12,
  MOVE_SPEED: 5,
  MARIO_WIDTH: 32,
  MARIO_HEIGHT: 32,
  PLATFORM_HEIGHT: 20,
  ENEMY_WIDTH: 24,
  ENEMY_HEIGHT: 24
};

// Game classes
class Mario {
  constructor(x, y) {
    this.x = x;
    this.y = y;
    this.width = GAME_CONFIG.MARIO_WIDTH;
    this.height = GAME_CONFIG.MARIO_HEIGHT;
    this.velocityX = 0;
    this.velocityY = 0;
    this.onGround = false;
    this.lives = 3;
    this.invulnerable = false;
    this.invulnerableTime = 0;
  }

  update() {
    // Apply gravity
    this.velocityY += GAME_CONFIG.GRAVITY;
    
    // Update position
    this.x += this.velocityX;
    this.y += this.velocityY;
    
    // Ground collision
    if (this.y + this.height >= GAME_CONFIG.CANVAS_HEIGHT - 50) {
      this.y = GAME_CONFIG.CANVAS_HEIGHT - 50 - this.height;
      this.velocityY = 0;
      this.onGround = true;
    }
    
    // Screen boundaries
    if (this.x < 0) this.x = 0;
    if (this.x + this.width > GAME_CONFIG.CANVAS_WIDTH) {
      this.x = GAME_CONFIG.CANVAS_WIDTH - this.width;
    }
    
    // Handle invulnerability
    if (this.invulnerable) {
      this.invulnerableTime--;
      if (this.invulnerableTime <= 0) {
        this.invulnerable = false;
      }
    }
    
    // Friction
    this.velocityX *= 0.8;
  }

  jump() {
    if (this.onGround) {
      this.velocityY = GAME_CONFIG.JUMP_FORCE;
      this.onGround = false;
    }
  }

  moveLeft() {
    this.velocityX = -GAME_CONFIG.MOVE_SPEED;
  }

  moveRight() {
    this.velocityX = GAME_CONFIG.MOVE_SPEED;
  }

  takeDamage() {
    if (!this.invulnerable) {
      this.lives--;
      this.invulnerable = true;
      this.invulnerableTime = 120; // 2 seconds at 60fps
      return true;
    }
    return false;
  }

  draw(ctx) {
    // Draw Mario as a red rectangle (simple placeholder)
    ctx.fillStyle = this.invulnerable && Math.floor(this.invulnerableTime / 10) % 2 ? 
      'rgba(255, 0, 0, 0.5)' : '#FF0000';
    ctx.fillRect(this.x, this.y, this.width, this.height);
    
    // Draw eyes
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(this.x + 8, this.y + 8, 4, 4);
    ctx.fillRect(this.x + 20, this.y + 8, 4, 4);
    
    // Draw mustache
    ctx.fillStyle = '#000000';
    ctx.fillRect(this.x + 12, this.y + 16, 8, 2);
  }
}

class Enemy {
  constructor(x, y, speed = 1) {
    this.x = x;
    this.y = y;
    this.width = GAME_CONFIG.ENEMY_WIDTH;
    this.height = GAME_CONFIG.ENEMY_HEIGHT;
    this.velocityX = -speed;
    this.velocityY = 0;
    this.alive = true;
  }

  update() {
    this.velocityY += GAME_CONFIG.GRAVITY;
    this.x += this.velocityX;
    this.y += this.velocityY;
    
    // Ground collision
    if (this.y + this.height >= GAME_CONFIG.CANVAS_HEIGHT - 50) {
      this.y = GAME_CONFIG.CANVAS_HEIGHT - 50 - this.height;
      this.velocityY = 0;
    }
    
    // Reverse direction at screen edges
    if (this.x <= 0 || this.x + this.width >= GAME_CONFIG.CANVAS_WIDTH) {
      this.velocityX *= -1;
    }
  }

  draw(ctx) {
    if (this.alive) {
      ctx.fillStyle = '#8B4513';
      ctx.fillRect(this.x, this.y, this.width, this.height);
      
      // Draw eyes
      ctx.fillStyle = '#FF0000';
      ctx.fillRect(this.x + 4, this.y + 4, 3, 3);
      ctx.fillRect(this.x + 17, this.y + 4, 3, 3);
    }
  }
}

class Platform {
  constructor(x, y, width) {
    this.x = x;
    this.y = y;
    this.width = width;
    this.height = GAME_CONFIG.PLATFORM_HEIGHT;
  }

  draw(ctx) {
    ctx.fillStyle = '#00FF00';
    ctx.fillRect(this.x, this.y, this.width, this.height);
  }
}

// Main Game Component
function MarioGame() {
  const canvasRef = useRef(null);
  const gameLoopRef = useRef(null);
  const keysRef = useRef({});
  
  const [gameState, setGameState] = useState({
    mario: new Mario(50, 400),
    enemies: [],
    platforms: [],
    score: 0,
    level: 1,
    gameOver: false,
    gameStarted: false,
    playerId: null,
    sessionStartTime: null,
    deaths: 0,
    difficultyLevel: 1.0
  });

  const [playerName, setPlayerName] = useState('');
  const [showNameInput, setShowNameInput] = useState(true);

  // Initialize game
  const initializeGame = useCallback(async (playerId, difficultyLevel = 1.0) => {
    try {
      // Get level configuration from AI
      const levelConfig = await axios.get(`${API}/level/1/config?player_id=${playerId}`);
      const config = levelConfig.data;
      
      // Create enemies based on AI difficulty
      const enemies = [];
      for (let i = 0; i < config.enemy_count; i++) {
        enemies.push(new Enemy(
          200 + i * 150, 
          GAME_CONFIG.CANVAS_HEIGHT - 100, 
          config.enemy_speed
        ));
      }
      
      // Create platforms
      const platforms = [
        new Platform(0, GAME_CONFIG.CANVAS_HEIGHT - 50, GAME_CONFIG.CANVAS_WIDTH),
        new Platform(300, 450, 200),
        new Platform(600, 350, 150),
        new Platform(150, 300, 100)
      ];
      
      setGameState(prev => ({
        ...prev,
        mario: new Mario(50, 400),
        enemies,
        platforms,
        score: 0,
        level: 1,
        gameOver: false,
        gameStarted: true,
        playerId,
        sessionStartTime: Date.now(),
        deaths: 0,
        difficultyLevel: config.difficulty_level
      }));
    } catch (error) {
      console.error('Error initializing game:', error);
    }
  }, []);

  // Create player
  const createPlayer = async () => {
    if (!playerName.trim()) return;
    
    try {
      const response = await axios.post(`${API}/player`, { name: playerName });
      const player = response.data;
      setShowNameInput(false);
      await initializeGame(player.id);
    } catch (error) {
      console.error('Error creating player:', error);
    }
  };

  // Collision detection
  const checkCollision = (rect1, rect2) => {
    return rect1.x < rect2.x + rect2.width &&
           rect1.x + rect1.width > rect2.x &&
           rect1.y < rect2.y + rect2.height &&
           rect1.y + rect1.height > rect2.y;
  };

  // Handle Mario-Enemy collision
  const handleEnemyCollision = (mario, enemy) => {
    if (!enemy.alive) return;
    
    // Mario jumping on enemy
    if (mario.velocityY > 0 && mario.y < enemy.y) {
      enemy.alive = false;
      mario.velocityY = GAME_CONFIG.JUMP_FORCE / 2; // Small bounce
      setGameState(prev => ({ ...prev, score: prev.score + 100 }));
    } else {
      // Mario takes damage
      if (mario.takeDamage()) {
        setGameState(prev => ({ ...prev, deaths: prev.deaths + 1 }));
        
        if (mario.lives <= 0) {
          endGame();
        }
      }
    }
  };

  // Handle Mario-Platform collision
  const handlePlatformCollision = (mario, platform) => {
    if (mario.velocityY > 0 && 
        mario.y < platform.y && 
        mario.y + mario.height > platform.y - 10) {
      mario.y = platform.y - mario.height;
      mario.velocityY = 0;
      mario.onGround = true;
    }
  };

  // End game and save session
  const endGame = async () => {
    const sessionData = {
      player_id: gameState.playerId,
      level: gameState.level,
      score: gameState.score,
      deaths: gameState.deaths,
      completion_time: (Date.now() - gameState.sessionStartTime) / 1000,
      difficulty_level: gameState.difficultyLevel,
      performance_metrics: {
        final_score: gameState.score,
        lives_remaining: gameState.mario.lives
      }
    };
    
    try {
      await axios.post(`${API}/game-session`, sessionData);
    } catch (error) {
      console.error('Error saving game session:', error);
    }
    
    setGameState(prev => ({ ...prev, gameOver: true }));
  };

  // Game loop
  const gameLoop = useCallback(() => {
    if (!gameState.gameStarted || gameState.gameOver) return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    
    // Clear canvas
    ctx.clearRect(0, 0, GAME_CONFIG.CANVAS_WIDTH, GAME_CONFIG.CANVAS_HEIGHT);
    
    // Handle input
    if (keysRef.current['ArrowLeft'] || keysRef.current['a']) {
      gameState.mario.moveLeft();
    }
    if (keysRef.current['ArrowRight'] || keysRef.current['d']) {
      gameState.mario.moveRight();
    }
    if (keysRef.current['Space'] || keysRef.current['ArrowUp'] || keysRef.current['w']) {
      gameState.mario.jump();
    }
    
    // Update Mario
    gameState.mario.update();
    
    // Update enemies
    gameState.enemies.forEach(enemy => {
      if (enemy.alive) {
        enemy.update();
        
        // Check collision with Mario
        if (checkCollision(gameState.mario, enemy)) {
          handleEnemyCollision(gameState.mario, enemy);
        }
      }
    });
    
    // Check platform collisions
    gameState.platforms.forEach(platform => {
      if (checkCollision(gameState.mario, platform)) {
        handlePlatformCollision(gameState.mario, platform);
      }
    });
    
    // Draw everything
    // Background
    ctx.fillStyle = '#87CEEB';
    ctx.fillRect(0, 0, GAME_CONFIG.CANVAS_WIDTH, GAME_CONFIG.CANVAS_HEIGHT);
    
    // Platforms
    gameState.platforms.forEach(platform => platform.draw(ctx));
    
    // Mario
    gameState.mario.draw(ctx);
    
    // Enemies
    gameState.enemies.forEach(enemy => enemy.draw(ctx));
    
    // UI
    ctx.fillStyle = '#000000';
    ctx.font = '20px Arial';
    ctx.fillText(`Score: ${gameState.score}`, 10, 30);
    ctx.fillText(`Lives: ${gameState.mario.lives}`, 10, 55);
    ctx.fillText(`Level: ${gameState.level}`, 10, 80);
    ctx.fillText(`Difficulty: ${gameState.difficultyLevel.toFixed(1)}`, 10, 105);
    
    // Check win condition (all enemies defeated)
    const aliveEnemies = gameState.enemies.filter(e => e.alive);
    if (aliveEnemies.length === 0) {
      // Level complete - could advance to next level
      setGameState(prev => ({ ...prev, score: prev.score + 1000 }));
      setTimeout(() => {
        initializeGame(gameState.playerId, gameState.difficultyLevel);
        setGameState(prev => ({ ...prev, level: prev.level + 1 }));
      }, 1000);
    }
    
  }, [gameState, initializeGame]);

  // Set up game loop
  useEffect(() => {
    if (gameState.gameStarted && !gameState.gameOver) {
      gameLoopRef.current = setInterval(gameLoop, 1000 / 60); // 60 FPS
      return () => clearInterval(gameLoopRef.current);
    }
  }, [gameState.gameStarted, gameState.gameOver, gameLoop]);

  // Keyboard event handlers
  useEffect(() => {
    const handleKeyDown = (e) => {
      keysRef.current[e.code] = true;
      if (e.code === 'Space') e.preventDefault();
    };
    
    const handleKeyUp = (e) => {
      keysRef.current[e.code] = false;
    };
    
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, []);

  // Restart game
  const restartGame = () => {
    if (gameState.playerId) {
      initializeGame(gameState.playerId);
    }
  };

  if (showNameInput) {
    return (
      <div className="game-container">
        <div className="name-input-screen">
          <h1>🎮 AI Mario Game</h1>
          <p>Enter your name to start playing!</p>
          <input
            type="text"
            value={playerName}
            onChange={(e) => setPlayerName(e.target.value)}
            placeholder="Enter your name"
            className="name-input"
            onKeyPress={(e) => e.key === 'Enter' && createPlayer()}
          />
          <button onClick={createPlayer} className="start-button">
            Start Game
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="game-container">
      <div className="game-header">
        <h1>🎮 AI Mario Game</h1>
        <p>Use ARROW KEYS or WASD to move, SPACE/UP to jump!</p>
      </div>
      
      <canvas
        ref={canvasRef}
        width={GAME_CONFIG.CANVAS_WIDTH}
        height={GAME_CONFIG.CANVAS_HEIGHT}
        className="game-canvas"
      />
      
      {gameState.gameOver && (
        <div className="game-over-screen">
          <h2>Game Over!</h2>
          <p>Final Score: {gameState.score}</p>
          <p>Level Reached: {gameState.level}</p>
          <p>Deaths: {gameState.deaths}</p>
          <button onClick={restartGame} className="restart-button">
            Play Again
          </button>
        </div>
      )}
      
      <div className="game-instructions">
        <h3>🤖 AI Features:</h3>
        <ul>
          <li>Difficulty automatically adjusts based on your performance</li>
          <li>Enemy count and speed change with your skill level</li>
          <li>The AI learns from your gameplay patterns</li>
          <li>Each level becomes more challenging as you improve</li>
        </ul>
      </div>
    </div>
  );
}

function App() {
  return (
    <div className="App">
      <MarioGame />
    </div>
  );
}

export default App;