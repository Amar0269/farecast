import { Link } from 'react-router-dom';

const formatRouteCode = (route) => {
  const origin = route?.originCode || route?.origin?.code || '—';
  const destination = route?.destinationCode || route?.destination?.code || '—';
  return `${origin} → ${destination}`;
};

export default function RouteTable({ routes = [] }) {
  if (!routes.length) {
    return (
      <div className="panel empty-panel">
        <p>No routes are currently available.</p>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-header-row">
        <h3>Supported routes</h3>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Origin</th>
              <th>Destination</th>
              <th>Route code</th>
              <th>Route ID</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {routes.map((route) => {
              const origin = route?.origin?.city || route?.originCode || '—';
              const destination = route?.destination?.city || route?.destinationCode || '—';
              const routeCode = formatRouteCode(route);

              return (
                <tr key={route.id ?? `${route.originCode}-${route.destinationCode}`}>
                  <td>{origin}</td>
                  <td>{destination}</td>
                  <td>{routeCode}</td>
                  <td>{route?.id ?? '—'}</td>
                  <td>
                    <Link to={`/routes/${route.id}`} className="table-link">
                      View route
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
