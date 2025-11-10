#!/bin/bash
# Setup script for godot-cpp dependency

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
EXTERNAL_DIR="$PROJECT_ROOT/external"

echo "Setting up godot-cpp..."

# Create external directory
mkdir -p "$EXTERNAL_DIR"

# Clone godot-cpp if not present
if [ ! -d "$EXTERNAL_DIR/godot-cpp" ]; then
    echo "Cloning godot-cpp..."
    git clone --recursive https://github.com/godotengine/godot-cpp.git "$EXTERNAL_DIR/godot-cpp"
    cd "$EXTERNAL_DIR/godot-cpp"
    git checkout 4.2  # Use Godot 4.2 compatible version
    git submodule update --init --recursive
else
    echo "godot-cpp already exists, updating..."
    cd "$EXTERNAL_DIR/godot-cpp"
    git pull
    git submodule update --init --recursive
fi

echo "godot-cpp setup complete!"
