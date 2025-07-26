#!/usr/bin/env python3
"""
Verification Progress Tracker
Tracks manual verification progress of Lucky Gas system exploration
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Tuple
import re

class VerificationTracker:
    def __init__(self):
        self.checklist_file = "MANUAL_VERIFICATION_CHECKLIST.md"
        self.progress_file = "verification_progress.json"
        self.screenshot_dir = "verification_screenshots"
        
        # Create screenshot directory
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        # Load or initialize progress
        self.progress = self.load_progress()
        
    def load_progress(self) -> Dict:
        """Load existing progress or create new"""
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {
                "start_time": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "total_nodes": 102,
                "verified_nodes": 0,
                "sections": {},
                "issues": [],
                "screenshots": []
            }
    
    def save_progress(self):
        """Save current progress"""
        self.progress["last_updated"] = datetime.now().isoformat()
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(self.progress, f, ensure_ascii=False, indent=2)
    
    def parse_checklist(self) -> Dict:
        """Parse the checklist to extract all verification items"""
        with open(self.checklist_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        sections = {}
        current_section = None
        current_subsection = None
        
        for line in content.split('\n'):
            # Main section headers (## 1. 會員作業...)
            if line.startswith('## ') and '. ' in line:
                match = re.search(r'## \d+\. (.+?) \((.+?)\) - (\d+) Leaf Nodes', line)
                if match:
                    chinese_name = match.group(1)
                    english_name = match.group(2)
                    node_count = int(match.group(3))
                    current_section = chinese_name
                    sections[current_section] = {
                        "english_name": english_name,
                        "total_nodes": node_count,
                        "verified": 0,
                        "subsections": {}
                    }
            
            # Subsection headers (### 客戶資料維護...)
            elif line.startswith('### ') and current_section:
                current_subsection = line.replace('### ', '').strip()
                if current_subsection:
                    sections[current_section]["subsections"][current_subsection] = {
                        "items": []
                    }
            
            # Checklist items (- [ ] **item name**)
            elif line.strip().startswith('- [ ]') and current_section and current_subsection:
                match = re.search(r'- \[ \] \*\*(.+?)\*\*', line)
                if match:
                    item_name = match.group(1)
                    sections[current_section]["subsections"][current_subsection]["items"].append({
                        "name": item_name,
                        "verified": False,
                        "screenshot": None,
                        "notes": ""
                    })
        
        return sections
    
    def mark_verified(self, section: str, subsection: str, item: str, screenshot: str = None, notes: str = ""):
        """Mark an item as verified"""
        if section not in self.progress["sections"]:
            self.progress["sections"] = self.parse_checklist()
        
        sections = self.progress["sections"]
        
        if section in sections and subsection in sections[section]["subsections"]:
            for item_obj in sections[section]["subsections"][subsection]["items"]:
                if item_obj["name"] == item:
                    item_obj["verified"] = True
                    item_obj["verified_at"] = datetime.now().isoformat()
                    if screenshot:
                        item_obj["screenshot"] = screenshot
                        self.progress["screenshots"].append(screenshot)
                    if notes:
                        item_obj["notes"] = notes
                    
                    # Update counts
                    self.update_counts()
                    self.save_progress()
                    return True
        
        return False
    
    def update_counts(self):
        """Update verification counts"""
        total_verified = 0
        
        for section_name, section_data in self.progress["sections"].items():
            section_verified = 0
            for subsection_name, subsection_data in section_data["subsections"].items():
                for item in subsection_data["items"]:
                    if item["verified"]:
                        section_verified += 1
                        total_verified += 1
            
            section_data["verified"] = section_verified
        
        self.progress["verified_nodes"] = total_verified
    
    def add_issue(self, issue: str, section: str = None):
        """Add an issue or blocker"""
        issue_obj = {
            "issue": issue,
            "section": section,
            "reported_at": datetime.now().isoformat()
        }
        self.progress["issues"].append(issue_obj)
        self.save_progress()
    
    def generate_report(self) -> str:
        """Generate progress report"""
        if not self.progress["sections"]:
            self.progress["sections"] = self.parse_checklist()
        
        report = f"""# Lucky Gas System Verification Progress Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Progress**: {self.progress['verified_nodes']}/{self.progress['total_nodes']} nodes verified ({self.progress['verified_nodes']/self.progress['total_nodes']*100:.1f}%)

## Section Progress

