#!/bin/bash
# Development server startup script

echo "🚀 Starting Lucky Gas Development Environment..."

# Function to cleanup on exit
cleanup() {
    echo "🛑 Shutting down servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup INT TERM

# Start backend server
echo "📦 Starting Backend Server..."
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 5

# Start frontend server
echo "🎨 Starting Frontend Server..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo "✅ Development servers started!"
echo "   Backend: http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo "   Analytics Dashboard: http://localhost:3000/analytics/dashboard"
echo ""
echo "Press Ctrl+C to stop all servers..."

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID