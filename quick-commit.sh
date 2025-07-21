#!/bin/bash
# Quick commit script for Lucky Gas project

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check for changes
if ! git status --porcelain | grep -q .; then
    echo -e "${YELLOW}No changes to commit${NC}"
    exit 0
fi

# Show status
echo -e "${GREEN}Current changes:${NC}"
git status --short

# Stage all changes
git add -A

# Generate commit message
timestamp=$(date '+%Y-%m-%d %H:%M:%S')
modified_count=$(git status --porcelain | grep -c "^ M")
added_count=$(git status --porcelain | grep -c "^A")
deleted_count=$(git status --porcelain | grep -c "^ D")

# Commit with auto-generated message
git commit -m "chore: Auto-commit at $timestamp

Changes summary:
- Modified: $modified_count files
- Added: $added_count files  
- Deleted: $deleted_count files

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push to remote
echo -e "${GREEN}Pushing to remote...${NC}"
if git push origin main; then
    echo -e "${GREEN}✅ Successfully committed and pushed!${NC}"
else
    echo -e "${RED}❌ Failed to push to remote${NC}"
    exit 1
fi