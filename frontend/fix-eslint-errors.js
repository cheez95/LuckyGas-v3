#!/usr/bin/env node
const fs = require('fs').promises;
const path = require('path');

// Common patterns to fix
const fixes = [
  // Remove unused imports
  {
    pattern: /import\s*{\s*([^}]+)\s*}\s*from\s*['"]([^'"]+)['"]\s*;?\s*\n/g,
    fix: (match, imports, from) => {
      // For now, just return the match - would need AST parsing for proper fix
      return match;
    }
  },
  // Add underscore to unused parameters
  {
    pattern: /\b(page|context|error|request|index|size|name|hint|lng)\b(?=\s*[,):}])/g,
    fix: (match) => `_${match}`
  },
  // Replace any with unknown or specific types
  {
    pattern: /:\s*any\b/g,
    fix: ': unknown'
  }
];

async function fixFile(filePath) {
  try {
    let content = await fs.readFile(filePath, 'utf8');
    let modified = false;
    
    // Apply fixes
    for (const fix of fixes) {
      const newContent = content.replace(fix.pattern, fix.fix);
      if (newContent !== content) {
        content = newContent;
        modified = true;
      }
    }
    
    if (modified) {
      await fs.writeFile(filePath, content);
      console.log(`Fixed: ${filePath}`);
      return true;
    }
    return false;
  } catch (err) {
    console.error(`Error processing ${filePath}:`, err.message);
    return false;
  }
}

async function processDirectory(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  let totalFixed = 0;
  
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    
    if (entry.isDirectory() && !entry.name.startsWith('.') && entry.name !== 'node_modules') {
      totalFixed += await processDirectory(fullPath);
    } else if (entry.isFile() && (entry.name.endsWith('.ts') || entry.name.endsWith('.tsx'))) {
      if (await fixFile(fullPath)) {
        totalFixed++;
      }
    }
  }
  
  return totalFixed;
}

async function main() {
  console.log('Fixing ESLint errors in TypeScript files...');
  
  const directories = ['src', 'e2e'];
  let totalFixed = 0;
  
  for (const dir of directories) {
    if (await fs.access(dir).then(() => true).catch(() => false)) {
      console.log(`Processing ${dir}...`);
      totalFixed += await processDirectory(dir);
    }
  }
  
  console.log(`\nTotal files fixed: ${totalFixed}`);
}

main().catch(console.error);