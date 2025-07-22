#!/bin/bash
# Lucky Gas Parallel Execution Spawn Commands
# Execute these commands in separate terminals for parallel work

echo "🚀 Lucky Gas Parallel Execution Commands"
echo "========================================"
echo ""
echo "📱 Frontend Team Commands:"
echo "--------------------------"
echo "# Terminal 1 - Frontend Lead Developer:"
echo "# Day 1-2: React Setup"
echo 'claude-code "/sc:implement \"Set up React frontend with TypeScript, Vite, Ant Design with Taiwan locale, React Router, and i18n for Traditional Chinese\"" --persona-frontend --c7 --magic'
echo ""
echo "# Day 3-4: Authentication UI"
echo 'claude-code "/sc:implement \"Create login/logout components with JWT token management, protected routes, and session timeout handling in React\"" --persona-frontend --seq'
echo ""
echo "# Day 5: Core Layouts"
echo 'claude-code "/sc:implement \"Build main dashboard layout with role-based navigation menu and responsive design for mobile\"" --persona-frontend --magic'
echo ""

echo "🔧 Backend/DevOps Team Commands:"
echo "---------------------------------"
echo "# Terminal 2 - DevOps Engineer:"
echo "# Day 1: GCP Setup"
echo 'claude-code "/sc:task execute \"Run gcp-setup-preflight.sh and gcp-setup-execute.sh to enable Google Cloud APIs and create service accounts\"" --persona-devops --validate'
echo ""
echo "# Day 2-3: Infrastructure Prep"
echo 'claude-code "/sc:implement \"Setup staging environment with secrets management, Terraform configs, and monitoring baseline\"" --persona-devops --seq'
echo ""

echo "# Terminal 3 - Backend Developer:"
echo "# Day 4-5: API Enhancement"
echo 'claude-code "/sc:implement \"Configure CORS, rate limiting, API versioning, and prepare WebSocket endpoints for Socket.io\"" --persona-backend --c7'
echo ""
echo "# Day 6-7: Vertex AI Configuration"
echo 'claude-code "/sc:implement \"Deploy demand prediction model on Vertex AI with AutoML Tables and batch prediction pipeline\"" --persona-backend --seq --c7'
echo ""

echo "🔌 Integration Team Commands:"
echo "-----------------------------"
echo "# Terminal 4 - Full-stack Developer (starts Day 8):"
echo "# Day 8-9: WebSocket Setup"
echo 'claude-code "/sc:implement \"Setup Socket.io server with Redis pub/sub for real-time event broadcasting\"" --persona-backend --c7 --seq'
echo ""
echo "# Day 10-11: Real-time Features"
echo 'claude-code "/sc:implement \"Implement live order updates, driver location tracking, and push notifications framework\"" --seq --magic'
echo ""

echo "📊 Progress Tracking Commands:"
echo "------------------------------"
echo "# Check overall status:"
echo 'claude-code "/sc:task status PROD-DEPLOY-001"'
echo ""
echo "# View parallel execution progress:"
echo 'claude-code "/sc:analyze PARALLEL_EXECUTION_PLAN.md --focus progress"'
echo ""
echo "# Daily standup summary:"
echo 'claude-code "/sc:task analytics --daily-progress --team-status"'
echo ""

echo "🔄 Sync Point Commands:"
echo "-----------------------"
echo "# End of Week 1 sync:"
echo 'claude-code "/sc:validate \"Frontend auth integration with backend CORS\" --cross-team"'
echo ""
echo "# API contract validation:"
echo 'claude-code "/sc:test \"API contracts between frontend and backend\" --validate"'
echo ""

echo "⚡ Quick Start:"
echo "--------------"
echo "1. Open 4 terminal windows"
echo "2. Assign each team member to a terminal"
echo "3. Execute the commands for Day 1"
echo "4. Run daily standup command at 9 AM"
echo ""
echo "💡 Tips:"
echo "- Use --parallel flag for independent tasks"
echo "- Add --validate for critical path items"
echo "- Include --c7 for library documentation needs"
echo "- Add --magic for UI component generation"
echo "- Use --seq for complex multi-step tasks"