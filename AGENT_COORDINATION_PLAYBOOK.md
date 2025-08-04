# Agent Coordination Playbook
## Cathedral Building Team Management Guide

### 🎯 Purpose
This playbook provides structured coordination patterns for BMad agents working as a team to complete planned tasks within project phases.

## 👥 Agent Team Roster

### Core Development Team
1. **Winston** (Architect) - Systems design, technical decisions, architecture
2. **Nigel** (Developer) - Code implementation, bug fixes, technical execution
3. **Mary** (Analyst) - Business rules, requirements analysis, data validation
4. **Devin** (Data Specialist) - Data migration, ETL processes, data integrity
5. **Sam** (QA) - Testing, quality assurance, test infrastructure

### Support Team
6. **Penelope** (DevOps) - Infrastructure, deployment, monitoring
7. **Phil** (PM) - Project coordination, timeline management
8. **Sally** (Scribe) - Documentation, guides, communication

## 📋 Phase-Based Coordination Patterns

### Phase 1: Core System Stabilization (Current)

#### Track 1: Security & Authentication
```yaml
lead: Winston
support: [Nigel]
handoff_pattern:
  1. Winston designs security architecture
  2. → Nigel implements authentication system
  3. → Sam creates security tests
  4. → Winston reviews implementation
  5. → Sally documents security guide
```

#### Track 2: Data Migration
```yaml
lead: Devin
support: [Mary]
handoff_pattern:
  1. Devin analyzes raw data files
  2. → Mary extracts business rules
  3. → Devin creates migration scripts
  4. → Sam validates data integrity
  5. → Mary confirms business logic preservation
```

#### Track 3: API Stabilization
```yaml
lead: Nigel
support: [Winston, Sam]
handoff_pattern:
  1. Winston reviews API architecture
  2. → Nigel implements missing endpoints
  3. → Sam creates API tests
  4. → Nigel fixes issues
  5. → Sally updates API documentation
```

### Phase 2: Feature Completion

#### Track 1: Route Optimization
```yaml
lead: Nigel
support: [Winston, Mary]
handoff_pattern:
  1. Mary defines routing requirements
  2. → Winston designs integration architecture
  3. → Nigel implements Google Routes API
  4. → Sam tests route calculations
  5. → Mary validates business rules
```

#### Track 2: AI Predictions
```yaml
lead: Winston
support: [Nigel, Devin]
handoff_pattern:
  1. Devin prepares historical data
  2. → Winston designs AI architecture
  3. → Nigel implements Vertex AI integration
  4. → Sam creates prediction tests
  5. → Mary validates predictions
```

### Phase 3: Production Readiness

#### Track 1: Deployment
```yaml
lead: Penelope
support: [Nigel, Winston]
handoff_pattern:
  1. Winston reviews deployment architecture
  2. → Penelope creates K8s configurations
  3. → Nigel fixes deployment issues
  4. → Sam runs deployment tests
  5. → Penelope sets up monitoring
```

## 🔄 Agent Switching Protocols

### Standard Handoff Template
```markdown
## 🤝 Handoff from [Agent A] to [Agent B]

**From**: [Agent A Name]
**To**: [Agent B Name]
**Task**: [Specific task description]
**Status**: [Current status]

### Completed Work:
- [List what was done]
- [Include file paths]
- [Note any decisions made]

### Next Steps:
1. [Specific action for Agent B]
2. [Expected deliverables]
3. [Success criteria]

### Context & Warnings:
- [Any blockers or issues]
- [Technical debt noted]
- [Dependencies to watch]

### Files to Review:
- `path/to/file1.py` - [Description]
- `path/to/file2.md` - [Description]
```

### Quick Switch Commands
```bash
# For BMad Master to execute
*task switch-to-winston "Review API architecture"
*task switch-to-nigel "Implement authentication"
*task switch-to-mary "Validate business rules"
*task switch-to-devin "Migrate customer data"
*task switch-to-sam "Create test suite"
```

## 🎭 Agent Collaboration Patterns

### 1. Sequential Handoff
```
Winston → Nigel → Sam → Sally
(Design → Build → Test → Document)
```

### 2. Parallel Collaboration
```
Track A: Winston + Nigel (Backend)
Track B: Devin + Mary (Data)
Merge: Sam (Integration Testing)
```

