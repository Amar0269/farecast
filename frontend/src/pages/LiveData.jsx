import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import ErrorMessage from '../components/ErrorMessage';
import LiveFareTable from '../components/LiveFareTable';
import Loading from '../components/Loading';
import { getLiveFares } from '../services/api';

const formatDateTime = (value) => {
  if (!value) return '—';
  return new Date(value).toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
};

export default function LiveData() {
  const [fares, setFares] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadFares = useCallback(async () => {
    try {
      setError('');
      setLoading(true);
      const data = await getLiveFares();
      setFares(data);
    } catch (err) {
      setError(err.message || 'Unable to load live fare data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFares();
    const intervalId = window.setInterval(loadFares, 60000);
    return () => window.clearInterval(intervalId);
  }, [loadFares]);

  return (
    <div className="page-shell page-shell-narrow">
      <header className="page-header">
        <div>
          <p className="eyebrow">Live fare feed</p>
          <h1>Live data</h1>
          <p className="subtitle">Latest observed airfare entries from the active scraper network.</p>
        </div>
        <div className="header-actions">
          <button type="button" className="action-button primary" onClick={loadFares}>
            Refresh
          </button>
          <Link to="/" className="action-button secondary">Dashboard</Link>
        </div>
      </header>

      <div className="updated-row">
        <span>Last updated</span>
        <strong>{formatDateTime(fares[0]?.collected_at)}</strong>
      </div>

      {loading ? (
        <Loading message="Loading live airfare feeds…" />
      ) : error ? (
        <ErrorMessage message={error} onRetry={loadFares} />
      ) : fares.length ? (
        <LiveFareTable fares={fares} />
      ) : (
        <div className="state-panel empty-panel">
          <h3>No airfare observations available yet.</h3>
          <p>The live fare feed is currently empty. Please check the scraper status or wait for the next collection cycle.</p>
          <button type="button" className="action-button primary" onClick={loadFares}>
            Retry
          </button>
        </div>
      )}
    </div>
  );
}
