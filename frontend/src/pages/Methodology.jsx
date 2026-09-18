export default function Methodology() {
  return (
    <div className="page-shell page-shell-narrow">
      <header className="page-header">
        <div>
          <p className="eyebrow">Methodology</p>
          <h1>Prototype fare index methodology</h1>
        </div>
      </header>

      <div className="panel section-block">
        <h3>Scope</h3>
        <p>
          FareCast is a working prototype for a real-time airfare price index framework for India. It is intended to demonstrate how route-level fare observations can be converted into a transparent index for monitoring price movements over time.
        </p>
        <p>
          This dashboard does not claim to represent official Government of India CPI weights or inflation methodology. Any weighting used in the prototype is for demonstration and research purposes only unless formally approved by the relevant analytics or statistical authority.
        </p>
      </div>

      <div className="panel section-block">
        <h3>Route Index</h3>
        <p className="math-block">Current Average Fare ÷ Base Period Average Fare × 100</p>
        <p>
          Each route is normalized against a chosen reference period to measure how its observed average fare changes over time. This produces an individual route index that can be aggregated into broader market-level trends.
        </p>
      </div>

      <div className="panel section-block">
        <h3>National Airfare Index</h3>
        <p>
          The national index combines route-level indices using the project&apos;s defined weighting scheme when route weights are available from the backend or analytics layer. Route coverage, route frequency, and observation quality are treated as operational considerations in the aggregation logic.
        </p>
      </div>

      <div className="panel section-block">
        <h3>Data pipeline</h3>
        <ul className="method-list">
          <li><strong>Data collection:</strong> fares are collected from live airline and OTA sources via automated scraper workflows.</li>
          <li><strong>Normalization:</strong> route and airline identifiers are standardized, and fare values are aligned to a common currency and structure.</li>
          <li><strong>Cleaning:</strong> malformed or incomplete observations are filtered before they enter the index logic.</li>
          <li><strong>Deduplication:</strong> repeated duplicate entries from the same route and collection window are removed to avoid skewing the sample.</li>
          <li><strong>Outlier detection:</strong> extreme values are reviewed as part of a quality-control step before aggregation.</li>
          <li><strong>Route-level aggregation:</strong> route averages are summarized to construct a route-specific index value.</li>
          <li><strong>National aggregation:</strong> route indices are combined, where weights are available, to derive a broader national airfare indicator.</li>
          <li><strong>Dashboard visualization:</strong> the API exposes the latest index, historical series, live fare feed, and route coverage for analytical review.</li>
        </ul>
      </div>
    </div>
  );
}
