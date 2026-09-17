# IndiGo Source Investigation Document

**Target Source**: IndiGo Official Website (`https://www.goindigo.in`)  
**Investigation Date**: September 17, 2026  
**Investigator**: Lead Software Engineer - Member 1 (Data Collection + Data Cleaning)  
**Project**: SIH26056 - Real-time Airfare Price Index for India (MoSPI / DIID)

---

## 1. Overview & Official Status

- **Official Website**: `https://www.goindigo.in/`
- **Robots.txt Status**: Accessible at `https://www.goindigo.in/robots.txt`
  - Key disallow paths include `/search.html`, `/bookings/*`, `/book/*`, `/booking/*`, `/content/skyplus6e/in/en/bookings/*`.
- **Developer API Portal**: `https://developer.goindigo.in`
  - Current status: Inaccessible / Returns 502 Bad Gateway.
  - Industry Standards: IndiGo utilizes IATA NDC (New Distribution Capability) XML-based API v21.3 for authorized travel agents & aggregators, requiring formal partner onboarding and credentials.

---

## 2. Flight Search & Booking Workflow

The search workflow follows a multi-step dynamic Single-Page Application (SPA) structure:

1. **Homepage (`/`)**:
   - Contains dynamic React search widget inside `[role="main"][aria-label="Booking Widget"]`.
   - Trip selection: One-way, Round-trip, Multi-city.
   - Input fields: Origin (From dropdown/combobox), Destination (To dropdown/combobox), Departure Date (React-Date-Range calendar picker).
   - Special fare chips: Standard, Student, Senior Citizen, Armed Forces, Family & Friends, Doctors & Nurses.

2. **Search Submission & Results Page (`/book/flight-select.html`)**:
   - Client-side navigation to flight selection page.
   - Page renders flight list cards dynamically via client-side JavaScript.
   - Displays carrier details (`6E`), flight numbers (e.g. `6E 449`, `6E 353`, `6E 5198`), departure/arrival times, departure airport terminals (T1, T2), route duration, and number of stops (`Non-stop`).

3. **Fare Classes & Family Comparison**:
   - Each flight presents multiple fare tiers / cabin options:
     - **IndiGo Lite Fare**: 7 kg Cabin bag only, no check-in bag.
     - **Saver Fare**: 7 kg Cabin bag + 15 kg Check-in bag.
     - **Flexi Plus Fare**: 7 kg Cabin bag + 15 kg Check-in bag, free seat selection, lower change fees, complimentary snack.
     - **IndiGo UpFront / Stretch (Business)**: Front-row economy or business cabin, extra legroom, 20 kg baggage allowance.

4. **Fare Breakdown Drawer**:
   - Clicking "View Details" on a selected flight tier opens a side drawer exposing:
     - **Base Airfare**: (e.g. ₹5,080 for DEL-BOM)
     - **Taxes & Fees**: (e.g. ₹1,466 for DEL-BOM)
     - **Total Fare**: (e.g. ₹6,546 for DEL-BOM)

---

## 3. Data Field Availability Analysis (Standardized 32-Field Schema)

| Field # | Field Name | Availability Status | Source / Location on Site |
|:---|:---|:---|:---|
| 1 | `observation_id` | **Generated** | UUID v4 generated upon extraction |
| 2 | `source` | **Available** | Standard string: `"indigo"` |
| 3 | `source_url` | **Available** | `https://www.goindigo.in/book/flight-select.html` |
| 4 | `collection_timestamp` | **Generated** | ISO 8601 UTC timestamp at run time |
| 5 | `airline` | **Available** | `"IndiGo"` |
| 6 | `flight_number` | **Available** | Flight card header (e.g., `"6E 449"`, `"6E 353"`) |
| 7 | `origin` | **Available** | Search selection / Airport badge (`"DEL"`) |
| 8 | `destination` | **Available** | Search selection / Airport badge (`"BOM"`) |
| 9 | `route` | **Derived** | `"DEL-BOM"` |
| 10 | `travel_date` | **Available** | Calendar selection (`"YYYY-MM-DD"`) |
| 11 | `departure_time` | **Available** | Flight card text (e.g., `"05:00"`) |
| 12 | `arrival_time` | **Available** | Flight card text (e.g., `"07:15"`) |
| 13 | `stops` | **Available** | Flight card text (`0` for Non-stop) |
| 14 | `cabin_class` | **Available** | `"Economy"`, `"Stretch | Business"` |
| 15 | `fare_class` | **Available** | Tiers: `"Lite"`, `"Saver"`, `"Flexi Plus"`, `"UpFront"` |
| 16 | `fare_type` | **Available** | Tiers / Special Fares (`"Standard"`, `"Student"`, etc.) |
| 17 | `base_fare` | **Partially Available** | Exposed in Fare Details breakdown drawer (`₹5,080`) |
| 18 | `taxes` | **Partially Available** | Exposed in Fare Details breakdown drawer (`₹1,466`) |
| 19 | `user_development_fee` | **Unavailable** | Itemized UDF bundled under Total Tax (`null`) |
| 20 | `convenience_fee` | **Unavailable** | Applied at final payment step (`null`) |
| 21 | `other_fees` | **Unavailable** | Bundled (`null`) |
| 22 | `total_fare` | **Available** | Prominently displayed on flight cards (`₹6,546`) |
| 23 | `currency` | **Available** | `"INR"` |
| 24 | `availability_status` | **Available** | `"available"`, `"sold_out"` |
| 25 | `seats_available` | **Unavailable** | Not explicitly enumerated on card unless low stock (`null`) |
| 26 | `advance_purchase_days` | **Calculated** | `(travel_date - collection_date).days` |
| 27 | `advance_purchase_window` | **Calculated** | Classification (`"T+1"`, `"T+7"`, `"T+15"`, `"T+30"`, `"T+45"`, `"Other"`) |
| 28 | `raw_fare_text` | **Preserved** | Raw HTML / JSON snippet captured from card |
| 29 | `cleaning_status` | **Pipeline Generated** | `"CLEAN"`, `"WARNING"`, `"INVALID"` |
| 30 | `outlier_flag` | **Pipeline Generated** | `true` / `false` based on IQR check |
| 31 | `duplicate_flag` | **Pipeline Generated** | `true` / `false` based on deterministic key |
| 32 | `missing_fields` | **Pipeline Generated** | List of null fields e.g., `["user_development_fee", "convenience_fee"]` |

---

## 4. Technical Strategy for Collector Implementation

- **Automation Technology**: Playwright (Python async/sync API) for headless Chromium rendering.
- **Workflow**:
  1. Initialize Playwright browser context with standard user-agent.
  2. Navigate directly to search page URL with formatted search query parameters or perform form interaction.
  3. Wait for flight results container selector to load.
  4. Extract all rendered flight card nodes into raw string representations.
  5. Save raw search response to `data/raw/` with metadata (timestamp, route, travel date).
  6. Parse individual flight cards into standard observation objects.
  7. Pass observations to the normalization and cleaning pipeline.
- **Security & Ethics Compliance**:
  - Respect rate limits and apply conservative request delays.
  - No CAPTCHA/anti-bot bypass attempt.
  - If access is blocked, return `SOURCE_BLOCKED` status safely without crashing or fabricating fake data.
