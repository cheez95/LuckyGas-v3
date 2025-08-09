/**
 * LuckyGas Token Injector Script
 * ================================
 * Emergency access script to bypass login issues
 * 
 * USAGE:
 * 1. Open the LuckyGas frontend in your browser
 * 2. Open browser console (F12)
 * 3. Copy and paste this entire script
 * 4. Press Enter
 * 5. You'll be logged in and redirected to dashboard
 */

(async function() {
    console.log('%c🚀 LuckyGas Token Injector Starting...', 'color: #667eea; font-size: 16px; font-weight: bold;');
    
    const BACKEND_URL = 'https://luckygas-backend-step4-yzoirwjj3q-de.a.run.app';
    const FRONTEND_URL = 'https://storage.googleapis.com/luckygas-frontend-prod';
    
    try {
        // Step 1: Get a fresh token
        console.log('📡 Requesting fresh token from backend...');
        
        const formData = new URLSearchParams({
            username: 'admin@luckygas.com',
            password: 'admin-password-2025'
        });
        
        const response = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok || !data.access_token) {
            throw new Error(`Login failed: ${data.detail || response.status}`);
        }
        
        const token = data.access_token;
        console.log('%c✅ Token received successfully!', 'color: #28a745; font-weight: bold;');
        console.log(`Token preview: ${token.substring(0, 50)}...`);
        
        // Step 2: Clear any existing auth data
        console.log('🧹 Clearing old authentication data...');
        const authKeys = ['token', 'auth_token', 'jwt', 'access_token', 'authToken', 'jwtToken'];
        authKeys.forEach(key => {
            if (localStorage.getItem(key)) {
                console.log(`  - Removed old ${key}`);
                localStorage.removeItem(key);
            }
        });
        
        // Step 3: Inject the new token
        console.log('💉 Injecting fresh token into localStorage...');
        authKeys.forEach(key => {
            localStorage.setItem(key, token);
            console.log(`  ✓ Set localStorage.${key}`);
        });
        
        // Step 4: Set user information
        console.log('👤 Setting user information...');
        const userInfo = {
            email: 'admin@luckygas.com',
            username: 'admin@luckygas.com',
            role: 'admin',
            isAuthenticated: true,
            token: token,
            loginTime: new Date().toISOString()
        };
        
        localStorage.setItem('user', JSON.stringify(userInfo));
        localStorage.setItem('userInfo', JSON.stringify(userInfo));
        localStorage.setItem('currentUser', JSON.stringify(userInfo));
        localStorage.setItem('isAuthenticated', 'true');
        localStorage.setItem('token_type', 'bearer');
        
        console.log('  ✓ User information set');
        
        // Step 5: Check current location
        const currentUrl = window.location.href;
        console.log(`📍 Current URL: ${currentUrl}`);
        
        // Step 6: Redirect to dashboard
        console.log('%c🎯 Authentication complete! Redirecting to dashboard...', 'color: #667eea; font-size: 14px; font-weight: bold;');
        
        // Try different dashboard URLs
        const dashboardUrls = [
            `${FRONTEND_URL}/index.html#/dashboard`,
            `${FRONTEND_URL}/#/dashboard`,
            `${currentUrl.split('#')[0]}#/dashboard`,
            `${currentUrl.split('#')[0]}#/app/dashboard`
        ];
        
        // Use the first URL that seems most appropriate
        let targetUrl = dashboardUrls[0];
        if (currentUrl.includes(FRONTEND_URL)) {
            targetUrl = dashboardUrls[2]; // Use current domain
        }
        
        console.log(`🚀 Redirecting to: ${targetUrl}`);
        console.log('%c================================', 'color: #667eea;');
        console.log('%c✅ LOGIN SUCCESSFUL!', 'color: #28a745; font-size: 20px; font-weight: bold;');
        console.log('%c================================', 'color: #667eea;');
        
        // Countdown before redirect
        let countdown = 3;
        const countdownInterval = setInterval(() => {
            console.log(`Redirecting in ${countdown}...`);
            countdown--;
            if (countdown === 0) {
                clearInterval(countdownInterval);
                window.location.href = targetUrl;
            }
        }, 1000);
        
    } catch (error) {
        console.error('%c❌ Token Injection Failed!', 'color: #dc3545; font-size: 16px; font-weight: bold;');
        console.error('Error:', error.message);
        
        // Provide fallback instructions
        console.log('%c📋 Manual Fallback Instructions:', 'color: #ffc107; font-weight: bold;');
        console.log('1. Copy this token (if available):');
        console.log('   [Token would be here if login succeeded]');
        console.log('2. Run this in console:');
        console.log(`   localStorage.setItem('token', 'PASTE_TOKEN_HERE');`);
        console.log(`   localStorage.setItem('auth_token', 'PASTE_TOKEN_HERE');`);
        console.log(`   window.location.href = '${FRONTEND_URL}/index.html#/dashboard';`);
        
        // Try alternate backend
        console.log('%c🔄 Trying alternate backend...', 'color: #17a2b8; font-weight: bold;');
        
        try {
            const altResponse = await fetch('https://luckygas-backend-step4-154687573210.asia-east1.run.app/api/v1/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: formData
            });
            
            const altData = await altResponse.json();
            
            if (altResponse.ok && altData.access_token) {
                console.log('%c✅ Alternate backend worked!', 'color: #28a745; font-weight: bold;');
                console.log('Token:', altData.access_token);
                
                // Inject this token
                localStorage.setItem('token', altData.access_token);
                localStorage.setItem('auth_token', altData.access_token);
                
                console.log('Token injected! Refreshing page...');
                setTimeout(() => location.reload(), 2000);
            }
        } catch (altError) {
            console.error('Alternate backend also failed:', altError.message);
        }
    }
})();

