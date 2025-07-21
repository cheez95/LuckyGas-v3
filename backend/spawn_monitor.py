#!/usr/bin/env python3
"""
Spawn Process Monitor for PROD-DEPLOY-001
Monitors task progress and updates tracking files
"""
import json
import os
from datetime import datetime
from pathlib import Path
import time

class SpawnMonitor:
    def __init__(self):
        self.base_path = Path(__file__).parent
        self.tracking_file = self.base_path / "TASK_TRACKING.json"
        self.monitor_file = self.base_path / "SPAWN_MONITOR.md"
        self.frontend_path = self.base_path.parent / "frontend"
        
    def load_tracking_data(self):
        """Load current task tracking data"""
        with open(self.tracking_file, 'r') as f:
            return json.load(f)
    
    def save_tracking_data(self, data):
        """Save updated task tracking data"""
        data['metadata']['last_updated'] = datetime.utcnow().isoformat() + 'Z'
        with open(self.tracking_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def check_file_creation(self, expected_files):
        """Check if expected files have been created"""
        created_files = []
        for file_path in expected_files:
            if Path(file_path).exists():
                created_files.append(file_path)
        return created_files
    
    def update_task_status(self, task_id, new_status, evidence=None):
        """Update a specific task status"""
        data = self.load_tracking_data()
        updated = False
        
        for epic in data['epics']:
            for story in epic['stories']:
                for task in story['tasks']:
                    if task['id'] == task_id:
                        task['status'] = new_status
                        if evidence:
                            task['evidence'] = evidence
                        task['updated_at'] = datetime.utcnow().isoformat() + 'Z'
                        updated = True
                        break
        
        if updated:
            self.save_tracking_data(data)
            return True
        return False
    
    def calculate_progress(self, data):
        """Calculate progress metrics"""
        epic_progress = {}
        total_completed = 0
        total_tasks = 0
        
        for epic in data['epics']:
            epic_completed = 0
            epic_total = 0
            
            for story in epic['stories']:
                for task in story['tasks']:
                    epic_total += 1
                    total_tasks += 1
                    if task['status'] == 'completed':
                        epic_completed += 1
                        total_completed += 1
            
            epic_progress[epic['id']] = {
                'completed': epic_completed,
                'total': epic_total,
                'percentage': round((epic_completed / epic_total * 100) if epic_total > 0 else 0)
            }
        
        return {
            'epics': epic_progress,
            'total_completed': total_completed,
            'total_tasks': total_tasks,
            'overall_percentage': round((total_completed / total_tasks * 100) if total_tasks > 0 else 0)
        }
    
    def generate_monitor_report(self):
        """Generate updated monitor report"""
        data = self.load_tracking_data()
        progress = self.calculate_progress(data)
        
        # Check for expected files
        fe_int_files = [
            str(self.frontend_path / "src/services/api.js"),
            str(self.frontend_path / "src/components/Auth/Login.jsx"),
            str(self.frontend_path / ".env.development")
        ]
        
        gcp_files = [
            str(self.base_path / "GCP_SETUP_GUIDE.md"),
            str(self.base_path / "service-account-key.json")
        ]
        
        fe_created = self.check_file_creation(fe_int_files)
        gcp_created = self.check_file_creation(gcp_files)
        
        # Update monitor file
        monitor_content = f"""# Spawn Process Monitoring Dashboard
**Project**: PROD-DEPLOY-001 - Lucky Gas Production Deployment  
**Last Updated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC  
**Mode**: Parallel Execution

## 🚀 Active Spawn Processes

### Terminal 1: Frontend-Backend Integration (FE-INT)
- **Status**: {'🟢 Active' if progress['epics']['FE-INT']['percentage'] > 0 else '🟡 Awaiting Progress'}
- **Progress**: {progress['epics']['FE-INT']['percentage']}% ({progress['epics']['FE-INT']['completed']}/{progress['epics']['FE-INT']['total']} tasks)
- **Created Files**: {len(fe_created)} of {len(fe_int_files)}

### Terminal 2: Google Cloud Setup (GCP-SETUP)  
- **Status**: {'🟢 Active' if progress['epics']['GCP-SETUP']['percentage'] > 0 else '🟡 Awaiting Progress'}
- **Progress**: {progress['epics']['GCP-SETUP']['percentage']}% ({progress['epics']['GCP-SETUP']['completed']}/{progress['epics']['GCP-SETUP']['total']} tasks)
- **Created Files**: {len(gcp_created)} of {len(gcp_files)}

## 📊 Overall Progress
- **Total Tasks Completed**: {progress['total_completed']}/{progress['total_tasks']} ({progress['overall_percentage']}%)
- **Active Spawns**: {len(data['metadata'].get('active_spawns', []))}
- **Execution Mode**: {data['metadata'].get('execution_mode', 'Unknown')}

## 📝 Recent Updates
Check TASK_TRACKING.json for detailed task status updates.
"""
        
        with open(self.monitor_file, 'w') as f:
            f.write(monitor_content)
    
    def monitor_loop(self, interval=30):
        """Main monitoring loop"""
        print(f"Starting spawn monitor... Checking every {interval} seconds")
        
        while True:
            try:
                self.generate_monitor_report()
                print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] Monitor updated")
                
                # Check for completion
                data = self.load_tracking_data()
                progress = self.calculate_progress(data)
                
                fe_done = progress['epics']['FE-INT']['percentage'] == 100
                gcp_done = progress['epics']['GCP-SETUP']['percentage'] == 100
                
                if fe_done and gcp_done:
                    print("Both epics completed! Monitoring complete.")
                    break
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\nMonitoring stopped by user")
                break
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(interval)

if __name__ == "__main__":
    monitor = SpawnMonitor()
    
    # Quick test of file creation
    print("Spawn Monitor initialized")
    print(f"Tracking file: {monitor.tracking_file}")
    print(f"Frontend path: {monitor.frontend_path}")
    
    # Generate initial report
    monitor.generate_monitor_report()
    print("Initial monitor report generated")
    
    # Uncomment to start continuous monitoring
    # monitor.monitor_loop(30)