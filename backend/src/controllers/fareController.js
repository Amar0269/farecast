const fareService = require('../services/fareService');

exports.createFare = async (req, res) => {
  try {
    const { source, airline, flight_number, origin, destination, travel_date, fare, currency } = req.body;
    if (!source || !airline || !flight_number || !origin || !destination || !travel_date || fare === undefined || !currency) {
      return res.status(400).json({ success: false, error: 'Missing required fields in fare observation.' });
    }
    
    const observation = await fareService.saveFareObservation(req.body);
    res.status(201).json({ success: true, data: observation });
  } catch (error) {
    console.error('Error in createFare:', error);
    res.status(500).json({ success: false, error: 'Failed to save fare observation', details: error.message });
  }
};

exports.getLiveFares = async (req, res) => {
  try {
    const data = await fareService.getLiveFares();
    res.status(200).json({ success: true, count: data.length, data });
  } catch (error) {
    console.error('Error in getLiveFares:', error);
    res.status(500).json({ success: false, error: 'Failed to fetch live fares' });
  }
};

exports.getAllFares = async (req, res) => {
  try {
    const data = await fareService.getAllFares();
    res.status(200).json({ success: true, count: data.length, data });
  } catch (error) {
    console.error('Error in getAllFares:', error);
    res.status(500).json({ success: false, error: 'Failed to fetch all fares' });
  }
};

exports.getStats = async (req, res) => {
  try {
    const data = await fareService.getStats();
    res.status(200).json({ success: true, data });
  } catch (error) {
    console.error('Error in getStats:', error);
    res.status(500).json({ success: false, error: 'Failed to fetch stats' });
  }
};

exports.getAllRoutes = async (req, res) => {
  try {
    const data = await fareService.getAllRoutes();
    res.status(200).json({ success: true, count: data.length, data });
  } catch (error) {
    console.error('Error in getAllRoutes:', error);
    res.status(500).json({ success: false, error: 'Failed to fetch routes' });
  }
};

exports.getRouteById = async (req, res) => {
  try {
    const data = await fareService.getRouteById(parseInt(req.params.id));
    if (!data) return res.status(404).json({ success: false, error: 'Route not found' });
    res.status(200).json({ success: true, data });
  } catch (error) {
    console.error('Error in getRouteById:', error);
    res.status(500).json({ success: false, error: 'Failed to fetch route details' });
  }
};

exports.getAllAirlines = async (req, res) => {
  try {
    const data = await fareService.getAllAirlines();
    res.status(200).json({ success: true, count: data.length, data });
  } catch (error) {
    console.error('Error in getAllAirlines:', error);
    res.status(500).json({ success: false, error: 'Failed to fetch airlines' });
  }
};

exports.saveIndex = async (req, res) => {
  try {
    const { date, national_index } = req.body;
    if (!date || national_index === undefined) {
      return res.status(400).json({ success: false, error: 'Missing required fields: date or national_index.' });
    }
    
    const data = await fareService.saveIndex(req.body);
    res.status(201).json({ success: true, data });
  } catch (error) {
    console.error('Error in saveIndex:', error);
    res.status(500).json({ success: false, error: 'Failed to save index data', details: error.message });
  }
};

exports.getLatestIndex = async (req, res) => {
  try {
    const data = await fareService.getLatestIndex();
    res.status(200).json({ success: true, data });
  } catch (error) {
    console.error('Error in getLatestIndex:', error);
    res.status(500).json({ success: false, error: 'Failed to fetch index' });
  }
};

exports.getIndexHistory = async (req, res) => {
  try {
    const data = await fareService.getIndexHistory();
    res.status(200).json({ success: true, count: data.length, data });
  } catch (error) {
    console.error('Error in getIndexHistory:', error);
    res.status(500).json({ success: false, error: 'Failed to fetch index history' });
  }
};