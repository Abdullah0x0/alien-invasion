# Use an official Python runtime as the base image
FROM ubuntu:20.04

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt /app/

# Install Python and any dependencies your game needs
RUN apt-get update && apt-get install -y \
    build-essential \
    python3 \
    python3-pip \
    libglib2.0-0

# Upgrade pip
RUN pip3 install --upgrade pip

# Install Python dependencies from requirements.txt
RUN pip3 install -r /app/requirements.txt

# Copy the rest of the game files into the container
COPY . /app/

# Set the default command to run the game
CMD ["python3", "run_game.py"]
