#!/usr/bin/env python3
import time
import random
import threading
import pygame
from multiprocessing import Value, Lock, Queue
from enum import Enum, auto
import sys

# Constants
FPS = 60
PLAYER_SPEED = 5
GRAVITY = 0.5
JUMP_POWER = 12
PLATFORM_COUNT = 8
ENEMY_TYPES = 3
SPAWN_INTERVAL = 3.0  # seconds

class EntityType(Enum):
    PLAYER = auto()
    ENEMY = auto()
    PLATFORM = auto()
    PROJECTILE = auto()
    POWERUP = auto()

class GameState(Enum):
    MENU = 0
    PLAYING = 1
    PAUSED = 2
    GAME_OVER = 3

class Entity:
    def __init__(self, entity_id, entity_type, x, y, width, height):
        self.id = entity_id
        self.type = entity_type
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.velocity_x = 0
        self.velocity_y = 0
        self.health = 100 if entity_type == EntityType.PLAYER else 30
        self.active = True
    
    def update(self):
        self.x += self.velocity_x
        self.y += self.velocity_y
    
    def check_collision(self, other):
        return (self.x < other.x + other.width and
                self.x + self.width > other.x and
                self.y < other.y + other.height and
                self.y + self.height > other.y)

class GameLogicProcess:
    def __init__(self, game_state, player_score, player_health, player_position,
                 game_state_lock, player_score_lock, player_health_lock, player_position_lock,
                 logic_to_render_queue, render_to_logic_queue):
        self.game_state = game_state
        self.player_score = player_score
        self.player_health = player_health
        self.player_position = player_position
        
        self.game_state_lock = game_state_lock
        self.player_score_lock = player_score_lock
        self.player_health_lock = player_health_lock
        self.player_position_lock = player_position_lock
        
        self.logic_to_render_queue = logic_to_render_queue
        self.render_to_logic_queue = render_to_logic_queue
        
        self.entities = {}
        self.entity_id_counter = 0
        self.platforms = []
        self.enemies = []
        self.projectiles = []
        self.powerups = []
        
        self.player = None
        self.player_facing_right = True  # Default facing direction
        self.wave_number = 1
        self.enemy_spawn_timer = 0
        self.last_spawn_time = time.time()
        
        # Thread locks
        self.entities_lock = threading.Lock()
        self.wave_lock = threading.Lock()
        
        # Start the game loop
        self.initialize_game()
        self.run()
    
    def initialize_game(self):
        """Set up initial game state and entities"""
        # Create player
        self.player = self.create_entity(EntityType.PLAYER, 
                                        self.player_position[0], 
                                        self.player_position[1], 
                                        50, 80)
        # Add player-specific attributes
        self.player.on_ground = True
        
        # Create platforms
        screen_width = 1200
        screen_height = 800
        platform_width = 200
        platform_height = 20
        
        # Ground platform
        self.create_entity(EntityType.PLATFORM, 
                          0, 
                          screen_height - 50, 
                          screen_width, 50)
        
        # Additional platforms
        for _ in range(PLATFORM_COUNT):
            x = random.randint(0, screen_width - platform_width)
            y = random.randint(100, screen_height - 150)
            self.create_entity(EntityType.PLATFORM, x, y, platform_width, platform_height)
        
        # Start enemy spawner thread
        self.enemy_spawner = threading.Thread(target=self.spawn_enemies)
        self.enemy_spawner.daemon = True
        self.enemy_spawner.start()
        
        # Start power-up spawner thread
        self.powerup_spawner = threading.Thread(target=self.spawn_powerups)
        self.powerup_spawner.daemon = True
        self.powerup_spawner.start()
        
        with self.game_state_lock:
            self.game_state.value = GameState.PLAYING.value
    
    def create_entity(self, entity_type, x, y, width, height):
        """Create a new game entity with synchronization"""
        with self.entities_lock:
            entity_id = self.entity_id_counter
            self.entity_id_counter += 1
            
            entity = Entity(entity_id, entity_type, x, y, width, height)
            self.entities[entity_id] = entity
            
            # Add to specific type list for faster processing
            if entity_type == EntityType.PLATFORM:
                self.platforms.append(entity)
            elif entity_type == EntityType.ENEMY:
                self.enemies.append(entity)
            elif entity_type == EntityType.PROJECTILE:
                self.projectiles.append(entity)
            elif entity_type == EntityType.POWERUP:
                self.powerups.append(entity)
            
            return entity
    
    def spawn_enemies(self):
        """Thread function to spawn enemies at intervals"""
        screen_width = 1200
        screen_height = 800
        screen_center_x = screen_width / 2
        
        while True:
            # Only spawn when playing
            with self.game_state_lock:
                if self.game_state.value != GameState.PLAYING.value:
                    time.sleep(0.5)
                    continue
            
            current_time = time.time()
            if current_time - self.last_spawn_time >= SPAWN_INTERVAL:
                with self.wave_lock:
                    # Determine number of enemies based on wave
                    spawn_count = min(self.wave_number, 5)
                    
                    for _ in range(spawn_count):
                        enemy_type = random.randint(1, ENEMY_TYPES)
                        
                        # Spawn from either side but slightly inside the screen
                        side = random.choice([-1, 1])
                        # Modified: Spawn 100px inside the screen instead of at the very edge
                        x = screen_width - 100 if side == -1 else 100
                        y = random.randint(50, screen_height - 150)
                        
                        # Increase enemy size from 40x40 to 60x60 to make them more visible
                        enemy = self.create_entity(EntityType.ENEMY, x, y, 60, 60)
                        
                        # Fix: Calculate velocity to always move toward center
                        # If enemy is on the right side (x > center), move left (negative velocity)
                        # If enemy is on the left side (x < center), move right (positive velocity)
                        direction = 1 if x < screen_center_x else -1
                        enemy.velocity_x = 2 * direction
                        
                        enemy.enemy_type = enemy_type
                        
                        # Different enemy types have different health/speed
                        if enemy_type == 2:
                            enemy.health = 50
                            enemy.velocity_x *= 0.7
                        elif enemy_type == 3:
                            enemy.health = 20
                            enemy.velocity_x *= 1.5
                        
                        # Comment out debug print
                        # print(f"Spawned enemy at ({x}, {y}) with velocity {enemy.velocity_x}")
                
                self.last_spawn_time = current_time
                
                # Check for wave completion
                if len(self.enemies) == 0:
                    with self.wave_lock:
                        self.wave_number += 1
                        print(f"Wave {self.wave_number} starting!")
            
            time.sleep(0.5)  # Check every half second
    
    def spawn_powerups(self):
        """Thread function to spawn power-ups occasionally"""
        screen_width = 1200
        screen_height = 800
        
        while True:
            # Only spawn when playing
            with self.game_state_lock:
                if self.game_state.value != GameState.PLAYING.value:
                    time.sleep(1.0)
                    continue
            
            # 5% chance to spawn a power-up every 5 seconds
            if random.random() < 0.05:
                x = random.randint(100, screen_width - 100)
                y = random.randint(100, screen_height - 200)
                powerup = self.create_entity(EntityType.POWERUP, x, y, 30, 30)
                powerup.powerup_type = random.randint(1, 3)  # Different powerup types
            
            time.sleep(5.0)
    
    def update_player(self):
        """Update player position and state"""
        # Read input from render process
        try:
            while not self.render_to_logic_queue.empty():
                command = self.render_to_logic_queue.get_nowait()
                
                # Skip non-input commands (e.g., exit_game commands are handled in run())
                if command.get('type') != 'input':
                    # Put it back in the queue for the run method to process
                    self.render_to_logic_queue.put(command)
                    continue
                
                keys = command.get('keys', {})
                key_press = command.get('key_press', {})  # Get the just-pressed keys
                
                # Get current game state
                with self.game_state_lock:
                    current_state = self.game_state.value
                
                # Handle game over state input
                if current_state == GameState.GAME_OVER.value:
                    # SPACE to restart the game - use key_press to detect a new press
                    if key_press.get(pygame.K_SPACE):
                        # Reset game state and restart
                        self.reset_game()
                        return
                    
                    # ESC to quit the game - use key_press to detect a new press
                    if key_press.get(pygame.K_ESCAPE):
                        # Instead of calling pygame.quit() and sys.exit() directly,
                        # put an exit command in the queue for the main thread to process
                        self.render_to_logic_queue.put({'type': 'exit_game'})
                        return
                    
                    # Don't process other inputs in game over state
                    continue
                
                # Handle menu state input
                if current_state == GameState.MENU.value:
                    # SPACE to start the game - use key_press to detect a new press
                    if key_press.get(pygame.K_SPACE):
                        with self.game_state_lock:
                            self.game_state.value = GameState.PLAYING.value
                        return
                    
                    # ESC to quit the game - use key_press to detect a new press
                    if key_press.get(pygame.K_ESCAPE):
                        # Use the exit command queue approach here too
                        self.render_to_logic_queue.put({'type': 'exit_game'})
                        return
                    
                    # Don't process other inputs in menu state
                    continue
                
                # Handle pause state input
                if current_state == GameState.PAUSED.value:
                    # ESC to toggle pause - use key_press to detect a new press
                    if key_press.get(pygame.K_ESCAPE):
                        with self.game_state_lock:
                            self.game_state.value = GameState.PLAYING.value
                        return
                    
                    # Don't process other inputs in paused state
                    continue
                
                # Only process gameplay inputs in PLAYING state
                if current_state == GameState.PLAYING.value:
                    # Move left
                    if keys.get(pygame.K_LEFT):
                        self.player.velocity_x = -PLAYER_SPEED
                        self.player_facing_right = False  # Update facing direction
                    # Move right
                    elif keys.get(pygame.K_RIGHT):
                        self.player.velocity_x = PLAYER_SPEED
                        self.player_facing_right = True  # Update facing direction
                    else:
                        self.player.velocity_x = 0
                    
                    # Jump - changed from SPACE to UP arrow key
                    if keys.get(pygame.K_UP) and self.player.on_ground:
                        self.player.velocity_y = -JUMP_POWER
                        self.player.on_ground = False
                    
                    # Attack
                    if keys.get(pygame.K_z) or keys.get(pygame.K_x):
                        self.fire_projectile()
                    
                    # Pause - use key_press to detect a new press
                    if key_press.get(pygame.K_ESCAPE):
                        with self.game_state_lock:
                            self.game_state.value = GameState.PAUSED.value
        except Exception as e:
            print(f"Error processing input: {e}")
        
        # In PLAYING state, continue updating player physics
        with self.game_state_lock:
            if self.game_state.value != GameState.PLAYING.value:
                return
                
        # Apply gravity
        self.player.velocity_y += GRAVITY
        
        # Update position
        self.player.update()
        
        # Check platform collisions
        self.player.on_ground = False
        for platform in self.platforms:
            if self.player.check_collision(platform):
                # Check if landing on top of platform
                if self.player.velocity_y > 0 and self.player.y + self.player.height - self.player.velocity_y <= platform.y:
                    self.player.y = platform.y - self.player.height
                    self.player.velocity_y = 0
                    self.player.on_ground = True
                # Hitting platform from below
                elif self.player.velocity_y < 0 and self.player.y >= platform.y + platform.height:
                    self.player.y = platform.y + platform.height
                    self.player.velocity_y = 0
                # Collision from side
                elif self.player.velocity_x > 0:
                    self.player.x = platform.x - self.player.width
                elif self.player.velocity_x < 0:
                    self.player.x = platform.x + platform.width
        
        # Update shared player position
        with self.player_position_lock:
            self.player_position[0] = int(self.player.x)
            self.player_position[1] = int(self.player.y)
    
    def fire_projectile(self):
        """Create a player projectile that shoots in the direction the player is facing"""
        # Calculate starting position based on direction
        if self.player_facing_right:
            start_x = self.player.x + self.player.width
        else:
            start_x = self.player.x
            
        projectile = self.create_entity(
            EntityType.PROJECTILE,
            start_x,
            self.player.y + self.player.height/2,
            10, 10
        )
        
        # Set velocity based on player direction
        projectile.velocity_x = 10 if self.player_facing_right else -10
        projectile.damage = 10
        projectile.source = 'player'
        projectile.direction = 1 if self.player_facing_right else -1  # Store direction for rendering
    
    def update_entities(self):
        """Update all game entities with thread safety"""
        with self.entities_lock:
            # Update enemies
            for enemy in self.enemies[:]:
                enemy.update()
                
                # Check if enemy is off-screen
                if enemy.x < -100 or enemy.x > 1300:
                    self.enemies.remove(enemy)
                    del self.entities[enemy.id]
                    # Comment out debug print
                    # print(f"Enemy removed at position ({enemy.x}, {enemy.y})")
                
                # Check collision with player
                if enemy.check_collision(self.player):
                    with self.player_health_lock:
                        self.player_health.value -= 10
                        
                        if self.player_health.value <= 0:
                            with self.game_state_lock:
                                self.game_state.value = GameState.GAME_OVER.value
            
            # Update projectiles
            for projectile in self.projectiles[:]:
                projectile.update()
                
                # Check if projectile is off-screen
                if (projectile.x < -20 or projectile.x > 1220 or 
                    projectile.y < -20 or projectile.y > 820):
                    self.projectiles.remove(projectile)
                    del self.entities[projectile.id]
                    continue
                
                # Check collisions with enemies
                if projectile.source == 'player':
                    for enemy in self.enemies[:]:
                        if projectile.check_collision(enemy):
                            enemy.health -= projectile.damage
                            
                            if enemy.health <= 0:
                                with self.player_score_lock:
                                    self.player_score.value += 10
                                self.enemies.remove(enemy)
                                del self.entities[enemy.id]
                            
                            self.projectiles.remove(projectile)
                            del self.entities[projectile.id]
                            break
            
            # Update powerups
            for powerup in self.powerups[:]:
                if powerup.check_collision(self.player):
                    # Apply power-up effect
                    if powerup.powerup_type == 1:  # Health
                        with self.player_health_lock:
                            self.player_health.value = min(100, self.player_health.value + 25)
                    elif powerup.powerup_type == 2:  # Score boost
                        with self.player_score_lock:
                            self.player_score.value += 50
                    elif powerup.powerup_type == 3:  # Temporary invincibility
                        self.player.invincible = True
                        # Start a thread to remove invincibility after 5 seconds
                        threading.Thread(target=self.remove_invincibility, daemon=True).start()
                    
                    self.powerups.remove(powerup)
                    del self.entities[powerup.id]
    
    def remove_invincibility(self):
        """Remove player invincibility after a delay"""
        time.sleep(5.0)
        self.player.invincible = False
    
    def update_game_state(self):
        """Send updated game state to the renderer"""
        entity_data = []
        
        with self.entities_lock:
            for entity in self.entities.values():
                data = {
                    'id': entity.id,
                    'type': entity.type.value,
                    'x': entity.x,
                    'y': entity.y,
                    'width': entity.width,
                    'height': entity.height,
                    'enemy_type': getattr(entity, 'enemy_type', 0),
                    'powerup_type': getattr(entity, 'powerup_type', 0)
                }
                
                # Add additional fields if they exist
                if hasattr(entity, 'direction'):
                    data['direction'] = entity.direction
                
                entity_data.append(data)
        
        game_data = {
            'entities': entity_data,
            'wave': self.wave_number,
            'player_facing_right': self.player_facing_right  # Send player direction to renderer
        }
        
        self.logic_to_render_queue.put(game_data)
    
    def run(self):
        """Main game loop"""
        clock = pygame.time.Clock()
        
        while True:
            # Check for special commands
            try:
                if not self.render_to_logic_queue.empty():
                    command = self.render_to_logic_queue.get_nowait()
                    if command.get('type') == 'exit_game':
                        print("Received exit command. Terminating game...")
                        pygame.quit()
                        sys.exit(0)
                    else:
                        # Put other commands back in the queue for update_player to handle
                        self.render_to_logic_queue.put(command)
            except Exception as e:
                print(f"Error checking for exit command: {e}")
            
            # Get current game state
            with self.game_state_lock:
                current_state = self.game_state.value
            
            if current_state == GameState.PLAYING.value:
                # Update player
                self.update_player()
                
                # Update other entities
                self.update_entities()
                
                # Send updated state to renderer
                self.update_game_state()
            else:
                # For non-playing states, still process player input
                # This ensures restart/exit functionality works
                self.update_player()
                
                # Also send state updates to keep renderer in sync
                self.update_game_state()
            
            # Maintain consistent frame rate
            clock.tick(FPS)
    
    def reset_game(self):
        """Reset the game to initial state for restart functionality"""
        print("Restarting game...")
        
        # Screen dimensions
        screen_width = 1200  # Same as WINDOW_WIDTH
        screen_height = 800  # Same as WINDOW_HEIGHT
        
        # Reset all entities
        with self.entities_lock:
            # Clear all entity collections
            self.entities.clear()
            self.platforms.clear()
            self.enemies.clear()
            self.projectiles.clear()
            self.powerups.clear()
            
            # Reset entity counter
            self.entity_id_counter = 0
        
        # Reset player stats
        with self.player_score_lock:
            self.player_score.value = 0
            
        with self.player_health_lock:
            self.player_health.value = 100
            
        with self.player_position_lock:
            self.player_position[0] = screen_width // 4
            self.player_position[1] = screen_height // 2
        
        # Reset wave counter
        with self.wave_lock:
            self.wave_number = 1
            
        # Reset spawn timer
        self.last_spawn_time = time.time()
        
        # Restart the game by reinitializing entities
        self.initialize_game()
        
        # Set game state to playing
        with self.game_state_lock:
            self.game_state.value = GameState.PLAYING.value 