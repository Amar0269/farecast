import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';

const formatTooltipValue = (value) => `${Number(value).toFixed(1)}`;

export default function IndexChart({ data }) {
  if (!Array.isArray(data) || data.length === 0) {
    return (
      <div className="panel empty-chart-panel">
        <p>No historical index data available yet.</p>
      </div>
    );
  }

  const chartData = data.map((point) => ({
    ...point,
    dateLabel: point.date ? new Date(point.date).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }) : '—',
  }));

  const isSinglePoint = chartData.length === 1;

  return (
    <div className="panel panel-chart">
      <div className="panel-header-row chart-header">
        <div>
          <h3>Historical Airfare Index</h3>
          <p className="section-subtitle">National index history based on available observations.</p>
        </div>
      </div>
      <div style={{ width: '100%', height: 280 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 16, right: 24, left: 8, bottom: 12 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#d9e3f0" />
            <XAxis dataKey="dateLabel" tickLine={false} axisLine={false} minTickGap={24} />
            <YAxis tickLine={false} axisLine={false} domain={['auto', 'auto']} />
            <Tooltip
              formatter={(value) => [formatTooltipValue(value), 'Index value']}
              labelFormatter={(label) => `Date: ${label}`}
            />
            <Line
              type="monotone"
              dataKey="index_value"
              stroke="#1f5f8f"
              strokeWidth={3}
              dot={{ r: isSinglePoint ? 5 : 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      {isSinglePoint ? (
        <div className="chart-note">One observation available. More points will appear as index history accumulates.</div>
      ) : null}
    </div>
  );
}
