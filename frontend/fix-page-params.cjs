const fs = require('fs');
const path = require('path');
const glob = require('glob');

// Function to fix page parameter usage
function fixPageParams(content) {
  // This regex finds test functions where _page is unused but page is used
  // We need to remove the underscore from the parameter and keep using page
  const fixedContent = content.replace(
    /test\(([^,]+),\s*async\s*\(\s*{\s*page:\s*_page([^}]*)\}\s*\)\s*=>/g,
    (match, testName, otherParams) => {
      // Check if the test body uses 'page' (not '_page')
      const testBodyStart = content.indexOf(match) + match.length;
      const nextTestIndex = content.indexOf('\n  test(', testBodyStart);
      const testBody = nextTestIndex > -1 ? 
        content.substring(testBodyStart, nextTestIndex) : 
        content.substring(testBodyStart);
      
      // If the test body uses 'page' (not '_page'), remove the underscore
      if (testBody.includes('page.') && !testBody.includes('_page.')) {
        return `test(${testName}, async ({ page${otherParams}}) =>`;
      }
      return match;
    }
  );
  
  return fixedContent;
}

// Find all spec files
const specFiles = glob.sync('e2e/**/*.spec.ts', { 
  ignore: ['**/node_modules/**'],
  cwd: __dirname
});

console.log(`Found ${specFiles.length} test files to check\n`);

let totalFixed = 0;

specFiles.forEach(file => {
  const filePath = path.join(__dirname, file);
  
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    const fixedContent = fixPageParams(content);
    
    if (content !== fixedContent) {
      fs.writeFileSync(filePath, fixedContent);
      
      // Count how many fixes were made
      const originalCount = (content.match(/page: _page/g) || []).length;
      const fixedCount = (fixedContent.match(/page: _page/g) || []).length;
      const fixCount = originalCount - fixedCount;
      
      console.log(`✅ Fixed ${file} - corrected ${fixCount} parameter(s)`);
      totalFixed += fixCount;
    }
  } catch (error) {
    console.error(`❌ Error processing ${file}:`, error.message);
  }
});

console.log(`\nTotal fixes: ${totalFixed} parameters corrected`);