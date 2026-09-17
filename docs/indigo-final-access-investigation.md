# IndiGo Final Access Investigation & Technical Evaluation

**Target**: IndiGo (`goindigo.in`)  
**Route Tested**: DEL → BOM  
**Date Tested**: 2026-10-17  
**Collection Method**: Standard permitted HTTP requests (`httpx` / `requests`)

---

## 1. Technical Access Evaluation

| Method Tested | Result | Technical Detail |
| :--- | :--- | :--- |
| **Direct Web Search** | `SOURCE_BLOCKED` | Akamai WAF blocks non-browser TLS / User-Agent |
| **Public HTML State** | `UNAVAILABLE` | No unauthenticated SSR HTML fare payload |
| **Public API Endpoint** | `SOURCE_BLOCKED` | Timeout / Akamai WAF protection on `/api/*` |
| **Authorized Partner API** | `API_REQUIRED` | Requires official partner credentials / NDC API |

---

## 2. Final Conclusion

IndiGo requires official partner API credentials or Akamai telemetry verification. In strict compliance with project guidelines (no stealth bypass, no bot-evasion), IndiGo is permanently classified as **`SOURCE_BLOCKED`** for unauthenticated automated HTTP collection.
