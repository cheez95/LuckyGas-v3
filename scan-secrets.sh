#!/bin/bash

# ============================================================
# Secret Scanner for Lucky Gas Codebase
# ============================================================
# Purpose: Comprehensive security scan for exposed secrets
# Author: Security Team
# Date: 2025-08-17
# ============================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Counters
TOTAL_FILES=0
SCANNED_FILES=0
FOUND_ISSUES=0
WARNINGS=0

# Report file
REPORT_FILE="security-scan-report-$(date +%Y%m%d-%H%M%S).md"

# Directories to exclude from scanning
EXCLUDE_DIRS=".git|node_modules|.venv|venv|dist|build|.pytest_cache|__pycache__|.mypy_cache|.ruff_cache"

# Files to exclude
EXCLUDE_FILES="package-lock.json|yarn.lock|poetry.lock|uv.lock|.gitignore|*.pyc|*.pyo|*.pyd|*.so|*.min.js|*.map"

# Initialize report
init_report() {
    cat > "$REPORT_FILE" << EOF
# 🔒 Security Scan Report

**Date**: $(date '+%Y-%m-%d %H:%M:%S')  
**Scanner Version**: 1.0.0  
**Project**: Lucky Gas Delivery System

---

## Scan Summary

EOF
}

# Print header
print_header() {
    echo -e "${BOLD}${BLUE}"
    echo "============================================================"
    echo "       🔒 Lucky Gas Security Scanner v1.0"
    echo "============================================================"
    echo -e "${NC}"
    echo "Starting comprehensive security scan..."
    echo ""
}

# Function to scan for patterns
scan_pattern() {
    local pattern="$1"
    local description="$2"
    local severity="$3"
    local exclude_pattern="${4:-}"
    
    echo -e "${BLUE}[SCANNING]${NC} $description..."
    
    local results=""
    if [ -n "$exclude_pattern" ]; then
        results=$(grep -r -n -E "$pattern" . 2>/dev/null \
            --exclude-dir={.git,node_modules,.venv,venv,dist,build} \
            --exclude="*.lock" \
            --exclude="*.min.js" \
            --exclude="*.map" \
            --exclude="scan-secrets.sh" \
            --exclude="SECURITY*.md" \
            --exclude="*.pyc" | grep -v "$exclude_pattern" || true)
    else
        results=$(grep -r -n -E "$pattern" . 2>/dev/null \
            --exclude-dir={.git,node_modules,.venv,venv,dist,build} \
            --exclude="*.lock" \
            --exclude="*.min.js" \
            --exclude="*.map" \
            --exclude="scan-secrets.sh" \
            --exclude="SECURITY*.md" \
            --exclude="*.pyc" || true)
    fi
    
    if [ -n "$results" ]; then
        echo -e "${RED}[FOUND]${NC} $description detected!"
        echo "$results" | head -5
        echo "" >> "$REPORT_FILE"
        echo "### ⚠️ $description" >> "$REPORT_FILE"
        echo "**Severity**: $severity" >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
        echo "$results" | head -10 >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
        ((FOUND_ISSUES++))
        return 1
    else
        echo -e "${GREEN}[CLEAN]${NC} No $description found"
        return 0
    fi
}

# Scan for Google API keys
scan_google_keys() {
    echo -e "\n${BOLD}Scanning for Google API Keys...${NC}"
    scan_pattern "AIza[0-9A-Za-z\-_]{35}" "Google API Keys" "CRITICAL" "\.env\.example|\.md|test_"
}

# Scan for AWS credentials
scan_aws_keys() {
    echo -e "\n${BOLD}Scanning for AWS Credentials...${NC}"
    scan_pattern "AKIA[0-9A-Z]{16}" "AWS Access Keys" "CRITICAL" "\.env\.example|\.md"
    scan_pattern "aws_secret_access_key\s*=\s*['\"][^'\"]{40}['\"]" "AWS Secret Keys" "CRITICAL" "\.env\.example"
}

# Scan for JWT tokens
scan_jwt_tokens() {
    echo -e "\n${BOLD}Scanning for JWT Tokens...${NC}"
    scan_pattern "eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+" "JWT Tokens" "HIGH" "test_|spec\.|\.test\."
}