// Additional helper functions that can be called manually if needed

window.LuckyGasEmergency = {
    // Force login with a specific token
    forceLogin: function(token) {
        if (!token) {
            console.error('Please provide a token');
            return;
        }
        
        ['token', 'auth_token', 'jwt', 'access_token'].forEach(key => {
            localStorage.setItem(key, token);
        });
        
        console.log('✅ Token injected! Redirecting...');
        window.location.href = 'https://storage.googleapis.com/luckygas-frontend-prod/index.html#/dashboard';
    },
    
    // Clear all auth data
    clearAuth: function() {
        const authKeys = ['token', 'auth_token', 'jwt', 'access_token', 'user', 'userInfo', 'isAuthenticated'];
        authKeys.forEach(key => {
            localStorage.removeItem(key);
            console.log(`Removed ${key}`);
        });
        console.log('✅ All auth data cleared');
    },
    
    // Check current auth status
    checkAuth: function() {
        console.log('Current Auth Status:');
        console.log('===================');
        
        const authKeys = ['token', 'auth_token', 'jwt', 'access_token', 'user', 'isAuthenticated'];
        authKeys.forEach(key => {
            const value = localStorage.getItem(key);
            if (value) {
                if (key.includes('token')) {
                    console.log(`${key}: ${value.substring(0, 50)}...`);
                } else {
                    console.log(`${key}: ${value}`);
                }
            } else {
                console.log(`${key}: [NOT SET]`);
            }
        });
    },
    
    // Get fresh token
    getToken: async function() {
        console.log('Fetching fresh token...');
        
        try {
            const response = await fetch('https://luckygas-backend-step4-yzoirwjj3q-de.a.run.app/api/v1/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: 'username=admin@luckygas.com&password=admin-password-2025'
            });
            
            const data = await response.json();
            
            if (response.ok && data.access_token) {
                console.log('✅ Token obtained:');
                console.log(data.access_token);
                
                // Copy to clipboard
                if (navigator.clipboard) {
                    navigator.clipboard.writeText(data.access_token);
                    console.log('📋 Token copied to clipboard!');
                }
                
                return data.access_token;
            } else {
                console.error('Failed to get token:', data);
            }
        } catch (error) {
            console.error('Error:', error);
        }
    }
};

console.log('%c💡 Emergency functions available:', 'color: #17a2b8; font-weight: bold;');
console.log('  LuckyGasEmergency.forceLogin(token) - Login with specific token');
console.log('  LuckyGasEmergency.clearAuth() - Clear all auth data');
console.log('  LuckyGasEmergency.checkAuth() - Check current auth status');
console.log('  LuckyGasEmergency.getToken() - Get fresh token from backend');