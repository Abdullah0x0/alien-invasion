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
JUMP_POWER = 15
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
        self.game_start_time = time.time()  # Track when the game started
        
        # Wave progression tracking
        self.enemies_killed_in_wave = 0
        self.enemies_to_kill_for_next_wave = 10  # Base number, will scale with wave
        self.wave_progress = 0  # 0 to 100 percent
        self.wave_message_shown = False
        
        # Weapon cooldown tracking
        self.last_primary_fire_time = 0
        self.primary_fire_cooldown = 0.15  # 150ms between shots for primary weapon
        self.last_secondary_fire_time = 0
        self.secondary_fire_cooldown = 0.5  # 500ms between shots for secondary weapon
        
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
        ground_platform = self.create_entity(EntityType.PLATFORM, 
                          0, 
                          screen_height - 50, 
                          screen_width, 50)
        
        # Calculate maximum jump height based on jump power and gravity
        # Using the formula: max_height = (jump_power^2) / (2 * gravity)
        max_jump_height = (JUMP_POWER ** 2) / (2 * GRAVITY)
        
        # Minimum spacing between platforms to prevent overlap
        min_horizontal_spacing = 50  # Minimum horizontal space between platforms
        min_vertical_spacing = 80    # Minimum vertical space between platforms
        
        # Additional platforms with height restrictions to ensure reachability
        # Start with platforms closer to the ground
        existing_platforms = [ground_platform]
        
        # Divide the screen into vertical sections for better distribution
        vertical_sections = 5
        section_height = (screen_height - 150) / vertical_sections
        
        # Create platforms in each vertical section
        platforms_per_section = PLATFORM_COUNT // vertical_sections
        remaining_platforms = PLATFORM_COUNT % vertical_sections
        
        for section in range(vertical_sections):
            section_y_min = 100 + section * section_height
            section_y_max = section_y_min + section_height - platform_height
            
            # Determine platforms to create in this section
            section_platforms = platforms_per_section
            if section < remaining_platforms:
                section_platforms += 1
            
            for _ in range(section_platforms):
                max_attempts = 15
                platform_created = False
                
                for attempt in range(max_attempts):
                    x = random.randint(0, screen_width - platform_width)
                    y = random.randint(int(section_y_min), int(section_y_max))
                    
                    # Check for overlap with existing platforms
                    overlapping = False
                    too_close = False
                    
                    for existing in existing_platforms:
                        # Check if platforms would overlap
                        if (x < existing.x + existing.width + min_horizontal_spacing and 
                            x + platform_width + min_horizontal_spacing > existing.x and
                            y < existing.y + existing.height + min_vertical_spacing and
                            y + platform_height + min_vertical_spacing > existing.y):
                            too_close = True
                            break
                    
                    if too_close:
                        continue
                    
                    # Check if this platform is reachable from at least one existing platform
                    platform_reachable = False
                    
                    # A platform is considered reachable if it's within max_jump_height of another platform
                    # and there's some horizontal overlap or it's close enough horizontally
                    for existing in existing_platforms:
                        # Vertical distance check (is the platform within jump range?)
                        vertical_dist = existing.y - y  # Note: y increases downward
                        
                        # Platform must be above the existing one (smaller y value) and within jump height
                        if 0 < vertical_dist < max_jump_height:
                            # Horizontal distance check (can the player reach it horizontally?)
                            # Check if platforms overlap horizontally or are close enough
                            platform_left = x
                            platform_right = x + platform_width
                            existing_left = existing.x
                            existing_right = existing.x + existing.width
                            
                            # Check for horizontal overlap or closeness
                            horizontal_overlap = (
                                (platform_left <= existing_right and platform_right >= existing_left) or
                                abs(platform_left - existing_right) < 100 or
                                abs(platform_right - existing_left) < 100
                            )
                            
                            if horizontal_overlap:
                                platform_reachable = True
                                break
                    
                    # Only create platform if it's reachable or it's in the lowest section
                    if platform_reachable or section == 0:
                        new_platform = self.create_entity(EntityType.PLATFORM, x, y, platform_width, platform_height)
                        existing_platforms.append(new_platform)
                        platform_created = True
                        break
                
                # If we couldn't create a reachable platform after max attempts,
                # place one that at least doesn't overlap with others
                if not platform_created:
                    for attempt in range(max_attempts):
                        x = random.randint(0, screen_width - platform_width)
                        y = random.randint(int(section_y_min), int(section_y_max))
                        
                        # Check only for overlap, not reachability
                        overlapping = False
                        for existing in existing_platforms:
                            if (x < existing.x + existing.width and 
                                x + platform_width > existing.x and
                                y < existing.y + existing.height and
                                y + platform_height > existing.y):
                                overlapping = True
                                break
                        
                        if not overlapping:
                            new_platform = self.create_entity(EntityType.PLATFORM, x, y, platform_width, platform_height)
                            existing_platforms.append(new_platform)
                            break
        
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
        
        # Adjust spawn interval based on wave
        base_spawn_interval = SPAWN_INTERVAL * 1.5
        
        while True:
            # Only spawn when playing
            with self.game_state_lock:
                if self.game_state.value != GameState.PLAYING.value:
                    time.sleep(0.5)
                    continue
            
            # Calculate spawn interval based on wave (gets shorter as waves progress)
            # Reduced wave scaling (0.15 instead of 0.2) to slow down difficulty increase
            current_spawn_interval = max(0.8, base_spawn_interval - (self.wave_number * 0.15))
            
            current_time = time.time()
            if current_time - self.last_spawn_time >= current_spawn_interval:
                with self.wave_lock:
                    # Determine number of enemies based on wave (reduced max from 5 to 3)
                    spawn_count = min(self.wave_number, 3)
                    
                    for _ in range(spawn_count):
                        # Higher chance of tougher enemies in later waves
                        if self.wave_number >= 3:
                            # 50% chance of enemy type 2 or 3 in higher waves
                            enemy_type_weights = [0.5, 0.3, 0.2]  # Type 1, 2, 3
                        elif self.wave_number == 2:
                            # 30% chance of enemy type 2 or 3 in wave 2
                            enemy_type_weights = [0.7, 0.2, 0.1]  # Type 1, 2, 3
                        else:
                            # Mostly basic enemies in wave 1
                            enemy_type_weights = [0.9, 0.1, 0.0]  # Type 1, 2, 3
                        
                        # Select enemy type based on weights
                        enemy_type = random.choices([1, 2, 3], weights=enemy_type_weights)[0]
                        
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
                        base_speed = 2
                        
                        # Scale speed slightly with wave number
                        wave_speed_multiplier = 1.0 + (self.wave_number - 1) * 0.1  # 10% increase per wave
                        enemy.velocity_x = base_speed * direction * wave_speed_multiplier
                        
                        enemy.enemy_type = enemy_type
                        
                        # Scale enemy health with wave number
                        base_health_multiplier = 1.0 + (self.wave_number - 1) * 0.2  # 20% increase per wave
                        
                        # Different enemy types have different health/speed
                        if enemy_type == 2:
                            enemy.health = int(50 * base_health_multiplier)
                            enemy.velocity_x *= 0.7
                        elif enemy_type == 3:
                            enemy.health = int(20 * base_health_multiplier)
                            enemy.velocity_x *= 1.5
                        else:  # type 1
                            enemy.health = int(30 * base_health_multiplier)
                        
                        # Track wave number with the enemy for rendering purposes
                        enemy.wave = self.wave_number
                
                self.last_spawn_time = current_time
                
                # Check for wave completion - moved to update_entities for accuracy
            
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
            
            # 15% chance to spawn a power-up every 4 seconds (reduced from 20% every 3 seconds)
            if random.random() < 0.15:
                x = random.randint(100, screen_width - 100)
                y = random.randint(100, screen_height - 200)
                powerup = self.create_entity(EntityType.POWERUP, x, y, 30, 30)
                powerup.powerup_type = random.randint(1, 3)  # Different powerup types
            
            time.sleep(4.0)
    
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
                
                # Check for Q key to quit in any state
                if key_press.get(pygame.K_q):
                    # Send exit command
                    self.render_to_logic_queue.put({'type': 'exit_game'})
                    return
                
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
                    
                    # Get current time for weapon cooldowns
                    current_time = time.time()
                    
                    # Attack with different weapons based on key
                    if keys.get(pygame.K_z) and (current_time - self.last_primary_fire_time) >= self.primary_fire_cooldown:
                        self.fire_projectile(weapon_type=1)  # Primary weapon (faster, rapid fire, less damage)
                        self.last_primary_fire_time = current_time
                    elif key_press.get(pygame.K_x) and (current_time - self.last_secondary_fire_time) >= self.secondary_fire_cooldown:
                        self.fire_projectile(weapon_type=2)  # Secondary weapon (slower, single shot, more damage)
                        self.last_secondary_fire_time = current_time
                    
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
    
    def fire_projectile(self, weapon_type=1):
        """Create a player projectile that shoots in the direction the player is facing
        
        Args:
            weapon_type (int): 1 for primary weapon (fast, low damage), 2 for secondary weapon (slow, high damage)
        """
        # Calculate starting position based on direction
        if self.player_facing_right:
            start_x = self.player.x + self.player.width
        else:
            start_x = self.player.x
        
        # Adjust Y position based on weapon type
        if weapon_type == 1:
            # Primary weapon - shoot from middle
            start_y = self.player.y + self.player.height/2
            projectile = self.create_entity(
                EntityType.PROJECTILE,
                start_x,
                start_y,
                10, 10
            )
            # Fast but less damage
            projectile.velocity_x = 15 if self.player_facing_right else -15
            projectile.damage = 10
            projectile.weapon_type = 1
            
        else:  # weapon_type == 2
            # Secondary weapon - shoot from slightly higher
            start_y = self.player.y + self.player.height/3
            projectile = self.create_entity(
                EntityType.PROJECTILE,
                start_x,
                start_y,
                15, 15  # Larger projectile
            )
            # Slower but more damage
            projectile.velocity_x = 8 if self.player_facing_right else -8
            projectile.damage = 20
            projectile.weapon_type = 2
        
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
                                    # Scale score with enemy type and wave
                                    base_score = 10
                                    enemy_type_bonus = (enemy.enemy_type - 1) * 5  # +0/+5/+10 for types 1/2/3
                                    wave_bonus = (self.wave_number - 1) * 2  # +2 per wave level
                                    score_gain = base_score + enemy_type_bonus + wave_bonus
                                    self.player_score.value += score_gain
                                
                                # Save enemy position before removing it
                                enemy_x = enemy.x
                                enemy_y = enemy.y
                                enemy_type = getattr(enemy, 'enemy_type', 1)
                                enemy_wave = getattr(enemy, 'wave', 1)
                                
                                # Remove the enemy
                                self.enemies.remove(enemy)
                                del self.entities[enemy.id]
                                
                                # Update wave progression
                                self.enemies_killed_in_wave += 1
                                self.wave_progress = min(100, int((self.enemies_killed_in_wave / self.enemies_to_kill_for_next_wave) * 100))
                                
                                # Check for wave completion
                                if self.enemies_killed_in_wave >= self.enemies_to_kill_for_next_wave and not self.wave_message_shown:
                                    self.wave_message_shown = True
                                    # Schedule a wave advancement if we've killed enough enemies
                                    threading.Thread(target=self.advance_wave, daemon=True).start()
                                
                                # Send explosion event to renderer
                                explosion_data = {
                                    'type': 'explosion',
                                    'x': enemy_x,
                                    'y': enemy_y,
                                    'enemy_type': enemy_type,
                                    'wave': enemy_wave
                                }
                                self.logic_to_render_queue.put(explosion_data)
                            
                            self.projectiles.remove(projectile)
                            del self.entities[projectile.id]
                            break
            
            # Update powerups
            for powerup in self.powerups[:]:
                if powerup.check_collision(self.player):
                    # Determine powerup message based on type
                    powerup_message = ""
                    powerup_color = (255, 255, 255)  # Default white
                    
                    # Apply power-up effect
                    if powerup.powerup_type == 1:  # Health
                        with self.player_health_lock:
                            self.player_health.value = min(100, self.player_health.value + 25)
                        powerup_message = "HEALTH +25"
                        powerup_color = (0, 255, 0)  # Green for health
                    elif powerup.powerup_type == 2:  # Score boost
                        with self.player_score_lock:
                            self.player_score.value += 50
                        powerup_message = "SCORE +50"
                        powerup_color = (255, 255, 0)  # Yellow for score
                    elif powerup.powerup_type == 3:  # Temporary invincibility
                        self.player.invincible = True
                        # Start a thread to remove invincibility after 5 seconds
                        threading.Thread(target=self.remove_invincibility, daemon=True).start()
                        powerup_message = "INVINCIBILITY (5s)"
                        powerup_color = (0, 100, 255)  # Blue for invincibility
                    
                    # Save powerup position for animation
                    powerup_x = powerup.x
                    powerup_y = powerup.y
                    powerup_type = powerup.powerup_type
                    
                    # Remove the powerup from the game
                    self.powerups.remove(powerup)
                    del self.entities[powerup.id]
                    
                    # Send powerup pickup message to renderer
                    pickup_data = {
                        'type': 'powerup_message',
                        'message': powerup_message,
                        'duration': 2.0,  # Show for 2 seconds
                        'color': powerup_color,
                        'x': powerup_x,
                        'y': powerup_y,
                        'powerup_type': powerup_type
                    }
                    self.logic_to_render_queue.put(pickup_data)
    
    def remove_invincibility(self):
        """Remove player invincibility after a delay"""
        time.sleep(5.0)
        self.player.invincible = False
    
    def advance_wave(self):
        """Advance to the next wave with a brief delay for the player to prepare"""
        # Send wave clear message to renderer
        wave_message = {
            'type': 'wave_message',
            'message': f"WAVE {self.wave_number} CLEARED!",
            'duration': 3.0  # Show for 3 seconds
        }
        self.logic_to_render_queue.put(wave_message)
        
        # Wait 3 seconds before starting the next wave
        time.sleep(3.0)
        
        with self.wave_lock:
            self.wave_number += 1
            # Increase the enemy count needed for the next wave
            self.enemies_to_kill_for_next_wave = 10 + (self.wave_number - 1) * 5  # +5 enemies per wave
            self.enemies_killed_in_wave = 0
            self.wave_progress = 0
            self.wave_message_shown = False
            
            # Send new wave start message
            new_wave_message = {
                'type': 'wave_message',
                'message': f"WAVE {self.wave_number} STARTING!",
                'duration': 2.0  # Show for 2 seconds
            }
            self.logic_to_render_queue.put(new_wave_message)
            
            print(f"Wave {self.wave_number} starting! Defeat {self.enemies_to_kill_for_next_wave} enemies to advance.")
    
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
                
                # Add velocity data for player entity
                if entity.type == EntityType.PLAYER:
                    data['velocity_x'] = entity.velocity_x
                    data['velocity_y'] = entity.velocity_y
                    data['facing_right'] = self.player_facing_right
                
                # Add additional fields if they exist
                if hasattr(entity, 'direction'):
                    data['direction'] = entity.direction
                
                # Add weapon type for projectiles
                if entity.type == EntityType.PROJECTILE and hasattr(entity, 'weapon_type'):
                    data['weapon_type'] = entity.weapon_type
                
                # Add wave information for enemies
                if entity.type == EntityType.ENEMY and hasattr(entity, 'wave'):
                    data['wave'] = entity.wave
                
                entity_data.append(data)
        
        # Calculate elapsed game time
        current_time = time.time()
        elapsed_time = current_time - self.game_start_time
        
        game_data = {
            'entities': entity_data,
            'wave': self.wave_number,
            'wave_progress': self.wave_progress,  # Add wave progress
            'player_facing_right': self.player_facing_right,  # Send player direction to renderer
            'game_time': elapsed_time  # Send elapsed time to renderer
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
        
        # Reset wave counter and related variables
        with self.wave_lock:
            self.wave_number = 1
            self.enemies_killed_in_wave = 0
            self.enemies_to_kill_for_next_wave = 10  # Base number for wave 1
            self.wave_progress = 0
            self.wave_message_shown = False
            
        # Reset spawn timer
        self.last_spawn_time = time.time()
        self.game_start_time = time.time()  # Reset game start time
        
        # Restart the game by reinitializing entities
        self.initialize_game()
        
        # Set game state to playing
        with self.game_state_lock:
            self.game_state.value = GameState.PLAYING.value 