#!/usr/bin/env python3
"""
Cosmic Conflict - OS Concepts Game
Run this script to start the game.
"""

import os
import sys
import subprocess

def check_dependencies():
    """Check if dependencies are installed and install if necessary"""
    try:
        import pygame
        print("Pygame is already installed.")
    except ImportError:
        print("Installing pygame...")
        try:
            subprocess.call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("Dependencies installed successfully!")
        except Exception as e:
            print(f"Error installing dependencies: {e}")
            return False
    return True

def run_game():
    """Run the game"""
    # Ensure we're in the right directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Check for dependencies
    if not check_dependencies():
        print("Failed to install dependencies. Please install manually with: pip install -r requirements.txt")
        return
    
    # Run the game
    try:
        print("Starting Cosmic Conflict game...")
        game_path = os.path.join(script_dir, "src", "main.py")
        os.environ['PYTHONPATH'] = script_dir  # Make imports work
        subprocess.call([sys.executable, game_path])
    except Exception as e:
        print(f"Error running game: {e}")

if __name__ == "__main__":
    run_game() 