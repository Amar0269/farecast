# Cleartrip Final Access Investigation & Technical Evaluation

**Target**: Cleartrip (`cleartrip.com`)  
**Route Tested**: DEL → BOM  
**Date Tested**: 2026-10-17  
**Collection Method**: Standard permitted HTTP requests (`httpx` / `requests`)

---

## 1. Technical Access Evaluation

| Method Tested | Result | Technical Detail |
| :--- | :--- | :--- |
| **Direct Web Search** | `SOURCE_BLOCKED` | Next.js shell with empty `results.data` (`isLoading: true`) |
| **Public HTML State** | `UNAVAILABLE` | Requires client-side JS fetch for results |
| **Public API Endpoint** | `401 Unauthorized` | Candidates return HTTP 401 without Akamai token |
| **Authorized Partner API** | `API_REQUIRED` | Requires official B2B/Affiliate API key |

---

## 2. Final Conclusion

Cleartrip API endpoints require client-side Akamai tokens. Classified as **`SOURCE_BLOCKED`**.
