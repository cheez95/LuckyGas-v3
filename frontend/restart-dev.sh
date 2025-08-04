#!/bin/bash
# Restart frontend dev server with clean environment

echo "🔄 Restarting frontend dev server..."
pkill -f "vite"
sleep 2

cd /Users/lgee258/Desktop/LuckyGas-v3/frontend

# Clear environment and restart
export VITE_API_URL=""
export VITE_WS_URL=""

npm run dev