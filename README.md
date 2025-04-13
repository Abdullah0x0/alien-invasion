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
    └── Particle System Thread
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
- **Z** - Fire projectile
- **X** - Special attack
- **ESC** - Pause game
- **P** - Toggle process info display

## Game Features

- Wave-based combat system with increasing difficulty
- Dynamic enemy AI with multiple behavior patterns
- Platform-based movement mechanics
- Power-up system with various effects
- Particle effects for visual feedback
- Real-time process/thread statistics display

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