const formatCurrency = (value) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(Number(value || 0));

const formatDate = (iso) => {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
};

const formatStops = (stops) => {
  if (stops === 0) return 'Non-stop';
  if (stops === 1) return '1 stop';
  return `${stops} stops`;
};

const formatRoute = (fare) => {
  const origin = fare?.route?.origin?.code || fare?.route?.originCode || '—';
  const destination = fare?.route?.destination?.code || fare?.route?.destinationCode || '—';
  return `${origin} → ${destination}`;
};

export default function LiveFareTable({ fares = [] }) {
  if (!fares.length) {
    return (
      <div className="panel empty-panel">
        <p>No live airfare observations are currently available.</p>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-header-row">
        <h3>Recent fare observations</h3>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Airline</th>
              <th>Flight</th>
              <th>Route</th>
              <th>Travel Date</th>
              <th>Departure</th>
              <th>Arrival</th>
              <th>Cabin</th>
              <th>Stops</th>
              <th>Fare</th>
              <th>Collected</th>
            </tr>
          </thead>
          <tbody>
            {fares.map((fare) => (
              <tr key={fare.id ?? `${fare.flight_number}-${fare.collected_at}`}>
                <td>{fare.airline?.name || fare.airlineId || '—'}</td>
                <td>{fare.flight_number || '—'}</td>
                <td>{formatRoute(fare)}</td>
                <td>{fare.travel_date ? new Date(fare.travel_date).toLocaleDateString('en-IN') : '—'}</td>
                <td>{fare.departure_time || '—'}</td>
                <td>{fare.arrival_time || '—'}</td>
                <td>{fare.cabin_class || '—'}</td>
                <td>{formatStops(fare.stops ?? 0)}</td>
                <td>{formatCurrency(fare.fare)}</td>
                <td>{formatDate(fare.collected_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