# Scan for private keys
scan_private_keys() {
    echo -e "\n${BOLD}Scanning for Private Keys...${NC}"
    scan_pattern "-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----" "Private Keys" "CRITICAL" "test_|example"
}

# Scan for database credentials
scan_database_creds() {
    echo -e "\n${BOLD}Scanning for Database Credentials...${NC}"
    scan_pattern "postgres(ql)?://[^:]+:[^@]+@[^/]+" "PostgreSQL URLs with passwords" "HIGH" "\.env\.example|localhost|password@localhost"
    scan_pattern "mysql://[^:]+:[^@]+@[^/]+" "MySQL URLs with passwords" "HIGH" "\.env\.example|localhost"
    scan_pattern "mongodb(\+srv)?://[^:]+:[^@]+@" "MongoDB URLs with passwords" "HIGH" "\.env\.example|localhost"
}

# Scan for hardcoded passwords
scan_passwords() {
    echo -e "\n${BOLD}Scanning for Hardcoded Passwords...${NC}"
    scan_pattern "(password|passwd|pwd)\s*=\s*['\"][^'\"]{8,}['\"]" "Hardcoded Passwords" "HIGH" "\.env\.example|example|test|dummy|placeholder|your-|change-|secret-key-"
}

# Scan for API tokens
scan_api_tokens() {
    echo -e "\n${BOLD}Scanning for API Tokens...${NC}"
    scan_pattern "(api[_-]?key|apikey|api_token|access[_-]?token)\s*=\s*['\"][A-Za-z0-9\-_]{20,}['\"]" "API Tokens" "HIGH" "\.env\.example|placeholder|your-|example|test_"
}

# Scan for email credentials
scan_email_creds() {
    echo -e "\n${BOLD}Scanning for Email Credentials...${NC}"
    scan_pattern "smtp_password\s*=\s*['\"][^'\"]+['\"]" "SMTP Passwords" "MEDIUM" "\.env\.example|your-"
    scan_pattern "email_password\s*=\s*['\"][^'\"]+['\"]" "Email Passwords" "MEDIUM" "\.env\.example|your-"
}

# Scan for Twilio credentials
scan_twilio() {
    echo -e "\n${BOLD}Scanning for Twilio Credentials...${NC}"
    scan_pattern "AC[a-z0-9]{32}" "Twilio Account SID" "MEDIUM" "\.env\.example"
    scan_pattern "SK[a-z0-9]{32}" "Twilio Auth Token" "HIGH" "\.env\.example"
}

# Scan for Stripe keys
scan_stripe() {
    echo -e "\n${BOLD}Scanning for Stripe Keys...${NC}"
    scan_pattern "sk_live_[0-9a-zA-Z]{24,}" "Stripe Live Secret Keys" "CRITICAL"
    scan_pattern "pk_live_[0-9a-zA-Z]{24,}" "Stripe Live Public Keys" "MEDIUM"
}

# Scan for GitHub tokens
scan_github() {
    echo -e "\n${BOLD}Scanning for GitHub Tokens...${NC}"
    scan_pattern "ghp_[0-9a-zA-Z]{36}" "GitHub Personal Access Tokens" "HIGH"
    scan_pattern "ghs_[0-9a-zA-Z]{36}" "GitHub Secret Tokens" "HIGH"
}

# Check for .env files in repository
check_env_files() {
    echo -e "\n${BOLD}Checking for .env files...${NC}"
    local env_files=$(find . -name ".env" -o -name ".env.*" 2>/dev/null | grep -v ".env.example" | grep -v node_modules | grep -v venv || true)
    
    if [ -n "$env_files" ]; then
        echo -e "${YELLOW}[WARNING]${NC} Found .env files that might contain secrets:"
        echo "$env_files"
        echo "" >> "$REPORT_FILE"
        echo "### ⚠️ Environment Files Found" >> "$REPORT_FILE"
        echo "**Severity**: MEDIUM" >> "$REPORT_FILE"
        echo "These files should not be committed to version control:" >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
        echo "$env_files" >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
        ((WARNINGS++))
    else
        echo -e "${GREEN}[CLEAN]${NC} No .env files found in repository"
    fi
}

