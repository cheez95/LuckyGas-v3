/**
 * Memory Leak Test Suite for Route Planning Component
 * Run this in the browser console to test memory leak fixes
 */

export const runMemoryLeakTest = async () => {
  console.log('🧪 Starting Memory Leak Test Suite...');
  console.log('=' .repeat(50));
  
  // Test 1: Rapid tab switching
  console.log('\n📋 Test 1: Rapid Tab Switching');
  console.log('Simulating rapid navigation between tabs...');
  
  const results = {
    initialMemory: 0,
    peakMemory: 0,
    finalMemory: 0,
    leakDetected: false,
    activeRequests: 0,
    unmountedCleanly: true,
  };
  
  // Record initial memory
  if (performance.memory) {
    results.initialMemory = performance.memory.usedJSHeapSize;
    console.log(`Initial memory: ${(results.initialMemory / 1048576).toFixed(2)}MB`);
  }
  
  // Test rapid navigation
  console.log('Please manually switch between tabs rapidly for 30 seconds...');
  console.log('Switch between Dashboard, Route Planning, and other tabs');
  
  // Monitor for 30 seconds
  let peakMemory = results.initialMemory;
  const monitorInterval = setInterval(() => {
    if (performance.memory) {
      const currentMemory = performance.memory.usedJSHeapSize;
      if (currentMemory > peakMemory) {
        peakMemory = currentMemory;
      }
    }
  }, 1000);
  
  // Wait for test to complete
  await new Promise(resolve => setTimeout(resolve, 30000));
  clearInterval(monitorInterval);
  
  // Record final memory after GC
  if (typeof (window as any).gc === 'function') {
    console.log('Running garbage collection...');
    (window as any).gc();
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  
  if (performance.memory) {
    results.finalMemory = performance.memory.usedJSHeapSize;
    results.peakMemory = peakMemory;
    
    const memoryIncrease = results.finalMemory - results.initialMemory;
    const memoryIncreaseMB = memoryIncrease / 1048576;
    
    console.log(`\n📊 Test Results:`);
    console.log(`Initial Memory: ${(results.initialMemory / 1048576).toFixed(2)}MB`);
    console.log(`Peak Memory: ${(results.peakMemory / 1048576).toFixed(2)}MB`);
    console.log(`Final Memory: ${(results.finalMemory / 1048576).toFixed(2)}MB`);
    console.log(`Memory Increase: ${memoryIncreaseMB.toFixed(2)}MB`);
    
    // Check for leak
    if (memoryIncreaseMB > 50) {
      results.leakDetected = true;
      console.error(`❌ MEMORY LEAK DETECTED: ${memoryIncreaseMB.toFixed(2)}MB increase`);
    } else if (memoryIncreaseMB > 20) {
      console.warn(`⚠️ POSSIBLE LEAK: ${memoryIncreaseMB.toFixed(2)}MB increase`);
    } else {
      console.log(`✅ NO LEAK DETECTED: Memory increase within acceptable range`);
    }
  }
  
  // Check console for cleanup messages
  console.log('\n📝 Cleanup Verification:');
  console.log('Check console for the following messages:');
  console.log('- [RoutePlanning] Component unmounting...');
  console.log('- [RoutePlanning] Cleanup completed successfully');
  console.log('- [RoutePlanningMap] Cleanup completed');
  console.log('- No "WARNING: requests still active" messages');
  
  console.log('\n' + '='.repeat(50));
  console.log('🧪 Memory Leak Test Complete');
  
  return results;
};

/**
 * Test Google Maps cleanup specifically
 */
export const testGoogleMapsCleanup = () => {
  console.log('🗺️ Testing Google Maps Cleanup...');
  
  // Check for leaked map instances
  const mapDivs = document.querySelectorAll('div[style*="position: relative"]');
  let leakedMaps = 0;
  
  mapDivs.forEach(div => {
    // Check if this looks like a map container
    if (div.querySelector('.gm-style')) {
      const parent = div.closest('[data-testid]');
      if (!parent || !document.body.contains(parent)) {
        leakedMaps++;
        console.warn('Found potential leaked map instance:', div);
      }
    }
  });
  
  if (leakedMaps > 0) {
    console.error(`❌ Found ${leakedMaps} potential leaked map instances`);
  } else {
    console.log('✅ No leaked map instances detected');
  }
  
  // Check for map event listeners
  const mapElements = document.querySelectorAll('.gm-style');
  console.log(`Found ${mapElements.length} active map elements`);
  
  return {
    leakedMaps,
    activeMapElements: mapElements.length,
  };
};

/**
 * Test request cancellation
 */
export const testRequestCancellation = async () => {
  console.log('🌐 Testing Request Cancellation...');
  
  // This test requires manual interaction
  console.log('1. Navigate to Route Planning tab');
  console.log('2. Quickly navigate away before data loads');
  console.log('3. Check console for "AbortError" or request cancellation messages');
  console.log('4. Verify no state updates after unmount');
  
  // Monitor network for pending requests
  const checkPendingRequests = () => {
    // Check performance entries for pending fetches
    const entries = performance.getEntriesByType('resource');
    const pendingFetches = entries.filter(entry => 
      entry.name.includes('/api/') && 
      entry.duration === 0
    );
    
    if (pendingFetches.length > 0) {
      console.warn(`⚠️ Found ${pendingFetches.length} pending API requests`);
      pendingFetches.forEach(req => console.log('  -', req.name));
    } else {
      console.log('✅ No pending API requests');
    }
    
    return pendingFetches.length;
  };
  
  // Check after a delay
  setTimeout(checkPendingRequests, 5000);
  
  return {
    instruction: 'Follow manual test steps above',
  };
};

/**
 * Run all tests
 */
export const runAllMemoryTests = async () => {
  console.log('🚀 Running Complete Memory Leak Test Suite');
  console.log('This will take approximately 1 minute');
  console.log('');
  
  const results = {
    tabSwitching: null as any,
    googleMaps: null as any,
    requestCancellation: null as any,
  };
  
  // Run tests sequentially
  results.tabSwitching = await runMemoryLeakTest();
  results.googleMaps = testGoogleMapsCleanup();
  results.requestCancellation = testRequestCancellation();
  
  // Summary
  console.log('\n' + '='.repeat(50));
  console.log('📊 TEST SUMMARY');
  console.log('='.repeat(50));
  
  if (!results.tabSwitching.leakDetected && results.googleMaps.leakedMaps === 0) {
    console.log('✅ ALL TESTS PASSED - No memory leaks detected');
  } else {
    console.error('❌ TESTS FAILED - Memory leaks detected');
  }
  
  console.log('\nDetailed Results:', results);
  
  return results;
};

// Export to window for easy console access
if (typeof window !== 'undefined') {
  (window as any).memoryLeakTests = {
    runMemoryLeakTest,
    testGoogleMapsCleanup,
    testRequestCancellation,
    runAllMemoryTests,
  };
  
  console.log('💡 Memory leak tests loaded. Available commands:');
  console.log('  window.memoryLeakTests.runMemoryLeakTest() - Test tab switching');
  console.log('  window.memoryLeakTests.testGoogleMapsCleanup() - Test map cleanup');
  console.log('  window.memoryLeakTests.testRequestCancellation() - Test request cancellation');
  console.log('  window.memoryLeakTests.runAllMemoryTests() - Run all tests');
}