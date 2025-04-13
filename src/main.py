#!/usr/bin/env python3
import os
import sys
import time
import signal
import pygame
import multiprocessing as mp
from multiprocessing import Process, Queue, Value, Lock, Array

# Local imports
from game_logic import GameLogicProcess
from renderer import RendererProcess

# Constants
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
GAME_TITLE = "Alien Invasion"

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\nGame shutting down...")
    pygame.quit()
    sys.exit(0)

def main():
    """Main entry point for the game"""
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize pygame
    pygame.init()
    pygame.display.set_caption(GAME_TITLE)
    
    # Create shared resources with proper synchronization
    game_state = Value('i', 0)  # 0: Menu, 1: Playing, 2: Paused, 3: Game Over
    player_score = Value('i', 0)
    player_health = Value('i', 100)
    player_position = Array('i', [WINDOW_WIDTH // 4, WINDOW_HEIGHT // 2])
    
    # Create locks for shared resources
    game_state_lock = Lock()
    player_score_lock = Lock()
    player_health_lock = Lock()
    player_position_lock = Lock()
    
    # Create communication queues
    logic_to_render_queue = Queue()
    render_to_logic_queue = Queue()
    
    # Create processes
    logic_process = Process(
        target=GameLogicProcess,
        args=(
            game_state, player_score, player_health, player_position,
            game_state_lock, player_score_lock, player_health_lock, player_position_lock,
            logic_to_render_queue, render_to_logic_queue
        )
    )
    logic_process.daemon = True  # Make the logic process a daemon so it exits when main exits
    
    render_process = Process(
        target=RendererProcess,
        args=(
            WINDOW_WIDTH, WINDOW_HEIGHT,
            game_state, player_score, player_health, player_position,
            game_state_lock, player_score_lock, player_health_lock, player_position_lock,
            logic_to_render_queue, render_to_logic_queue
        )
    )
    render_process.daemon = True  # Make the render process a daemon so it exits when main exits
    
    # Start processes
    logic_process.start()
    render_process.start()
    
    print(f"Game processes started with PIDs: Logic={logic_process.pid}, Renderer={render_process.pid}")
    
    try:
        # Wait for processes to complete
        logic_process.join()
        render_process.join()
    except KeyboardInterrupt:
        print("Game interrupted by user.")
    except Exception as e:
        print(f"Error in game execution: {e}")
    finally:
        # Clean up
        pygame.quit()
        print("Game shut down successfully")

if __name__ == "__main__":
    main() 