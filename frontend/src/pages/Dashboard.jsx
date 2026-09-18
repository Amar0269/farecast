import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import IndexCard from '../components/IndexCard';
import IndexChart from '../components/IndexChart';
import LiveFareTable from '../components/LiveFareTable';
import Loading from '../components/Loading';
import ErrorMessage from '../components/ErrorMessage';
import RouteMap from '../components/RouteMap';
import StatCard from '../components/StatCard';
import { getIndexHistory, getLatestIndex, getLiveFares, getRoutes, getStats } from '../services/api';

const formatDateTime = (value) => {
  if (!value) return '—';

  return new Date(value).toLocaleString('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
};

const formatPercent = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  const number = Number(value);
  return `${number > 0 ? '+' : ''}${number.toFixed(2)}%`;
};

export default function Dashboard() {
  const [stats, setStats] = useState({});
  const [latestIndex, setLatestIndex] = useState(null);
  const [history, setHistory] = useState([]);
  const [fares, setFares] = useState([]);
  const [routes, setRoutes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadDashboard = useCallback(async () => {
    setError('');
    setLoading(true);

    const results = await Promise.allSettled([
      getStats(),
      getLatestIndex(),
      getIndexHistory(),
      getLiveFares(),
      getRoutes(),
    ]);

    const nextStats = results[0].status === 'fulfilled' ? results[0].value : {};
    const nextIndex = results[1].status === 'fulfilled' ? results[1].value : null;
    const nextHistory = results[2].status === 'fulfilled' ? results[2].value : [];
    const nextFares = results[3].status === 'fulfilled' ? results[3].value : [];
    const nextRoutes = results[4].status === 'fulfilled' ? results[4].value : [];

    setStats(nextStats || {});
    setLatestIndex(nextIndex || null);
    setHistory(Array.isArray(nextHistory) ? nextHistory : []);
    setFares(Array.isArray(nextFares) ? nextFares : []);
    setRoutes(Array.isArray(nextRoutes) ? nextRoutes : []);

    const failedCalls = results.filter((result) => result.status === 'rejected');
    if (failedCalls.length === results.length) {
      setError(failedCalls[0].reason?.message || 'Failed to load dashboard data.');
    } else if (failedCalls.length > 0) {
      setError('Some dashboard data could not be refreshed. Showing available data.');
    }

    setLoading(false);
  }, []);

  useEffect(() => {
    loadDashboard();
    const intervalId = window.setInterval(loadDashboard, 60000);
    return () => window.clearInterval(intervalId);
  }, [loadDashboard]);

  const change24h = useMemo(() => {
    if (!history || history.length < 2) return null;

    const newest = history[history.length - 1]?.index_value;
    const previous = history[history.length - 2]?.index_value;

    if (newest === undefined || previous === undefined || previous === 0) return null;

    return ((newest - previous) / previous) * 100;
  }, [history]);

  const firstHistoryDate = history.length ? history[0]?.date : null;
  const latestDate = latestIndex?.date || firstHistoryDate || null;
  const hasAnyData = Boolean(
    stats.totalObservations !== undefined ||
      latestIndex ||
      history.length ||
      fares.length ||
      routes.length,
  );

  if (loading && !error && !hasAnyData) {
    return <Loading message="Loading FareCast dashboard…" />;
  }

  if (error && !hasAnyData) {
    return (
      <div className="page-shell page-shell-narrow">
        <ErrorMessage message={error} onRetry={loadDashboard} />
      </div>
    );
  }

  return (
    <div className="page-shell">
      <header className="hero-header">
        <div>
          <p className="eyebrow">India airfare intelligence</p>
          <h1>FareCast</h1>
          <p className="subtitle">Real-time airfare price index for India, based on observed domestic route pricing data.</p>
        </div>
        <div className="header-meta">
          <span>Last updated</span>
          <strong>{formatDateTime(latestDate || (fares[0]?.collected_at ?? null))}</strong>
        </div>
      </header>

      {error ? (
        <div className="state-panel error-panel" style={{ marginBottom: '16px' }}>
          <p>{error}</p>
          <button type="button" className="action-button secondary" onClick={loadDashboard}>
            Retry
          </button>
        </div>
      ) : null}

      <section className="stats-grid">
        <StatCard
          label="Current Airfare Index"
          value={latestIndex ? Number(latestIndex.index_value).toFixed(1) : '—'}
          hint={latestIndex ? `As of ${formatDateTime(latestIndex.date)}` : 'Insufficient historical data'}
          tone="primary"
        />
        <StatCard
          label="24h change"
          value={change24h === null ? '—' : formatPercent(change24h)}
          hint={change24h === null ? 'Insufficient historical data' : 'Compared with previous observation'}
          tone={change24h === null ? 'neutral' : change24h >= 0 ? 'up' : 'down'}
        />
        <StatCard
          label="Total observations"
          value={stats.totalObservations ?? 0}
          hint="Current live fare samples"
        />
        <StatCard
          label="Routes with data"
          value={stats.totalRoutes ?? routes.length ?? 0}
          hint="Unique routes represented"
        />
        <StatCard
          label="Airlines with data"
          value={stats.totalAirlines ?? 0}
          hint="Covered carriers"
        />
      </section>

      <section className="grid-two">
        <IndexCard value={latestIndex?.index_value} date={formatDateTime(latestIndex?.date)} />
        <div className="panel statistic-panel">
          <div className="panel-header-row">
            <h3>Coverage and data quality</h3>
          </div>
          <div className="coverage-list">
            <div>
              <span>Total observations</span>
              <strong>{stats.totalObservations ?? fares.length ?? 0}</strong>
            </div>
            <div>
              <span>Routes currently represented</span>
              <strong>{stats.totalRoutes ?? routes.length ?? 0}</strong>
            </div>
            <div>
              <span>Airlines currently represented</span>
              <strong>{stats.totalAirlines ?? 0}</strong>
            </div>
            <div>
              <span>Last collection time</span>
              <strong>{formatDateTime(fares[0]?.collected_at ?? latestIndex?.created_at ?? null)}</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="panel section-block">
        <div className="panel-header-row">
          <h3>Historical index trend</h3>
        </div>
        <IndexChart data={history} />
      </section>

      <section className="panel section-block map-section">
        <div className="panel-header-row chart-header">
          <div>
            <h3>India Route Coverage</h3>
            <p className="section-subtitle">Displayed route lines reflect airport pairs currently returned by the backend. Supported airports are reference markers only.</p>
          </div>
        </div>
        <div className="map-legend" aria-label="Map legend">
          <span><i className="legend-dot airport-dot" />Airport</span>
          <span><i className="legend-line route-line" />Observed route</span>
        </div>
        <RouteMap routes={routes} />
        {routes.length && routes.some((route) => !route?.originCode || !route?.destinationCode) ? (
          <div className="map-warning">Some route records are missing airport codes and were skipped for mapping.</div>
        ) : null}
      </section>

      <section className="section-block">
        <div className="panel-header-row split-header">
          <h3>Recent fare observations</h3>
          <Link to="/live" className="action-button secondary">View all live data</Link>
        </div>
        <LiveFareTable fares={fares.slice(0, 8)} />
      </section>
    </div>
  );
}
