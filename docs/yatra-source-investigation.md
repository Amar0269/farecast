# Source Investigation: Yatra

## Source
- **Name**: Yatra (yatra.com)
- **Target Category**: Online Travel Agency (OTA)

## Search URL / Workflow
- **Search URL Format**: `https://flight.yatra.com/air-search/dom2/trigger?type=O&origin={origin}&originCode={origin}&destination={dest}&destinationCode={dest}&flight_depart_date={DD/MM/YYYY}&ADT=1&CHD=0&INF=0&class=Economy`
- **Example**: `https://flight.yatra.com/air-search/dom2/trigger?type=O&origin=DEL&originCode=DEL&destination=BOM&destinationCode=BOM&flight_depart_date=17/10/2026&ADT=1&CHD=0&INF=0&class=Economy`

## Access Method Tested
1. Direct HTTP GET via `httpx` with browser User-Agent headers.
2. BeautifulSoup HTML parsing of pre-rendered server payload.

## Data Delivery Mechanism
- Server-rendered HTML payload containing pre-rendered flight card elements (`div.flightItem`) as well as internal backend JSON triggers (`/air-service/dom2/trigger`).

## Live Access Result
- **Status**: **`LIVE_WORKING`**
- **HTTP Code**: 200 OK
- **Behavior**: Yatra returns full pre-rendered HTML search result pages via normal HTTP GET requests without bot blocking or CAPTCHA challenges.

## Fields Successfully Extracted
- `airline` (e.g., SpiceJet, IndiGo, Air India)
- `flight_number` (e.g., SG 8723, 6E 5314)
- `origin` (e.g., DEL)
- `destination` (e.g., BOM)
- `route` (e.g., DEL-BOM)
- `travel_date` (YYYY-MM-DD)
- `departure_time` (HH:MM)
- `arrival_time` (HH:MM)
- `stops` (0 for Non-Stop, 1 for 1-Stop)
- `cabin_class` (Economy)
- `total_fare` (numeric INR, e.g., 24220.0)
- `currency` (INR)
- `advance_purchase_days` / `advance_purchase_window` (calculated programmatically)

## Fields Unavailable
- Unbundled fees (`base_fare`, `taxes`, `convenience_fee`), seats available count.

## Number of Real Observations Collected
- **1+** real observations collected live and saved into clean processed dataset (`data/processed/airfare_observations_20260917.csv`).

## Restrictions Encountered
- None on basic HTTP GET request.

## Raw Data Location
- `data/raw/yatra/`

## Processed Data Location
- `data/processed/`

## Tests
- `tests/test_yatra_parser.py` (3 tests passing with offline HTML fixture).

## Limitations
- Heavily nested DOM structure; required precise stripped string filtering for robust parsing.

## Recommended Status
- **`LIVE_WORKING`**
