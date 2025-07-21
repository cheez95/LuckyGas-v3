#!/bin/bash
# Auto-commit script for Lucky Gas project
# This script will automatically commit and push changes periodically

# Configuration
PROJECT_DIR="/Users/lgee258/Desktop/LuckyGas-v3"
COMMIT_INTERVAL=1800  # 30 minutes in seconds
LOG_FILE="$PROJECT_DIR/auto-commit.log"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to log messages
log_message() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to check if there are changes to commit
has_changes() {
    cd "$PROJECT_DIR"
    git status --porcelain | grep -q .
}

# Function to generate commit message based on changes
generate_commit_message() {
    cd "$PROJECT_DIR"
    
    # Count changes by type
    modified_count=$(git status --porcelain | grep -c "^ M")
    added_count=$(git status --porcelain | grep -c "^A")
    deleted_count=$(git status --porcelain | grep -c "^ D")
    
    # Get the most recently modified files
    recent_files=$(git status --porcelain | head -5 | awk '{print $2}' | xargs)
    
    # Generate timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Build commit message
    echo "chore: Auto-commit at $timestamp

Changes:
- Modified: $modified_count files
- Added: $added_count files
- Deleted: $deleted_count files

Recent files: $recent_files

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
}

# Function to perform auto-commit
auto_commit() {
    cd "$PROJECT_DIR"
    
    if has_changes; then
        log_message "${GREEN}Changes detected. Committing...${NC}"
        
        # Stage all changes
        git add -A
        
        # Generate and use commit message
        commit_msg=$(generate_commit_message)
        git commit -m "$commit_msg"
        
        # Push to remote
        if git push origin main; then
            log_message "${GREEN}Successfully pushed to remote${NC}"
        else
            log_message "${RED}Failed to push to remote${NC}"
        fi
    else
        log_message "${YELLOW}No changes to commit${NC}"
    fi
}

# Main loop
log_message "${GREEN}Starting auto-commit script${NC}"
log_message "Monitoring: $PROJECT_DIR"
log_message "Interval: $COMMIT_INTERVAL seconds"

while true; do
    auto_commit
    log_message "Sleeping for $COMMIT_INTERVAL seconds..."
    sleep $COMMIT_INTERVAL
done