const express = require('express');
const bodyParser = require('body-parser');

const app = express();
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Mock bank accounts
const accounts = {
  'LUCKY001': {
    accountNumber: 'LUCKY001',
    balance: 1000000,
    currency: 'TWD',
    transactions: []
  }
};

// Mock payment gateway
app.post('/mock-banking/payment', (req, res) => {
  const {
    amount,
    currency,
    customerAccount,
    merchantAccount,
    reference,
    description
  } = req.body;
  
  // Simulate payment processing
  const transactionId = `TXN${Date.now()}`;
  const transaction = {
    id: transactionId,
    type: 'payment',
    amount,
    currency: currency || 'TWD',
    customerAccount,
    merchantAccount: merchantAccount || 'LUCKY001',
    reference,
    description,
    status: 'completed',
    timestamp: new Date().toISOString()
  };
  
  // Update merchant account
  if (accounts[merchantAccount || 'LUCKY001']) {
    accounts[merchantAccount || 'LUCKY001'].balance += amount;
    accounts[merchantAccount || 'LUCKY001'].transactions.push(transaction);
  }
  
  console.log(`[Mock Banking] Payment processed: ${transactionId} - ${amount} ${currency}`);
  
  res.json({
    success: true,
    transactionId,
    status: 'completed',
    timestamp: transaction.timestamp
  });
});

// Get account balance
app.get('/mock-banking/account/:accountNumber/balance', (req, res) => {
  const account = accounts[req.params.accountNumber];
  
  if (!account) {
    return res.status(404).json({ error: 'Account not found' });
  }
  
  res.json({
    accountNumber: account.accountNumber,
    balance: account.balance,
    currency: account.currency,
    lastUpdated: new Date().toISOString()
  });
});

// Get transaction history
app.get('/mock-banking/account/:accountNumber/transactions', (req, res) => {
  const account = accounts[req.params.accountNumber];
  
  if (!account) {
    return res.status(404).json({ error: 'Account not found' });
  }
  
  res.json({
    accountNumber: account.accountNumber,
    transactions: account.transactions,
    count: account.transactions.length
  });
});

// Process refund
app.post('/mock-banking/refund', (req, res) => {
  const {
    originalTransactionId,
    amount,
    reason
  } = req.body;
  
  const refundId = `REF${Date.now()}`;
  const refund = {
    id: refundId,
    originalTransactionId,
    type: 'refund',
    amount,
    reason,
    status: 'completed',
    timestamp: new Date().toISOString()
  };
  
  console.log(`[Mock Banking] Refund processed: ${refundId} - ${amount} TWD`);
  
  res.json({
    success: true,
    refundId,
    status: 'completed',
    timestamp: refund.timestamp
  });
});

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'mock-banking' });
});

const PORT = process.env.PORT || 8003;
app.listen(PORT, () => {
  console.log(`Mock Banking service running on port ${PORT}`);
});