const fs = require('fs');
const path = require('path');
const glob = require('glob');

// Function to fix test descriptions
function fixTestDescriptions(content) {
  // Fix test descriptions that were replaced with $1
  // This regex captures the full test call and replaces just the parameter part
  const fixedContent = content.replace(
    /test\(\$1, async \(\{ page: _page \}\) =>/g,
    (match, offset) => {
      // Look backwards to find the actual test description
      // Find the previous test( and extract the description
      let startIndex = offset;
      let parenCount = 0;
      let inString = false;
      let stringChar = null;
      
      // Search backwards for the test description
      for (let i = offset - 1; i >= 0; i--) {
        const char = content[i];
        
        if (inString) {
          if (char === stringChar && content[i-1] !== '\\') {
            inString = false;
          }
          continue;
        }
        
        if (char === '"' || char === "'") {
          inString = true;
          stringChar = char;
          continue;
        }
        
        if (char === ')') parenCount++;
        if (char === '(') {
          parenCount--;
          if (parenCount === -1 && content.substring(i-4, i) === 'test') {
            // Found the start of the test call
            // Now extract the description
            let descStart = i + 1;
            let descEnd = offset - 1;
            
            // Find the actual description between test( and the comma
            for (let j = descStart; j < descEnd; j++) {
              if (content[j] === ',') {
                descEnd = j;
                break;
              }
            }
            
            const description = content.substring(descStart, descEnd).trim();
            if (description && description !== '$1') {
              return `test(${description}, async ({ page: _page }) =>`;
            }
            break;
          }
        }
      }
      
      // If we couldn't find a description, return the original
      return match;
    }
  );
  
  return fixedContent;
}

// Read and process specific files that need fixing
const filesToFix = [
  'e2e/localization.spec.ts',
  'e2e/inspect-customer-form.spec.ts',
  'e2e/driver-mobile.spec.ts',
  'e2e/customer.spec.ts',
  'e2e-backend/auth.spec.ts',
  'e2e-backend/critical-flow.spec.ts',
  'e2e-backend/dashboard.spec.ts',
  'e2e-backend/offline.spec.ts',
  'e2e-backend/order.spec.ts',
  'e2e-backend/performance.spec.ts',
  'e2e-backend/rbac.spec.ts',
  'e2e-backend/route.spec.ts'
];

console.log('Reading original test files to extract descriptions...');

// First, let's read the original content from git to get the correct descriptions
const { execSync } = require('child_process');

filesToFix.forEach(file => {
  const filePath = path.join(__dirname, file);
  
  if (!fs.existsSync(filePath)) {
    console.log(`Skipping ${file} - file not found`);
    return;
  }
  
  try {
    // Get the original file content from git
    const originalContent = execSync(`git show HEAD:frontend/${file}`, { encoding: 'utf-8' });
    
    // Extract test descriptions from original
    const testDescriptions = [];
    const testRegex = /test\(['"`]([^'"`]+)['"`],\s*async\s*\(\s*{\s*page(?:,\s*\w+)*\s*}\s*\)\s*=>/g;
    let match;
    
    while ((match = testRegex.exec(originalContent)) !== null) {
      testDescriptions.push(match[1]);
    }
    
    // Read current file
    let currentContent = fs.readFileSync(filePath, 'utf-8');
    
    // Replace $1 with actual descriptions
    let descIndex = 0;
    currentContent = currentContent.replace(
      /test\(\$1, async \(\{ page: _page(.*?)\}\) =>/g,
      (match, params) => {
        if (descIndex < testDescriptions.length) {
          const desc = testDescriptions[descIndex++];
          return `test('${desc}', async ({ page: _page${params}}) =>`;
        }
        return match;
      }
    );
    
    // Write the fixed content
    fs.writeFileSync(filePath, currentContent);
    console.log(`✅ Fixed ${file} - restored ${descIndex} test descriptions`);
    
  } catch (error) {
    console.error(`❌ Error processing ${file}:`, error.message);
    
    // Fallback: manually fix common test descriptions based on context
    let content = fs.readFileSync(filePath, 'utf-8');
    
    // Fix based on file name and common patterns
    if (file.includes('localization')) {
      content = fixLocalizationTests(content);
    } else if (file.includes('customer')) {
      content = fixCustomerTests(content);
    } else if (file.includes('driver-mobile')) {
      content = fixDriverMobileTests(content);
    }
    
    fs.writeFileSync(filePath, content);
    console.log(`✅ Fixed ${file} using fallback patterns`);
  }
});

// Fallback functions for specific test files
function fixLocalizationTests(content) {
  const replacements = [
    { line: 25, desc: 'should display login form in Traditional Chinese' },
    { line: 40, desc: 'should show validation messages in Chinese' },
    { line: 59, desc: 'should display dashboard with Chinese text' },
    { line: 81, desc: 'should show all menu items in Chinese' },
    { line: 97, desc: 'should display customer page in Chinese' },
    { line: 123, desc: 'should display order page in Chinese' },
    { line: 140, desc: 'should display route page in Chinese' },
    { line: 157, desc: 'should use Taiwan date format (YYYY/MM/DD)' },
    { line: 189, desc: 'should display currency in NT$' },
    { line: 198, desc: 'should show customer form labels in Chinese' },
    { line: 224, desc: 'should display product names in Chinese' },
    { line: 247, desc: 'should show success message in Chinese' },
    { line: 256, desc: 'should display phone numbers in Taiwan format' },
    { line: 269, desc: 'should show tooltips in Chinese' },
    { line: 283, desc: 'should display logout confirmation in Chinese' },
    { line: 301, desc: 'should support language switching' }
  ];
  
  return applyReplacements(content, replacements);
}

function fixCustomerTests(content) {
  const replacements = [
    { line: 26, desc: 'should display customer list page' },
    { line: 38, desc: 'should create new customer successfully' },
    { line: 67, desc: 'should edit existing customer' },
    { line: 95, desc: 'should delete customer' },
    { line: 110, desc: 'should search customers by name' },
    { line: 131, desc: 'should handle pagination correctly' },
    { line: 151, desc: 'should validate required fields' },
    { line: 169, desc: 'should prevent duplicate customer codes' },
    { line: 184, desc: 'should handle bulk operations' },
    { line: 196, desc: 'should navigate to customer detail page' },
    { line: 206, desc: 'should export customer data' },
    { line: 223, desc: 'should be responsive on mobile' },
    { line: 235, desc: 'should validate phone number formats' },
    { line: 253, desc: 'should filter by area' },
    { line: 270, desc: 'should display customer inventory' },
    { line: 284, desc: 'should handle network errors gracefully' }
  ];
  
  return applyReplacements(content, replacements);
}

function fixDriverMobileTests(content) {
  const replacements = [
    { line: 34, desc: 'should display mobile interface correctly' },
    { line: 61, desc: 'should show assigned routes' },
    { line: 70, desc: 'should display route details' },
    { line: 85, desc: 'should open delivery completion modal' },
    { line: 103, desc: 'should capture signature with touch' },
    { line: 134, desc: 'should compress photos before upload' },
    { line: 153, desc: 'should handle multiple photo uploads' },
    { line: 191, desc: 'should work offline and sync when online' },
    { line: 232, desc: 'should persist offline queue across sessions' },
    { line: 256, desc: 'should validate completion requirements' },
    { line: 282, desc: 'should handle screen rotation' },
    { line: 296, desc: 'should display optimized route information' },
    { line: 313, desc: 'should handle network interruptions gracefully' },
    { line: 345, desc: 'should display interface in Traditional Chinese' },
    { line: 371, desc: 'should handle logout correctly' },
    { line: 383, desc: 'should load quickly on slow networks' },
    { line: 410, desc: 'should handle large route lists efficiently' }
  ];
  
  return applyReplacements(content, replacements);
}

function applyReplacements(content, replacements) {
  const lines = content.split('\n');
  
  replacements.forEach(({ line, desc }) => {
    // Find the line with test($1
    for (let i = line - 5; i < line + 5 && i < lines.length; i++) {
      if (lines[i] && lines[i].includes('test($1,')) {
        lines[i] = lines[i].replace('test($1,', `test('${desc}',`);
        break;
      }
    }
  });
  
  return lines.join('\n');
}

console.log('\nDone fixing test descriptions!');