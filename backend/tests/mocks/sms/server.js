const express = require('express');
const bodyParser = require('body-parser');

const app = express();
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Store sent messages for testing
const sentMessages = [];

// Mock SMS endpoint
app.post('/mock-sms', (req, res) => {
  const { phone, message, username, password } = req.body;
  
  // Basic auth check
  if (username !== 'test' || password !== 'test') {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  
  // Validate phone number
  if (!phone || !phone.match(/^09\d{8}$/)) {
    return res.status(400).json({ error: 'Invalid phone number' });
  }
  
  // Store message
  const messageId = `MSG${Date.now()}`;
  sentMessages.push({
    id: messageId,
    phone,
    message,
    timestamp: new Date().toISOString(),
    status: 'sent'
  });
  
  console.log(`[Mock SMS] Sent message to ${phone}: ${message}`);
  
  res.json({
    success: true,
    messageId,
    status: 'sent'
  });
});

// Get message status
app.get('/mock-sms/status/:messageId', (req, res) => {
  const message = sentMessages.find(m => m.id === req.params.messageId);
  
  if (!message) {
    return res.status(404).json({ error: 'Message not found' });
  }
  
  res.json({
    id: message.id,
    status: message.status,
    timestamp: message.timestamp
  });
});

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'mock-sms' });
});

// List all messages (for testing)
app.get('/mock-sms/messages', (req, res) => {
  res.json(sentMessages);
});

const PORT = process.env.PORT || 8001;
app.listen(PORT, () => {
  console.log(`Mock SMS service running on port ${PORT}`);
});