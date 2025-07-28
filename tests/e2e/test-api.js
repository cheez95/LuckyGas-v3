const fetch = (...args) => import('node-fetch').then(({default: fetch}) => fetch(...args));

async function testAPI() {
  console.log('Testing mock backend API...\n');
  
  // 1. Test login
  console.log('1. Testing login...');
  const loginResponse = await fetch('http://localhost:3001/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: 'username=admin&password=admin123'
  });
  
  const loginData = await loginResponse.json();
  console.log('Login response:', loginResponse.status);
  console.log('Access token:', loginData.access_token ? 'Received' : 'Missing');
  
  if (!loginData.access_token) {
    console.error('Login failed:', loginData);
    return;
  }
  
  // 2. Test /auth/me
  console.log('\n2. Testing /auth/me...');
  const meResponse = await fetch('http://localhost:3001/api/v1/auth/me', {
    headers: {
      'Authorization': `Bearer ${loginData.access_token}`
    }
  });
  
  console.log('Me response:', meResponse.status);
  if (meResponse.ok) {
    const meData = await meResponse.json();
    console.log('User data:', meData);
  } else {
    console.error('Me request failed:', await meResponse.text());
  }
  
  // 3. Test /api/v1/users/me (alternative endpoint)
  console.log('\n3. Testing /api/v1/users/me...');
  const usersmeResponse = await fetch('http://localhost:3001/api/v1/users/me', {
    headers: {
      'Authorization': `Bearer ${loginData.access_token}`
    }
  });
  
  console.log('Users/me response:', usersmeResponse.status);
  if (usersmeResponse.ok) {
    const usersmeData = await usersmeResponse.json();
    console.log('User data:', usersmeData);
  } else {
    console.log('Users/me not found (this is expected)');
  }
}

testAPI().catch(console.error);