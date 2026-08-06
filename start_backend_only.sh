#!/bin/bash

echo "Starting Voice Agent Backend (Health Access Track)..."
echo "Make sure your .env.local files are configured in backend/ and frontend/ directories"
echo ""

# Start backend agent
echo "Starting backend agent..."
(cd backend && uv run python src/agent.py dev) &
BACKEND_PID=$!

echo "Backend agent started with PID: $BACKEND_PID"
echo "Waiting for agent to register with LiveKit..."
sleep 5

echo ""
echo "=== BACKEND IS RUNNING ==="
echo "To test your voice agent:"
echo "1. Frontend: If you can get the frontend working, open http://localhost:3000"
echo "2. Manual test: Use LiveKit SDK to connect to your agent"
echo "3. The agent is registered as: my-agent"
echo ""
echo "To stop the backend, press Ctrl+C or run: kill $BACKEND_PID"
echo ""

# Wait for backend process
wait $BACKEND_PID
