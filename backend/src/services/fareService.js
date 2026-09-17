const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

// 1. Ingest
exports.saveFareObservation = async (data) => {
  const { source, airline, flight_number, origin, destination, travel_date, departure_time, arrival_time, cabin_class, stops, fare, currency, collected_at } = data;

  const dbAirline = await prisma.airline.upsert({
    where: { name: airline },
    update: {},
    create: { name: airline, code: airline.substring(0, 2).toUpperCase() }
  });

  const dbRoute = await prisma.route.upsert({
    where: { originCode_destinationCode: { originCode: origin, destinationCode: destination } },
    update: {},
    create: {
      origin: { connectOrCreate: { where: { code: origin }, create: { code: origin, city: origin } } },
      destination: { connectOrCreate: { where: { code: destination }, create: { code: destination, city: destination } } }
    }
  });

  return await prisma.fareObservation.create({
    data: {
      source, flight_number, travel_date: new Date(travel_date), departure_time, arrival_time,
      cabin_class, stops, fare, currency, collected_at: collected_at ? new Date(collected_at) : new Date(),
      airlineId: dbAirline.id, routeId: dbRoute.id
    }
  });
};

// 2. Fares (Live & History)
exports.getLiveFares = async () => {
  return await prisma.fareObservation.findMany({
    take: 50,
    orderBy: { collected_at: 'desc' },
    include: { airline: true, route: { include: { origin: true, destination: true } } }
  });
};

exports.getAllFares = async () => {
  return await prisma.fareObservation.findMany({
    orderBy: { collected_at: 'desc' },
    include: { airline: true, route: { include: { origin: true, destination: true } } }
  });
};

// 3. Stats & Routing
exports.getStats = async () => {
  const totalObservations = await prisma.fareObservation.count();
  const totalRoutes = await prisma.route.count();
  const totalAirlines = await prisma.airline.count();
  return { totalObservations, totalRoutes, totalAirlines };
};

exports.getAllRoutes = async () => {
  return await prisma.route.findMany({ include: { origin: true, destination: true } });
};

exports.getRouteById = async (routeId) => {
  return await prisma.route.findUnique({
    where: { id: routeId },
    include: { origin: true, destination: true, observations: { take: 10, orderBy: { collected_at: 'desc' }, include: { airline: true } } }
  });
};

exports.getAllAirlines = async () => {
  return await prisma.airline.findMany();
};

// 4. Index Analytics
exports.saveIndex = async (data) => {
  const { date, national_index, route_indices } = data;
  const indexDate = new Date(date);

  const newNationalIndex = await prisma.nationalIndex.create({
    data: { date: indexDate, index_value: national_index }
  });

  let savedRouteIndices = [];
  if (route_indices && route_indices.length > 0) {
    savedRouteIndices = await Promise.all(
      route_indices.map(route => 
        prisma.routeIndex.create({
          data: { routeId: route.route_id, date: indexDate, index_value: route.index_value }
        })
      )
    );
  }
  return { national: newNationalIndex, routes: savedRouteIndices };
};

exports.getLatestIndex = async () => {
  return await prisma.nationalIndex.findFirst({ orderBy: { date: 'desc' } });
};

exports.getIndexHistory = async () => {
  return await prisma.nationalIndex.findMany({ orderBy: { date: 'asc' } });
};