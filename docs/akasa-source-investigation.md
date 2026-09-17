# Akasa Air Source Investigation & Technical Evaluation

**Target**: Akasa Air (`akasaair.com`)  
**Route Tested**: DEL → BOM  
**Date Tested**: 2026-10-17  
**Collection Method**: Standard permitted HTTP requests (`httpx` / `requests`)

---

## 1. Technical Access Evaluation

| Parameter | Result |
| :--- | :--- |
| **HTTP Status Code** | Timeout / Connection Reset / 403 |
| **Server Security** | Web Application Firewall (WAF) / Rate-Limiting Socket Filters |
| **TLS/Socket Fingerprinting** | Drops raw socket connection on automated search routes |
| **Automated Access Permitted** | No (Connection timeout on search endpoints) |
| **Status Classification** | `SOURCE_BLOCKED` |

---

## 2. Investigation Summary

- Direct GET requests to `https://www.akasaair.com/booking/search?origin=DEL&destination=BOM` fail with read operation timeouts on automated HTTP clients.
- Automated access without real-time browser rendering or anti-bot challenge completion is blocked at the network transport level.
- In strict adherence to project ethical guidelines (no stealth bypass, no proxy rotation), the adapter returns `SOURCE_BLOCKED`.
- The parser (`AkasaSource.parse_html`) is implemented and tested to extract 32-field `FareObservation` objects from DOM cards.
