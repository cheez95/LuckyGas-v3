#!/usr/bin/env python3
"""
Lucky Gas Parallel Execution Monitor
Real-time progress tracking for parallel development
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    
class TeamStream(Enum):
    FRONTEND = "Frontend"
    BACKEND = "Backend/DevOps"
    INTEGRATION = "Integration"

@dataclass
class Task:
    id: str
    name: str
    team: TeamStream
    day_start: int
    day_end: int
    status: TaskStatus
    progress: int
    dependencies: List[str]
    blockers: List[str]
    
@dataclass
class TeamStatus:
    team: TeamStream
    current_task: Optional[str]
    utilization: int
    active: bool
    
class ParallelExecutionMonitor:
    def __init__(self, tracking_file="TASK_TRACKING.json"):
        self.tracking_file = tracking_file
        self.start_date = datetime(2025, 7, 22)
        self.tasks = self._initialize_tasks()
        self.load_progress()
        
    def _initialize_tasks(self) -> Dict[str, Task]:
        """Initialize all tasks from the execution plan"""
        tasks = {
            # Week 1 - Frontend
            "FE-1.1": Task("FE-1.1", "React Setup", TeamStream.FRONTEND, 1, 2, 
                         TaskStatus.PENDING, 0, [], []),
            "FE-1.2": Task("FE-1.2", "Authentication UI", TeamStream.FRONTEND, 3, 4,
                         TaskStatus.PENDING, 0, ["FE-1.1"], []),
            "FE-1.3": Task("FE-1.3", "Core Layouts", TeamStream.FRONTEND, 5, 5,
                         TaskStatus.PENDING, 0, ["FE-1.2"], []),
                         
            # Week 1 - Backend/DevOps
            "BE-1.1": Task("BE-1.1", "GCP Project Setup", TeamStream.BACKEND, 1, 1,
                         TaskStatus.PENDING, 0, [], ["GCP credentials needed"]),
            "BE-1.2": Task("BE-1.2", "Infrastructure Prep", TeamStream.BACKEND, 2, 3,
                         TaskStatus.PENDING, 0, ["BE-1.1"], []),
            "BE-1.3": Task("BE-1.3", "API Enhancement", TeamStream.BACKEND, 4, 5,
                         TaskStatus.PENDING, 0, [], []),
                         
            # Week 2 - Frontend
            "FE-2.1": Task("FE-2.1", "Office Portal", TeamStream.FRONTEND, 6, 8,
                         TaskStatus.PENDING, 0, ["FE-1.3"], []),
                         
            # Week 2 - Backend
            "BE-2.1": Task("BE-2.1", "Vertex AI Config", TeamStream.BACKEND, 6, 7,
                         TaskStatus.PENDING, 0, ["BE-1.1"], []),
            "BE-2.2": Task("BE-2.2", "Routes API", TeamStream.BACKEND, 8, 9,
                         TaskStatus.PENDING, 0, ["BE-1.1"], []),
                         
            # Week 2 - Integration
            "INT-2.1": Task("INT-2.1", "WebSocket Setup", TeamStream.INTEGRATION, 8, 9,
                          TaskStatus.PENDING, 0, ["BE-1.3"], []),
                          
            # Week 3 tasks
            "FE-3.1": Task("FE-3.1", "Driver Mobile", TeamStream.FRONTEND, 11, 13,
                         TaskStatus.PENDING, 0, ["FE-2.1"], []),
            "FE-3.2": Task("FE-3.2", "Customer Portal", TeamStream.FRONTEND, 14, 15,
                         TaskStatus.PENDING, 0, ["FE-2.1"], []),
            "INT-3.1": Task("INT-3.1", "Real-time Features", TeamStream.INTEGRATION, 10, 11,
                          TaskStatus.PENDING, 0, ["INT-2.1", "BE-2.1", "BE-2.2"], []),
            "INT-3.2": Task("INT-3.2", "Reporting Dashboard", TeamStream.INTEGRATION, 12, 12,
                          TaskStatus.PENDING, 0, [], []),
            "INT-3.3": Task("INT-3.3", "E2E Testing", TeamStream.INTEGRATION, 13, 15,
                          TaskStatus.PENDING, 0, ["FE-3.1", "INT-3.1"], []),
                          
            # Week 4 - Production
            "PROD-4.1": Task("PROD-4.1", "CI/CD Pipeline", TeamStream.BACKEND, 16, 17,
                           TaskStatus.PENDING, 0, ["INT-3.3"], []),
            "PROD-4.2": Task("PROD-4.2", "Infrastructure", TeamStream.BACKEND, 18, 18,
                           TaskStatus.PENDING, 0, ["PROD-4.1"], []),
            "PROD-4.3": Task("PROD-4.3", "Monitoring", TeamStream.BACKEND, 19, 19,
                           TaskStatus.PENDING, 0, ["PROD-4.2"], []),
            "PROD-4.4": Task("PROD-4.4", "Go-Live", TeamStream.BACKEND, 20, 20,
                           TaskStatus.PENDING, 0, ["PROD-4.3"], []),
        }
        return tasks
        
    def load_progress(self):
        """Load saved progress from tracking file"""
        if os.path.exists(self.tracking_file):
            with open(self.tracking_file, 'r') as f:
                data = json.load(f)
                for task_id, task_data in data.get('tasks', {}).items():
                    if task_id in self.tasks:
                        self.tasks[task_id].status = TaskStatus(task_data['status'])
                        self.tasks[task_id].progress = task_data['progress']
                        self.tasks[task_id].blockers = task_data.get('blockers', [])
                        
    def save_progress(self):
        """Save current progress to tracking file"""
        data = {
            'last_updated': datetime.now().isoformat(),
            'tasks': {
                task_id: {
                    'status': task.status.value,
                    'progress': task.progress,
                    'blockers': task.blockers
                }
                for task_id, task in self.tasks.items()
            }
        }
        with open(self.tracking_file, 'w') as f:
            json.dump(data, f, indent=2)
            
    def get_current_day(self) -> int:
        """Get current day number since project start"""
        delta = datetime.now() - self.start_date
        return max(1, delta.days + 1)
        
    def get_team_status(self) -> List[TeamStatus]:
        """Get current status for each team"""
        current_day = self.get_current_day()
        team_statuses = []
        
        for team in TeamStream:
            team_tasks = [t for t in self.tasks.values() if t.team == team]
            current_tasks = [t for t in team_tasks 
                           if t.day_start <= current_day <= t.day_end 
                           and t.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]]
            
            if current_tasks:
                current_task = current_tasks[0]
                utilization = 80 if current_task.status == TaskStatus.IN_PROGRESS else 60
                team_statuses.append(TeamStatus(team, current_task.id, utilization, True))
            else:
                team_statuses.append(TeamStatus(team, None, 0, False))
                
        return team_statuses
        
    def get_overall_progress(self) -> Dict:
        """Calculate overall project progress"""
        total_tasks = len(self.tasks)
        completed_tasks = len([t for t in self.tasks.values() 
                             if t.status == TaskStatus.COMPLETED])
        
        phase_progress = {
            'Phase 1': self._calculate_phase_progress(['FE-1.1', 'FE-1.2', 'FE-1.3', 
                                                     'BE-1.1', 'BE-1.2', 'BE-1.3']),
            'Phase 2': self._calculate_phase_progress(['FE-2.1', 'BE-2.1', 'BE-2.2', 
                                                     'INT-2.1']),
            'Phase 3': self._calculate_phase_progress(['FE-3.1', 'FE-3.2', 'INT-3.1', 
                                                     'INT-3.2', 'INT-3.3']),
            'Phase 4': self._calculate_phase_progress(['PROD-4.1', 'PROD-4.2', 
                                                     'PROD-4.3', 'PROD-4.4']),
        }
        
        return {
            'overall_percentage': (completed_tasks / total_tasks) * 100,
            'completed_tasks': completed_tasks,
            'total_tasks': total_tasks,
            'phase_progress': phase_progress
        }
        
    def _calculate_phase_progress(self, task_ids: List[str]) -> int:
        """Calculate progress for a specific phase"""
        phase_tasks = [self.tasks[tid] for tid in task_ids if tid in self.tasks]
        if not phase_tasks:
            return 0
            
        total_progress = sum(t.progress for t in phase_tasks)
        return int(total_progress / len(phase_tasks))
        
    def get_critical_path_status(self) -> List[Dict]:
        """Get status of critical path tasks"""
        critical_tasks = ['BE-1.1', 'BE-2.1', 'BE-2.2', 'INT-3.3', 
                         'PROD-4.1', 'PROD-4.2', 'PROD-4.3', 'PROD-4.4']
        
        return [{
            'task_id': tid,
            'name': self.tasks[tid].name,
            'status': self.tasks[tid].status.value,
            'progress': self.tasks[tid].progress,
            'blockers': self.tasks[tid].blockers
        } for tid in critical_tasks if tid in self.tasks]
        
    def update_task(self, task_id: str, status: Optional[TaskStatus] = None,
                   progress: Optional[int] = None, blocker: Optional[str] = None):
        """Update task status, progress, or add blocker"""
        if task_id not in self.tasks:
            return False
            
        task = self.tasks[task_id]
        
        if status:
            task.status = status
        if progress is not None:
            task.progress = min(100, max(0, progress))
        if blocker:
            if blocker not in task.blockers:
                task.blockers.append(blocker)
                
        self.save_progress()
        return True
        
    def generate_status_report(self) -> str:
        """Generate formatted status report"""
        overall = self.get_overall_progress()
        team_statuses = self.get_team_status()
        critical_path = self.get_critical_path_status()
        current_day = self.get_current_day()
        
        report = f"""
