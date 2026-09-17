const express = require('express');
const cors = require('cors');
const fareRoutes = require('./routes/fareRoutes');

const app = express();

app.use(cors());
app.use(express.json());

// This applies the '/api' prefix to every route in fareRoutes.js
app.use('/api', fareRoutes);

// Handle 404 for unknown routes
app.use((req, res, next) => {
  res.status(404).json({ success: false, error: 'API route not found' });
});

// Global error handler for malformed JSON or other synchronous errors
app.use((err, req, res, next) => {
  console.error('Unhandled Server Error:', err);
  res.status(500).json({ success: false, error: 'Internal server error', details: err.message });
});

module.exports = app;