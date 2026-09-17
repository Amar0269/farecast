# Ixigo Final Access Investigation & Technical Evaluation

**Target**: Ixigo (`ixigo.com`)  
**Route Tested**: DEL → BOM  
**Date Tested**: 2026-10-17  
**Collection Method**: Standard permitted HTTP requests (`httpx` / `requests`)

---

## 1. Technical Access Evaluation

| Method Tested | Result | Technical Detail |
| :--- | :--- | :--- |
| **Direct Web Search** | `SOURCE_BLOCKED` | HTTP 403 Forbidden / Anti-bot |
| **Public HTML State** | `UNAVAILABLE` | Next.js shell with client JS hydration required |
| **Public API Endpoint** | `404 Not Found` | Internal API endpoints return 404/403 |
| **Authorized Partner API** | `API_REQUIRED` | Requires official affiliate/partner credentials |

---

## 2. Final Conclusion

Ixigo uses client-side API hydration protected by WAF and session tokens. In compliance with project guidelines, Ixigo is permanently classified as **`SOURCE_BLOCKED`**.
