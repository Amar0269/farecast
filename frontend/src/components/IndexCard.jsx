const formatIndexValue = (value) => {
  if (value === null || value === undefined || value === '') return '—';
  const number = Number(value);
  if (Number.isNaN(number)) return '—';
  return number.toFixed(1);
};

export default function IndexCard({ value, date, label = 'Current Airfare Index' }) {
  return (
    <div className="index-card">
      <div className="eyebrow">{label}</div>
      <div className="index-value">{formatIndexValue(value)}</div>
      <div className="index-meta">{date || 'No data available'}</div>
      <div className="index-label">Index value normalized to the selected base period.</div>
    </div>
  );
}
