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
ORANGE = (255, 165, 0)

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
        
        # Create jet flame animations - right-facing flame
        right_flames = []
        
        # Base flame
        flame1 = pygame.Surface((30, 20), pygame.SRCALPHA)
        points = [(0, 10), (15, 0), (15, 20), (0, 10)]
        pygame.draw.polygon(flame1, YELLOW, points)
        pygame.draw.polygon(flame1, RED, [(5, 10), (15, 5), (15, 15), (5, 10)])
        right_flames.append(flame1)
        
        # Animated flame 2 - shorter
        flame2 = pygame.Surface((25, 18), pygame.SRCALPHA)
        points = [(0, 9), (12, 2), (12, 16), (0, 9)]
        pygame.draw.polygon(flame2, YELLOW, points)
        pygame.draw.polygon(flame2, RED, [(4, 9), (12, 4), (12, 14), (4, 9)])
        right_flames.append(flame2)
        
        # Animated flame 3 - longer
        flame3 = pygame.Surface((35, 22), pygame.SRCALPHA)
        points = [(0, 11), (18, 0), (18, 22), (0, 11)]
        pygame.draw.polygon(flame3, YELLOW, points)
        pygame.draw.polygon(flame3, ORANGE, [(5, 11), (18, 5), (18, 17), (5, 11)])
        pygame.draw.polygon(flame3, RED, [(10, 11), (18, 7), (18, 15), (10, 11)])
        right_flames.append(flame3)
        
        # Create left-facing flames by flipping the right ones
        left_flames = []
        for flame in right_flames:
            left_flame = pygame.transform.flip(flame, True, False)
            left_flames.append(left_flame)
        
        # Add the animation details to the class
        self.player_frames = frames
        self.player_frame_idx = 0
        self.player_anim_delay = 8
        self.player_anim_counter = 0
        self.player_right_flames = right_flames
        self.player_left_flames = left_flames
        self.flame_anim_idx = 0
        self.flame_anim_delay = 5
        self.flame_anim_counter = 0
        
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
                
                # Quick quit with Q key
                if event.key == pygame.K_q:
                    # Send an exit command to the logic process
                    self.render_to_logic_queue.put({'type': 'exit_game'})
                    pygame.quit()
                    sys.exit()
                
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
        
        # Update flame animation
        self.flame_anim_counter += 1
        if self.flame_anim_counter >= self.flame_anim_delay:
            self.flame_anim_counter = 0
            self.flame_anim_idx = (self.flame_anim_idx + 1) % len(self.player_right_flames)
        
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
                # Get player velocity from the game logic - we need to see if it's there
                player_velocity_x = entity.get('velocity_x', 0)
                
                # Make sure we're using the correct data from game logic
                facing_right = entity.get('facing_right', True)
                
                # Draw jet flame based on velocity direction (draw flames BEFORE player so they appear behind)
                if random.random() > 0.1:  # Occasionally skip for flickering
                    # Choose flame based on current animation frame
                    flame_index = self.flame_anim_idx
                    flame_scale = random.uniform(0.9, 1.4)  # Random size for flickering
                    
                    # Important: Make sure we check both velocity AND facing direction
                    # When facing right, flame should be on LEFT side
                    # When facing left, flame should be on RIGHT side
                    if facing_right:  # Facing right -> flame on left
                        # LEFT flame (appears on left side)
                        flame_surface = self.player_left_flames[flame_index]
                        flame_width = int(flame_surface.get_width() * flame_scale)
                        flame_height = int(flame_surface.get_height() * flame_scale)
                        
                        # Scale flame
                        scaled_flame = pygame.transform.scale(flame_surface, (flame_width, flame_height))
                        
                        # Position flame on left side of player - move it further away from player
                        flame_x = x - flame_width - 5
                        flame_y = y + 30 - (flame_height // 2)
                        flame_y += random.randint(-2, 2)  # Add slight jitter
                        
                        # Draw the flame
                        self.screen.blit(scaled_flame, (flame_x, flame_y))
                        
                        # Add particle effects from flame
                        if random.random() > 0.5:
                            particle_x = flame_x + random.randint(0, 5)
                            particle_y = flame_y + random.randint(0, flame_height)
                            particle_color = random.choice([YELLOW, ORANGE, RED])
                            particle_size = random.uniform(1, 3)
                            particle_lifetime = random.randint(5, 15)
                            self.projectile_particles.append((
                                particle_x, particle_y, particle_color, 
                                particle_size, particle_lifetime, -2, random.uniform(-0.5, 0.5)
                            ))
                            
                    else:  # Facing left -> flame on right
                        # RIGHT flame (appears on right side)
                        flame_surface = self.player_right_flames[flame_index]
                        flame_width = int(flame_surface.get_width() * flame_scale)
                        flame_height = int(flame_surface.get_height() * flame_scale)
                        
                        # Scale flame
                        scaled_flame = pygame.transform.scale(flame_surface, (flame_width, flame_height))
                        
                        # Position flame on right side of player - move it further away from player
                        flame_x = x + width + 5
                        flame_y = y + 30 - (flame_height // 2)
                        flame_y += random.randint(-2, 2)  # Add slight jitter
                        
                        # Draw the flame
                        self.screen.blit(scaled_flame, (flame_x, flame_y))
                        
                        # Add particle effects from flame
                        if random.random() > 0.5:
                            particle_x = flame_x + flame_width - random.randint(0, 5)
                            particle_y = flame_y + random.randint(0, flame_height)
                            particle_color = random.choice([YELLOW, ORANGE, RED])
                            particle_size = random.uniform(1, 3)
                            particle_lifetime = random.randint(5, 15)
                            self.projectile_particles.append((
                                particle_x, particle_y, particle_color, 
                                particle_size, particle_lifetime, 2, random.uniform(-0.5, 0.5)
                            ))
                
                # Draw current animation frame of player AFTER flame so player appears in front
                player_frame = self.player_frames[self.player_frame_idx]
                self.screen.blit(player_frame, (x, y))
            
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
        
        # Enhanced Controls Display
        controls_bg_height = 60
        controls_bg_width = 750  # Increase width from 650 to 750 to accommodate all controls
        controls_bg_rect = pygame.Rect(
            (self.width - controls_bg_width) // 2,
            self.height - controls_bg_height - 10,
            controls_bg_width,
            controls_bg_height
        )
        
        # Semi-transparent background with border
        controls_bg_surface = pygame.Surface((controls_bg_width, controls_bg_height), pygame.SRCALPHA)
        controls_bg_surface.fill((0, 10, 30, 180))  # Dark blue with transparency
        pygame.draw.rect(controls_bg_surface, (100, 150, 255, 255), (0, 0, controls_bg_width, controls_bg_height), 2, border_radius=10)
        
        # Add a highlight at the top
        for i in range(5):
            alpha = 50 - i * 10
            pygame.draw.rect(controls_bg_surface, (150, 200, 255, alpha), 
                            (3, 3 + i, controls_bg_width - 6, 1), 0, border_radius=10)
        
        self.screen.blit(controls_bg_surface, controls_bg_rect)
        
        # Control Key Visualization
        key_size = 30
        key_margin = 8
        key_y = self.height - controls_bg_height + 15
        
        # Helper function to draw a key
        def draw_key(text, x_pos, color=LIGHT_BLUE, width=None):
            if width is None:
                width = key_size
            
            # Key background with gradient
            key_surf = pygame.Surface((width, key_size), pygame.SRCALPHA)
            for y in range(key_size):
                alpha = 200 - int(y * 3)
                pygame.draw.line(key_surf, (*color[:3], alpha), (0, y), (width, y))
            
            # Key border
            pygame.draw.rect(key_surf, (*color[:3], 255), (0, 0, width, key_size), 2, border_radius=4)
            
            # Key text
            text_surf = self.small_font.render(text, True, WHITE)
            key_surf.blit(text_surf, ((width - text_surf.get_width()) // 2, (key_size - text_surf.get_height()) // 2))
            
            # Add a highlight
            pygame.draw.line(key_surf, (255, 255, 255, 100), (3, 3), (width - 3, 3), 1)
            
            self.screen.blit(key_surf, (x_pos, key_y))
            return x_pos + width + key_margin
        
        # Draw the arrow keys
        start_x = controls_bg_rect.x + 20
        
        # Left Arrow
        left_x = start_x
        start_x = draw_key("←", start_x)
        
        # Up Arrow
        up_x = start_x
        start_x = draw_key("↑", start_x)
        
        # Right Arrow 
        right_x = start_x
        start_x = draw_key("→", start_x)
        
        # Movement Text
        move_x = start_x + 5
        move_text = self.small_font.render("Move/Jump", True, WHITE)
        self.screen.blit(move_text, (move_x, key_y + 7))
        start_x = move_x + move_text.get_width() + 20
        
        # Attack Keys
        z_x = start_x
        start_x = draw_key("Z", start_x, color=RED)
        x_x = start_x
        start_x = draw_key("X", start_x, color=RED)
        
        # Attack Text
        attack_x = start_x + 5
        attack_text = self.small_font.render("Attack", True, WHITE)
        self.screen.blit(attack_text, (attack_x, key_y + 7))
        start_x = attack_x + attack_text.get_width() + 20
        
        # ESC Key
        esc_x = start_x
        start_x = draw_key("ESC", start_x, color=YELLOW, width=45)
        
        # ESC Text
        esc_text = self.small_font.render("Pause", True, WHITE)
        self.screen.blit(esc_text, (start_x + 5, key_y + 7))
        start_x = start_x + esc_text.get_width() + 15
        
        # P Key for process info
        p_x = start_x
        start_x = draw_key("P", start_x, color=PURPLE)
        
        # P Text
        p_text = self.small_font.render("Info", True, WHITE)
        self.screen.blit(p_text, (start_x + 5, key_y + 7))
        start_x = start_x + p_text.get_width() + 15
        
        # Q Key for quitting
        q_x = start_x
        start_x = draw_key("Q", start_x, color=RED)
        
        # Q Text
        q_text = self.small_font.render("Quit", True, WHITE)
        self.screen.blit(q_text, (start_x + 5, key_y + 7))
        
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
            
            # Background for process info with improved styling
            info_width = 350  # Increase width to prevent text overlap
            info_height = 270  # Increase height to accommodate taller rows
            info_bg_rect = pygame.Rect(self.width - info_width - 20, 60, info_width, info_height)
            
            # Semi-transparent panel with gradient
            info_surface = pygame.Surface((info_width, info_height), pygame.SRCALPHA)
            for y in range(info_height):
                alpha = min(180, 160 + int(y * 0.1))
                pygame.draw.line(info_surface, (0, 10, 30, alpha), (0, y), (info_width, y))
            
            # Panel border with glow
            pygame.draw.rect(info_surface, (100, 150, 255, 255), (0, 0, info_width, info_height), 2, border_radius=8)
            
            # Title bar for process info
            pygame.draw.rect(info_surface, (80, 120, 220, 200), (2, 2, info_width-4, 26), border_radius=6)
            title_text = "SYSTEM METRICS"
            title_surf = self.small_font.render(title_text, True, WHITE)
            info_surface.blit(title_surf, ((info_width - title_surf.get_width()) // 2, 6))
            
            self.screen.blit(info_surface, info_bg_rect)
            
            # Display info with improved styling and spacing
            y_offset = info_bg_rect.y + 36
            
            # Draw table-like headers with color coding
            header_colors = [LIGHT_BLUE, GREEN]
            label_column_width = 150  # Increase label column width
            value_column_width = 180  # Increase value column width
            
            # Column headers
            header_height = 26
            pygame.draw.rect(self.screen, (40, 60, 100, 180), 
                           (info_bg_rect.x + 10, y_offset - 2, info_width - 20, header_height))
            
            metric_header = self.small_font.render("Metric", True, header_colors[0])
            value_header = self.small_font.render("Value", True, header_colors[1])
            
            # Calculate vertical centers for headers
            metric_y = y_offset + (header_height - metric_header.get_height()) // 2 - 2
            value_y = y_offset + (header_height - value_header.get_height()) // 2 - 2
            
            self.screen.blit(metric_header, (info_bg_rect.x + 20, metric_y))
            self.screen.blit(value_header, (info_bg_rect.x + label_column_width + 20, value_y))
            
            y_offset += header_height
            
            # Add separator line between header and data rows
            pygame.draw.line(self.screen, GRAY, 
                            (info_bg_rect.x + 10, y_offset - 1), 
                            (info_bg_rect.x + info_width - 10, y_offset - 1))
            
            # Metrics data in two columns
            metrics = [
                ("FPS", f"{current_fps:.1f}"),
                ("Frame Time", f"{avg_frame_time*1000:.1f} ms"),
                ("Entities", f"{len(self.entities)}"),
                ("Particles", f"{len(self.projectile_particles) + len(self.explosion_particles)}"),
                ("Queue Size", f"{self.logic_to_render_queue.qsize()}")
            ]
            
            # System metrics if available
            try:
                import psutil
                process = psutil.Process()
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                cpu_percent = process.cpu_percent(interval=None) / psutil.cpu_count()
                
                metrics.extend([
                    ("Memory", f"{memory_mb:.1f} MB"),
                    ("CPU Usage", f"{cpu_percent:.1f}%")
                ])
            except (ImportError, AttributeError):
                metrics.append(("Status", "No system metrics"))
            
            # Draw metrics with alternating row colors and proper spacing
            row_height = 32  # Further increase row height for better text visibility
            for i, (label, value) in enumerate(metrics):
                # Alternating row background
                row_color = (30, 40, 60, 100) if i % 2 == 0 else (20, 30, 50, 100)
                pygame.draw.rect(self.screen, row_color, 
                                (info_bg_rect.x + 10, y_offset, info_width - 20, row_height))
                
                # Label - left-aligned with proper truncation if needed
                label_surf = self.small_font.render(label, True, LIGHT_BLUE)
                # Calculate vertical center position for text
                label_y = y_offset + (row_height - label_surf.get_height()) // 2
                self.screen.blit(label_surf, (info_bg_rect.x + 20, label_y))
                
                # Value - ensure it fits within the available space
                # Calculate max allowed width for the value
                max_value_width = info_width - label_column_width - 40
                
                # Render and check if it's too long
                value_surf = self.small_font.render(value, True, WHITE)
                if value_surf.get_width() > max_value_width:
                    # If too long, truncate or use smaller font
                    if len(value) > 15:
                        # Truncate with ellipsis
                        shortened_value = value[:12] + "..."
                        value_surf = self.small_font.render(shortened_value, True, WHITE)
                    else:
                        # Try with a smaller font
                        smaller_font = pygame.font.SysFont('Arial', SMALL_FONT_SIZE - 2)
                        value_surf = smaller_font.render(value, True, WHITE)
                
                # Calculate vertical center position for value text
                value_y = y_offset + (row_height - value_surf.get_height()) // 2
                self.screen.blit(value_surf, (info_bg_rect.x + label_column_width + 20, value_y))
                
                y_offset += row_height
    
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
            "ESC: Pause",
            "P: Toggle process info display",
            "Q: Quit game",
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
            "Press ESC or Q to Quit"
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
        
        # Simple resume instructions
        resume_text = "Press ESC to Resume"
        resume_surf = self.main_font.render(resume_text, True, WHITE)
        
        # Add a pulsing effect to make it more visible
        pulse = math.sin(pygame.time.get_ticks() * 0.005) * 0.3 + 0.7
        pulse_color = (int(255 * pulse), int(255 * pulse), int(100 * pulse))
        resume_surf_pulse = self.main_font.render(resume_text, True, pulse_color)
        
        # Quit instructions
        quit_text = "Press Q to Quit"
        quit_surf_pulse = self.main_font.render(quit_text, True, pulse_color)
        
        # Position at the center of the screen
        self.screen.blit(resume_surf_pulse, (self.width//2 - resume_surf_pulse.get_width()//2, 300))
        self.screen.blit(quit_surf_pulse, (self.width//2 - quit_surf_pulse.get_width()//2, 350))
    
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