# Air India Final Access Investigation & Technical Evaluation

**Target**: Air India (`airindia.com`)  
**Route Tested**: DEL → BOM  
**Date Tested**: 2026-10-17  
**Collection Method**: Standard permitted HTTP requests (`httpx` / `requests`)

---

## 1. Technical Access Evaluation

| Method Tested | Result | Technical Detail |
| :--- | :--- | :--- |
| **Direct Web Search** | `SOURCE_BLOCKED` | Akamai WAF / Connection timeout |
| **Public HTML State** | `UNAVAILABLE` | Server-side rendering blocked by Akamai |
| **Public API Endpoint** | `SOURCE_BLOCKED` | Read operation timeout / WAF protection |
| **Authorized Partner API** | `API_REQUIRED` | Requires official IATA NDC API access |

---

## 2. Final Conclusion

Air India protects its booking portal using Akamai WAF and TLS fingerprinting. Air India is classified as **`SOURCE_BLOCKED`**.
