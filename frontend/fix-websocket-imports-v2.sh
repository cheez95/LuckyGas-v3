#!/bin/bash

# Fix WebSocket imports that should use useWebSocketContext instead of useWebSocket
echo "Fixing WebSocket imports..."

# Files that import useWebSocket directly but should use useWebSocketContext
files=(
  "src/components/office/RouteManagement.tsx"
  "src/components/office/OrderList.tsx"
  "src/components/driver/DeliveryList.tsx"
  "src/components/Dashboard.tsx"
  "src/components/office/DispatchDashboard.tsx"
)

for file in "${files[@]}"; do
  if [ -f "$file" ]; then
    echo "Fixing imports in $file"
    # Replace import statement
    sed -i '' "s|import { useWebSocket } from '../../hooks/useWebSocket';|import { useWebSocketContext } from '../../contexts/WebSocketContext';|g" "$file"
    sed -i '' "s|import { useWebSocket } from '../hooks/useWebSocket';|import { useWebSocketContext } from '../contexts/WebSocketContext';|g" "$file"
    # Replace usage
    sed -i '' "s|const { on } = useWebSocket()|const { on } = useWebSocketContext()|g" "$file"
    sed -i '' "s|const { lastMessage } = useWebSocket()|const { lastMessage } = useWebSocketContext()|g" "$file"
    sed -i '' "s|const { sendMessage, lastMessage } = useWebSocket()|const { sendMessage, lastMessage } = useWebSocketContext()|g" "$file"
  fi
done

echo "WebSocket imports fixed!"