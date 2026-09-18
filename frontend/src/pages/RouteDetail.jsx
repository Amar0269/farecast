import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import ErrorMessage from '../components/ErrorMessage';
import Loading from '../components/Loading';
import { getRoute } from '../services/api';

const formatRouteName = (route) => {
  const origin = route?.originCode || route?.origin?.code || '—';
  const destination = route?.destinationCode || route?.destination?.code || '—';
  return `${origin} → ${destination}`;
};

const formatCurrency = (value, currency = 'INR') =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(Number(value || 0));

const formatDate = (value) => {
  if (!value) return '—';

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;

  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(parsed);
};

const formatDateTime = (value) => {
  if (!value) return '—';

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;

  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(parsed);
};

const getRouteIndex = (route) => {
  if (!route) return null;

  return (
    route.indexValue ??
    route.routeIndex ??
    route.index?.value ??
    route.index?.latest ??
    route.marketIndex ??
    route.airfareIndex ??
    null
  );
};

export default function RouteDetail() {
  const { id } = useParams();
  const [route, setRoute] = useState(null);
  const [fares, setFares] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadRouteData = useCallback(async () => {
    try {
      setError('');
      setLoading(true);
      const routeResponse = await getRoute(id);
      setRoute(routeResponse);
      setFares(Array.isArray(routeResponse?.observations) ? routeResponse.observations : []);
    } catch (err) {
      setError(err.message || 'Unable to load route data.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadRouteData();
  }, [loadRouteData]);

  const routeIndexValue = getRouteIndex(route);

  return (
    <div className="page-shell page-shell-narrow">
      <header className="page-header">
        <div>
          <p className="eyebrow">Route detail</p>
          <h1>{route ? formatRouteName(route) : 'Route overview'}</h1>
        </div>
        <Link to="/routes" className="action-button secondary">Back to routes</Link>
      </header>

      {loading ? (
        <Loading message="Loading route detail…" />
      ) : error ? (
        <ErrorMessage message={error} onRetry={loadRouteData} />
      ) : (
        <>
          <div className="grid-two compact-grid">
            <div className="panel stat-card-panel">
              <div className="stat-label">Route</div>
              <div className="stat-value text-inline">{route ? formatRouteName(route) : '—'}</div>
              <div className="stat-hint">
                {route?.origin?.city || route?.originCode || '—'} to {route?.destination?.city || route?.destinationCode || '—'}
              </div>
            </div>
            <div className="panel stat-card-panel">
              <div className="stat-label">Route index</div>
              <div className="stat-value text-inline">
                {routeIndexValue === null || routeIndexValue === undefined ? 'Not available' : routeIndexValue}
              </div>
              <div className="stat-hint">
                {routeIndexValue === null || routeIndexValue === undefined
                  ? 'Route index not available'
                  : 'Latest route index value from the backend'}
              </div>
            </div>
          </div>

          <div className="panel detail-panel">
            <div className="panel-header-row">
              <h3>Route summary</h3>
            </div>
            <div className="detail-grid">
              <div className="detail-field">
                <span>Route</span>
                <strong>{route ? formatRouteName(route) : '—'}</strong>
              </div>
              <div className="detail-field">
                <span>Origin</span>
                <strong>{route?.origin?.city || route?.originCode || '—'}</strong>
              </div>
              <div className="detail-field">
                <span>Destination</span>
                <strong>{route?.destination?.city || route?.destinationCode || '—'}</strong>
              </div>
              <div className="detail-field">
                <span>Route ID</span>
                <strong>{route?.id ?? '—'}</strong>
              </div>
              <div className="detail-field detail-field-wide">
                <span>Route index</span>
                <strong>
                  {routeIndexValue === null || routeIndexValue === undefined
                    ? 'Route index not available'
                    : routeIndexValue}
                </strong>
              </div>
            </div>
          </div>

          {fares.length ? (
            <div className="panel">
              <div className="panel-header-row">
                <h3>Latest fare observations</h3>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Airline</th>
                      <th>Flight</th>
                      <th>Travel date</th>
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
                      <tr key={fare.id ?? `${fare.flight_number}-${fare.collected_at}-${fare.travel_date}`}>
                        <td>{fare.airline?.name || fare.airline?.code || fare.airlineId || '—'}</td>
                        <td>{fare.flight_number || '—'}</td>
                        <td>{formatDate(fare.travel_date)}</td>
                        <td>{fare.departure_time || '—'}</td>
                        <td>{fare.arrival_time || '—'}</td>
                        <td>{fare.cabin_class || '—'}</td>
                        <td>{fare.stops === 0 ? 'Non-stop' : `${fare.stops} stop${fare.stops > 1 ? 's' : ''}`}</td>
                        <td>{formatCurrency(fare.fare, fare.currency || 'INR')}</td>
                        <td>{formatDateTime(fare.collected_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="state-panel empty-panel">
              <h3>No fare observations</h3>
              <p>No fare observations are currently available for this route.</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
