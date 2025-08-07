#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const glob = require('glob');

// Find all test files with syntax errors
const testFiles = glob.sync('e2e/**/*.spec.ts', { 
  cwd: __dirname,
  absolute: true 
});

console.log(`Found ${testFiles.length} test files to check...`);

let fixedCount = 0;

testFiles.forEach(file => {
  try {
    let content = fs.readFileSync(file, 'utf8');
    const originalContent = content;
    
    // Fix test($1, ...) pattern
    content = content.replace(/test\(\$1,/g, 'test(\'should complete the test\',');
    
    // Fix test.skip($1, ...) pattern
    content = content.replace(/test\.skip\(\$1,/g, 'test.skip(\'should complete the test\',');
    
    // Fix specific test descriptions based on context
    if (file.includes('delivery-tracking')) {
      content = content.replace(/test\('should complete the test',/g, 'test(\'should track delivery status in real-time\',');
    } else if (file.includes('order-flow')) {
      content = content.replace(/test\('should complete the test',/g, 'test(\'should complete order creation flow\',');
    } else if (file.includes('route-optimization')) {
      content = content.replace(/test\('should complete the test',/g, 'test(\'should optimize delivery routes\',');
    } else if (file.includes('visual-regression')) {
      content = content.replace(/test\('should complete the test',/g, 'test(\'should match visual snapshot\',');
    } else if (file.includes('performance')) {
      content = content.replace(/test\('should complete the test',/g, 'test(\'should meet performance benchmarks\',');
    } else if (file.includes('error-recovery')) {
      content = content.replace(/test\('should complete the test',/g, 'test(\'should recover from errors gracefully\',');
    } else if (file.includes('comprehensive-frontend')) {
      content = content.replace(/test\('should complete the test',/g, 'test(\'should pass comprehensive frontend tests\',');
    } else if (file.includes('simple-login')) {
      content = content.replace(/test\('should complete the test',/g, 'test(\'should login successfully\',');
    }
    
    if (content !== originalContent) {
      fs.writeFileSync(file, content, 'utf8');
      console.log(`✅ Fixed: ${path.basename(file)}`);
      fixedCount++;
    }
  } catch (error) {
    console.error(`❌ Error processing ${file}:`, error.message);
  }
});

console.log(`\n✨ Fixed ${fixedCount} test files with syntax errors`);