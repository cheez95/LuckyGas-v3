#!/bin/bash

# Script to remove unused imports from TypeScript files

echo "🧹 Removing unused imports..."

# Fix specific unused imports identified in the build output
sed -i '' '/^import.*DriverInterface.*from.*\.\/components\/driver\/DriverInterface/d' src/App.tsx

# src/components/admin/PerformanceMonitor.tsx
sed -i '' 's/, Tooltip//g' src/components/admin/PerformanceMonitor.tsx
sed -i '' '/^const performanceMonitor/d' src/components/admin/PerformanceMonitor.tsx

# src/components/common/ErrorBoundary.tsx
sed -i '' '/^import React from/d' src/components/common/ErrorBoundary.tsx

# src/components/common/GoogleMapsPlaceholder.tsx
sed -i '' 's/, CarOutlined//g' src/components/common/GoogleMapsPlaceholder.tsx

# src/components/common/NotificationBell.tsx
sed -i '' 's/, CheckOutlined//g' src/components/common/NotificationBell.tsx

# src/components/dispatch/assignment/RouteColumn.tsx
sed -i '' '/onAssign,/d' src/components/dispatch/assignment/RouteColumn.tsx
sed -i '' '/const getStatusColor/d' src/components/dispatch/assignment/RouteColumn.tsx

# src/components/dispatch/dashboard/DispatchMetrics.tsx
sed -i '' 's/CarOutlined,//g' src/components/dispatch/dashboard/DispatchMetrics.tsx

# src/components/dispatch/dashboard/LiveRouteTracker.tsx
sed -i '' 's/ClockCircleOutlined,//g' src/components/dispatch/dashboard/LiveRouteTracker.tsx
sed -i '' 's/CheckCircleOutlined,//g' src/components/dispatch/dashboard/LiveRouteTracker.tsx

# src/components/dispatch/emergency/EmergencyDispatchModal.tsx
sed -i '' '/^import.*orderService/d' src/components/dispatch/emergency/EmergencyDispatchModal.tsx
sed -i '' '/const getEmergencyIcon/d' src/components/dispatch/emergency/EmergencyDispatchModal.tsx

# src/components/dispatch/maps/RoutePlanningMap.tsx
sed -i '' '/onStopsReordered,/d' src/components/dispatch/maps/RoutePlanningMap.tsx

# src/components/driver/DriverInterface.tsx
sed -i '' '/const \[routeStarted/d' src/components/driver/DriverInterface.tsx

# src/components/driver/mobile/MobileDriverInterface.tsx
sed -i '' 's/CameraOutlined, EditOutlined,//g' src/components/driver/mobile/MobileDriverInterface.tsx
sed -i '' '/const \[refreshing/d' src/components/driver/mobile/MobileDriverInterface.tsx

# src/components/driver/PhotoCapture.tsx
sed -i '' '/const fileInputRef/d' src/components/driver/PhotoCapture.tsx
sed -i '' '/const uploadButton/d' src/components/driver/PhotoCapture.tsx

# src/components/ForgotPassword.tsx
sed -i '' 's/, Link//g' src/components/ForgotPassword.tsx

# src/components/MainLayout.tsx
sed -i '' 's/, CloseOutlined//g' src/components/MainLayout.tsx
sed -i '' '/const screens = Grid/d' src/components/MainLayout.tsx

# src/components/office/CustomerDetail.tsx
sed -i '' 's/Timeline,//g' src/components/office/CustomerDetail.tsx
sed -i '' 's/, DollarOutlined//g' src/components/office/CustomerDetail.tsx

# src/components/office/RouteManagement.tsx
sed -i '' 's/List,//g' src/components/office/RouteManagement.tsx
sed -i '' 's/SyncOutlined,//g' src/components/office/RouteManagement.tsx
sed -i '' 's/FieldTimeOutlined,//g' src/components/office/RouteManagement.tsx

echo "✅ Unused imports removed!"