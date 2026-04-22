#!/bin/bash

# Fruit Ninja YOLO Backend - Startup Script for Linux/Mac

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Fruit Ninja YOLO Backend${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Check Python version
echo -e "${BLUE}[1/5] Checking Python version...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}Python ${PYTHON_VERSION} found${NC}"
echo ""

# Create virtual environment if it doesn't exist
echo -e "${BLUE}[2/5] Setting up virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}Virtual environment created${NC}"
else
    echo -e "${GREEN}Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate
echo ""

# Upgrade pip
echo -e "${BLUE}[3/5] Upgrading pip...${NC}"
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
echo -e "${GREEN}Pip upgraded${NC}"
echo ""

# Install requirements
echo -e "${BLUE}[4/5] Installing dependencies...${NC}"
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo -e "${GREEN}Dependencies installed${NC}"
else
    echo -e "${RED}Error: requirements.txt not found${NC}"
    exit 1
fi
echo ""

# Check CUDA availability
echo -e "${BLUE}[5/5] Checking CUDA availability...${NC}"
python3 -c "
import torch
if torch.cuda.is_available():
    print(f'CUDA Detected')
    print(f'  Device: {torch.cuda.get_device_name(0)}')
    print(f'  CUDA Version: {torch.version.cuda}')
    print(f'  GPU Count: {torch.cuda.device_count()}')
else:
    print('CUDA Not Available - Using CPU')
"
echo ""

# Create logs directory
mkdir -p logs

echo -e "${BLUE}================================${NC}"
echo -e "${GREEN}Ready to start server!${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Ask to start server
read -p "Start server now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Starting Fruit Ninja YOLO Backend Server...${NC}"
    echo ""
    python3 app.py
else
    echo -e "${YELLOW}Server startup cancelled.${NC}"
    echo "Run 'python3 app.py' to start manually."
fi
