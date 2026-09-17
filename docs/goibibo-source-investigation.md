# Goibibo Source Investigation & Technical Evaluation

**Target**: Goibibo (`goibibo.com`)  
**Route Tested**: DEL → BOM  
**Date Tested**: 2026-10-17  
**Collection Method**: Standard permitted HTTP requests (`httpx` / `requests`)

---

## 1. Technical Access Evaluation

| Parameter | Result |
| :--- | :--- |
| **HTTP Status Code** | 200 OK (Akamai Challenge Page) |
| **Server WAF Detected** | **Akamai Bot Manager** |
| **Page Title** | `Challenge Validation` |
| **Challenge Sensor Script** | `/kCy-ELamfAKQKgd_LcOJMiq4/Qp/BUNFX1U/NU/ECZQ5EeXMs` |
| **Payload Structure** | Akamai JavaScript challenge iframe (`sec-if-container`) |
| **Automated Access Permitted** | No (Akamai bot detection blocks direct HTTP access) |
| **Status Classification** | `SOURCE_BLOCKED` |

---

## 2. Investigation Summary

- Direct HTTP GET requests to Goibibo search URLs (e.g. `https://www.goibibo.com/flights/air-DEL-BOM-20261017--1-0-0-E-g/`) return an Akamai `Challenge Validation` page (1,615 bytes).
- The response requires JavaScript evaluation and sensor telemetry submission before access to flight data is granted.
- In strict adherence to project ethical constraints (no CAPTCHA bypass, no browser fingerprint manipulation, no anti-bot evasion), Goibibo is classified as `SOURCE_BLOCKED`.
- The parser (`GoibiboSource.parse_html` and `GoibiboSource.parse_json`) is fully implemented and unit-tested to extract 32-field `FareObservation` objects from valid HTML/JSON payloads.
