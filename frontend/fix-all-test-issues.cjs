const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// List of all test files to fix
const testFiles = [
  'e2e/auth.spec.ts',
  'e2e/comprehensive-frontend-test.spec.ts', 
  'e2e/comprehensive-quality-validation.spec.ts',
  'e2e/customer-management.spec.ts',
  'e2e/offline-error-handling.spec.ts',
  'e2e/predictions-routes.spec.ts',
  'e2e/quick-test.spec.ts',
  'e2e/route-optimization-basic.spec.ts',
  'e2e/route-optimization-validation.spec.ts',
  'e2e/simple-login.spec.ts',
  'e2e/websocket-basic.spec.ts',
  'e2e/websocket-realtime.spec.ts',
  'e2e/critical/delivery-tracking.spec.ts',
  'e2e/critical/order-flow.spec.ts',
  'e2e/critical/route-optimization.spec.ts',
  'e2e/performance/performance.spec.ts',
  'e2e/resilience/error-recovery.spec.ts',
  'e2e/visual/visual-regression.spec.ts'
];

console.log('Fixing test files...\n');

let totalFixed = 0;
let totalDescriptions = 0;

testFiles.forEach(file => {
  const filePath = path.join(__dirname, file);
  
  if (!fs.existsSync(filePath)) {
    console.log(`⚠️  Skipping ${file} - file not found`);
    return;
  }
  
  try {
    // Get the original file content from git
    let originalContent;
    try {
      originalContent = execSync(`git show HEAD:frontend/${file}`, { encoding: 'utf-8' });
    } catch (gitError) {
      console.log(`⚠️  Could not get git history for ${file}, using fallback`);
      originalContent = '';
    }
    
    // Read current file
    let currentContent = fs.readFileSync(filePath, 'utf-8');
    
    // Extract test descriptions from original
    const testDescriptions = [];
    if (originalContent) {
      const testRegex = /test\(['"`]([^'"`]+)['"`],\s*async\s*\(\s*{\s*page(?:,\s*\w+)*\s*}\s*\)\s*=>/g;
      let match;
      
      while ((match = testRegex.exec(originalContent)) !== null) {
        testDescriptions.push(match[1]);
      }
    }
    
    // Fix test descriptions and parameters
    let fixedContent = currentContent;
    let descIndex = 0;
    
    // First pass: fix $1 placeholders with actual descriptions
    fixedContent = fixedContent.replace(
      /test\(\$1,\s*async\s*\(\s*{\s*page:\s*_page([^}]*)\}\s*\)\s*=>/g,
      (match, otherParams) => {
        if (descIndex < testDescriptions.length) {
          const desc = testDescriptions[descIndex++];
          return `test('${desc}', async ({ page: _page${otherParams}}) =>`;
        }
        return match;
      }
    );
    
    // Second pass: remove underscore from _page where page is used in the test body
    const lines = fixedContent.split('\n');
    let inTest = false;
    let testStartLine = -1;
    let testIndent = '';
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      
      // Detect test start
      if (line.includes('test(') && line.includes('async') && line.includes('_page')) {
        inTest = true;
        testStartLine = i;
        testIndent = line.match(/^(\s*)/)[1];
        
        // Look ahead to see if the test body uses 'page' (not '_page')
        let usesPage = false;
        let j = i + 1;
        
        while (j < lines.length) {
          const testLine = lines[j];
          
          // Check if we've exited the test
          if (testLine.startsWith(testIndent + 'test(') || 
              testLine.startsWith(testIndent + '});') ||
              (testLine.trim() === '});' && !testLine.startsWith(testIndent + '  '))) {
            break;
          }
          
          // Check if line uses 'page.' but not '_page.'
          if (testLine.includes('page.') && !testLine.includes('_page.')) {
            usesPage = true;
            break;
          }
          
          j++;
        }
        
        // If test uses 'page', remove the underscore
        if (usesPage) {
          lines[i] = lines[i].replace('page: _page', 'page');
        }
      }
    }
    
    fixedContent = lines.join('\n');
    
    // Third pass: fix unused _context parameters
    fixedContent = fixedContent.replace(
      /context:\s*_context/g,
      'context'
    );
    
    // Fourth pass: remove unused variable assignments
    fixedContent = fixedContent.replace(
      /const\s+_API_URL\s*=\s*['"`][^'"`]+['"`];?/g,
      '// const _API_URL removed - unused'
    );
    
    // Count fixes
    const fixCount = (currentContent.match(/\$1/g) || []).length - (fixedContent.match(/\$1/g) || []).length;
    const paramFixCount = (currentContent.match(/_page/g) || []).length - (fixedContent.match(/_page/g) || []).length;
    
    if (currentContent !== fixedContent) {
      fs.writeFileSync(filePath, fixedContent);
      console.log(`✅ Fixed ${file} - ${fixCount} descriptions, ${paramFixCount} parameters`);
      totalFixed++;
      totalDescriptions += fixCount;
    } else {
      console.log(`⏭️  No changes needed for ${file}`);
    }
    
  } catch (error) {
    console.error(`❌ Error processing ${file}:`, error.message);
  }
});

console.log(`\n✨ Done! Fixed ${totalFixed} files with ${totalDescriptions} test descriptions restored.`);