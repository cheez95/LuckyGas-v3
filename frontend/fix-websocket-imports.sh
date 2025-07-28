#!/bin/bash

# Fix WebSocket import issues in frontend

echo "Fixing WebSocket context imports..."

# Files that need fixing
files=(
    "src/components/dispatch/dashboard/LiveRouteTracker.tsx"
    "src/components/dispatch/dashboard/DispatchMetrics.tsx"
    "src/components/dispatch/emergency/PriorityQueueManager.tsx"
    "src/components/dispatch/emergency/EmergencyAlertBanner.tsx"
)

# Change to frontend directory
cd /Users/lgee258/Desktop/LuckyGas-v3/frontend

# Fix each file
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "Fixing $file..."
        # Replace import statement
        sed -i '' "s/import { useWebSocket } from/import { useWebSocketContext } from/g" "$file"
        # Replace usage
        sed -i '' "s/useWebSocket()/useWebSocketContext()/g" "$file"
    else
        echo "Warning: $file not found"
    fi
done

echo "WebSocket import fixes completed!"