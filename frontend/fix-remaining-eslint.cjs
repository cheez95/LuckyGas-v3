const fs = require('fs');
const path = require('path');
const glob = require('glob');

// Function to fix remaining ESLint issues
function fixRemainingIssues(content, filePath) {
  let fixedContent = content;
  
  // 1. Fix unnecessary escape character in regex
  fixedContent = fixedContent.replace(/\\(\+)/g, '+');
  
  // 2. Fix _page parameters that are still unused
  // Look for test functions where _page is in parameters but page is used in body
  const lines = fixedContent.split('\n');
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    
    // Check if line has async function with _page parameter
    if (line.includes('async') && line.includes('_page')) {
      // Look ahead to see if 'page.' is used (not '_page.')
      let usesPage = false;
      let j = i + 1;
      const functionIndent = line.match(/^(\s*)/)[1];
      
      while (j < lines.length && j < i + 50) { // Check next 50 lines max
        const checkLine = lines[j];
        
        // If we hit another function at same or less indentation, stop
        if (checkLine.match(new RegExp(`^${functionIndent}(test|it|describe|\\})`))) {
          break;
        }
        
        if (checkLine.includes('page.') && !checkLine.includes('_page.')) {
          usesPage = true;
          break;
        }
        j++;
      }
      
      if (usesPage) {
        // Remove underscore from _page
        lines[i] = lines[i].replace(/_page/g, 'page');
      }
    }
  }
  
  fixedContent = lines.join('\n');
  
  // 3. Fix unused context parameters - remove underscore if context is used
  fixedContent = fixedContent.replace(/context:\s*_context/g, (match, offset) => {
    // Check if context is used in the function body
    const functionStart = fixedContent.lastIndexOf('async', offset);
    const functionEnd = fixedContent.indexOf('\n  });', offset);
    
    if (functionStart !== -1 && functionEnd !== -1) {
      const functionBody = fixedContent.substring(functionStart, functionEnd);
      if (functionBody.includes('context.') && !functionBody.includes('_context.')) {
        return 'context';
      }
    }
    return match;
  });
  
  // 4. Fix specific unused variables
  if (filePath.includes('visual-regression.spec.ts')) {
    // Comment out unused _isConnected variable
    fixedContent = fixedContent.replace(
      /const\s+_isConnected\s*=\s*[^;]+;/g,
      '// const _isConnected = ...; // Removed - unused'
    );
  }
  
  return fixedContent;
}

// Find all test files
const testFiles = glob.sync('e2e/**/*.spec.ts', { 
  ignore: ['**/node_modules/**'],
  cwd: __dirname
});

console.log(`Fixing remaining ESLint issues in ${testFiles.length} files...\n`);

let totalFixed = 0;

testFiles.forEach(file => {
  const filePath = path.join(__dirname, file);
  
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    const fixedContent = fixRemainingIssues(content, filePath);
    
    if (content !== fixedContent) {
      fs.writeFileSync(filePath, fixedContent);
      console.log(`✅ Fixed ${file}`);
      totalFixed++;
    }
  } catch (error) {
    console.error(`❌ Error processing ${file}:`, error.message);
  }
});

// Also fix the specific contract test file with regex issue
const contractTestPath = path.join(__dirname, 'e2e/api/contract-tests.spec.ts');
if (fs.existsSync(contractTestPath)) {
  try {
    let content = fs.readFileSync(contractTestPath, 'utf-8');
    // Fix the unnecessary escape character
    content = content.replace(/09\\d{2}-\\d{3}-\\d{3}\|0\\d-\\d{4}-\\d{4}/g, '09\\d{2}-\\d{3}-\\d{3}|0\\d-\\d{4}-\\d{4}');
    fs.writeFileSync(contractTestPath, content);
    console.log(`✅ Fixed contract-tests.spec.ts regex issue`);
  } catch (error) {
    console.error('❌ Error fixing contract test:', error.message);
  }
}

console.log(`\n✨ Done! Fixed ${totalFixed} files.`);