### 3. Review Cycle
```
Nigel (Implement) ↔ Winston (Review)
                  ↔ Sam (Test)
                  → Sally (Document)
```

### 4. Crisis Response
```
All Stop → Winston (Assess) → Assign Teams
Team A: Nigel + Sam (Fix + Test)
Team B: Mary + Phil (Communication)
```

## 📊 Communication Matrix

### Daily Sync Pattern
```yaml
morning_sync:
  time: "9:00 AM Taiwan"
  attendees: [Active agents only]
  format:
    - Yesterday's progress
    - Today's goals
    - Blockers
    - Handoffs needed

evening_update:
  time: "5:00 PM Taiwan"
  format:
    - Progress update
    - Tomorrow's plan
    - Overnight handoffs
```

### Status Report Template
```markdown
## [Agent Name] Status - [Date]

### Completed Today:
- ✅ [Task 1]
- ✅ [Task 2]

### In Progress:
- 🔄 [Current task] - [X]% complete

### Blocked:
- 🚫 [Blocker] - Need [Who] to [What]

### Tomorrow:
- 📋 [Planned task 1]
- 📋 [Planned task 2]

### Handoffs:
- 🤝 To [Agent]: [Task description]
```

## 🚦 Decision Escalation

### Level 1: Technical Decisions
- **Owner**: Winston (Architect)
- **Consult**: Nigel, Sam
- **Inform**: Team

### Level 2: Business Logic
- **Owner**: Mary (Analyst)
- **Consult**: Phil, Customer
- **Inform**: Team

### Level 3: Project Scope
- **Owner**: Phil (PM)
- **Consult**: Winston, Mary
- **Approve**: Customer

### Level 4: Critical Issues
- **Escalate**: BMad Master
- **Coordinate**: All agents
- **Decision**: Consensus or Customer

## 🛠️ Tool Integration

### Shared Resources
```yaml
documentation:
  - /docs/ADR-*.md - Architecture decisions
  - /docs/API/    - API documentation
  - /TASK.md      - Current sprint tasks

code_review:
  - PR template includes agent assignments
  - Review checklist by role
  - Sign-off requirements

testing:
  - /tests/unit/     - Nigel maintains
  - /tests/e2e/      - Sam maintains
  - /tests/security/ - Winston reviews
```

### Agent-Specific Tools
```yaml
Winston:
  - Architecture diagrams (draw.io)
  - ADR templates
  - Security scanners

Nigel:
  - VS Code with team settings
  - uv for Python
  - npm for frontend

Sam:
  - Jest for frontend tests
  - pytest for backend
  - Playwright for E2E

Devin:
  - pandas for data analysis
  - Migration scripts
  - Data validation tools

Mary:
  - Business rule validator
  - Excel analyzers
  - Requirement trackers
```

## 📈 Progress Tracking

### Phase Completion Criteria
```yaml
phase_complete_when:
  - All tracks complete
  - All tests passing
  - Documentation updated
  - Customer sign-off
  - No critical bugs
```

### Velocity Tracking
```yaml
track_per_agent:
  - Tasks completed
  - Story points delivered
  - Bugs fixed
  - Tests written
  - Docs created
```

## 🎯 Best Practices

### 1. Clear Handoffs
- Always use handoff template
- Include all context
- List specific next actions
- Note any blockers

### 2. Avoid Bottlenecks
- Parallel work when possible
- Clear dependencies upfront
- Regular sync points
- Proactive communication

### 3. Quality Gates
- Code review before handoff
- Tests must pass
- Documentation updated
- No technical debt without ADR

### 4. Communication
- Over-communicate during handoffs
- Daily status updates
- Immediate escalation of blockers
- Celebrate completions

## 🚀 Quick Start Commands

```bash
# Start new phase
*task start-phase "Core System Stabilization"

# Switch agents
*task switch-to-nigel "Fix authentication"

# Status check
*task team-status

# Create handoff
*task create-handoff from=winston to=nigel

# Emergency meeting
*task emergency-sync "Critical bug in production"
```

## 📝 Notes

- This playbook is a living document
- Update patterns based on what works
- Each agent can propose improvements
- Regular retrospectives to refine process

---

**Last Updated**: 2024-01-21
**Maintained By**: BMad Master
**Version**: 1.0