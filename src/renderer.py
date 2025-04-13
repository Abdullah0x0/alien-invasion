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
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                self.keys_pressed[event.key] = True
            elif event.type == pygame.KEYUP:
                self.keys_pressed[event.key] = False
        
        # Send current input state to game logic
        input_data = {
            'type': 'input',
            'keys': self.keys_pressed
        }
        self.render_to_logic_queue.put(input_data)
    
    def receive_game_state(self):
        """Receive and process game state from logic process"""
        try:
            if not self.logic_to_render_queue.empty():
                game_data = self.logic_to_render_queue.get_nowait()
                self.entities = game_data.get('entities', [])
                self.current_wave = game_data.get('wave', 1)
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
                
                self.screen.blit(frame, (x, y))
                
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
        """Draw user interface elements with modern styling"""
        # Get synchronized values
        with self.player_score_lock:
            score = self.player_score.value
        
        with self.player_health_lock:
            health = self.player_health.value
        
        with self.game_state_lock:
            game_state = self.game_state.value
        
        # Draw score with glow effect
        score_text = f"SCORE: {score}"
        # Shadow text
        shadow_surf = self.main_font.render(score_text, True, (0, 0, 0))
        self.screen.blit(shadow_surf, (12, 12))
        # Actual text
        score_surf = self.main_font.render(score_text, True, (200, 200, 255))
        self.screen.blit(score_surf, (10, 10))
        
        # Draw health bar with modern styling
        # Background panel with transparency
        panel_surface = pygame.Surface((220, 30), pygame.SRCALPHA)
        panel_surface.fill((0, 0, 0, 128))
        self.screen.blit(panel_surface, (10, 50))
        
        # Border
        pygame.draw.rect(self.screen, WHITE, (10, 50, 220, 30), 1)
        
        # Health bar background
        pygame.draw.rect(self.screen, (50, 50, 50), (20, 55, 200, 20))
        
        # Health gradient (changes color based on health)
        health_width = int(200 * (health / 100))
        if health > 70:
            health_color = GREEN
        elif health > 30:
            health_color = YELLOW
        else:
            health_color = RED
            
            # Flashing effect for low health
            if pygame.time.get_ticks() % 1000 < 500:
                health_color = (255, 150, 150)
        
        # Draw the health bar with a gradient effect
        for i in range(health_width):
            # Create a gradient from left to right
            gradient_factor = i / 200
            color = (
                int(health_color[0] * (0.8 + gradient_factor * 0.2)),
                int(health_color[1] * (0.8 + gradient_factor * 0.2)),
                int(health_color[2] * (0.8 + gradient_factor * 0.2))
            )
            pygame.draw.line(self.screen, color, (20 + i, 55), (20 + i, 74))
        
        # Health text
        health_text = f"HEALTH: {health}%"
        health_surf = self.small_font.render(health_text, True, WHITE)
        text_x = 20 + (200 - health_surf.get_width()) // 2
        self.screen.blit(health_surf, (text_x, 58))
        
        # Draw wave number with a badge style
        wave_badge = pygame.Surface((150, 40), pygame.SRCALPHA)
        pygame.draw.rect(wave_badge, (0, 0, 0, 170), (0, 0, 150, 40), border_radius=10)
        pygame.draw.rect(wave_badge, BLUE, (0, 0, 150, 40), 2, border_radius=10)
        
        wave_text = f"WAVE {self.current_wave}"
        wave_surf = self.main_font.render(wave_text, True, WHITE)
        badge_x = self.width - 160
        wave_badge.blit(wave_surf, ((150 - wave_surf.get_width()) // 2, (40 - wave_surf.get_height()) // 2))
        self.screen.blit(wave_badge, (badge_x, 10))
        
        # Draw animated wave indicator
        pulse_size = int(5 + 3 * math.sin(pygame.time.get_ticks() * 0.01))
        pygame.draw.circle(self.screen, BLUE, (badge_x - 10, 30), pulse_size)
        
        # Draw game state overlay
        if game_state == GameState.MENU.value:
            self.draw_menu()
        elif game_state == GameState.PAUSED.value:
            self.draw_pause_screen()
        elif game_state == GameState.GAME_OVER.value:
            self.draw_game_over()
    
    def draw_menu(self):
        """Draw main menu screen with visual effects"""
        # Overlay with gradient
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        for y in range(WINDOW_HEIGHT):
            alpha = min(210, 100 + int(y * 0.15))
            # Create proper RGBA color
            gradient_color = (0, 0, 0, alpha)
            pygame.draw.line(overlay, gradient_color, (0, y), (WINDOW_WIDTH, y))
        self.screen.blit(overlay, (0, 0))
        
        # Title with glow effect
        title_glow_surf = pygame.Surface((400, 100), pygame.SRCALPHA)
        title_text = "ALIEN INVASION"
        title_size = 60
        title_font = pygame.font.SysFont('Arial', title_size, bold=True)
        
        # Draw glow
        glow_size = 10
        for i in range(glow_size, 0, -2):
            alpha = 10 + (glow_size - i) * 5
            # Create proper RGBA color
            glow_color = (0, 100, 255, alpha)
            title_glow = title_font.render(title_text, True, (0, 100, 255))
            
            # Create a surface with alpha
            glow_surf = pygame.Surface(title_glow.get_size(), pygame.SRCALPHA)
            glow_surf.fill((0, 100, 255, alpha))
            glow_surf.blit(title_glow, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            
            title_glow_surf.blit(
                glow_surf, 
                ((400 - title_glow.get_width()) // 2 - i // 2, (100 - title_glow.get_height()) // 2 - i // 2)
            )
        
        # Main title
        title = title_font.render(title_text, True, (200, 200, 255))
        title_glow_surf.blit(title, ((400 - title.get_width()) // 2, (100 - title.get_height()) // 2))
        
        # Position and draw title
        title_y = WINDOW_HEIGHT // 4
        title_x = (WINDOW_WIDTH - 400) // 2
        self.screen.blit(title_glow_surf, (title_x, title_y))
        
        # Subtitle with animation
        subtitle_y = title_y + 120
        subtitle_wave = int(5 * math.sin(pygame.time.get_ticks() * 0.005))
        subtitle = self.main_font.render("Press SPACE to Start", True, (150, 150, 255))
        self.screen.blit(subtitle, (WINDOW_WIDTH // 2 - subtitle.get_width() // 2, subtitle_y + subtitle_wave))
        
        # Controls panel
        panel_y = subtitle_y + 100
        panel = pygame.Surface((500, 200), pygame.SRCALPHA)
        # Create proper RGBA color for panel
        panel_bg_color = (0, 0, 50, 200)
        panel_border_color = (100, 100, 255, 255)
        pygame.draw.rect(panel, panel_bg_color, (0, 0, 500, 200), border_radius=20)
        pygame.draw.rect(panel, panel_border_color, (0, 0, 500, 200), 2, border_radius=20)
        
        # Panel header
        header = self.main_font.render("CONTROLS", True, WHITE)
        panel.blit(header, ((500 - header.get_width()) // 2, 20))
        
        # Panel content - controls
        controls = [
            ("ARROW KEYS", "Move"),
            ("SPACE", "Jump"),
            ("Z / X", "Attack"),
            ("ESC", "Pause")
        ]
        
        for i, (key, action) in enumerate(controls):
            y_pos = 70 + i * 30
            
            # Key box
            key_surf = self.small_font.render(key, True, BLACK)
            key_box = pygame.Surface((150, 25), pygame.SRCALPHA)
            pygame.draw.rect(key_box, (200, 200, 255), (0, 0, 150, 25), border_radius=5)
            key_box.blit(key_surf, ((150 - key_surf.get_width()) // 2, (25 - key_surf.get_height()) // 2))
            panel.blit(key_box, (50, y_pos))
            
            # Action text
            action_surf = self.small_font.render(action, True, WHITE)
            panel.blit(action_surf, (220, y_pos + 5))
        
        # Draw panel
        self.screen.blit(panel, (WINDOW_WIDTH // 2 - 250, panel_y))
    
    def draw_pause_screen(self):
        """Draw pause screen overlay with visual effects"""
        # Create blur effect by drawing the game at reduced alpha
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        # Use proper RGBA color
        overlay_color = (0, 0, 30, 200)
        overlay.fill(overlay_color)
        self.screen.blit(overlay, (0, 0))
        
        # Pause text with pulsing effect
        scale = 1.0 + 0.1 * math.sin(pygame.time.get_ticks() * 0.003)
        pause_font = pygame.font.SysFont('Arial', int(80 * scale), bold=True)
        pause_text = pause_font.render("PAUSED", True, WHITE)
        text_x = WINDOW_WIDTH // 2 - pause_text.get_width() // 2
        text_y = WINDOW_HEIGHT // 3 - pause_text.get_height() // 2
        
        # Draw text shadow
        shadow = pause_font.render("PAUSED", True, (0, 0, 0))
        self.screen.blit(shadow, (text_x + 5, text_y + 5))
        self.screen.blit(pause_text, (text_x, text_y))
        
        # Continue text with bouncing arrow
        continue_text = self.small_font.render("Press ESC to Continue", True, (200, 200, 255))
        arrow_offset = int(5 * math.sin(pygame.time.get_ticks() * 0.01))
        
        # Draw arrow
        arrow_points = [
            (WINDOW_WIDTH // 2 - 50, WINDOW_HEIGHT // 2 + 50 + arrow_offset),
            (WINDOW_WIDTH // 2 - 40, WINDOW_HEIGHT // 2 + 60 + arrow_offset),
            (WINDOW_WIDTH // 2 - 45, WINDOW_HEIGHT // 2 + 60 + arrow_offset),
            (WINDOW_WIDTH // 2 - 45, WINDOW_HEIGHT // 2 + 70 + arrow_offset),
            (WINDOW_WIDTH // 2 - 55, WINDOW_HEIGHT // 2 + 70 + arrow_offset),
            (WINDOW_WIDTH // 2 - 55, WINDOW_HEIGHT // 2 + 60 + arrow_offset),
            (WINDOW_WIDTH // 2 - 60, WINDOW_HEIGHT // 2 + 60 + arrow_offset),
        ]
        pygame.draw.polygon(self.screen, (200, 200, 255), arrow_points)
        
        # Draw text
        self.screen.blit(continue_text, (WINDOW_WIDTH // 2 - continue_text.get_width() // 2, WINDOW_HEIGHT // 2 + 50))
    
    def draw_game_over(self):
        """Draw game over screen with visual effects"""
        # Darken the screen with gradient
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        for y in range(WINDOW_HEIGHT):
            alpha = min(220, 180 + int(y * 0.1))
            # Create proper RGBA color
            gradient_color = (50, 0, 0, alpha)
            pygame.draw.line(overlay, gradient_color, (0, y), (WINDOW_WIDTH, y))
        self.screen.blit(overlay, (0, 0))
        
        with self.player_score_lock:
            score = self.player_score.value
        
        # Game over text with animation
        game_over_font = pygame.font.SysFont('Arial', 80, bold=True)
        for i in range(4, 0, -1):
            # Shadow layers with proper RGBA colors
            alpha = 40 * i
            shadow_color = (255, 0, 0, alpha)
            
            # Create a surface with alpha for text shadow
            shadow_text = game_over_font.render("GAME OVER", True, RED)
            shadow_surf = pygame.Surface(shadow_text.get_size(), pygame.SRCALPHA)
            shadow_surf.fill((255, 0, 0, alpha))
            shadow_surf.blit(shadow_text, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            
            self.screen.blit(
                shadow_surf, 
                (WINDOW_WIDTH // 2 - shadow_text.get_width() // 2 + i, WINDOW_HEIGHT // 3 + i)
            )
        
        # Main text
        game_over_text = game_over_font.render("GAME OVER", True, RED)
        self.screen.blit(game_over_text, (WINDOW_WIDTH // 2 - game_over_text.get_width() // 2, WINDOW_HEIGHT // 3))
        
        # Score panel
        panel = pygame.Surface((400, 150), pygame.SRCALPHA)
        # Create proper RGBA color for panel background
        panel_bg_color = (30, 0, 0, 220)
        pygame.draw.rect(panel, panel_bg_color, (0, 0, 400, 150), border_radius=15)
        pygame.draw.rect(panel, RED, (0, 0, 400, 150), 3, border_radius=15)
        
        # Final score text
        score_text = self.main_font.render("FINAL SCORE", True, WHITE)
        panel.blit(score_text, ((400 - score_text.get_width()) // 2, 30))
        
        # Score value with highlight
        score_value_font = pygame.font.SysFont('Arial', 50, bold=True)
        score_value = score_value_font.render(str(score), True, (255, 255, 0))
        panel.blit(score_value, ((400 - score_value.get_width()) // 2, 80))
        
        # Draw panel
        panel_y = WINDOW_HEIGHT // 2
        self.screen.blit(panel, (WINDOW_WIDTH // 2 - 200, panel_y))
        
        # Restart/quit text with flashing effect
        if pygame.time.get_ticks() % 1000 < 500:
            restart_color = (255, 255, 255)
        else:
            restart_color = (200, 200, 200)
        
        restart_text = self.small_font.render("Press SPACE to Restart or ESC to Quit", True, restart_color)
        self.screen.blit(restart_text, (WINDOW_WIDTH // 2 - restart_text.get_width() // 2, panel_y + 200))
    
    def run(self):
        """Main render loop"""
        clock = pygame.time.Clock()
        
        while True:
            # Handle events
            self.handle_events()
            
            # Receive game state from logic process
            self.receive_game_state()
            
            # Update animations
            self.update_animations()
            
            # Draw everything
            self.draw_background()
            self.draw_entities()
            self.draw_ui()
            
            # Update display
            pygame.display.flip()
            
            # Cap the frame rate
            clock.tick(FPS) 