# Lucky Gas Parallel Execution Status
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
Current Day: {current_day}

## Overall Progress: {overall['overall_percentage']:.1f}%
Completed: {overall['completed_tasks']}/{overall['total_tasks']} tasks

## Phase Progress:
"""
        
        for phase, progress in overall['phase_progress'].items():
            bar = '█' * (progress // 10) + '░' * (10 - progress // 10)
            report += f"- {phase}: {bar} {progress}%\n"
            
        report += "\n## Team Status:\n"
        for team_status in team_statuses:
            status = "🟢 Active" if team_status.active else "🔵 Idle"
            report += f"\n### {team_status.team.value}\n"
            report += f"- Status: {status}\n"
            report += f"- Current Task: {team_status.current_task or 'None'}\n"
            report += f"- Utilization: {team_status.utilization}%\n"
            
        report += "\n## Critical Path Status:\n"
        for task in critical_path:
            status_emoji = {
                'pending': '⏳',
                'in_progress': '🔄',
                'blocked': '🚫',
                'completed': '✅'
            }.get(task['status'], '❓')
            
            report += f"- {status_emoji} {task['task_id']}: {task['name']} ({task['progress']}%)\n"
            if task['blockers']:
                report += f"  ⚠️ Blockers: {', '.join(task['blockers'])}\n"
                
        return report


def main():
    """Main execution for standalone monitoring"""
    monitor = ParallelExecutionMonitor()
    
    # Example: Update some task progress
    # monitor.update_task('FE-1.1', TaskStatus.IN_PROGRESS, 50)
    # monitor.update_task('BE-1.1', TaskStatus.BLOCKED, 0, "Awaiting GCP credentials")
    
    # Generate and print status report
    print(monitor.generate_status_report())
    
    # Save burndown data
    burndown_data = {
        'day': monitor.get_current_day(),
        'remaining_tasks': len([t for t in monitor.tasks.values() 
                              if t.status != TaskStatus.COMPLETED]),
        'timestamp': datetime.now().isoformat()
    }
    
    # Append to burndown log
    burndown_file = 'burndown.json'
    burndown_log = []
    if os.path.exists(burndown_file):
        with open(burndown_file, 'r') as f:
            burndown_log = json.load(f)
    burndown_log.append(burndown_data)
    with open(burndown_file, 'w') as f:
        json.dump(burndown_log, f, indent=2)


if __name__ == "__main__":
    main()