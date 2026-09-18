export default function Loading({ message = 'Loading data…' }) {
  return (
    <div className="state-panel loading-panel" role="status" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <p>{message}</p>
    </div>
  );
}
