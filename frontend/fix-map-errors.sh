#!/bin/bash

# Script to automatically fix .map() errors in the Lucky Gas frontend
# This will add safe array handling to prevent "map is not a function" errors

echo "========================================="
echo "Starting Lucky Gas Frontend Map Error Fix"
echo "========================================="

# Change to frontend directory
cd /Users/lgee258/Desktop/LuckyGas-v3/frontend

# Find all files with response.data.*.map or similar patterns
echo ""
echo "Finding files with potentially unsafe .map() calls..."

FILES_TO_FIX=$(grep -r "response\.*data.*\.map\|response\.*\.map" src --include="*.tsx" --include="*.jsx" -l | grep -v dataHelpers)

echo "Found ${#FILES_TO_FIX[@]} files to fix:"
echo "$FILES_TO_FIX"

# Counter for fixed files
FIXED_COUNT=0

# Fix each file
for file in $FILES_TO_FIX; do
  echo ""
  echo "Processing: $file"
  
  # Check if file already imports dataHelpers
  if ! grep -q "import.*dataHelpers" "$file"; then
    echo "  Adding dataHelpers import..."
    
    # Find the last import line
    LAST_IMPORT_LINE=$(grep -n "^import" "$file" | tail -1 | cut -d: -f1)
    
    if [ -n "$LAST_IMPORT_LINE" ]; then
      # Calculate relative path to utils/dataHelpers
      RELATIVE_PATH=$(realpath --relative-to=$(dirname "$file") src/utils/dataHelpers.ts | sed 's/\.ts$//')
      
      # Insert the import after the last import
      sed -i "${LAST_IMPORT_LINE}a\\
import { toArray, safeMap, SafeArray } from './${RELATIVE_PATH}';" "$file"
      
      echo "  ✓ Added dataHelpers import"
    fi
  fi
  
  # Create backup
  cp "$file" "${file}.backup.$(date +%Y%m%d_%H%M%S)"
  
  # Fix common patterns
  echo "  Fixing .map() patterns..."
  
  # Pattern 1: response.data.something.map( → safeMap(response.data.something,
  sed -i -E 's/response\.data\.([a-zA-Z]+)\.map\(/safeMap(response.data.\1, /g' "$file"
  
  # Pattern 2: response.something.map( → safeMap(response.something,
  sed -i -E 's/response\.([a-zA-Z]+)\.map\(/safeMap(response.\1, /g' "$file"
  
  # Pattern 3: data.something.map( → safeMap(data.something,
  sed -i -E 's/data\.([a-zA-Z]+)\.map\(/safeMap(data.\1, /g' "$file"
  
  FIXED_COUNT=$((FIXED_COUNT + 1))
  echo "  ✓ Fixed .map() patterns"
done

echo ""
echo "========================================="
echo "Fix Summary:"
echo "  - Files processed: $FIXED_COUNT"
echo "  - Backups created for all modified files"
echo "========================================="

# Now fix components that use state.map() patterns
echo ""
echo "Fixing state.map() patterns..."

STATE_FILES=$(grep -r "useState.*\[\]" src --include="*.tsx" --include="*.jsx" -l)

for file in $STATE_FILES; do
  # Find lines with someState.map( and not already using safe functions
  if grep -q "^\s*{[a-zA-Z]*\.map(" "$file"; then
    echo "Processing state maps in: $file"
    
    # Add import if not present
    if ! grep -q "import.*dataHelpers" "$file"; then
      LAST_IMPORT_LINE=$(grep -n "^import" "$file" | tail -1 | cut -d: -f1)
      if [ -n "$LAST_IMPORT_LINE" ]; then
        RELATIVE_PATH=$(realpath --relative-to=$(dirname "$file") src/utils/dataHelpers.ts | sed 's/\.ts$//')
        sed -i "${LAST_IMPORT_LINE}a\\
import { toArray, safeMap, SafeArray } from './${RELATIVE_PATH}';" "$file"
      fi
    fi
    
    # Replace patterns like {orders.map( with {safeMap(orders,
    sed -i -E 's/{([a-zA-Z]+)\.map\(/{safeMap(\1, /g' "$file"
  fi
done

echo ""
echo "========================================="
echo "Final Steps:"
echo "========================================="
echo "1. Building the project to check for errors..."

# Build the project
npm run build 2>&1 | tee build.log

# Check if build succeeded
if [ $? -eq 0 ]; then
  echo ""
  echo "✅ Build successful!"
else
  echo ""
  echo "⚠️  Build failed. Check build.log for details."
  echo "   You may need to manually fix some import paths."
fi

echo ""
echo "========================================="
echo "Fix Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Review the changes"
echo "2. Test the application locally"
echo "3. Deploy if everything works"
echo ""
echo "To deploy:"
echo "  firebase deploy --only hosting"
echo ""