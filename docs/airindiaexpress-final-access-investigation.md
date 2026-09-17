# Air India Express Final Access Investigation & Technical Evaluation

**Target**: Air India Express (`airindiaexpress.com`)  
**Route Tested**: DEL → BOM  
**Date Tested**: 2026-10-17  
**Collection Method**: Standard permitted HTTP requests (`httpx` / `requests`)

---

## 1. Technical Access Evaluation

| Method Tested | Result | Technical Detail |
| :--- | :--- | :--- |
| **Direct Web Search** | `SOURCE_BLOCKED` | Redirects (301) to `/page-not-found` via Akamai sensor |
| **Public HTML State** | `UNAVAILABLE` | Page contains Akamai sensor script payload |
| **Public API Endpoint** | `SOURCE_BLOCKED` | Redirects to WAF challenge |
| **Authorized Partner API** | `API_REQUIRED` | Requires official B2B/NDC API credentials |

---

## 2. Final Conclusion

Air India Express requires Akamai telemetry token evaluation. Classified as **`SOURCE_BLOCKED`**.
