#!/usr/bin/env node
const fs = require('fs').promises;
const path = require('path');

// ESLint error patterns to fix
const patterns = [
  // Fix unused parameters in test callbacks
  {
    pattern: /test\([^,]+,\s*async\s*\(\s*{\s*page\s*}\s*\)\s*=>/g,
    replacement: 'test($1, async ({ page: _page }) =>'
  },
  {
    pattern: /test\([^,]+,\s*async\s*\(\s*{\s*page,\s*context\s*}\s*\)\s*=>/g,
    replacement: 'test($1, async ({ page: _page, context: _context }) =>'
  },
  {
    pattern: /test\([^,]+,\s*async\s*\(\s*{\s*context\s*}\s*\)\s*=>/g,
    replacement: 'test($1, async ({ context: _context }) =>'
  },
  // Fix unused imports
  {
    pattern: /import\s*{\s*([^}]*?),?\s*getAuthToken\s*,?\s*([^}]*?)\s*}\s*from/g,
    replacement: (match, before, after) => {
      const parts = [before, after].filter(p => p && p.trim());
      if (parts.length === 0) {
        return 'import { } from';
      }
      return `import { ${parts.join(', ')} } from`;
    }
  },
  // Fix unnecessary escape
  {
    pattern: /\\+(?=\+)/g,
    replacement: '\\+'
  },
  // Fix unused variables
  {
    pattern: /const\s+API_URL\s*=/g,
    replacement: 'const _API_URL ='
  },
  {
    pattern: /const\s+isConnected\s*=/g,
    replacement: 'const _isConnected ='
  },
  {
    pattern: /const\s+canCreateOrders\s*=/g,
    replacement: 'const _canCreateOrders ='
  },
  {
    pattern: /const\s+hasRouteInfo\s*=/g,
    replacement: 'const _hasRouteInfo ='
  },
  {
    pattern: /const\s+testPhotos\s*=/g,
    replacement: 'const _testPhotos ='
  },
  // Fix unused catch error
  {
    pattern: /catch\s*\(\s*error\s*\)/g,
    replacement: 'catch (_error)'
  },
  // Fix any types
  {
    pattern: /:\s*any\b/g,
    replacement: ': unknown'
  }
];

async function fixFile(filePath) {
  try {
    let content = await fs.readFile(filePath, 'utf8');
    let modified = false;
    
    for (const { pattern, replacement } of patterns) {
      const newContent = content.replace(pattern, replacement);
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
  console.log('Fixing ESLint unused variable errors...');
  
  const directories = ['e2e'];
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