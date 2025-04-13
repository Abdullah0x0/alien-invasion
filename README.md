# Alien Invasion - OS Concepts Game

A platform combat game where players fight against waves of aliens, demonstrating practical implementations of operating system concepts through game mechanics.

## OS Concepts Implemented

1. **Process Management**
   - Separate processes for game logic and rendering using Python's multiprocessing
   - Process synchronization through shared memory
   - Proper process initialization and termination handling

2. **Thread Management**
   - Multiple concurrent threads handling:
     - Background animations
     - Enemy AI and spawning
     - Power-up generation
     - Particle effects
   - Daemon threads for automatic cleanup
   - Thread-safe resource access

3. **Synchronization Mechanisms**
   - Mutex locks for critical sections:
     - Entity management (`entities_lock`)
     - Wave management (`wave_lock`)
     - Shared resource access (`player_score_lock`, etc.)
   - Context managers for proper lock handling
   - Race condition prevention

4. **Inter-Process Communication (IPC)**
   - Shared Memory:
     - Game state management
     - Player statistics (health, score)
     - Position tracking
   - Message Queues:
     - Input event handling
     - Game state updates
     - Entity synchronization

5. **Resource Management**
   - Memory allocation and deallocation
   - Shared resource coordination
   - Safe process/thread termination
   - Asset loading and management
   - Sound and music system with dynamic loading

6. **Audio System**
   - Sound effect management
   - Dynamic sound loading and playback
   - Context-sensitive audio feedback based on game events
   - Adaptive volume based on event significance

## Technical Architecture

### Core Components
- `main.py` - Entry point and process orchestration
- `game_logic.py` - Game mechanics and entity management
- `renderer.py` - Graphics pipeline and display handling
- `entities.py` - Game object definitions and behaviors

### Process Structure
```
Main Process
├── Game Logic Process
│   ├── Enemy Spawner Thread
│   ├── Power-up Spawner Thread
│   └── Physics Update Thread
└── Renderer Process
    ├── Animation Thread
    ├── Particle System Thread
    └── Sound Effect System
```

## Setup and Installation

1. Requirements:
   - Python 3.8 or higher
   - Pygame library
   - Multiprocessing support

2. Installation:
   ```bash
   pip install -r requirements.txt
   ```

3. Running the game:
   ```bash
   python src/main.py
   ```

## Controls

- **Arrow Keys** - Move the player
- **Space** - Jump
- **Z** - Fire primary weapon
- **X** - Fire secondary weapon
- **ESC** - Pause game
- **P** - Toggle process info display
- **D** - Toggle platform reachability debug visualization
- **Q** - Quit game

## Game Features

- Wave-based combat system with increasing difficulty
- Dynamic enemy AI with multiple behavior patterns
- Platform-based movement mechanics
- Power-up system with various effects
- Particle effects for visual feedback
- Real-time process/thread statistics display
- Smart platform generation ensuring reachability

## Gameplay Details

### Waves
- The game features a progressive wave system that increases in difficulty
- Each wave introduces more enemies with enhanced abilities
- Wave progression is shown with on-screen notifications
- Higher waves feature elite enemies with special abilities and increased health

### Enemy Types
1. **Basic Enemy (Type 1)**
   - Circular shape with basic movement patterns
   - Color changes from gray (wave 1) to red (wave 3+)
   - Elite versions feature glowing auras and teeth

2. **Tough Enemy (Type 2)**
   - Square shape with higher health
   - Color changes from dark blue (wave 1) to deep blue (wave 3+)
   - Elite versions have armor plates and glowing eyes

3. **Fast Enemy (Type 3)**
   - Triangle shape with rapid movement
   - Color changes from dark green (wave 1) to bright green (wave 3+)
   - Enhanced versions leave motion trails

### Weapons
1. **Primary Weapon**
   - Fast-firing blue energy bolts
   - Quick cooldown and medium damage
   - Visible blue particle trails

2. **Secondary Weapon**
   - Powerful green plasma balls
   - Slower fire rate but higher damage
   - Creates green particle effects

### Power-ups
1. **Health (Green)**
   - Restores player health
   - Green cross symbol with pulsing animation
   - Creates expanding ring effect when collected

2. **Score Boost (Yellow)**
   - Grants bonus points
   - Yellow star symbol with rotating animation
   - Creates rising particle effects when collected

3. **Invincibility (Blue)**
   - Temporary invulnerability to damage
   - Blue shield symbol with shield rotation effect
   - Creates expanding blue rings when collected

### Sound Effects
- Context-sensitive enemy defeat sounds based on enemy type
- Subtle sound for regular enemies, explosion sounds for elite enemies
- Different sound effects for various game events (powerups, shooting, etc.)
- Volume automatically adjusted based on event importance

### Visual Effects
- Dynamic particle systems for explosions and projectiles
- Expanding ring animations for power-up collection
- Enemy-specific death animations based on type and wave
- Glowing effects for elite enemies
- Parallax starfield background with nebula effects

### Player Controls
- **Arrow Keys** - Move the player and jump
- **Z** - Fire primary weapon
- **X** - Fire secondary weapon
- **ESC** - Pause game
- **P** - Toggle process info display
- **D** - Toggle platform reachability debug visualization
- **Q** - Quit game

## Implementation Details

### Synchronization
- Mutex locks prevent race conditions in entity updates
- Message queues handle inter-process communication
- Shared memory manages game state across processes

### Resource Management
- Texture and sound assets loaded once and shared
- Memory-efficient particle system
- Automatic resource cleanup on exit

### Performance Considerations
- Optimized collision detection
- Efficient entity management system
- Background thread pooling for resource operations

### Platform Generation Algorithm
The game implements a smart platform generation algorithm that ensures platforms are always reachable by the player:

1. Calculates the maximum jump height based on physics constants (jump power and gravity)
2. Places platforms only at heights reachable from at least one existing platform
3. Ensures adequate horizontal spacing for effective gameplay
4. Provides debug visualization (press 'D' in-game) to show platform reachability

## Development

To contribute or modify:
1. Fork the repository
2. Create a feature branch
3. Implement changes with appropriate OS concept usage
4. Submit a pull request with detailed documentation

## Educational Value

This project demonstrates practical applications of operating system concepts in a real-world scenario, making it valuable for:
- Understanding process/thread management
- Learning synchronization techniques
- Practicing IPC implementations
- Studying resource management strategies