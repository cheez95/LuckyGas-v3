#!/usr/bin/env python3
"""
Test Coverage Analysis Script for Lucky Gas Backend
Analyzes test coverage for Epic 7 components and generates visual reports
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import xml.etree.ElementTree as ET

class TestCoverageAnalyzer:
    def __init__(self, backend_path: Path):
        self.backend_path = backend_path
        self.coverage_data = {}
        self.epic7_components = [
            "app/api/v1/routes.py",
            "app/api/v1/route_optimization.py",
            "app/api/v1/websocket.py",
            "app/api/v1/analytics.py",
            "app/services/route_optimization_service.py",
            "app/services/websocket_service.py",
            "app/services/analytics_service.py",
            "app/services/dispatch/route_optimizer.py",
            "app/services/dispatch/google_routes_service.py",
            "app/services/optimization/vrp_optimizer.py",
            "app/services/optimization/enhanced_vrp_solver.py",
            "app/models/route.py",
            "app/models/route_plan.py",
            "app/models/optimization.py"
        ]
        
    def run_coverage_analysis(self) -> Dict:
        """Run pytest with coverage and analyze results"""
        print("🔍 Running test coverage analysis...")
        
        # Run pytest with coverage for Epic 7 tests
        cmd = [
            "pytest",
            "--cov=app",
            "--cov-report=xml",
            "--cov-report=json",
            "--cov-report=html",
            "--cov-report=term-missing",
            "-v",
            "tests/integration/test_epic7_complete_flow.py",
            "tests/integration/test_story_3_3_realtime_adjustment.py",
            "tests/integration/test_story_3_3_simple.py",
            "tests/integration/test_route_optimization_integration.py",
            "tests/integration/test_websocket_realtime.py",
            "tests/integration/test_analytics_flow.py"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.backend_path,
                capture_output=True,
                text=True
            )
            
            # Parse coverage results
            coverage_json_path = self.backend_path / "coverage.json"
            if coverage_json_path.exists():
                with open(coverage_json_path, 'r') as f:
                    self.coverage_data = json.load(f)
                    
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "coverage_data": self.coverage_data
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "coverage_data": {}
            }
    
    def analyze_epic7_coverage(self) -> Dict:
        """Analyze coverage specifically for Epic 7 components"""
        epic7_coverage = {}
        
        if "files" in self.coverage_data:
            for component in self.epic7_components:
                file_path = str(self.backend_path / component)
                if file_path in self.coverage_data["files"]:
                    file_data = self.coverage_data["files"][file_path]
                    epic7_coverage[component] = {
                        "percent_covered": file_data["summary"]["percent_covered"],
                        "missing_lines": file_data["summary"]["missing_lines"],
                        "covered_lines": file_data["summary"]["covered_lines"],
                        "total_lines": file_data["summary"]["num_statements"]
                    }
                else:
                    epic7_coverage[component] = {
                        "percent_covered": 0,
                        "missing_lines": 0,
                        "covered_lines": 0,
                        "total_lines": 0,
                        "not_found": True
                    }
                    
        return epic7_coverage
    
    def identify_uncovered_paths(self) -> List[Dict]:
        """Identify critical uncovered code paths"""
        uncovered_paths = []
        
        if "files" in self.coverage_data:
            for file_path, file_data in self.coverage_data["files"].items():
                if any(component in file_path for component in self.epic7_components):
                    if "missing_lines" in file_data and file_data["missing_lines"]:
                        uncovered_paths.append({
                            "file": file_path.replace(str(self.backend_path) + "/", ""),
                            "missing_lines": file_data["missing_lines"],
                            "missing_branches": file_data.get("missing_branches", [])
                        })
                        
        return uncovered_paths
    
    def generate_visual_report(self) -> str:
        """Generate a visual coverage report"""
        report = []
        report.append("# Epic 7 Test Coverage Visual Report\n")
        report.append(f"Generated at: {datetime.now().isoformat()}\n")
        
        # Overall coverage
        if "totals" in self.coverage_data:
            totals = self.coverage_data["totals"]
            percent = totals.get("percent_covered", 0)
            report.append(f"## Overall Coverage: {percent:.1f}%\n")
            report.append(self._generate_progress_bar(percent))
            report.append("\n")
        
        # Epic 7 component coverage
        epic7_coverage = self.analyze_epic7_coverage()
        report.append("## Epic 7 Component Coverage\n")
        
        for component, coverage in sorted(epic7_coverage.items()):
            if coverage.get("not_found"):
                report.append(f"- ❌ {component}: Not found\n")
            else:
                percent = coverage["percent_covered"]
                emoji = "✅" if percent >= 80 else "⚠️" if percent >= 60 else "❌"
                report.append(f"- {emoji} {component}: {percent:.1f}%\n")
                report.append(f"  {self._generate_progress_bar(percent, width=30)}\n")
                report.append(f"  Lines: {coverage['covered_lines']}/{coverage['total_lines']}\n")
                
        # Uncovered paths
        uncovered = self.identify_uncovered_paths()
        if uncovered:
            report.append("\n## Critical Uncovered Paths\n")
            for path in uncovered[:10]:  # Top 10
                report.append(f"- {path['file']}\n")
                report.append(f"  Missing lines: {path['missing_lines'][:5]}...\n")
                
        return "\n".join(report)
    
    def _generate_progress_bar(self, percent: float, width: int = 50) -> str:
        """Generate a text-based progress bar"""
        filled = int(width * percent / 100)
        empty = width - filled
        return f"[{'█' * filled}{'░' * empty}] {percent:.1f}%"
    
    def save_report(self, report: str, filename: str = "coverage_visual_report.txt"):
        """Save the visual report to a file"""
        report_path = self.backend_path / filename
        with open(report_path, 'w') as f:
            f.write(report)
        print(f"✅ Visual report saved to {report_path}")
        
    def analyze_test_files(self) -> Dict:
        """Analyze existing test files for Epic 7"""
        test_files = {
            "integration": [],
            "unit": [],
            "e2e": [],
            "performance": []
        }
        
        test_patterns = {
            "integration": ["test_epic7_", "test_story_3_3_", "test_route_", "test_websocket_"],
            "unit": ["test_vrp_", "test_optimizer_", "test_routes_service"],
            "e2e": ["test_driver_", "test_complete_order_"],
            "performance": ["test_.*_performance", "load_test_", "benchmark_"]
        }
        
        tests_path = self.backend_path / "tests"
        for test_type, patterns in test_patterns.items():
            for pattern in patterns:
                # Use glob to find matching test files
                for test_file in tests_path.rglob(f"*{pattern}*.py"):
                    test_files[test_type].append(str(test_file.relative_to(self.backend_path)))
                    
        return test_files

def main():
    """Main execution function"""
    backend_path = Path(__file__).parent
    analyzer = TestCoverageAnalyzer(backend_path)
    
    print("🚀 Starting Epic 7 Test Coverage Analysis")
    
    # Run coverage analysis
    coverage_result = analyzer.run_coverage_analysis()
    
    if not coverage_result["success"]:
        print("⚠️  Coverage analysis completed with warnings")
        if "error" in coverage_result:
            print(f"Error: {coverage_result['error']}")
    
    # Generate visual report
    visual_report = analyzer.generate_visual_report()
    print("\n" + visual_report)
    
    # Save report
    analyzer.save_report(visual_report)
    
    # Analyze test files
    test_files = analyzer.analyze_test_files()
    
    print("\n📊 Test File Analysis")
    for test_type, files in test_files.items():
        print(f"\n{test_type.capitalize()} Tests ({len(files)} files):")
        for file in files[:5]:  # Show first 5
            print(f"  - {file}")
        if len(files) > 5:
            print(f"  ... and {len(files) - 5} more")
    
    # Generate summary
    epic7_coverage = analyzer.analyze_epic7_coverage()
    avg_coverage = sum(c["percent_covered"] for c in epic7_coverage.values() if not c.get("not_found")) / len(epic7_coverage)
    
    print(f"\n📈 Summary:")
    print(f"  - Average Epic 7 Coverage: {avg_coverage:.1f}%")
    print(f"  - Total Test Files: {sum(len(files) for files in test_files.values())}")
    print(f"  - Components Analyzed: {len(epic7_coverage)}")
    
    return coverage_result["success"]

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)