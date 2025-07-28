import { Router } from 'express';
import jwt from 'jsonwebtoken';
import { mockData } from '../mock-data';

const router = Router();
const SECRET_KEY = 'test-secret-key-for-e2e-testing';

function generateToken(user: any) {
  return jwt.sign(
    { 
      user_id: user.id, 
      username: user.username, 
      role: user.role,
      email: user.email 
    },
    SECRET_KEY,
    { expiresIn: '30m' }
  );
}

function verifyToken(req: any, res: any, next: any) {
  const authHeader = req.headers.authorization;
  if (!authHeader) {
    return res.status(401).json({ detail: '未授權' });
  }
  
  const token = authHeader.split(' ')[1];
  try {
    const decoded = jwt.verify(token, SECRET_KEY);
    req.user = decoded;
    next();
  } catch (error) {
    return res.status(401).json({ detail: '無效的令牌' });
  }
}

// Login endpoint
router.post('/login', (req, res) => {
  const { username, password } = req.body;
  const user = mockData.users.find(u => u.username === username);
  
  if (!user || user.password !== password) {
    return res.status(401).json({ detail: '帳號或密碼錯誤' });
  }
  
  const access_token = generateToken(user);
  const refresh_token = generateToken(user); // In real app, this would be different
  
  res.json({
    access_token,
    refresh_token,
    token_type: 'bearer',
    user: {
      id: user.id,
      username: user.username,
      role: user.role,
      display_name: user.display_name
    }
  });
});

// Token refresh endpoint
router.post('/refresh', verifyToken, (req, res) => {
  const user = mockData.users.find(u => u.username === req.user.username);
  if (!user) {
    return res.status(401).json({ detail: '用戶不存在' });
  }
  
  const access_token = generateToken(user);
  
  res.json({
    access_token,
    token_type: 'bearer'
  });
});

// Get current user endpoint
router.get('/me', verifyToken, (req, res) => {
  const user = mockData.users.find(u => u.username === req.user.username);
  if (!user) {
    return res.status(401).json({ detail: '用戶不存在' });
  }
  
  res.json({
    id: user.id,
    username: user.username,
    role: user.role,
    display_name: user.display_name,
    email: user.email,
    full_name: user.full_name,
    is_active: user.is_active,
    created_at: user.created_at
  });
});

// Logout endpoint (for completeness)
router.post('/logout', verifyToken, (req, res) => {
  // In a real app, you might blacklist the token here
  res.json({ message: '登出成功' });
});

// Password reset request
router.post('/forgot-password', (req, res) => {
  const { email } = req.body;
  const user = mockData.users.find(u => u.email === email);
  
  if (!user) {
    // Don't reveal if email exists
    res.json({ message: '如果該電子郵件存在，將會收到重設密碼的連結' });
    return;
  }
  
  // Simulate sending email
  console.log(`Password reset requested for ${email}`);
  res.json({ message: '如果該電子郵件存在，將會收到重設密碼的連結' });
});

// Password reset
router.post('/reset-password', (req, res) => {
  const { token, new_password } = req.body;
  
  // In real app, validate reset token
  if (!token || !new_password) {
    return res.status(400).json({ detail: '無效的請求' });
  }
  
  res.json({ message: '密碼已成功重設' });
});

export { router as authRoutes, verifyToken };