# MakeMyTrip Source Investigation & Technical Evaluation

**Target**: MakeMyTrip (`makemytrip.com`)  
**Route Tested**: DEL → BOM  
**Date Tested**: 2026-10-17  
**Collection Method**: Standard permitted HTTP requests (`httpx` / `requests`)

---

## 1. Technical Access Evaluation

| Parameter | Result |
| :--- | :--- |
| **HTTP Status Code** | Connection Timeout / HTTP 403 Forbidden |
| **Server Security** | Web Application Firewall (WAF) / Akamai Bot Manager |
| **TLS/Socket Fingerprinting** | Connection reset / read operation timeout on automated HTTP requests |
| **Automated Access Permitted** | No (Transport layer blocking and WAF rate-limiting) |
| **Status Classification** | `SOURCE_BLOCKED` |

---

## 2. Investigation Summary

- Direct HTTP GET requests to `https://www.makemytrip.com/flight/search?itinerary=DEL-BOM-17/10/2026` fail with read operation timeouts and socket drops.
- MakeMyTrip deploys strict anti-bot security controls at both the network transport layer and WAF level to prevent automated extraction of airfares.
- In strict adherence to project ethical constraints (no stealth evasion, no IP/proxy rotation, no fingerprint manipulation), MakeMyTrip is classified as `SOURCE_BLOCKED`.
- The parser (`MakeMyTripSource.parse_html` and `MakeMyTripSource.parse_json`) is implemented and unit-tested to parse 32-field `FareObservation` objects from valid HTML/JSON flight cards.