"""
        
        for section_name, section_data in self.progress["sections"].items():
            verified = section_data.get("verified", 0)
            total = section_data["total_nodes"]
            percentage = (verified/total*100) if total > 0 else 0
            
            report += f"### {section_name} ({section_data['english_name']})\n"
            report += f"Progress: {verified}/{total} ({percentage:.1f}%)\n"
            report += f"{'█' * int(percentage/10)}{'░' * (10-int(percentage/10))} {percentage:.0f}%\n\n"
            
            # Show subsection details
            for subsection_name, subsection_data in section_data["subsections"].items():
                verified_items = sum(1 for item in subsection_data["items"] if item["verified"])
                total_items = len(subsection_data["items"])
                
                if total_items > 0:
                    report += f"- **{subsection_name}**: {verified_items}/{total_items}\n"
                    
                    # Show unverified items
                    unverified = [item["name"] for item in subsection_data["items"] if not item["verified"]]
                    if unverified and verified_items < total_items:
                        report += f"  - Pending: {', '.join(unverified[:3])}"
                        if len(unverified) > 3:
                            report += f" (+{len(unverified)-3} more)"
                        report += "\n"
            
            report += "\n"
        
        # Issues section
        if self.progress["issues"]:
            report += "## Issues & Blockers\n\n"
            for i, issue in enumerate(self.progress["issues"], 1):
                report += f"{i}. {issue['issue']}"
                if issue['section']:
                    report += f" (Section: {issue['section']})"
                report += f" - Reported: {issue['reported_at'][:10]}\n"
        
        # Statistics
        report += f"\n## Statistics\n\n"
        report += f"- Start Time: {self.progress['start_time'][:19]}\n"
        report += f"- Last Updated: {self.progress['last_updated'][:19]}\n"
        report += f"- Total Screenshots: {len(self.progress['screenshots'])}\n"
        report += f"- Issues Reported: {len(self.progress['issues'])}\n"
        
        # Time estimate
        if self.progress['verified_nodes'] > 0:
            elapsed = datetime.now() - datetime.fromisoformat(self.progress['start_time'])
            avg_time_per_node = elapsed.total_seconds() / self.progress['verified_nodes']
            remaining_nodes = self.progress['total_nodes'] - self.progress['verified_nodes']
            estimated_remaining = avg_time_per_node * remaining_nodes
            
            report += f"\n### Time Estimates\n"
            report += f"- Average time per node: {avg_time_per_node/60:.1f} minutes\n"
            report += f"- Estimated time remaining: {estimated_remaining/3600:.1f} hours\n"
        
        return report
    
    def create_screenshot_index(self):
        """Create an HTML index of all screenshots"""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Lucky Gas System Screenshots</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; }
        .screenshot { display: inline-block; margin: 10px; text-align: center; }
        .screenshot img { max-width: 300px; border: 1px solid #ccc; }
        .verified { background-color: #d4edda; }
        .pending { background-color: #f8d7da; }
    </style>
</head>
<body>
    <h1>Lucky Gas System Verification Screenshots</h1>
"""
        
        if not self.progress["sections"]:
            self.progress["sections"] = self.parse_checklist()
        
        for section_name, section_data in self.progress["sections"].items():
            html += f'<div class="section">'
            html += f'<h2>{section_name} ({section_data["english_name"]})</h2>'
            
            for subsection_name, subsection_data in section_data["subsections"].items():
                html += f'<h3>{subsection_name}</h3>'
                
                for item in subsection_data["items"]:
                    status_class = "verified" if item["verified"] else "pending"
                    html += f'<div class="screenshot {status_class}">'
                    
                    if item.get("screenshot") and os.path.exists(f"{self.screenshot_dir}/{item['screenshot']}"):
                        html += f'<img src="{self.screenshot_dir}/{item["screenshot"]}" alt="{item["name"]}">'
                    else:
                        html += f'<div style="width:300px;height:200px;background:#eee;display:flex;align-items:center;justify-content:center;">No screenshot</div>'
                    
                    html += f'<p>{item["name"]}</p>'
                    if item["verified"]:
                        html += f'<p style="color:green;">✓ Verified</p>'
                    else:
                        html += f'<p style="color:red;">⏳ Pending</p>'
                    
                    if item.get("notes"):
                        html += f'<p style="font-size:0.9em;color:#666;">{item["notes"]}</p>'
                    
                    html += '</div>'
            
            html += '</div>'
        
        html += """
</body>
</html>"""
        
        with open('screenshot_index.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        print("📸 Screenshot index created: screenshot_index.html")

def main():
    """Interactive verification tracker"""
    tracker = VerificationTracker()
    
    while True:
        print("\n" + "="*60)
        print("Lucky Gas System Verification Tracker")
        print("="*60)
        print(f"Progress: {tracker.progress['verified_nodes']}/{tracker.progress['total_nodes']} nodes verified")
        print("\nOptions:")
        print("1. Mark item as verified")
        print("2. Report an issue")
        print("3. Generate progress report")
        print("4. Create screenshot index")
        print("5. Show current stats")
        print("6. Exit")
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == '1':
            print("\n--- Mark Item as Verified ---")
            section = input("Section name (e.g., 會員作業): ").strip()
            subsection = input("Subsection name (e.g., 客戶資料維護): ").strip()
            item = input("Item name (e.g., 新增客戶 Form): ").strip()
            screenshot = input("Screenshot filename (optional): ").strip()
            notes = input("Notes (optional): ").strip()
            
            if tracker.mark_verified(section, subsection, item, screenshot, notes):
                print("✅ Item marked as verified!")
            else:
                print("❌ Item not found. Please check the names.")
        
        elif choice == '2':
            print("\n--- Report an Issue ---")
            issue = input("Describe the issue: ").strip()
            section = input("Related section (optional): ").strip()
            tracker.add_issue(issue, section if section else None)
            print("📝 Issue recorded!")
        
        elif choice == '3':
            report = tracker.generate_report()
            filename = f"verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"📊 Report generated: {filename}")
            print("\nReport Preview:")
            print(report[:500] + "...")
        
        elif choice == '4':
            tracker.create_screenshot_index()
        
        elif choice == '5':
            print("\n--- Current Statistics ---")
            print(f"Total Nodes: {tracker.progress['total_nodes']}")
            print(f"Verified: {tracker.progress['verified_nodes']}")
            print(f"Remaining: {tracker.progress['total_nodes'] - tracker.progress['verified_nodes']}")
            print(f"Screenshots: {len(tracker.progress['screenshots'])}")
            print(f"Issues: {len(tracker.progress['issues'])}")
            
            if tracker.progress['verified_nodes'] > 0:
                elapsed = datetime.now() - datetime.fromisoformat(tracker.progress['start_time'])
                print(f"\nTime elapsed: {elapsed}")
                avg_time = elapsed.total_seconds() / tracker.progress['verified_nodes']
                print(f"Average time per node: {avg_time/60:.1f} minutes")
        
        elif choice == '6':
            print("\n👋 Exiting verification tracker...")
            break
        
        else:
            print("❌ Invalid option. Please try again.")

if __name__ == "__main__":
    main()