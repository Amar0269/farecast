# SpiceJet Source Investigation & Technical Evaluation

**Target**: SpiceJet (`spicejet.com` / `book.spicejet.com`)  
**Route Tested**: DEL → BOM  
**Date Tested**: 2026-10-17  
**Collection Method**: Standard permitted HTTP requests (`httpx` / `requests`)

---

## 1. Technical Access Evaluation

| Parameter | Result |
| :--- | :--- |
| **HTTP Status Code** | 200 OK (ASP.NET Shell) |
| **Server WAF Detected** | **Cloudflare** |
| **Payload Structure** | ASP.NET Web Form / JS App Shell ("Please wait...") |
| **Automated Data Access** | Dynamic JavaScript execution and ASP.NET ViewState required |
| **Status Classification** | `SOURCE_BLOCKED` |

---

## 2. Investigation Summary

- Direct HTTP GET to `https://book.spicejet.com/Search.aspx` returns an initial ASP.NET application shell (369 KB) with placeholder elements and a "Please wait..." loading message.
- Flight fare schedules are loaded dynamically via ASP.NET postbacks and JavaScript API invocations protected by Cloudflare.
- Standard static HTTP fetching yields no rendered flight observations without dynamic execution.
- In strict adherence to project ethical guidelines, SpiceJet is marked as `SOURCE_BLOCKED`.
- The parser (`SpiceJetSource.parse_html`) is implemented and tested to extract observations when DOM flight cards are present.
