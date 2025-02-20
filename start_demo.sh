#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting GPU Fleet Manager Demo${NC}"

# Activate virtual environment
if [ ! -d "venv_py311" ]; then
    echo -e "${RED}✗ Virtual environment not found. Creating one...${NC}"
    python3.11 -m venv venv_py311
    source venv_py311/bin/activate
    pip install --no-cache-dir -r requirements.txt
else
    echo -e "${GREEN}✓ Activating virtual environment${NC}"
    source venv_py311/bin/activate
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}✗ .env file not found${NC}"
    exit 1
fi

# Export environment variables
echo -e "${GREEN}✓ Loading environment variables${NC}"
set -a
source .env
set +a

# Start the FastAPI server in the background
echo -e "${GREEN}✓ Starting API server${NC}"
uvicorn src.main:app --reload --port 8000 &
API_PID=$!

# Wait for the API server to start
echo -e "${BLUE}⏳ Waiting for API server to start...${NC}"
sleep 5

# Run the demo
echo -e "${GREEN}✓ Running job lifecycle demo${NC}"
python -m src.demo.job_lifecycle

# Cleanup
echo -e "${GREEN}✓ Cleaning up${NC}"
kill $API_PID

echo -e "${BLUE}✨ Demo completed${NC}"
