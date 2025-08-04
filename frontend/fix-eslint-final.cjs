const fs = require('fs');
const path = require('path');
const glob = require('glob');

// Function to fix all remaining ESLint issues
function fixAllIssues(content, filePath) {
  let fixedContent = content;
  
  // Split into lines for line-by-line processing
  const lines = fixedContent.split('\n');
  
  // Track if we're inside a test function
  let inTestFunction = false;
  let testFunctionIndent = '';
  let currentTestParams = {};
  let testStartLine = -1;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmedLine = line.trim();
    
    // Detect test function start
    if (trimmedLine.includes('test(') && line.includes('async') && line.includes('=>')) {
      inTestFunction = true;
      testStartLine = i;
      testFunctionIndent = line.match(/^(\s*)/)[1];
      currentTestParams = {};
      
      // Extract parameters from the test function
      const paramMatch = line.match(/async\s*\(\s*{([^}]+)}\s*\)/);
      if (paramMatch) {
        const params = paramMatch[1].split(',').map(p => p.trim());
        params.forEach(param => {
          const [name, alias] = param.split(':').map(p => p.trim());
          if (alias && alias.startsWith('_')) {
            currentTestParams[alias] = name;
          } else {
            currentTestParams[name] = name;
          }
        });
      }
    }
    
    // Detect test function end
    if (inTestFunction && trimmedLine === '});' && line.startsWith(testFunctionIndent)) {
      // Now check if we need to fix the parameters
      const testBody = lines.slice(testStartLine + 1, i).join('\n');
      
      // Check which parameters are actually used
      Object.entries(currentTestParams).forEach(([paramName, originalName]) => {
        if (paramName.startsWith('_')) {
          const nonUnderscoreName = paramName.substring(1);
          // Check if the non-underscore version is used in the body
          const regex = new RegExp(`\\b${nonUnderscoreName}\\b(?!:)`, 'g');
          if (regex.test(testBody)) {
            // Replace _param with param in the function signature
            lines[testStartLine] = lines[testStartLine].replace(
              new RegExp(`${originalName}:\\s*${paramName}\\b`),
              originalName
            );
          }
        }
      });
      
      inTestFunction = false;
    }
  }
  
  fixedContent = lines.join('\n');
  
  // Fix specific issues
  
  // 1. Remove unused imports
  fixedContent = fixedContent.replace(
    /import\s*{\s*([^}]*)\s*}\s*from\s*['"][^'"]+['"]/g,
    (match, imports) => {
      const importList = imports.split(',').map(i => i.trim());
      const usedImports = importList.filter(imp => {
        // Check if this import is used in the file (excluding the import line itself)
        const importRegex = new RegExp(`\\b${imp}\\b`, 'g');
        const matches = fixedContent.match(importRegex);
        return matches && matches.length > 1; // More than just the import line
      });
      
      if (usedImports.length === 0) {
        return ''; // Remove the entire import
      } else if (usedImports.length < importList.length) {
        return match.replace(imports, usedImports.join(', '));
      }
      return match;
    }
  );
  
  // 2. Fix unused variable assignments
  if (filePath.includes('visual-regression.spec.ts')) {
    fixedContent = fixedContent.replace(
      /const\s+_isConnected\s*=\s*await[^;]+;/g,
      '// Removed unused _isConnected variable'
    );
  }
  
  // 3. Clean up empty lines from removed imports
  fixedContent = fixedContent.replace(/\n\n\n+/g, '\n\n');
  
  return fixedContent;
}

// Find all test files
const testFiles = glob.sync('e2e/**/*.spec.ts', { 
  ignore: ['**/node_modules/**'],
  cwd: __dirname
});

console.log(`Performing final ESLint fixes on ${testFiles.length} files...\n`);

let totalFixed = 0;
const errors = [];

testFiles.forEach(file => {
  const filePath = path.join(__dirname, file);
  
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    const fixedContent = fixAllIssues(content, filePath);
    
    if (content !== fixedContent) {
      fs.writeFileSync(filePath, fixedContent);
      console.log(`✅ Fixed ${file}`);
      totalFixed++;
    }
  } catch (error) {
    errors.push({ file, error: error.message });
  }
});

// Special handling for specific files with known issues
const specialFiles = [
  {
    path: 'e2e/auth.spec.ts',
    fixes: [
      { pattern: /page:\s*_page/g, replacement: 'page' }
    ]
  },
  {
    path: 'e2e/comprehensive-frontend-test.spec.ts', 
    fixes: [
      { pattern: /page:\s*_page/g, replacement: 'page' },
      { pattern: /context:\s*_context/g, replacement: 'context' }
    ]
  },
  {
    path: 'e2e/comprehensive-quality-validation.spec.ts',
    fixes: [
      { pattern: /context(?!:)/g, replacement: 'context' }
    ]
  }
];

specialFiles.forEach(({ path: specialPath, fixes }) => {
  const fullPath = path.join(__dirname, specialPath);
  if (fs.existsSync(fullPath)) {
    try {
      let content = fs.readFileSync(fullPath, 'utf-8');
      let changed = false;
      
      fixes.forEach(({ pattern, replacement }) => {
        const newContent = content.replace(pattern, replacement);
        if (newContent !== content) {
          content = newContent;
          changed = true;
        }
      });
      
      if (changed) {
        fs.writeFileSync(fullPath, content);
        console.log(`✅ Applied special fixes to ${specialPath}`);
        totalFixed++;
      }
    } catch (error) {
      errors.push({ file: specialPath, error: error.message });
    }
  }
});

if (errors.length > 0) {
  console.log('\n❌ Errors encountered:');
  errors.forEach(({ file, error }) => {
    console.log(`  ${file}: ${error}`);
  });
}

console.log(`\n✨ Done! Fixed ${totalFixed} files.`);