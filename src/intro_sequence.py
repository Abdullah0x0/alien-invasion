#!/usr/bin/env python3
import pygame
import math
import os
import time
import random

class IntroSequence:
    """
    Intro animation sequence showing a spaceship flying and crashing on a planet
    """
    def __init__(self, screen_width, screen_height):
        # Initialize the intro sequence
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.completed = False
        self.skip_intro = False
        self.alpha = 255  # For fade effects
        
        # Animation timing
        self.start_time = time.time()
        self.sequence_duration = 25.0
        
        # Camera shake effect
        self.camera_shake = 0
        self.camera_offset = [0, 0]
        
        # Load assets
        self.assets_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
        self.images_path = os.path.join(self.assets_path, "images")
        
        # Create images directory if it doesn't exist
        os.makedirs(self.images_path, exist_ok=True)
        
        # Load background stars with parallax effect (multiple layers)
        self.stars_bg = []
        self.stars_speeds = [0.2, 0.5, 1.0]  # Different speeds for parallax effect
        for i in range(3):  # 3 layers of stars
            star_layer = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
            # More stars and brighter for closer (faster) layers
            self._generate_stars(star_layer, 100 + i * 50, brightness_range=(100 + i * 50, 200 + i * 25))
            self.stars_bg.append(star_layer)
        
        # Star movement tracking
        self.star_offsets = [0, 0, 0]
        
        # Try to load spaceship image, or create one
        spaceship_path = os.path.join(self.images_path, "spaceship.png")
        if os.path.exists(spaceship_path):
            try:
                self.spaceship = pygame.image.load(spaceship_path).convert_alpha()
                self.spaceship = pygame.transform.scale(self.spaceship, (80, 40))
            except pygame.error:
                self._create_spaceship()
        else:
            self._create_spaceship()
            
        # Try to load planet image, or create one
        planet_path = os.path.join(self.images_path, "planet.png")
        if os.path.exists(planet_path):
            try:
                self.planet = pygame.image.load(planet_path).convert_alpha()
                self.planet = pygame.transform.scale(self.planet, (400, 400))
            except pygame.error:
                self._create_planet()
        else:
            self._create_planet()
        
        # Flame animation for spaceship
        self.flame_counter = 0
        self.flame_surfaces = []
        for i in range(5):  # More flame frames
            flame = pygame.Surface((30 + i * 3, 15 + i), pygame.SRCALPHA)
            flame_color = (200, 100 + i * 30, 0, 200 - i * 30)
            pygame.draw.polygon(flame, flame_color, [(0, 0), (0, 15 + i), (30 + i * 3, (15 + i) // 2)])
            self.flame_surfaces.append(flame)
        
        # Engine particle effects
        self.particles = []
        
        # Explosion animation - more detailed
        self.explosion_frames = []
        # Create a more impressive explosion with multiple elements
        for radius in range(10, 120, 10):
            explosion = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
            # Main explosion circle
            pygame.draw.circle(explosion, (200, 100, 0, 255 - radius*2), (radius, radius), radius)
            # Add some random debris particles
            for _ in range(radius // 2):
                angle = random.uniform(0, math.pi * 2)
                distance = random.uniform(0, radius * 0.8)
                size = random.randint(1, 3 + radius // 20)
                x = radius + math.cos(angle) * distance
                y = radius + math.sin(angle) * distance
                color = (255, random.randint(100, 200), random.randint(0, 50), 255)
                pygame.draw.circle(explosion, color, (int(x), int(y)), size)
            self.explosion_frames.append(explosion)
        
        # Load music
        pygame.mixer.init()
        self.music_path = os.path.join(self.assets_path, "sounds", "Burning_on_the_Bayou.mp3")
        # Sound effects
        self.jet_sound_path = os.path.join(self.assets_path, "sounds", "jet.wav")
        self.explosion_sound_path = os.path.join(self.assets_path, "sounds", "explosion.wav")
        
        # Ship properties for animation
        self.ship_x = -100
        self.ship_y = screen_height // 3
        self.ship_rotation = 0
        self.ship_speed = 3
        self.ship_trail = []  # For motion trail effect
        
        # Planet position (starts off-screen)
        self.planet_x = screen_width + 200
        self.planet_y = screen_height // 2 - 200
        self.planet_rotation = 0  # For slow rotation animation
        
        # Animation states
        self.state = "flying"  # flying, approaching, crash, aftermath
        self.explosion_index = 0
        
        # Text for intro
        self.font = pygame.font.Font(None, 100)
        self.text_alpha = 0
        self.text_scale = 0.1  # For text zoom effect
    
    def _create_spaceship(self):
        """Create a spaceship surface if image isn't available"""
        self.spaceship = pygame.Surface((80, 40), pygame.SRCALPHA)
        pygame.draw.polygon(self.spaceship, (200, 200, 200), [(0, 20), (80, 0), (80, 40)])
        pygame.draw.polygon(self.spaceship, (150, 150, 150), [(65, 10), (65, 30), (90, 20)])
        
        # Add some details
        pygame.draw.circle(self.spaceship, (100, 100, 200), (25, 20), 10)  # Cockpit window
        pygame.draw.rect(self.spaceship, (120, 120, 120), (40, 15, 20, 10))  # Engine
    
    def _create_planet(self):
        """Create a planet surface if image isn't available"""
        self.planet = pygame.Surface((400, 400), pygame.SRCALPHA)
        # Base planet
        pygame.draw.circle(self.planet, (80, 120, 80), (200, 200), 200)
        
        # Add some surface details
        for _ in range(15):
            pos = (int(random.uniform(20, 380)), int(random.uniform(20, 380)))
            size = int(random.random() * 40 + 10)
            color = (60, 100, 60)
            pygame.draw.circle(self.planet, color, pos, size)
        
        # Add atmosphere
        atmosphere = pygame.Surface((440, 440), pygame.SRCALPHA)
        pygame.draw.circle(atmosphere, (120, 200, 255, 50), (220, 220), 220)
        self.planet.blit(atmosphere, (-20, -20))
        
    def _generate_stars(self, surface, count=200, brightness_range=(180, 255)):
        """Generate a starfield background"""
        for _ in range(count):
            # Create random position for stars
            x = random.uniform(0, self.screen_width)
            y = random.uniform(0, self.screen_height)
            
            # Vary the star sizes
            radius = random.choice([0.5, 1, 1.5, 2]) if random.random() > 0.9 else 0.5
            
            # Vary the brightness within the given range
            brightness = random.randint(brightness_range[0], brightness_range[1])
            color = (brightness, brightness, brightness)
            
            # Some stars have a slight color tint
            if random.random() > 0.9:
                r, g, b = color
                tint = random.choice([(255, 200, 200), (200, 255, 200), (200, 200, 255)])
                color = (min(255, r * tint[0] // 255), min(255, g * tint[1] // 255), min(255, b * tint[2] // 255))
            
            pygame.draw.circle(surface, color, (int(x), int(y)), radius)
    
    def start(self):
        """Start the intro sequence"""
        self.start_time = time.time()
        self.completed = False
        self.skip_intro = False
        
        # Play music
        try:
            pygame.mixer.music.load(self.music_path)
            pygame.mixer.music.play(-1)  # Loop the music
        except pygame.error as e:
            print(f"Warning: Could not play music: {e}")
        
        # Play jet sound
        try:
            self.jet_sound = pygame.mixer.Sound(self.jet_sound_path)
            self.jet_sound.play(-1)  # Loop the jet sound
        except pygame.error as e:
            print(f"Warning: Could not play jet sound: {e}")
    
    def update(self, dt, events):
        """Update the intro sequence animation"""
        # Check for skip input
        for event in events:
            if event.type == pygame.KEYDOWN and (event.key == pygame.K_SPACE or event.key == pygame.K_RETURN):
                self.skip_intro = True
        
        # If skip requested, end the sequence
        if self.skip_intro:
            self.completed = True
            # Stop sounds
            pygame.mixer.music.stop()
            pygame.mixer.stop()
            return
        
        # Calculate elapsed time
        elapsed = time.time() - self.start_time
        
        # Update star parallax movement
        for i in range(len(self.star_offsets)):
            self.star_offsets[i] += self.stars_speeds[i] * dt * 60
            if self.star_offsets[i] > self.screen_width:
                self.star_offsets[i] -= self.screen_width
        
        # Update camera shake
        if self.camera_shake > 0:
            self.camera_shake -= dt * 2
            self.camera_offset = [random.uniform(-self.camera_shake, self.camera_shake),
                                random.uniform(-self.camera_shake, self.camera_shake)]
        else:
            self.camera_offset = [0, 0]
        
        # Update planet rotation
        self.planet_rotation += dt * 2  # Slow rotation
        
        # Update based on current state
        if self.state == "flying":
            self.ship_x += self.ship_speed * dt * 60
            self.ship_y = self.screen_height // 3 + math.sin(elapsed * 0.5) * 20
            
            # Add engine particles
            if random.random() < 0.3:
                self.particles.append({
                    'x': self.ship_x, 
                    'y': self.ship_y + random.uniform(-5, 5) + 20,
                    'size': random.uniform(1, 3),
                    'speed': random.uniform(1, 3),
                    'color': (255, random.randint(100, 200), 0),  # RGB only
                    'life': 1.0
                })
            
            # Save trail positions
            if len(self.ship_trail) < 10:
                self.ship_trail.append((self.ship_x + 40, self.ship_y + 20))
            else:
                self.ship_trail.pop(0)
                self.ship_trail.append((self.ship_x + 40, self.ship_y + 20))
            
            # When ship reaches 1/3 of screen, start showing planet
            if self.ship_x > self.screen_width / 3:
                self.state = "approaching"
                
        elif self.state == "approaching":
            self.ship_x += self.ship_speed * dt * 60
            
            # More dynamic movement
            self.ship_y += math.sin(elapsed * 1.5) * 0.5 + 0.3
            self.ship_rotation = math.sin(elapsed * 1.5) * 8  # More pronounced wobble
            
            # Add engine particles
            if random.random() < 0.4:
                self.particles.append({
                    'x': self.ship_x, 
                    'y': self.ship_y + random.uniform(-5, 5) + 20,
                    'size': random.uniform(1, 4),
                    'speed': random.uniform(1, 4),
                    'color': (255, random.randint(100, 200), 0),  # RGB only
                    'life': 1.0
                })
            
            # Save trail positions
            if len(self.ship_trail) < 10:
                self.ship_trail.append((self.ship_x + 40, self.ship_y + 20))
            else:
                self.ship_trail.pop(0)
                self.ship_trail.append((self.ship_x + 40, self.ship_y + 20))
            
            # Move planet into view faster
            self.planet_x -= 4 * dt * 60
            
            # When planet is visible and ship is at 2/3 of screen, start crash sequence
            if self.planet_x < self.screen_width - 100 and self.ship_x > self.screen_width * 2/3:
                self.state = "crash"
                pygame.mixer.stop()  # Stop jet sound
                # Play explosion
                try:
                    explosion_sound = pygame.mixer.Sound(self.explosion_sound_path)
                    explosion_sound.play()
                    # Start camera shake
                    self.camera_shake = 15
                except pygame.error as e:
                    print(f"Warning: Could not play explosion sound: {e}")
            
        elif self.state == "crash":
            # Ship rapidly descends and rotates towards planet
            self.ship_x += self.ship_speed * 1.5 * dt * 60
            self.ship_y += self.ship_speed * 3 * dt * 60
            self.ship_rotation += 5 * dt * 60
            
            # Add damage particles
            if random.random() < 0.7:
                self.particles.append({
                    'x': self.ship_x + random.uniform(0, 80), 
                    'y': self.ship_y + random.uniform(0, 40),
                    'size': random.uniform(1, 5),
                    'speed': random.uniform(0.5, 2),
                    'color': (255, random.randint(100, 255), random.randint(0, 100)),  # RGB only
                    'life': 1.0
                })
            
            # Check if ship has "crashed" into planet or traveled far enough
            ship_center = (self.ship_x + 40, self.ship_y + 20)
            planet_center = (self.planet_x + 200, self.planet_y + 200)
            distance = math.sqrt((ship_center[0] - planet_center[0])**2 + (ship_center[1] - planet_center[1])**2)
            
            # Force transition to aftermath if ship is near planet or has traveled past the center
            if distance < 180 or self.ship_x > self.screen_width * 0.75:
                self.state = "aftermath"
                self.aftermath_start = time.time()
                
                # Maximum camera shake
                self.camera_shake = 25
                
                # Add a bunch of explosion particles
                for _ in range(50):
                    angle = random.uniform(0, math.pi * 2)
                    speed = random.uniform(1, 10)
                    self.particles.append({
                        'x': self.ship_x + 40, 
                        'y': self.ship_y + 20,
                        'vx': math.cos(angle) * speed,
                        'vy': math.sin(angle) * speed,
                        'size': random.uniform(2, 7),
                        'speed': 0,  # Using vx/vy instead
                        'color': (255, random.randint(100, 255), random.randint(0, 100)),  # RGB only
                        'life': random.uniform(1.0, 3.0)
                    })
                
                # Play explosion sound
                try:
                    explosion_sound = pygame.mixer.Sound(self.explosion_sound_path)
                    explosion_sound.play()
                except pygame.error as e:
                    print(f"Warning: Could not play explosion sound: {e}")
        
        elif self.state == "aftermath":
            # Show explosion and fade out
            aftermath_elapsed = time.time() - self.aftermath_start
            
            # Continue camera shake, reducing over time
            if self.camera_shake > 0:
                self.camera_shake = max(0, 25 - aftermath_elapsed * 8)
                self.camera_offset = [random.uniform(-self.camera_shake, self.camera_shake),
                                    random.uniform(-self.camera_shake, self.camera_shake)]
            
            # Cycle through explosion frames
            if aftermath_elapsed < 2.0:
                self.explosion_index = min(int(aftermath_elapsed * 5), len(self.explosion_frames) - 1)
                
                # Add additional particles during explosion
                if random.random() < 0.5:
                    angle = random.uniform(0, math.pi * 2)
                    distance = random.uniform(0, 20 + aftermath_elapsed * 30)
                    self.particles.append({
                        'x': self.ship_x + 40 + math.cos(angle) * distance, 
                        'y': self.ship_y + 20 + math.sin(angle) * distance,
                        'size': random.uniform(1, 4),
                        'speed': random.uniform(0.2, 1),
                        'color': (255, random.randint(100, 255), random.randint(0, 100)),  # RGB only
                        'life': random.uniform(0.5, 1.5)
                    })
            else:
                # Fade out music very gradually
                try:
                    # Slower fade - divide by 4.0 instead of 2.0 to make fade more gradual
                    fade_factor = max(0, 1.0 - (aftermath_elapsed - 2.0) / 4.0)
                    pygame.mixer.music.set_volume(fade_factor)
                except:
                    pass
                
                # Animate text scaling for dramatic effect
                if aftermath_elapsed < 4.0:
                    # Scale text from small to large
                    self.text_scale = min(1.0, (aftermath_elapsed - 2.0) / 1.0)
                else:
                    # Add subtle pulsing
                    self.text_scale = 1.0 + math.sin((aftermath_elapsed - 4.0) * 2) * 0.05
                
                # End sequence after text displayed
                if aftermath_elapsed > 7.0: 
                    self.completed = True
                    pygame.mixer.music.stop()
        
        # Update particles
        for i in range(len(self.particles) - 1, -1, -1):
            p = self.particles[i]
            p['life'] -= dt
            
            if 'vx' in p:  # Particles with velocity components
                p['x'] += p['vx'] * dt * 60
                p['y'] += p['vy'] * dt * 60
                # Slow down over time
                p['vx'] *= 0.98
                p['vy'] *= 0.98
                # Add gravity
                p['vy'] += 0.1 * dt * 60
            else:  # Simple particles
                p['x'] -= p['speed'] * dt * 60  # Move left
            
            # Remove dead particles
            if p['life'] <= 0:
                self.particles.pop(i)
        
        # End sequence if total time exceeds duration
        if elapsed > self.sequence_duration:
            self.completed = True
            pygame.mixer.music.stop()
            pygame.mixer.stop()
        
        # Force transition to aftermath after certain time, regardless of other states
        if elapsed > 15.0 and self.state != "aftermath":  # Increased from 12.0 to 15.0 seconds
            self.state = "aftermath"
            self.aftermath_start = time.time()
    
    def render(self, screen):
        """Render the intro sequence to the screen"""
        # Get elapsed time
        elapsed = time.time() - self.start_time
        aftermath_elapsed = time.time() - self.aftermath_start if self.state == "aftermath" else 0
        
        # Create a surface with camera shake applied
        display = pygame.Surface((self.screen_width, self.screen_height))
        
        # Draw starfield background with parallax
        for i, star_layer in enumerate(self.stars_bg):
            # Draw each star layer twice to create seamless scrolling
            offset = int(self.star_offsets[i]) % self.screen_width
            display.blit(star_layer, (-offset, 0))
            display.blit(star_layer, (self.screen_width - offset, 0))
        
        # Draw planet if in view
        if self.state in ["approaching", "crash", "aftermath"]:
            # Apply slow rotation to planet for visual interest
            if self.planet_x < self.screen_width + 400:  # Only if potentially visible
                rotated_planet = pygame.transform.rotate(self.planet, self.planet_rotation)
                planet_rect = rotated_planet.get_rect(center=(self.planet_x + 200, self.planet_y + 200))
                display.blit(rotated_planet, planet_rect.topleft)
        
        # Draw ship trail
        if self.state != "aftermath" and len(self.ship_trail) > 2:
            points = self.ship_trail.copy()
            # Fade the trail based on position in the list
            for i, point in enumerate(points):
                alpha = int(255 * (i / len(points)) * 0.6)
                color = (200, 150, 255, alpha)
                size = int(i / 2) + 1
                pygame.draw.circle(display, color, (int(point[0]), int(point[1])), size)
        
        # Draw particles
        for p in self.particles:
            # Calculate alpha based on life
            alpha = int(p['life'] * 255)
            
            # Handle color properly based on whether it has alpha component
            if len(p['color']) == 4:  # RGBA
                color = (p['color'][0], p['color'][1], p['color'][2])  # Extract RGB components only
            else:  # RGB
                color = p['color']
            
            size = p['size'] * min(1.0, p['life'] * 2)  # Shrink as they die
            pygame.draw.circle(display, color, (int(p['x']), int(p['y'])), int(size))
        
        # Draw spaceship if not in aftermath
        if self.state != "aftermath":
            # Rotate ship
            rotated_ship = pygame.transform.rotate(self.spaceship, self.ship_rotation)
            ship_rect = rotated_ship.get_rect(center=(self.ship_x + 40, self.ship_y + 20))
            display.blit(rotated_ship, ship_rect.topleft)
            
            # Draw flame behind ship
            if self.state in ["flying", "approaching"]:
                self.flame_counter = (self.flame_counter + 1) % len(self.flame_surfaces)
                flame = self.flame_surfaces[self.flame_counter]
                rotated_flame = pygame.transform.rotate(flame, self.ship_rotation)
                flame_rect = rotated_flame.get_rect(center=(self.ship_x, self.ship_y + 20))
                display.blit(rotated_flame, flame_rect.topleft)
        
        # Draw explosion in aftermath
        if self.state == "aftermath" and self.explosion_index < len(self.explosion_frames):
            explosion = self.explosion_frames[self.explosion_index]
            # Scale the explosion for dramatic effect
            scale_factor = 1.0 + aftermath_elapsed * 0.2
            scaled_explosion = pygame.transform.scale(
                explosion, 
                (int(explosion.get_width() * scale_factor), 
                 int(explosion.get_height() * scale_factor))
            )
            explosion_rect = scaled_explosion.get_rect(center=(self.ship_x + 40, self.ship_y + 20))
            display.blit(scaled_explosion, explosion_rect.topleft)
        
        # Draw text in aftermath state
        if self.state == "aftermath" and aftermath_elapsed > 2.0:
            # Render text with bright color for high visibility
            text = self.font.render("Alien Invasion Begins...", True, (255, 255, 0))
            
            # Scale text for animation effect
            if self.text_scale != 1.0:
                scaled_width = int(text.get_width() * self.text_scale)
                scaled_height = int(text.get_height() * self.text_scale)
                text = pygame.transform.scale(text, (scaled_width, scaled_height))
            
            # Draw text with solid black background for maximum contrast
            text_rect = text.get_rect(center=(self.screen_width // 2, self.screen_height // 2))
            
            # Draw black background rectangle with glow
            bg_rect = text_rect.inflate(40, 40)
            pygame.draw.rect(display, (0, 0, 0), bg_rect)
            
            # Draw glowing border with correct RGB format
            glow_intensity = int(128 + 127 * math.sin(aftermath_elapsed * 3))
            glow_color = (255, 255, glow_intensity)  # Yellow with varying intensity
            pygame.draw.rect(display, glow_color, bg_rect, 3)
            
            # Draw text
            display.blit(text, text_rect)
            
            # Add additional animation: small decorative particles around text
            if aftermath_elapsed > 3.0:
                for _ in range(2):  # Add a few particles per frame
                    angle = random.uniform(0, math.pi * 2)
                    distance = text_rect.width / 1.5
                    self.particles.append({
                        'x': self.screen_width // 2 + math.cos(angle) * distance,
                        'y': self.screen_height // 2 + math.sin(angle) * distance,
                        'size': random.uniform(1, 3),
                        'speed': random.uniform(0.2, 1),
                        'vx': math.cos(angle) * -2,  # Move toward text
                        'vy': math.sin(angle) * -2,
                        'color': (255, 255, 0),  # RGB only
                        'life': random.uniform(0.5, 1.5)
                    })
        
        # Unconditional text drawing after enough time has passed
        # This will draw text regardless of state, after a certain amount of time has passed
        elif elapsed > 15.0:  # Increased from 12.0 to 15.0 seconds, only if not already in aftermath state
            # Force draw the text, regardless of state
            font = pygame.font.Font(None, 100)
            text = font.render("Alien Invasion Begins...", True, (255, 0, 0))  # Bright red for high visibility
            text_rect = text.get_rect(center=(self.screen_width // 2, self.screen_height // 2))
            
            # Draw black background
            bg_rect = text_rect.inflate(40, 40)
            pygame.draw.rect(display, (0, 0, 0), bg_rect)
            pygame.draw.rect(display, (255, 255, 0), bg_rect, 3)  # Yellow border
            
            # Draw text
            display.blit(text, text_rect)
        
        # Apply camera shake
        screen.blit(display, self.camera_offset)
        
        # Draw skip message (directly to the screen, not affected by camera shake)
        skip_text = pygame.font.Font(None, 24).render("Press SPACE to skip", True, (200, 200, 200))
        skip_text.set_alpha(150)
        screen.blit(skip_text, (self.screen_width - 200, self.screen_height - 30))
    
    def is_completed(self):
        """Check if the intro sequence is complete"""
        return self.completed 