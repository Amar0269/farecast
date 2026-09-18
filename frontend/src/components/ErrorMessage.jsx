export default function ErrorMessage({ title = 'Unable to load data', message, onRetry }) {
  return (
    <div className="state-panel error-panel" role="alert">
      <h3>{title}</h3>
      <p>{message || 'The server did not return usable data.'}</p>
      {onRetry ? (
        <button type="button" className="action-button secondary" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}
