#!/usr/bin/env python3
"""
Security Scanner for LuckyGas v3

Scans codebase for potential security vulnerabilities:
- Hardcoded API keys and secrets
- Exposed credentials
- Insecure configurations
"""

import re
import os
import json
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

# Patterns for detecting secrets
SECRET_PATTERNS = {
    "google_maps_api_key": re.compile(r'AIza[0-9A-Za-z\-_]{35}'),
    "google_service_account": re.compile(r'"type"\s*:\s*"service_account"'),
    "aws_access_key": re.compile(r'AKIA[0-9A-Z]{16}'),
    "aws_secret_key": re.compile(r'[0-9a-zA-Z/+=]{40}'),
    "generic_api_key": re.compile(r'[aA][pP][iI][-_]?[kK][eE][yY]\s*[:=]\s*["\']?[0-9a-zA-Z\-_]{16,}["\']?'),
    "generic_secret": re.compile(r'[sS][eE][cC][rR][eE][tT]\s*[:=]\s*["\']?[0-9a-zA-Z\-_]{16,}["\']?'),
    "password_assignment": re.compile(r'[pP][aA][sS][sS][wW][oO][rR][dD]\s*[:=]\s*["\'][^"\'\n]{8,}["\']'),
    "private_key": re.compile(r'-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----'),
    "jwt_token": re.compile(r'eyJ[0-9a-zA-Z_-]+\.[0-9a-zA-Z_-]+\.[0-9a-zA-Z_-]+'),
    "hardcoded_ip": re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
    "taiwan_phone": re.compile(r'09\d{8}|0[2-8]\d{7,8}'),
    "bank_account": re.compile(r'\b\d{10,16}\b'),
}

# Files and directories to skip
SKIP_PATTERNS = [
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "*.pyc",
    "*.log",
    "*.lock",
    "package-lock.json",
    "poetry.lock",
    "security_scan.py",  # Skip self
    "SECURITY_*.md",     # Skip security docs
]

# Known safe patterns (to reduce false positives)
SAFE_PATTERNS = [
    "test-secret-key-for-testing-only",
    "luckygas123",  # Test database password
    "TestAdmin123!",  # Test admin password
    "example_api_key",
    "your-api-key-here",
    "<your-api-key>",
    "placeholder",
]


