#!/bin/bash
# Complete setup script for Agent Arena

set -e

echo "========================================"
echo "  Agent Arena Setup Script"
echo "========================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v git &> /dev/null; then
    echo -e "${RED}Error: git is not installed${NC}"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is not installed${NC}"
    exit 1
fi

if ! command -v cmake &> /dev/null; then
    echo -e "${RED}Error: cmake is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisites found${NC}"
echo ""

# Setup godot-cpp
echo -e "${YELLOW}Setting up godot-cpp...${NC}"
"$SCRIPT_DIR/setup_godot_cpp.sh"
echo -e "${GREEN}✓ godot-cpp setup complete${NC}"
echo ""

# Build C++ module
echo -e "${YELLOW}Building C++ module...${NC}"
cd "$PROJECT_ROOT/godot"

if [ ! -d "build" ]; then
    mkdir build
fi

cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release

echo -e "${GREEN}✓ C++ module built${NC}"
echo ""

# Setup Python environment
echo -e "${YELLOW}Setting up Python environment...${NC}"
cd "$PROJECT_ROOT/python"

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}✓ Python environment ready${NC}"
echo ""

# Create necessary directories
echo -e "${YELLOW}Creating project directories...${NC}"
mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$PROJECT_ROOT/replays"
mkdir -p "$PROJECT_ROOT/metrics"
mkdir -p "$PROJECT_ROOT/models"

echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# Run tests
echo -e "${YELLOW}Running tests...${NC}"
cd "$PROJECT_ROOT/tests"
pytest -v || echo -e "${YELLOW}Warning: Some tests failed${NC}"
echo ""

echo "========================================"
echo -e "${GREEN}Setup complete!${NC}"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Download a model to models/ directory"
echo "2. Update configs/backend/llama_cpp.yaml with model path"
echo "3. Open the project in Godot 4"
echo "4. Run: python python/test_agent.py"
echo ""
echo "See docs/quickstart.md for detailed instructions"
