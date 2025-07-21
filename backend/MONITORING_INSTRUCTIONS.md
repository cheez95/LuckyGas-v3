# Spawn Monitoring Instructions

## 🔍 Overview

This monitoring system tracks the parallel execution of FE-INT and GCP-SETUP epics for the Lucky Gas Production Deployment project (PROD-DEPLOY-001).

## 📂 Monitoring Components

### 1. SPAWN_MONITOR.md
- Real-time dashboard showing spawn process status
- Progress visualization for both epics
- Expected deliverables checklist
- Alert conditions and notifications

### 2. spawn_monitor.py
- Python script for automated monitoring
- Updates tracking files automatically
- Checks for file creation
- Calculates progress metrics

### 3. TASK_TRACKING.json
- Central task state repository
- Updated by spawn processes
- Tracks all 75 tasks across 5 epics
- Maintains execution history

## 🚀 How to Monitor

### Option 1: Manual Monitoring
1. Check SPAWN_MONITOR.md for current status
2. Review TASK_TRACKING.json for detailed task updates
3. Use status commands:
   ```bash
   /sc:task status FE-INT
   /sc:task status GCP-SETUP
   /sc:task analytics PROD-DEPLOY-001
   ```

### Option 2: Automated Monitoring
1. Run the Python monitor script:
   ```bash
   cd backend
   python3 spawn_monitor.py
   ```
2. Script checks every 30 seconds for:
   - Task status changes
   - File creation
   - Progress updates
   - Completion status

## 📋 Expected Updates from Spawns

### Frontend Integration (Terminal 1)
The FE-INT spawn should:
1. Create API client files in `/frontend/src/services/`
2. Build auth components in `/frontend/src/components/Auth/`
3. Set up protected routes
4. Configure environment files
5. Update TASK_TRACKING.json after each task

Expected file outputs:
- `/frontend/src/services/api.js`
- `/frontend/src/services/auth.service.js`
- `/frontend/src/components/Auth/Login.jsx`
- `/frontend/src/components/Auth/Logout.jsx`
- `/frontend/src/routes/ProtectedRoute.jsx`
- `/frontend/.env.development`
- `/frontend/.env.production`

### Google Cloud Setup (Terminal 2)
The GCP-SETUP spawn should:
1. Document GCP setup steps
2. Create service account
3. Enable required APIs
4. Configure security settings
5. Update tracking after each step

Expected outputs:
- `/backend/GCP_SETUP_GUIDE.md`
- Service account JSON key file
- Updated `.env` with GCP credentials
- Cost alert configuration proof
- Security setup documentation

## 🔄 Update Protocol

When spawns complete tasks, they should:

1. **Update Task Status**:
   ```json
   {
     "id": "1.1.1",
     "name": "Create axios/fetch client with interceptors",
     "status": "completed",
     "completed_at": "2025-07-22T03:00:00Z",
     "evidence": "Created /frontend/src/services/api.js"
   }
   ```

2. **Create Evidence Files**:
   - Actual code/config files
   - Documentation
   - Test results
   - Screenshots (if applicable)

3. **Update Story/Epic Progress**:
   - Story status changes when all tasks complete
   - Epic status changes when all stories complete

## ⚠️ Alert Conditions

Monitor for these conditions:

### 🔴 Critical
- No updates for >1 hour
- Task marked as "failed"
- Spawn process terminated unexpectedly

### 🟡 Warning
- Task marked as "blocked"
- Slower than expected progress
- Missing expected files

### 🟢 Success
- Task marked as "completed"
- Expected files created
- Tests passing

## 📊 Progress Tracking

### Quick Progress Check
```bash
# Overall project
/sc:task analytics PROD-DEPLOY-001

# Specific epic
/sc:task status FE-INT --detailed
/sc:task status GCP-SETUP --detailed
```

### Progress Visualization
```
FE-INT:     [████░░░░░░] 40% (6/14 tasks)
GCP-SETUP:  [██░░░░░░░░] 20% (3/15 tasks)
Overall:    [██░░░░░░░░] 12% (9/75 tasks)
```

## 🛠️ Troubleshooting

### If Terminal 1 (FE-INT) Stalls:
1. Check if backend is still running at http://localhost:8000
2. Verify frontend directory exists
3. Check for npm/yarn issues
4. Review any error messages

### If Terminal 2 (GCP-SETUP) Stalls:
1. Verify GCP credentials are available
2. Check GCP project permissions
3. Ensure billing is enabled
4. Review API enablement status

## 📝 Manual Task Updates

If needed, manually update task status:

```bash
# Mark task as completed
/sc:task update 1.1.1 --status completed --evidence "api.js created successfully"

# Mark task as blocked
/sc:task update 2.1.1 --status blocked --reason "Waiting for GCP project access"

# Mark task as in-progress
/sc:task update 1.2.1 --status in_progress --assignee "FE-INT-SPAWN"
```

## 🎯 Success Criteria

Both epics are considered complete when:

### FE-INT Success:
- [ ] All 14 tasks marked completed
- [ ] Frontend can authenticate with backend
- [ ] Protected routes working
- [ ] Environment configs tested

### GCP-SETUP Success:
- [ ] All 15 tasks marked completed
- [ ] Service account created and secured
- [ ] All APIs enabled with quotas
- [ ] Security measures in place
- [ ] Documentation complete

## 🔗 Next Steps

Once both epics complete:
1. Validate integration between frontend and GCP services
2. Begin MON-ALERT epic (depends on GCP-SETUP)
3. Begin CICD epic (depends on FE-INT)
4. Update project roadmap

---
**Remember**: The spawn processes are working in parallel. Check both terminals regularly and update tracking as tasks complete!