class SecurityScanner:
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        self.findings = []
        self.stats = {
            "files_scanned": 0,
            "secrets_found": 0,
            "high_risk": 0,
            "medium_risk": 0,
            "low_risk": 0,
        }
    
    def should_scan_file(self, file_path: Path) -> bool:
        """Check if file should be scanned"""
        # Skip based on patterns
        for pattern in SKIP_PATTERNS:
            if pattern.startswith("*") and file_path.name.endswith(pattern[1:]):
                return False
            elif pattern in str(file_path):
                return False
        
        # Only scan text files
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read(1)
            return True
        except:
            return False
    
    def is_safe_pattern(self, match: str) -> bool:
        """Check if matched pattern is known to be safe"""
        return any(safe in match.lower() for safe in SAFE_PATTERNS)
    
    def calculate_risk_level(self, pattern_type: str, file_path: Path) -> str:
        """Calculate risk level based on pattern type and file location"""
        high_risk_patterns = ["google_maps_api_key", "private_key", "aws_access_key", "bank_account"]
        high_risk_files = [".env", "config", "settings", "production"]
        
        if pattern_type in high_risk_patterns:
            return "HIGH"
        elif any(risk_file in str(file_path).lower() for risk_file in high_risk_files):
            return "MEDIUM"
        else:
            return "LOW"
    
    def scan_file(self, file_path: Path) -> List[Dict]:
        """Scan a single file for security issues"""
        findings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
            
            for pattern_name, pattern in SECRET_PATTERNS.items():
                matches = pattern.finditer(content)
                for match in matches:
                    matched_text = match.group(0)
                    
                    # Skip safe patterns
                    if self.is_safe_pattern(matched_text):
                        continue
                    
                    # Find line number
                    line_num = content[:match.start()].count('\n') + 1
                    
                    # Calculate risk level
                    risk_level = self.calculate_risk_level(pattern_name, file_path)
                    
                    finding = {
                        "file": str(file_path.relative_to(self.root_path)),
                        "line": line_num,
                        "type": pattern_name,
                        "risk": risk_level,
                        "match": matched_text[:50] + "..." if len(matched_text) > 50 else matched_text,
                        "context": lines[line_num-1].strip() if line_num <= len(lines) else "",
                    }
                    
                    findings.append(finding)
                    self.stats[f"{risk_level.lower()}_risk"] += 1
        
        except Exception as e:
            print(f"Error scanning {file_path}: {e}")
        
        return findings
    
    def scan_directory(self, directory: Path = None) -> None:
        """Recursively scan directory for security issues"""
        if directory is None:
            directory = self.root_path
        
        for file_path in directory.rglob("*"):
            if file_path.is_file() and self.should_scan_file(file_path):
                self.stats["files_scanned"] += 1
                
                findings = self.scan_file(file_path)
                if findings:
                    self.findings.extend(findings)
                    self.stats["secrets_found"] += len(findings)
    
    def generate_report(self) -> Dict:
        """Generate security scan report"""
        report = {
            "scan_date": datetime.now().isoformat(),
            "root_path": str(self.root_path),
            "statistics": self.stats,
            "findings": self.findings,
            "summary": {
                "total_issues": self.stats["secrets_found"],
                "critical_action_required": self.stats["high_risk"] > 0,
                "requires_immediate_attention": [],
            },
        }
        
        # Group high-risk findings
        for finding in self.findings:
            if finding["risk"] == "HIGH":
                report["summary"]["requires_immediate_attention"].append({
                    "file": finding["file"],
                    "type": finding["type"],
                    "line": finding["line"],
                })
        
        return report
    
    def print_report(self, report: Dict) -> None:
        """Print formatted security report"""
        print("\n" + "="*60)
        print("SECURITY SCAN REPORT")
        print("="*60)
        print(f"Scan Date: {report['scan_date']}")
        print(f"Files Scanned: {report['statistics']['files_scanned']}")
        print(f"Total Issues Found: {report['statistics']['secrets_found']}")
        print("\nRisk Distribution:")
        print(f"  HIGH:   {report['statistics']['high_risk']}")
        print(f"  MEDIUM: {report['statistics']['medium_risk']}")
        print(f"  LOW:    {report['statistics']['low_risk']}")
        
        if report['summary']['critical_action_required']:
            print("\n" + "!"*60)
            print("CRITICAL: HIGH RISK SECRETS DETECTED!")
            print("!"*60)
            for item in report['summary']['requires_immediate_attention']:
                print(f"  - {item['file']}:{item['line']} ({item['type']})")
        
        if report['findings']:
            print("\nDetailed Findings:")
            print("-"*60)
            
            # Group by risk level
            for risk in ["HIGH", "MEDIUM", "LOW"]:
                risk_findings = [f for f in report['findings'] if f['risk'] == risk]
                if risk_findings:
                    print(f"\n{risk} RISK:")
                    for finding in risk_findings:
                        print(f"  File: {finding['file']}")
                        print(f"  Line: {finding['line']}")
                        print(f"  Type: {finding['type']}")
                        print(f"  Match: {finding['match']}")
                        print(f"  Context: {finding['context']}")
                        print("-"*40)
        else:
            print("\n✅ No security issues found!")
        
        print("\n" + "="*60)
        print("RECOMMENDATIONS:")
        print("="*60)
        print("1. Review all HIGH risk findings immediately")
        print("2. Move all secrets to environment variables or Secret Manager")
        print("3. Rotate any exposed credentials")
        print("4. Add pre-commit hooks to prevent future exposures")
        print("5. Use backend proxy for all external API calls")


def main():
    """Main execution function"""
    # Parse arguments
    root_path = sys.argv[1] if len(sys.argv) > 1 else "."
    
    print(f"Starting security scan of: {root_path}")
    print("This may take a few moments...\n")
    
    # Run scan
    scanner = SecurityScanner(root_path)
    scanner.scan_directory()
    
    # Generate and print report
    report = scanner.generate_report()
    scanner.print_report(report)
    
    # Save report to file
    report_file = "security_scan_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nDetailed report saved to: {report_file}")
    
    # Exit with error code if high-risk issues found
    if report['statistics']['high_risk'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()