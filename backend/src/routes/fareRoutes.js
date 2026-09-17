const express = require('express');
const router = express.Router();
const fareController = require('../controllers/fareController');

// Fares
router.post('/fares', fareController.createFare);
router.get('/fares', fareController.getAllFares);
router.get('/fares/live', fareController.getLiveFares);

// Infrastructure (Routes & Airlines)
router.get('/routes', fareController.getAllRoutes);
router.get('/routes/:id', fareController.getRouteById);
router.get('/airlines', fareController.getAllAirlines);

// Analytics
router.get('/stats', fareController.getStats);
router.post('/index', fareController.saveIndex);
router.get('/index', fareController.getLatestIndex);
router.get('/index/history', fareController.getIndexHistory);

module.exports = router;