# MakeMyTrip Final Access Investigation & Technical Evaluation

**Target**: MakeMyTrip (`makemytrip.com`)  
**Route Tested**: DEL → BOM  
**Date Tested**: 2026-10-17  
**Collection Method**: Standard permitted HTTP requests (`httpx` / `requests`)

---

## 1. Technical Access Evaluation

| Method Tested | Result | Technical Detail |
| :--- | :--- | :--- |
| **Direct Web Search** | `SOURCE_BLOCKED` | WAF / Connection Timeout / 403 Forbidden |
| **Public HTML State** | `UNAVAILABLE` | No unauthenticated static fare state exposed |
| **Public API Endpoint** | `SOURCE_BLOCKED` | Read operation timeout / WAF socket drops |
| **Authorized Partner API** | `API_REQUIRED` | Requires official MakeMyTrip B2B API access |

---

## 2. Final Conclusion

MakeMyTrip protects search interfaces with WAF transport filters. Classified as **`SOURCE_BLOCKED`**.
