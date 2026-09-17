# Source Investigation: Ixigo

## Source
- **Name**: Ixigo (ixigo.com)
- **Target Category**: Online Travel Agency (OTA)

## Search URL / Workflow
- **Search URL Format**: `https://www.ixigo.com/search/result/flight/{origin}/{destination}/{DDMMYYYY}/1/0/0/e`
- **Example**: `https://www.ixigo.com/search/result/flight/DEL/BOM/17102026/1/0/0/e`

## Access Method Tested
1. Direct HTTP GET via `httpx` and `requests`.
2. Playwright Chromium headless DOM navigation.

## Data Delivery Mechanism
- JavaScript-rendered single-page app (SPA) backed by private internal search APIs.

## Live Access Result
- **Status**: `SOURCE_BLOCKED`
- **HTTP Code**: 403 Access Denied / "Oops...too many requests !"
- **Behavior**: Ixigo employs strict Cloudflare anti-bot and rate-limiting rules that reject automated headless browser navigation and non-browser HTTP clients.

## Fields Successfully Extracted
- Extracted via offline static DOM parser: `airline`, `flight_number`, `origin`, `destination`, `route`, `travel_date`, `departure_time`, `arrival_time`, `stops`, `total_fare`, `currency`.

## Fields Unavailable
- Unbundled fees (`base_fare`, `taxes`, `convenience_fee`), exact seats available.

## Number of Real Observations Collected
- **0** (live access blocked by Cloudflare anti-bot).

## Restrictions Encountered
- Cloudflare bot challenge and HTTP 403 access denial.

## Raw Data Location
- `data/raw/ixigo/`

## Processed Data Location
- `data/processed/`

## Tests
- `tests/test_ixigo_parser.py` (3 tests passing with offline HTML fixture).

## Limitations
- Automated collection blocked without official API key or authorized access credentials.

## Recommended Status
- **`SOURCE_BLOCKED`**