# Check git history for removed secrets
check_git_history() {
    echo -e "\n${BOLD}Checking git history...${NC}"
    echo -e "${BLUE}[INFO]${NC} Checking last 20 commits for removed secrets..."
    
    # Check if we're in a git repository
    if [ -d .git ]; then
        local history_check=$(git log -20 -p 2>/dev/null | grep -E "AIza[0-9A-Za-z\-_]{35}|AKIA[0-9A-Z]{16}" || true)
        
        if [ -n "$history_check" ]; then
            echo -e "${YELLOW}[WARNING]${NC} Found potential secrets in git history"
            echo "Consider cleaning git history with BFG Repo-Cleaner or git filter-branch"
            echo "" >> "$REPORT_FILE"
            echo "### ⚠️ Secrets Found in Git History" >> "$REPORT_FILE"
            echo "**Severity**: HIGH" >> "$REPORT_FILE"
            echo "Secrets were found in git history. Consider cleaning with BFG Repo-Cleaner." >> "$REPORT_FILE"
            ((WARNINGS++))
        else
            echo -e "${GREEN}[CLEAN]${NC} No secrets found in recent git history"
        fi
    else
        echo -e "${BLUE}[SKIP]${NC} Not a git repository"
    fi
}

# Generate summary
generate_summary() {
    echo -e "\n${BOLD}${BLUE}============================================================${NC}"
    echo -e "${BOLD}                    SCAN COMPLETE${NC}"
    echo -e "${BOLD}${BLUE}============================================================${NC}"
    
    local status="✅ SECURE"
    local status_color="${GREEN}"
    
    if [ $FOUND_ISSUES -gt 0 ]; then
        status="❌ VULNERABLE"
        status_color="${RED}"
    elif [ $WARNINGS -gt 0 ]; then
        status="⚠️ WARNINGS"
        status_color="${YELLOW}"
    fi
    
    echo ""
    echo -e "Status: ${status_color}${BOLD}${status}${NC}"
    echo -e "Critical Issues Found: ${RED}${FOUND_ISSUES}${NC}"
    echo -e "Warnings: ${YELLOW}${WARNINGS}${NC}"
    echo ""
    
    # Add summary to report
    sed -i.bak "s/## Scan Summary/## Scan Summary\n\n**Status**: $status\n**Critical Issues**: $FOUND_ISSUES\n**Warnings**: $WARNINGS\n/" "$REPORT_FILE"
    rm "${REPORT_FILE}.bak" 2>/dev/null || true
    
    if [ $FOUND_ISSUES -eq 0 ] && [ $WARNINGS -eq 0 ]; then
        echo "" >> "$REPORT_FILE"
        echo "## ✅ All Clear!" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        echo "No secrets or sensitive information detected in the codebase." >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
        echo "### Security Checks Passed:" >> "$REPORT_FILE"
        echo "- ✅ No Google API keys" >> "$REPORT_FILE"
        echo "- ✅ No AWS credentials" >> "$REPORT_FILE"
        echo "- ✅ No JWT tokens" >> "$REPORT_FILE"
        echo "- ✅ No private keys" >> "$REPORT_FILE"
        echo "- ✅ No database passwords" >> "$REPORT_FILE"
        echo "- ✅ No hardcoded passwords" >> "$REPORT_FILE"
        echo "- ✅ No API tokens" >> "$REPORT_FILE"
        echo "- ✅ No email credentials" >> "$REPORT_FILE"
        echo "- ✅ No payment processor keys" >> "$REPORT_FILE"
        echo "- ✅ No GitHub tokens" >> "$REPORT_FILE"
    fi
    
    echo "" >> "$REPORT_FILE"
    echo "---" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "**Scan completed at**: $(date '+%Y-%m-%d %H:%M:%S')" >> "$REPORT_FILE"
    
    echo -e "${GREEN}Report saved to: ${BOLD}${REPORT_FILE}${NC}"
    
    # Return exit code based on findings
    if [ $FOUND_ISSUES -gt 0 ]; then
        exit 1
    fi
}

# Main execution
main() {
    print_header
    init_report
    
    # Run all scans
    scan_google_keys
    scan_aws_keys
    scan_jwt_tokens
    scan_private_keys
    scan_database_creds
    scan_passwords
    scan_api_tokens
    scan_email_creds
    scan_twilio
    scan_stripe
    scan_github
    
    # Additional checks
    check_env_files
    check_git_history
    
    # Generate final summary
    generate_summary
}

# Run the scanner
main "$@"