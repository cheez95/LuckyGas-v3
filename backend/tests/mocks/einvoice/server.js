const express = require('express');
const bodyParser = require('body-parser');

const app = express();
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Store invoices for testing
const invoices = [];

// Mock E-Invoice creation endpoint
app.post('/mock-einvoice', (req, res) => {
  const { 
    username, 
    password, 
    buyer_tax_id,
    buyer_name,
    buyer_address,
    items,
    total_amount,
    tax_amount
  } = req.body;
  
  // Basic auth check
  if (username !== 'test' || password !== 'test') {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  
  // Generate invoice number
  const invoiceNumber = `TW${Date.now()}`;
  const invoice = {
    invoiceNumber,
    buyer_tax_id,
    buyer_name,
    buyer_address,
    items,
    total_amount,
    tax_amount,
    net_amount: total_amount - tax_amount,
    issue_date: new Date().toISOString(),
    status: 'issued'
  };
  
  invoices.push(invoice);
  
  console.log(`[Mock E-Invoice] Created invoice ${invoiceNumber} for ${buyer_name}`);
  
  res.json({
    success: true,
    invoiceNumber,
    qrCode: `https://einvoice.nat.gov.tw/mock/${invoiceNumber}`,
    status: 'issued'
  });
});

// Get invoice details
app.get('/mock-einvoice/:invoiceNumber', (req, res) => {
  const invoice = invoices.find(i => i.invoiceNumber === req.params.invoiceNumber);
  
  if (!invoice) {
    return res.status(404).json({ error: 'Invoice not found' });
  }
  
  res.json(invoice);
});

// Cancel invoice
app.post('/mock-einvoice/:invoiceNumber/cancel', (req, res) => {
  const invoice = invoices.find(i => i.invoiceNumber === req.params.invoiceNumber);
  
  if (!invoice) {
    return res.status(404).json({ error: 'Invoice not found' });
  }
  
  invoice.status = 'cancelled';
  invoice.cancel_date = new Date().toISOString();
  
  res.json({
    success: true,
    invoiceNumber: invoice.invoiceNumber,
    status: 'cancelled'
  });
});

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'mock-einvoice' });
});

// List all invoices (for testing)
app.get('/mock-einvoice', (req, res) => {
  res.json(invoices);
});

const PORT = process.env.PORT || 8002;
app.listen(PORT, () => {
  console.log(`Mock E-Invoice service running on port ${PORT}`);
});