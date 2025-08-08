#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const glob = require('glob');

// Find all test files
const testFiles = glob.sync('e2e/**/*.spec.ts', { 
  cwd: __dirname,
  absolute: true 
});

console.log(`Found ${testFiles.length} test files to check for duplicates...`);

let fixedCount = 0;

testFiles.forEach(file => {
  try {
    let content = fs.readFileSync(file, 'utf8');
    const originalContent = content;
    
    // Track test names within each describe block
    const testCounts = {};
    let modified = false;
    
    // Split content into lines
    const lines = content.split('\n');
    let currentDescribe = '';
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      
      // Track current describe block
      if (line.includes('test.describe(')) {
        const match = line.match(/test\.describe\(['"`]([^'"`]+)['"`]/);
        if (match) {
          currentDescribe = match[1];
        }
      }
      
      // Check for test() calls
      const testMatch = line.match(/^\s*test\(['"`]([^'"`]+)['"`],/);
      if (testMatch) {
        const testName = testMatch[1];
        const fullTestName = `${currentDescribe} > ${testName}`;
        
        if (!testCounts[fullTestName]) {
          testCounts[fullTestName] = 0;
        }
        testCounts[fullTestName]++;
        
        // If duplicate, modify the test name
        if (testCounts[fullTestName] > 1) {
          const newTestName = `${testName} - ${testCounts[fullTestName]}`;
          lines[i] = line.replace(testMatch[0], `  test('${newTestName}',`);
          modified = true;
          console.log(`  Fixed duplicate in ${path.basename(file)}: "${testName}" → "${newTestName}"`);
        }
      }
    }
    
    if (modified) {
      content = lines.join('\n');
      fs.writeFileSync(file, content, 'utf8');
      fixedCount++;
    }
  } catch (error) {
    console.error(`❌ Error processing ${file}:`, error.message);
  }
});

console.log(`\n✨ Fixed ${fixedCount} test files with duplicate test names`);