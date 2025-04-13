#!/usr/bin/env python3
import os
import sys
import pygame
import threading
import time
import random
import math
from multiprocessing import Value, Lock, Queue
from enum import Enum

# Import game state from game_logic
from game_logic import GameState, EntityType

# Constants
FPS = 60
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
FONT_SIZE = 32
SMALL_FONT_SIZE = 24

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 100, 255)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
GRAY = (150, 150, 150)
DARK_BLUE = (0, 0, 50)
LIGHT_BLUE = (100, 100, 255)

class RendererProcess:
    def __init__(self, width, height, game_state, player_score, player_health, player_position,
                game_state_lock, player_score_lock, player_health_lock, player_position_lock,
                logic_to_render_queue, render_to_logic_queue):
        """Initialize the renderer process"""
        self.width = width
        self.height = height
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
        
        # Initialize pygame
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Alien Invasion")
        
        # Load fonts
        self.main_font = pygame.font.SysFont('Arial', FONT_SIZE, bold=True)
        self.small_font = pygame.font.SysFont('Arial', SMALL_FONT_SIZE)
        
        # Load assets
        self.load_assets()
        
        # Game entities
        self.entities = []
        self.current_wave = 1
        
        # Particle systems
        self.projectile_particles = []
        self.explosion_particles = []
        
        # Input state
        self.keys_pressed = {}
        self.keys_just_pressed = {}  # Track keys that were just pressed this frame
        
        # Display flags
        self.show_process_info = False  # Toggle for process info display
        
        # Performance metrics
        self.fps_samples = []
        self.frame_times = []
        self.last_frame_time = time.time()
        
        # Background setup
        self.stars = self.generate_stars(150)
        self.far_stars = self.generate_stars(100)
        self.near_stars = self.generate_stars(50)
        self.nebulas = self.generate_nebulas(5)
        self.parallax_offset = 0
        
        # Start animation thread
        self.animation_thread = threading.Thread(target=self.animate_background)
        self.animation_thread.daemon = True
        self.animation_thread.start()
        
        # Run the game loop
        self.run()
    
    def load_assets(self):
        """Load game assets and create sprites"""
        # We'll use basic shapes for now, but this is where you'd load images
        self.assets = {
            'player': self.create_player_sprite(),
            'platform': self.create_platform_sprite(),
            'enemy1': self.create_enemy_sprite(1),  # Basic enemy
            'enemy2': self.create_enemy_sprite(2),  # Tough enemy
            'enemy3': self.create_enemy_sprite(3),  # Fast enemy
            'powerup1': self.create_powerup_sprite(1),  # Health
            'powerup2': self.create_powerup_sprite(2),  # Score
            'powerup3': self.create_powerup_sprite(3),  # Invincibility
            'projectile': self.create_projectile_sprite(),
            'background': self.create_background()
        }
    
    def create_player_sprite(self):
        """Create player sprite with animation frames"""
        frames = []
        
        # Base player frame
        base_surf = pygame.Surface((50, 80), pygame.SRCALPHA)
        # Body
        pygame.draw.rect(base_surf, BLUE, (5, 10, 40, 50))
        # Head
        pygame.draw.circle(base_surf, BLUE, (25, 15), 15)
        # Eyes
        pygame.draw.circle(base_surf, WHITE, (20, 10), 5)
        pygame.draw.circle(base_surf, WHITE, (30, 10), 5)
        pygame.draw.circle(base_surf, BLACK, (20, 10), 2)
        pygame.draw.circle(base_surf, BLACK, (30, 10), 2)
        # Legs
        pygame.draw.rect(base_surf, BLUE, (10, 60, 10, 20))
        pygame.draw.rect(base_surf, BLUE, (30, 60, 10, 20))
        # Arms
        pygame.draw.rect(base_surf, BLUE, (0, 20, 10, 30))
        pygame.draw.rect(base_surf, BLUE, (40, 20, 10, 30))
        
        frames.append(base_surf)
        
        # Frame 2 - Arms slightly different position
        frame2 = base_surf.copy()
        pygame.draw.rect(frame2, (0, 0, 0, 0), (0, 20, 10, 30), 0)  # Clear previous arm
        pygame.draw.rect(frame2, (0, 0, 0, 0), (40, 20, 10, 30), 0)  # Clear previous arm
        pygame.draw.rect(frame2, BLUE, (0, 15, 10, 30))  # New arm position
        pygame.draw.rect(frame2, BLUE, (40, 25, 10, 30))  # New arm position
        frames.append(frame2)
        
        # Frame 3 - Legs slightly different position
        frame3 = base_surf.copy()
        pygame.draw.rect(frame3, (0, 0, 0, 0), (10, 60, 10, 20), 0)  # Clear previous leg
        pygame.draw.rect(frame3, (0, 0, 0, 0), (30, 60, 10, 20), 0)  # Clear previous leg
        pygame.draw.rect(frame3, BLUE, (12, 60, 10, 20))  # New leg position
        pygame.draw.rect(frame3, BLUE, (28, 60, 10, 20))  # New leg position
        frames.append(frame3)
        
        # Frame 4 - Combination of different limb positions
        frame4 = frame2.copy()
        pygame.draw.rect(frame4, (0, 0, 0, 0), (10, 60, 10, 20), 0)  # Clear previous leg
        pygame.draw.rect(frame4, (0, 0, 0, 0), (30, 60, 10, 20), 0)  # Clear previous leg
        pygame.draw.rect(frame4, BLUE, (8, 60, 10, 20))  # New leg position
        pygame.draw.rect(frame4, BLUE, (32, 60, 10, 20))  # New leg position
        frames.append(frame4)
        
        # Create an additional surfacex for jet flames
        jet_flame = pygame.Surface((30, 20), pygame.SRCALPHA)
        points = [(0, 10), (10, 0), (10, 20), (0, 10)]
        pygame.draw.polygon(jet_flame, YELLOW, points)
        pygame.draw.polygon(jet_flame, RED, [(5, 10), (10, 5), (10, 15), (5, 10)])
        
        # Add the animation details to the class
        self.player_frames = frames
        self.player_frame_idx = 0
        self.player_anim_delay = 8
        self.player_anim_counter = 0
        self.player_jet_flame = jet_flame
        
        # Return the first frame as the initial sprite
        return frames[0]
    
    def create_platform_sprite(self):
        """Create an enhanced platform sprite with tech details"""
        surf = pygame.Surface((200, 20), pygame.SRCALPHA)
        
        # Base platform with gradient
        for y in range(20):
            # Create a gradient from top to bottom
            color_value = 150 - y * 3
            color = (color_value, color_value, color_value + 20)
            pygame.draw.line(surf, color, (0, y), (200, y))
        
        # Add tech patterns
        for i in range(0, 200, 20):
            # Vertical lines
            pygame.draw.line(surf, (50, 50, 70), (i, 0), (i, 20), 1)
            
            # Tech details
            if i % 40 == 0:
                pygame.draw.rect(surf, (100, 100, 255), (i+8, 2, 4, 4))
                pygame.draw.rect(surf, (100, 100, 255), (i+8, 14, 4, 4))
            else:
                pygame.draw.rect(surf, (70, 70, 90), (i+8, 8, 4, 4))
        
        # Horizontal lines
        pygame.draw.line(surf, (80, 80, 100), (0, 0), (200, 0), 2)
        pygame.draw.line(surf, (30, 30, 50), (0, 19), (200, 19), 2)
        
        # Add subtle highlights
        for i in range(0, 200, 40):
            # Use proper RGBA color format
            highlight_color = (200, 200, 255, 50)
            pygame.draw.line(surf, highlight_color, (i, 0), (i+20, 0), 1)
        
        return surf
    
    def create_enemy_sprite(self, enemy_type):
        """Create enemy sprite based on type with animation frames"""
        frames = []
        
        if enemy_type == 1:  # Basic enemy
            # Frame 1
            surf1 = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(surf1, RED, (20, 20), 15)
            pygame.draw.circle(surf1, WHITE, (15, 15), 5)
            pygame.draw.circle(surf1, WHITE, (25, 15), 5)
            pygame.draw.circle(surf1, BLACK, (15, 15), 2)
            pygame.draw.circle(surf1, BLACK, (25, 15), 2)
            pygame.draw.arc(surf1, BLACK, (10, 15, 20, 20), 0, 3.14, 2)
            pygame.draw.line(surf1, RED, (10, 35), (5, 40), 3)
            pygame.draw.line(surf1, RED, (30, 35), (35, 40), 3)
            frames.append(surf1)
            
            # Frame 2 - Tentacles in different position
            surf2 = surf1.copy()
            pygame.draw.line(surf2, (0, 0, 0, 0), (10, 35), (5, 40), 3)  # Clear previous tentacle
            pygame.draw.line(surf2, (0, 0, 0, 0), (30, 35), (35, 40), 3)  # Clear previous tentacle
            pygame.draw.line(surf2, RED, (10, 35), (0, 35), 3)  # New tentacle position
            pygame.draw.line(surf2, RED, (30, 35), (40, 35), 3)  # New tentacle position
            frames.append(surf2)
            
            # Frame 3 - Eyes blink
            surf3 = surf1.copy()
            pygame.draw.circle(surf3, (0, 0, 0, 0), (15, 15), 5)  # Clear previous eye
            pygame.draw.circle(surf3, (0, 0, 0, 0), (25, 15), 5)  # Clear previous eye
            pygame.draw.circle(surf3, (0, 0, 0, 0), (15, 15), 2)  # Clear previous pupil
            pygame.draw.circle(surf3, (0, 0, 0, 0), (25, 15), 2)  # Clear previous pupil
            pygame.draw.rect(surf3, WHITE, (10, 15, 10, 2))  # Closed eye
            pygame.draw.rect(surf3, WHITE, (20, 15, 10, 2))  # Closed eye
            frames.append(surf3)
            
        elif enemy_type == 2:  # Tough enemy
            # Frame 1
            surf1 = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(surf1, PURPLE, (20, 20), 18)
            pygame.draw.circle(surf1, WHITE, (15, 15), 4)
            pygame.draw.circle(surf1, WHITE, (25, 15), 4)
            pygame.draw.circle(surf1, BLACK, (15, 15), 2)
            pygame.draw.circle(surf1, BLACK, (25, 15), 2)
            pygame.draw.arc(surf1, GRAY, (5, 5, 30, 30), 0, 6.28, 3)
            frames.append(surf1)
            
            # Frame 2 - Armor pulsing
            surf2 = surf1.copy()
            pygame.draw.arc(surf2, (0, 0, 0, 0), (5, 5, 30, 30), 0, 6.28, 3)  # Clear previous armor
            pygame.draw.arc(surf2, GRAY, (7, 7, 26, 26), 0, 6.28, 4)  # New armor size
            frames.append(surf2)
            
            # Frame 3 - Armor and eyes pulsing
            surf3 = surf1.copy()
            pygame.draw.circle(surf3, (0, 0, 0, 0), (15, 15), 4)  # Clear previous eye
            pygame.draw.circle(surf3, (0, 0, 0, 0), (25, 15), 4)  # Clear previous eye
            pygame.draw.circle(surf3, WHITE, (15, 15), 5)  # Larger eye
            pygame.draw.circle(surf3, WHITE, (25, 15), 5)  # Larger eye
            pygame.draw.circle(surf3, RED, (15, 15), 3)  # Colored pupil
            pygame.draw.circle(surf3, RED, (25, 15), 3)  # Colored pupil
            frames.append(surf3)
            
        else:  # Fast enemy
            # Frame 1
            surf1 = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.rect(surf1, YELLOW, (10, 10, 20, 25))
            pygame.draw.circle(surf1, RED, (15, 15), 3)
            pygame.draw.circle(surf1, RED, (25, 15), 3)
            pygame.draw.polygon(surf1, YELLOW, [(5, 15), (10, 10), (10, 30), (5, 25)])
            pygame.draw.polygon(surf1, YELLOW, [(30, 10), (35, 15), (35, 25), (30, 30)])
            frames.append(surf1)
            
            # Frame 2 - Wings flapping
            surf2 = surf1.copy()
            pygame.draw.polygon(surf2, (0, 0, 0, 0), [(5, 15), (10, 10), (10, 30), (5, 25)])  # Clear previous wing
            pygame.draw.polygon(surf2, (0, 0, 0, 0), [(30, 10), (35, 15), (35, 25), (30, 30)])  # Clear previous wing
            pygame.draw.polygon(surf2, YELLOW, [(2, 20), (10, 10), (10, 30), (2, 20)])  # New wing position
            pygame.draw.polygon(surf2, YELLOW, [(30, 10), (38, 20), (38, 20), (30, 30)])  # New wing position
            frames.append(surf2)
            
            # Frame 3 - Different wing position and glowing eyes
            surf3 = surf1.copy()
            pygame.draw.polygon(surf3, (0, 0, 0, 0), [(5, 15), (10, 10), (10, 30), (5, 25)])  # Clear previous wing
            pygame.draw.polygon(surf3, (0, 0, 0, 0), [(30, 10), (35, 15), (35, 25), (30, 30)])  # Clear previous wing
            pygame.draw.polygon(surf3, YELLOW, [(8, 10), (10, 10), (10, 30), (8, 30)])  # New wing position (folded)
            pygame.draw.polygon(surf3, YELLOW, [(30, 10), (32, 10), (32, 30), (30, 30)])  # New wing position (folded)
            pygame.draw.circle(surf3, (255, 255, 0), (15, 15), 4)  # Glowing eye
            pygame.draw.circle(surf3, (255, 255, 0), (25, 15), 4)  # Glowing eye
            frames.append(surf3)
        
        # Store animation frames
        if enemy_type == 1:
            self.enemy1_frames = frames
            self.enemy1_frame_idx = 0
            self.enemy1_anim_counter = 0
            self.enemy1_anim_delay = 10
        elif enemy_type == 2:
            self.enemy2_frames = frames
            self.enemy2_frame_idx = 0
            self.enemy2_anim_counter = 0
            self.enemy2_anim_delay = 15
        else:
            self.enemy3_frames = frames
            self.enemy3_frame_idx = 0
            self.enemy3_anim_counter = 0
            self.enemy3_anim_delay = 5
        
        return frames[0]
    
    def create_powerup_sprite(self, powerup_type):
        """Create enhanced powerup sprite based on type with animations"""
        # Base frame 
        if powerup_type == 1:  # Health
            frames = []
            
            # Frame 1
            surf1 = pygame.Surface((30, 30), pygame.SRCALPHA)
            # Outer glow
            pygame.draw.circle(surf1, (0, 255, 100, 50), (15, 15), 15)
            # Main circle
            pygame.draw.circle(surf1, GREEN, (15, 15), 12)
            # Inner circle
            pygame.draw.circle(surf1, (200, 255, 200), (15, 15), 8)
            # Cross
            pygame.draw.rect(surf1, WHITE, (7, 12, 16, 6))
            pygame.draw.rect(surf1, WHITE, (12, 7, 6, 16))
            frames.append(surf1)
            
            # Frame 2 - pulsing
            surf2 = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(surf2, (0, 255, 100, 70), (15, 15), 14)
            pygame.draw.circle(surf2, GREEN, (15, 15), 11)
            pygame.draw.circle(surf2, (200, 255, 200), (15, 15), 7)
            pygame.draw.rect(surf2, WHITE, (8, 12, 14, 6))
            pygame.draw.rect(surf2, WHITE, (12, 8, 6, 14))
            frames.append(surf2)
            
            # Frame 3 - pulsing
            surf3 = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(surf3, (0, 255, 100, 90), (15, 15), 13)
            pygame.draw.circle(surf3, GREEN, (15, 15), 10)
            pygame.draw.circle(surf3, (200, 255, 200), (15, 15), 6)
            pygame.draw.rect(surf3, WHITE, (9, 12, 12, 6))
            pygame.draw.rect(surf3, WHITE, (12, 9, 6, 12))
            frames.append(surf3)
            
            self.powerup1_frames = frames
            self.powerup1_frame_idx = 0
            self.powerup1_anim_counter = 0
            self.powerup1_anim_delay = 8
            
            return frames[0]
            
        elif powerup_type == 2:  # Score boost
            frames = []
            
            # Frame 1
            surf1 = pygame.Surface((30, 30), pygame.SRCALPHA)
            # Outer glow
            pygame.draw.circle(surf1, (255, 255, 0, 50), (15, 15), 15)
            # Main circle
            pygame.draw.circle(surf1, YELLOW, (15, 15), 12)
            # Inner detail
            pygame.draw.circle(surf1, (255, 255, 200), (15, 15), 8)
            # Star shape
            star_points = []
            for i in range(5):
                angle = math.pi/2 + i * 2*math.pi/5
                x1 = 15 + 10 * math.cos(angle)
                y1 = 15 + 10 * math.sin(angle)
                angle += math.pi/5
                x2 = 15 + 5 * math.cos(angle)
                y2 = 15 + 5 * math.sin(angle)
                star_points.extend([(x1, y1), (x2, y2)])
            pygame.draw.polygon(surf1, (255, 200, 0), star_points)
            frames.append(surf1)
            
            # Frame 2 - rotating star
            surf2 = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(surf2, (255, 255, 0, 70), (15, 15), 14)
            pygame.draw.circle(surf2, YELLOW, (15, 15), 11)
            pygame.draw.circle(surf2, (255, 255, 200), (15, 15), 7)
            star_points = []
            for i in range(5):
                angle = math.pi/5 + i * 2*math.pi/5  # Rotated star
                x1 = 15 + 9 * math.cos(angle)
                y1 = 15 + 9 * math.sin(angle)
                angle += math.pi/5
                x2 = 15 + 4 * math.cos(angle)
                y2 = 15 + 4 * math.sin(angle)
                star_points.extend([(x1, y1), (x2, y2)])
            pygame.draw.polygon(surf2, (255, 200, 0), star_points)
            frames.append(surf2)
            
            # Frame 3 - further rotation
            surf3 = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(surf3, (255, 255, 0, 90), (15, 15), 13)
            pygame.draw.circle(surf3, YELLOW, (15, 15), 10)
            pygame.draw.circle(surf3, (255, 255, 200), (15, 15), 6)
            star_points = []
            for i in range(5):
                angle = 3*math.pi/10 + i * 2*math.pi/5  # Further rotated
                x1 = 15 + 8 * math.cos(angle)
                y1 = 15 + 8 * math.sin(angle)
                angle += math.pi/5
                x2 = 15 + 4 * math.cos(angle)
                y2 = 15 + 4 * math.sin(angle)
                star_points.extend([(x1, y1), (x2, y2)])
            pygame.draw.polygon(surf3, (255, 200, 0), star_points)
            frames.append(surf3)
            
            self.powerup2_frames = frames
            self.powerup2_frame_idx = 0
            self.powerup2_anim_counter = 0
            self.powerup2_anim_delay = 10
            
            return frames[0]
            
        else:  # Invincibility
            frames = []
            
            # Frame 1
            surf1 = pygame.Surface((30, 30), pygame.SRCALPHA)
            # Outer glow
            pygame.draw.circle(surf1, (100, 100, 255, 50), (15, 15), 15)
            # Shield effect
            pygame.draw.circle(surf1, BLUE, (15, 15), 12)
            # Inner shield
            pygame.draw.circle(surf1, (200, 200, 255), (15, 15), 8)
            # Shield pattern
            pygame.draw.arc(surf1, (255, 255, 255), (5, 5, 20, 20), 0, math.pi, 2)
            pygame.draw.arc(surf1, (150, 150, 255), (8, 8, 14, 14), 0, math.pi, 2)
            frames.append(surf1)
            
            # Frame 2 - shield rotation
            surf2 = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(surf2, (100, 100, 255, 70), (15, 15), 14)
            pygame.draw.circle(surf2, BLUE, (15, 15), 11)
            pygame.draw.circle(surf2, (200, 200, 255), (15, 15), 7)
            pygame.draw.arc(surf2, (255, 255, 255), (5, 5, 20, 20), math.pi/2, 3*math.pi/2, 2)
            pygame.draw.arc(surf2, (150, 150, 255), (8, 8, 14, 14), math.pi/2, 3*math.pi/2, 2)
            frames.append(surf2)
            
            # Frame 3 - further rotation
            surf3 = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(surf3, (100, 100, 255, 90), (15, 15), 13)
            pygame.draw.circle(surf3, BLUE, (15, 15), 10)
            pygame.draw.circle(surf3, (200, 200, 255), (15, 15), 6)
            pygame.draw.arc(surf3, (255, 255, 255), (5, 5, 20, 20), math.pi, 2*math.pi, 2)
            pygame.draw.arc(surf3, (150, 150, 255), (8, 8, 14, 14), math.pi, 2*math.pi, 2)
            frames.append(surf3)
            
            self.powerup3_frames = frames
            self.powerup3_frame_idx = 0
            self.powerup3_anim_counter = 0
            self.powerup3_anim_delay = 12
            
            return frames[0]
    
    def create_projectile_sprite(self):
        """Create projectile sprite"""
        surf = pygame.Surface((10, 10), pygame.SRCALPHA)
        pygame.draw.circle(surf, BLUE, (5, 5), 5)
        pygame.draw.circle(surf, WHITE, (5, 5), 2)
        return surf
    
    def create_background(self):
        """Create starfield background"""
        surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        # Create a gradient background from dark blue to black
        for y in range(WINDOW_HEIGHT):
            # Calculate the ratio of position
            ratio = y / WINDOW_HEIGHT
            # Create a gradient from dark blue to black
            r = int(DARK_BLUE[0] * (1 - ratio))
            g = int(DARK_BLUE[1] * (1 - ratio))
            b = int(DARK_BLUE[2] * (1 - ratio) + BLACK[2] * ratio)
            color = (r, g, b)
            pygame.draw.line(surf, color, (0, y), (WINDOW_WIDTH, y))
        return surf
    
    def generate_stars(self, count):
        """Generate random stars for the background"""
        stars = []
        for _ in range(count):
            x = random.randint(0, WINDOW_WIDTH)
            y = random.randint(0, WINDOW_HEIGHT)
            size = random.randint(1, 3)
            brightness = random.randint(100, 255)
            color = (brightness, brightness, brightness)
            stars.append((x, y, size, color, random.random() * 2 - 1))  # x, y, size, color, twinkle_offset
        return stars
    
    def generate_nebulas(self, count):
        """Generate colorful nebula clouds"""
        nebulas = []
        colors = [(255, 100, 100), (100, 100, 255), (255, 100, 255), 
                 (100, 255, 255), (255, 255, 100)]
        
        for _ in range(count):
            x = random.randint(0, WINDOW_WIDTH)
            y = random.randint(0, WINDOW_HEIGHT)
            radius = random.randint(100, 300)
            color = random.choice(colors)
            alpha = random.randint(20, 40)
            speed = random.random() * 0.2
            nebulas.append((x, y, radius, color, alpha, speed))
        
        return nebulas
    
    def animate_background(self):
        """Thread to animate background elements"""
        twinkle_counter = 0
        while True:
            twinkle_counter += 0.1
            self.parallax_offset += 0.1
            
            # Animate stars
            for i, star in enumerate(self.stars):
                # Make stars twinkle by varying brightness based on time and offset
                x, y, size, color, offset = star
                brightness = int(abs(127 * (1 + (offset + 1) * 0.3 * 
                                  (0.9 + 0.2 * (3 + offset) * 
                                   (0.9 + 0.1 * size) * 
                                   (0.9 + 0.1 * (1 + offset) * 
                                    (0.9 + 0.1 * (1 + size) * 
                                     (0.9 + 0.1 * (1 + offset) * 
                                      (0.9 + 0.1 * (1 + size) * 
                                       (0.9 + 0.1 * (1 + twinkle_counter)
                                   ))))))) % 155 + 100))
                new_color = (brightness, brightness, brightness)
                self.stars[i] = (x, y, size, new_color, offset)
            
            # Similar for near and far stars with different speeds
            for i, star in enumerate(self.near_stars):
                x, y, size, color, offset = star
                # Make near stars move faster (parallax effect)
                x = (x - 0.5) % WINDOW_WIDTH
                brightness = int((math.sin(twinkle_counter + offset) * 55 + 200))
                new_color = (brightness, brightness, brightness)
                self.near_stars[i] = (x, y, size, new_color, offset)
                
            for i, star in enumerate(self.far_stars):
                x, y, size, color, offset = star
                # Make far stars move slower
                x = (x - 0.1) % WINDOW_WIDTH
                brightness = int((math.sin(twinkle_counter * 0.5 + offset) * 55 + 200))
                new_color = (brightness, brightness, brightness)
                self.far_stars[i] = (x, y, size, new_color, offset)
            
            # Animate nebulas
            for i, nebula in enumerate(self.nebulas):
                x, y, radius, color, alpha, speed = nebula
                # Slowly move nebulas
                x = (x - speed) % (WINDOW_WIDTH + radius * 2)
                # Pulse alpha with bounds checking
                new_alpha = max(0, min(255, int(alpha + math.sin(twinkle_counter * 0.2) * 5)))
                self.nebulas[i] = (x, y, radius, color, new_alpha, speed)
            
            time.sleep(0.05)
    
    def handle_events(self):
        """Handle pygame events"""
        # Reset keys_just_pressed every frame
        self.keys_just_pressed = {}
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Send an exit command to the logic process
                self.render_to_logic_queue.put({'type': 'exit_game'})
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                self.keys_pressed[event.key] = True
                self.keys_just_pressed[event.key] = True  # Mark this key as just pressed this frame
                
                # Toggle process info display with P key
                if event.key == pygame.K_p:
                    self.show_process_info = not self.show_process_info
                    print(f"Process info display: {'ON' if self.show_process_info else 'OFF'}")
                
                # Check for ESC in game over state to exit directly from renderer too
                with self.game_state_lock:
                    if self.game_state.value == GameState.GAME_OVER.value and event.key == pygame.K_ESCAPE:
                        # Send an exit command to the logic process
                        self.render_to_logic_queue.put({'type': 'exit_game'})
                        pygame.quit()
                        sys.exit()
            elif event.type == pygame.KEYUP:
                self.keys_pressed[event.key] = False
        
        # Send current input state to game logic
        input_data = {
            'type': 'input',
            'keys': self.keys_pressed,
            'key_press': self.keys_just_pressed  # Send the just-pressed keys separately
        }
        self.render_to_logic_queue.put(input_data)
    
    def receive_game_state(self):
        """Receive and process game state from logic process"""
        try:
            if not self.logic_to_render_queue.empty():
                game_data = self.logic_to_render_queue.get_nowait()
                self.entities = game_data.get('entities', [])
                self.current_wave = game_data.get('wave', 1)
                
                # Comment out debug prints
                # Debug: Count entities by type
                # entity_counts = {}
                # for entity in self.entities:
                #     entity_type = entity['type']
                #     if entity_type not in entity_counts:
                #         entity_counts[entity_type] = 0
                #     entity_counts[entity_type] += 1
                
                # Print enemy count (if any)
                # if EntityType.ENEMY.value in entity_counts:
                #     print(f"Received {entity_counts[EntityType.ENEMY.value]} enemies")
                #     # Debug first enemy position
                #     for entity in self.entities:
                #         if entity['type'] == EntityType.ENEMY.value:
                #             print(f"Enemy at position: ({entity['x']}, {entity['y']})")
                #             break
        except Exception as e:
            print(f"Error receiving game state: {e}")
    
    def draw_background(self):
        """Draw the game background with parallax effect"""
        # Draw base background
        self.screen.blit(self.assets['background'], (0, 0))
        
        # Draw nebulas (furthest layer)
        for x, y, radius, color, alpha, _ in self.nebulas:
            # Create a surface for the nebula with alpha channel
            nebula_surf = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            # Draw a soft gradient circle
            for r in range(radius, 0, -10):
                current_alpha = int(alpha * (r / radius))
                # Create a proper RGBA tuple instead of concatenating
                rgba_color = (color[0], color[1], color[2], current_alpha)
                pygame.draw.circle(nebula_surf, rgba_color, (radius, radius), r)
            # Blit the nebula
            self.screen.blit(nebula_surf, (int(x - radius), int(y - radius)))
        
        # Draw far stars (slow moving)
        for x, y, size, color, _ in self.far_stars:
            pygame.draw.circle(self.screen, color, (int(x), int(y)), size)
        
        # Draw middle layer stars
        for x, y, size, color, _ in self.stars:
            pygame.draw.circle(self.screen, color, (int(x), int(y)), size)
        
        # Draw near stars (fast moving)
        for x, y, size, color, _ in self.near_stars:
            # Draw with a slight glow effect
            if size > 1:
                glow_size = size + 2
                glow_color = (min(color[0], 150), min(color[1], 150), min(color[2], 150))
                pygame.draw.circle(self.screen, glow_color, (int(x), int(y)), glow_size)
            pygame.draw.circle(self.screen, color, (int(x), int(y)), size)
    
    def update_animations(self):
        """Update animation frames for all entities"""
        # Update player animation
        self.player_anim_counter += 1
        if self.player_anim_counter >= self.player_anim_delay:
            self.player_anim_counter = 0
            self.player_frame_idx = (self.player_frame_idx + 1) % len(self.player_frames)
        
        # Update enemy animations
        self.enemy1_anim_counter += 1
        if self.enemy1_anim_counter >= self.enemy1_anim_delay:
            self.enemy1_anim_counter = 0
            self.enemy1_frame_idx = (self.enemy1_frame_idx + 1) % len(self.enemy1_frames)
            
        self.enemy2_anim_counter += 1
        if self.enemy2_anim_counter >= self.enemy2_anim_delay:
            self.enemy2_anim_counter = 0
            self.enemy2_frame_idx = (self.enemy2_frame_idx + 1) % len(self.enemy2_frames)
            
        self.enemy3_anim_counter += 1
        if self.enemy3_anim_counter >= self.enemy3_anim_delay:
            self.enemy3_anim_counter = 0
            self.enemy3_frame_idx = (self.enemy3_frame_idx + 1) % len(self.enemy3_frames)
            
        # Update projectile particles
        for i, particle in enumerate(self.projectile_particles):
            x, y, color, size, lifetime, dx, dy = particle
            lifetime -= 1
            size = max(1, size - 0.2)
            x += dx
            y += dy
            if lifetime <= 0:
                self.projectile_particles.pop(i)
            else:
                self.projectile_particles[i] = (x, y, color, size, lifetime, dx, dy)
        
        # Update explosion particles
        for i, particle in enumerate(self.explosion_particles):
            x, y, color, size, lifetime, dx, dy = particle
            lifetime -= 1
            size = max(1, size - 0.1)
            x += dx
            y += dy
            dy += 0.05  # Gravity effect
            if lifetime <= 0:
                self.explosion_particles.pop(i)
            else:
                self.explosion_particles[i] = (x, y, color, size, lifetime, dx, dy)
    
    def create_explosion(self, x, y, color=(255, 100, 0), count=30):
        """Create particle explosion effect"""
        for _ in range(count):
            angle = random.random() * math.pi * 2
            speed = random.random() * 3 + 1
            dx = math.cos(angle) * speed
            dy = math.sin(angle) * speed
            size = random.random() * 4 + 2
            lifetime = random.randint(20, 40)
            # Slightly randomize the color
            r = min(255, max(0, color[0] + random.randint(-20, 20)))
            g = min(255, max(0, color[1] + random.randint(-20, 20)))
            b = min(255, max(0, color[2] + random.randint(-20, 20)))
            self.explosion_particles.append((x, y, (r, g, b), size, lifetime, dx, dy))
    
    def create_projectile_trail(self, x, y):
        """Create particle trail behind projectiles"""
        for _ in range(2):
            dx = random.random() * 0.5 - 1.5  # Move backward
            dy = random.random() * 1 - 0.5  # Slight vertical spread
            size = random.random() * 2 + 1
            lifetime = random.randint(5, 15)
            self.projectile_particles.append((x, y, BLUE, size, lifetime, dx, dy))
    
    def draw_entities(self):
        """Draw all game entities with animations"""
        # Draw explosion particles first (behind everything)
        for x, y, color, size, lifetime, _, _ in self.explosion_particles:
            # Fade out as lifetime decreases
            alpha = int(lifetime * 255 / 40)
            # Create proper RGBA color
            color_with_alpha = (color[0], color[1], color[2], alpha)
            # Create a temporary surface for the particle with alpha
            particle_surf = pygame.Surface((int(size*2), int(size*2)), pygame.SRCALPHA)
            pygame.draw.circle(particle_surf, color_with_alpha, (int(size), int(size)), int(size))
            self.screen.blit(particle_surf, (int(x - size), int(y - size)))
        
        # Draw projectile particles (trails)
        for x, y, color, size, lifetime, _, _ in self.projectile_particles:
            # Fade out as lifetime decreases
            alpha = int(lifetime * 255 / 15)
            # Create proper RGBA color
            color_with_alpha = (color[0], color[1], color[2], alpha)
            # Create a temporary surface for the particle with alpha
            particle_surf = pygame.Surface((int(size*2), int(size*2)), pygame.SRCALPHA)
            pygame.draw.circle(particle_surf, color_with_alpha, (int(size), int(size)), int(size))
            self.screen.blit(particle_surf, (int(x - size), int(y - size)))
        
        # Draw regular entities
        for entity in self.entities:
            entity_type = entity['type']
            x = entity['x']
            y = entity['y']
            width = entity['width']
            height = entity['height']
            
            if entity_type == EntityType.PLAYER.value:
                # Draw current animation frame
                player_frame = self.player_frames[self.player_frame_idx]
                self.screen.blit(player_frame, (x, y))
                
                # Draw jet flame behind player (with flickering effect)
                if random.random() > 0.2:  # Occasionally skip for flickering
                    flame_scale = random.uniform(0.8, 1.2)  # Random size for flickering
                    flame_surface = pygame.transform.scale(
                        self.player_jet_flame,
                        (int(30 * flame_scale), int(20 * flame_scale))
                    )
                    self.screen.blit(flame_surface, (x - 25, y + 30))
            
            elif entity_type == EntityType.PLATFORM.value:
                # We need to stretch the platform sprite to match the size
                platform_surf = pygame.transform.scale(
                    self.assets['platform'], 
                    (width, height)
                )
                self.screen.blit(platform_surf, (x, y))
                
                # Add glow effect for platform edges
                glow_surf = pygame.Surface((width, 5), pygame.SRCALPHA)
                for i in range(5):
                    alpha = 150 - i * 30
                    # Create proper RGBA color
                    glow_color = (100, 200, 255, alpha)
                    pygame.draw.rect(glow_surf, glow_color, (0, i, width, 1))
                self.screen.blit(glow_surf, (x, y - 5))
            
            elif entity_type == EntityType.ENEMY.value:
                enemy_type = entity.get('enemy_type', 1)
                
                # Draw current animation frame based on enemy type
                if enemy_type == 1:
                    frame = self.enemy1_frames[self.enemy1_frame_idx]
                elif enemy_type == 2:
                    frame = self.enemy2_frames[self.enemy2_frame_idx]
                else:
                    frame = self.enemy3_frames[self.enemy3_frame_idx]
                
                # Comment out debug outline
                # debug_rect = pygame.Rect(x-2, y-2, width+4, height+4)
                # pygame.draw.rect(self.screen, (255, 0, 255), debug_rect, 2)  # Magenta outline
                
                # Draw enemy with its normal frame
                self.screen.blit(frame, (x, y))
                
                # Comment out position text for debugging
                # pos_text = f"({int(x)},{int(y)})"
                # pos_surf = self.small_font.render(pos_text, True, (255, 255, 0))
                # self.screen.blit(pos_surf, (x, y - 15))
                
                # Draw enemy health bar if damaged
                entity_health = entity.get('health', 30)  # Default health
                max_health = 30
                if enemy_type == 2:
                    max_health = 50
                elif enemy_type == 3:
                    max_health = 20
                
                if entity_health < max_health:
                    health_pct = entity_health / max_health
                    bar_width = 30
                    current_width = int(bar_width * health_pct)
                    pygame.draw.rect(self.screen, RED, (x + 5, y - 5, bar_width, 3))
                    pygame.draw.rect(self.screen, GREEN, (x + 5, y - 5, current_width, 3))
            
            elif entity_type == EntityType.PROJECTILE.value:
                # Add a glowing effect to projectiles
                glow_size = 20
                glow_surf = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
                
                # Create a radial gradient
                for radius in range(int(glow_size/2), 0, -1):
                    alpha = int(150 * (radius / (glow_size/2)))
                    # Create proper RGBA color
                    glow_color = (100, 100, 255, alpha)
                    pygame.draw.circle(glow_surf, glow_color, (int(glow_size/2), int(glow_size/2)), radius)
                
                # Position the glow behind the projectile
                glow_x = x - int(glow_size/2) + 5
                glow_y = y - int(glow_size/2) + 5
                self.screen.blit(glow_surf, (glow_x, glow_y))
                
                # Draw the actual projectile
                self.screen.blit(self.assets['projectile'], (x, y))
                
                # Create particle trail
                self.create_projectile_trail(x + 5, y + 5)
            
            elif entity_type == EntityType.POWERUP.value:
                powerup_type = entity.get('powerup_type', 1)
                
                # Add pulsing glow effect
                pulse = (math.sin(pygame.time.get_ticks() * 0.01) + 1) * 0.5  # 0 to 1
                glow_size = int(40 + 10 * pulse)
                glow_surf = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
                
                # Different colors for different powerups
                if powerup_type == 1:  # Health
                    glow_color = (0, 255, 0, 50)  # Already in RGBA format
                    powerup_frame = self.powerup1_frames[self.powerup1_frame_idx]
                elif powerup_type == 2:  # Score
                    glow_color = (255, 255, 0, 50)  # Already in RGBA format
                    powerup_frame = self.powerup2_frames[self.powerup2_frame_idx]
                else:  # Invincibility
                    glow_color = (0, 100, 255, 50)  # Already in RGBA format
                    powerup_frame = self.powerup3_frames[self.powerup3_frame_idx]
                
                pygame.draw.circle(glow_surf, glow_color, (glow_size // 2, glow_size // 2), glow_size // 2)
                self.screen.blit(glow_surf, (x - (glow_size - 30) // 2, y - (glow_size - 30) // 2))
                
                # Draw the powerup with a hovering effect
                hover_offset = int(math.sin(pygame.time.get_ticks() * 0.005) * 3)
                self.screen.blit(powerup_frame, (x, y + hover_offset))
    
    def draw_ui(self):
        """Draw game UI elements"""
        # Get current game state
        with self.game_state_lock:
            current_state = self.game_state.value
        
        # Don't draw UI on menu or game over screens
        if current_state == GameState.MENU.value or current_state == GameState.GAME_OVER.value:
            return
        
        # Draw score
        with self.player_score_lock:
            score_text = f"SCORE: {self.player_score.value}"
        score_surface = self.main_font.render(score_text, True, WHITE)
        self.screen.blit(score_surface, (20, 20))
        
        # Draw wave information
        wave_text = f"WAVE: {self.current_wave}"
        wave_surface = self.main_font.render(wave_text, True, WHITE)
        self.screen.blit(wave_surface, (self.width - wave_surface.get_width() - 20, 20))
        
        # Draw health bar
        with self.player_health_lock:
            health = self.player_health.value
        
        health_text = f"HEALTH: {health}"
        health_surface = self.main_font.render(health_text, True, WHITE)
        self.screen.blit(health_surface, (20, 60))
        
        # Health bar background
        pygame.draw.rect(self.screen, GRAY, (20, 100, 200, 20))
        # Health bar fill
        health_width = int(health / 100 * 200)
        if health > 60:
            health_color = GREEN
        elif health > 30:
            health_color = YELLOW
        else:
            health_color = RED
        pygame.draw.rect(self.screen, health_color, (20, 100, health_width, 20))
        
        # Controls reminder
        controls_text = "CONTROLS: ARROWS=Move  UP=Jump  Z/X=Attack  ESC=Pause  P=Toggle Info"
        controls_surface = self.small_font.render(controls_text, True, WHITE)
        self.screen.blit(controls_surface, (20, self.height - 30))
        
        # If paused, show pause icon
        if current_state == GameState.PAUSED.value:
            pause_text = "PAUSED"
            pause_surface = self.main_font.render(pause_text, True, WHITE)
            text_width = pause_surface.get_width()
            
            # Background rectangle
            pygame.draw.rect(self.screen, (0, 0, 0, 150), 
                             (self.width // 2 - text_width // 2 - 20, 
                              self.height // 2 - 30, 
                              text_width + 40, 60))
            
            # Text
            self.screen.blit(pause_surface, 
                           (self.width // 2 - text_width // 2, 
                            self.height // 2 - pause_surface.get_height() // 2))
        
        # Process info display (when toggled on with P key)
        if self.show_process_info:
            # Update performance metrics
            current_time = time.time()
            frame_time = current_time - self.last_frame_time
            self.last_frame_time = current_time
            
            self.frame_times.append(frame_time)
            if len(self.frame_times) > 60:  # Keep only last 60 frames
                self.frame_times.pop(0)
            
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            current_fps = 1.0 / max(avg_frame_time, 0.0001)  # Avoid division by zero
            
            # Background for process info
            info_bg_rect = pygame.Rect(self.width - 300, 60, 280, 180)
            pygame.draw.rect(self.screen, (0, 0, 0, 150), info_bg_rect)
            pygame.draw.rect(self.screen, GRAY, info_bg_rect, 1)
            
            # Display info
            y_offset = 70
            info_texts = [
                f"FPS: {current_fps:.1f}",
                f"Frame Time: {avg_frame_time*1000:.1f} ms",
                f"Entities: {len(self.entities)}",
                f"Particles: {len(self.projectile_particles) + len(self.explosion_particles)}",
                f"Render Queue: {self.logic_to_render_queue.qsize()}"
            ]
            
            for info in info_texts:
                info_surface = self.small_font.render(info, True, WHITE)
                self.screen.blit(info_surface, (self.width - 290, y_offset))
                y_offset += 25
            
            # Memory info (if available)
            try:
                import psutil
                process = psutil.Process()
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                cpu_percent = process.cpu_percent(interval=None) / psutil.cpu_count()
                
                memory_text = f"Memory: {memory_mb:.1f} MB"
                cpu_text = f"CPU: {cpu_percent:.1f}%"
                
                mem_surface = self.small_font.render(memory_text, True, WHITE)
                cpu_surface = self.small_font.render(cpu_text, True, WHITE)
                
                self.screen.blit(mem_surface, (self.width - 290, y_offset))
                y_offset += 25
                self.screen.blit(cpu_surface, (self.width - 290, y_offset))
            except (ImportError, AttributeError):
                # psutil not available or error accessing metrics
                no_metrics = self.small_font.render("System metrics unavailable", True, GRAY)
                self.screen.blit(no_metrics, (self.width - 290, y_offset))
    
    def draw_menu(self):
        """Draw the game menu screen"""
        # Opaque overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        # Title
        title_text = "ALIEN INVASION"
        title_surf = pygame.font.SysFont('Arial', 72, bold=True).render(title_text, True, LIGHT_BLUE)
        self.screen.blit(title_surf, (self.width//2 - title_surf.get_width()//2, 150))
        
        # Subtitle
        subtitle_text = "A Game about Operating System Concepts"
        subtitle_surf = self.main_font.render(subtitle_text, True, WHITE)
        self.screen.blit(subtitle_surf, (self.width//2 - subtitle_surf.get_width()//2, 230))
        
        # Instructions
        instructions = [
            "CONTROLS:",
            "ARROWS: Move player (← →) and Jump (↑)",
            "Z/X: Attack",
            "ESC: Pause/Quit",
            "P: Toggle process info display",
            "",
            "Press SPACE to Start"
        ]
        
        y_pos = 350
        for instruction in instructions:
            if instruction == "Press SPACE to Start":
                # Make it pulse
                pulse = math.sin(pygame.time.get_ticks() * 0.005) * 0.3 + 0.7
                color = (int(255 * pulse), int(255 * pulse), int(100 * pulse))
                text_surf = self.main_font.render(instruction, True, color)
                y_pos += 30  # Extra space before start prompt
            else:
                text_surf = self.small_font.render(instruction, True, WHITE)
            
            self.screen.blit(text_surf, (self.width//2 - text_surf.get_width()//2, y_pos))
            y_pos += 30
    
    def draw_game_over(self):
        """Draw the game over screen"""
        # Opaque overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        # Title
        title_text = "GAME OVER"
        title_surf = pygame.font.SysFont('Arial', 72, bold=True).render(title_text, True, RED)
        self.screen.blit(title_surf, (self.width//2 - title_surf.get_width()//2, 150))
        
        # Score
        with self.player_score_lock:
            score = self.player_score.value
        
        score_text = f"FINAL SCORE: {score}"
        score_surf = self.main_font.render(score_text, True, WHITE)
        self.screen.blit(score_surf, (self.width//2 - score_surf.get_width()//2, 250))
        
        # Wave reached
        wave_text = f"WAVE REACHED: {self.current_wave}"
        wave_surf = self.main_font.render(wave_text, True, WHITE)
        self.screen.blit(wave_surf, (self.width//2 - wave_surf.get_width()//2, 300))
        
        # Instructions - with pulse effect
        pulse = math.sin(pygame.time.get_ticks() * 0.005) * 0.3 + 0.7
        color = (int(255 * pulse), int(255 * pulse), int(100 * pulse))
        
        instructions = [
            "Press SPACE to Restart",
            "Press ESC to Quit"
        ]
        
        y_pos = 400
        for instruction in instructions:
            text_surf = self.main_font.render(instruction, True, color)
            self.screen.blit(text_surf, (self.width//2 - text_surf.get_width()//2, y_pos))
            y_pos += 50
    
    def draw_pause_screen(self):
        """Draw the pause screen overlay"""
        # Create semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 30, 180))
        self.screen.blit(overlay, (0, 0))
        
        # Main pause text
        pause_text = "PAUSED"
        pause_surf = pygame.font.SysFont('Arial', 72, bold=True).render(pause_text, True, WHITE)
        self.screen.blit(pause_surf, (self.width//2 - pause_surf.get_width()//2, 200))
        
        # Controls reminder
        controls = [
            "Press ESC to Resume",
            "CONTROLS:",
            "ARROWS: Move player (← →) and Jump (↑)",
            "Z/X: Attack",
            "P: Toggle process info display"
        ]
        
        y_pos = 300
        for control in controls:
            text_surf = self.small_font.render(control, True, WHITE)
            self.screen.blit(text_surf, (self.width//2 - text_surf.get_width()//2, y_pos))
            y_pos += 30
    
    def run(self):
        """Main rendering loop"""
        clock = pygame.time.Clock()
        running = True
        
        while running:
            # Handle events
            self.handle_events()
            
            # Receive updated game state from logic process
            self.receive_game_state()
            
            # Get current game state
            with self.game_state_lock:
                current_state = self.game_state.value
            
            # Clear screen and draw background
            self.screen.fill(BLACK)
            self.draw_background()
            
            # Update animations
            self.update_animations()
            
            # Draw game entities
            self.draw_entities()
            
            # Draw UI elements
            self.draw_ui()
            
            # Draw game state screens
            if current_state == GameState.MENU.value:
                self.draw_menu()
            elif current_state == GameState.GAME_OVER.value:
                self.draw_game_over()
            elif current_state == GameState.PAUSED.value:
                self.draw_pause_screen()
            
            # Update display
            pygame.display.flip()
            
            # Cap to 60 FPS
            clock.tick(FPS) 