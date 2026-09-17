# Goibibo Final Access Investigation & Technical Evaluation

**Target**: Goibibo (`goibibo.com`)  
**Route Tested**: DEL → BOM  
**Date Tested**: 2026-10-17  
**Collection Method**: Standard permitted HTTP requests (`httpx` / `requests`)

---

## 1. Technical Access Evaluation

| Method Tested | Result | Technical Detail |
| :--- | :--- | :--- |
| **Direct Web Search** | `SOURCE_BLOCKED` | Returns Akamai `Challenge Validation` iframe page |
| **Public HTML State** | `UNAVAILABLE` | Payload contains sensor script challenge |
| **Public API Endpoint** | `SOURCE_BLOCKED` | Read operation timeout / Akamai WAF |
| **Authorized Partner API** | `API_REQUIRED` | Requires official Goibibo/MakeMyTrip B2B API |

---

## 2. Final Conclusion

Goibibo blocks unauthenticated HTTP calls using Akamai Bot Manager. Classified as **`SOURCE_BLOCKED`**.
