# Air India Express Source Investigation & Technical Evaluation

**Target**: Air India Express (`airindiaexpress.com`)  
**Route Tested**: DEL → BOM  
**Date Tested**: 2026-10-17  
**Collection Method**: Standard permitted HTTP requests (`httpx` / `requests`)

---

## 1. Technical Access Evaluation

| Parameter | Result |
| :--- | :--- |
| **HTTP Status Code** | 301 Redirect to `/page-not-found` / 403 Forbidden |
| **Server WAF Detected** | **Akamai Bot Manager** |
| **WAF Challenge / Sensor** | Contains `/u5yVH/ci/Z0a/3d/iYdU4HJ` Akamai telemetry script |
| **TLS/Socket Fingerprinting** | Blocks non-browser TLS signatures and automated client user agents |
| **Automated Access Permitted** | No (Akamai WAF blocks direct HTTP access) |
| **Status Classification** | `SOURCE_BLOCKED` |

---

## 2. Investigation Summary

- Direct GET requests to `https://www.airindiaexpress.com/flights/search?src=DEL&dst=BOM&dt=2026-10-17` return an immediate HTTP 301 redirect or 403 forbidden error.
- Page body contains Akamai sensor scripts and challenge telemetry requiring JavaScript evaluation and browser fingerprinting.
- In strict adherence to project ethical guidelines (no stealth bypass, no anti-bot evasion), the system correctly flags this source as `SOURCE_BLOCKED`.
- The parser (`AirIndiaExpressSource.parse_html`) is fully implemented and unit-tested to handle valid flight card structures whenever HTML is provided.
