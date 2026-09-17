# Akasa Air Final Access Investigation & Technical Evaluation

**Target**: Akasa Air (`akasaair.com`)  
**Route Tested**: DEL → BOM  
**Date Tested**: 2026-10-17  
**Collection Method**: Standard permitted HTTP requests (`httpx` / `requests`)

---

## 1. Technical Access Evaluation

| Method Tested | Result | Technical Detail |
| :--- | :--- | :--- |
| **Direct Web Search** | `SOURCE_BLOCKED` | WAF transport layer connection timeout |
| **Public HTML State** | `UNAVAILABLE` | Base homepage loads, search routes time out |
| **Public API Endpoint** | `404 Not Found` | Candidate endpoints return HTTP 404 |
| **Authorized Partner API** | `API_REQUIRED` | Requires official partner API credentials |

---

## 2. Final Conclusion

Akasa Air drops direct socket connections on search paths. Classified as **`SOURCE_BLOCKED`**.
