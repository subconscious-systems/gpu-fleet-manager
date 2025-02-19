#!/bin/bash

# Load environment variables
set -a
source .env
set +a

# Start API server in background
echo "Starting API server..."
python src/main.py &
API_PID=$!

# Wait for API to start
sleep 5

# Run demo
echo "Running demo..."
python src/demo.py

# Cleanup
kill $API_PID
