import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import ErrorMessage from '../components/ErrorMessage';
import Loading from '../components/Loading';
import RouteTable from '../components/RouteTable';
import { getRoutes } from '../services/api';

export default function RoutesPage() {
  const [routes, setRoutes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadRoutes = useCallback(async () => {
    try {
      setError('');
      setLoading(true);
      const data = await getRoutes();
      setRoutes(data);
    } catch (err) {
      setError(err.message || 'Unable to load routes.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRoutes();
  }, [loadRoutes]);

  return (
    <div className="page-shell page-shell-narrow">
      <header className="page-header">
        <div>
          <p className="eyebrow">Route coverage</p>
          <h1>Supported routes</h1>
        </div>
        <Link to="/" className="action-button secondary">Back to dashboard</Link>
      </header>

      {loading ? (
        <Loading message="Loading routes…" />
      ) : error ? (
        <ErrorMessage message={error} onRetry={loadRoutes} />
      ) : routes.length ? (
        <RouteTable routes={routes} />
      ) : (
        <div className="state-panel empty-panel">
          <h3>No routes currently represented.</h3>
          <p>No route records are available from the backend at the moment.</p>
          <button type="button" className="action-button primary" onClick={loadRoutes}>
            Retry
          </button>
        </div>
      )}
    </div>
  );
}
