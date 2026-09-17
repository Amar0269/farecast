# Source Investigation: Air India

## Source
- **Name**: Air India (airindia.com)
- **Target Category**: Direct Airline Carrier

## Search URL / Workflow
- **Search URL Format**: `https://www.airindia.com/in/en/book/flight-select.{origin}-{destination}.{YYYY-MM-DD}.economy.1.0.0.html`
- **Example**: `https://www.airindia.com/in/en/book/flight-select.DEL-BOM.2026-10-17.economy.1.0.0.html`

## Access Method Tested
1. Direct HTTP GET via `httpx`.
2. Playwright Chromium headless DOM navigation.

## Data Delivery Mechanism
- JavaScript dynamic rendering protected by Akamai Bot Manager / Web Application Firewall (WAF).

## Live Access Result
- **Status**: `SOURCE_BLOCKED`
- **Error**: Connection timeout / Akamai TLS handshake reset.
- **Behavior**: Air India enforces strict Akamai WAF protection that drops non-browser TLS connections and automated Playwright browser instances.

## Fields Successfully Extracted
- Extracted via offline static DOM parser: `airline`, `flight_number`, `origin`, `destination`, `route`, `travel_date`, `departure_time`, `arrival_time`, `stops`, `total_fare`, `currency`.

## Fields Unavailable
- Detailed fee breakdowns (`base_fare`, `taxes`, `convenience_fee`), seat availability count.

## Number of Real Observations Collected
- **0** (live access blocked by Akamai WAF).

## Restrictions Encountered
- Akamai Bot Manager edge blocking and connection timeouts.

## Raw Data Location
- `data/raw/airindia/`

## Processed Data Location
- `data/processed/`

## Tests
- `tests/test_airindia_parser.py` (3 tests passing with offline HTML fixture).

## Limitations
- Direct automated access blocked without authorized carrier API or partner integration.

## Recommended Status
- **`SOURCE_BLOCKED`**
