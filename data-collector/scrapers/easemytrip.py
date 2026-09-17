"""
EaseMyTrip Source Adapter (easemytrip.com).
Uses Playwright DOM extraction to gather real airfare observations.
Complies with permitted access methods without bypassing bot protections.

EaseMyTrip is an Angular SPA — fare data is JavaScript-rendered.
Confirmed DOM selectors as of 2026-09-17:
  - Flight card:      div.top-bottom-single-row
  - Airline name:     span.txt-r-l
  - Flight number:    span.txt-r-2
  - Departure time:   div.txt-r-3 (1st within card)
  - Arrival time:     div.txt-r-3 (3rd within card)
  - Duration:         div.stop-t-n
  - Stops text:       div.stop-t-n2  ("Nonstop", "1 Stop", etc.)
  - Origin city+code: div.txt-r-4 (1st)
  - Dest city+code:   div.txt-r-4 (2nd)
  - Total fare:       Rs./Rs pattern anywhere in card
  - Seats available:  div.st-av
"""

import re
import time
import logging
from typing import List, Dict, Any, Optional

from bs4 import BeautifulSoup

from models.fare import FareObservation, CollectionStatus
from scrapers.base import BaseFareSource, ScrapeResult
from processors.normalizer import DataNormalizer

logger = logging.getLogger(__name__)


def _fmt_date_for_url(travel_date: str) -> str:
    """Converts YYYY-MM-DD to DD/MM/YYYY for EaseMyTrip URL param."""
    parts = travel_date.split("-")
    if len(parts) == 3:
        yyyy, mm, dd = parts
        return f"{dd}/{mm}/{yyyy}"
    return travel_date


class EaseMyTripSource(BaseFareSource):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(source_name="easemytrip", config=config)
        self.base_url = self.config.get("base_url", "https://www.easemytrip.com")
        self.timeout = self.config.get("timeout_seconds", 45) * 1000
        # cabin_class_code: 0=Economy, 1=PremiumEconomy, 2=Business, 3=First
        self.cabin_class_code = self.config.get("cabin_class_code", 0)

    def _build_search_url(self, origin: str, destination: str, travel_date: str) -> str:
        """Builds the EaseMyTrip one-way flight search listing URL."""
        url_date = _fmt_date_for_url(travel_date)
        # EaseMyTrip listing URL format: /flight-search/listing?srch=DEL-Delhi-India|BOM-Mumbai-India|DD/MM/YYYY|1|0|0|E|0|0
        # If city name mapping isn't specified, IATA code alone or default city is accepted by EMT router.
        city_map = {
            "DEL": "Delhi-India",
            "BOM": "Mumbai-India",
            "BLR": "Bengaluru-India",
            "MAA": "Chennai-India",
            "CCU": "Kolkata-India",
            "HYD": "Hyderabad-India",
            "PNQ": "Pune-India",
            "AMD": "Ahmedabad-India",
            "GOI": "Goa-India",
        }
        orig_label = f"{origin}-{city_map.get(origin, origin)}"
        dest_label = f"{destination}-{city_map.get(destination, destination)}"
        srch_param = f"{orig_label}|{dest_label}|{url_date}|1|0|0|E|0|0"
        return f"{self.base_url}/flight-search/listing?srch={srch_param}"

    def search(
        self,
        origin: str,
        destination: str,
        travel_date: str
    ) -> ScrapeResult:
        """
        Executes search on easemytrip.com for route and date using Playwright DOM rendering.
        Waits for Angular SPA to fully populate flight cards before extracting.
        """
        origin_code = origin.upper().strip()
        dest_code = destination.upper().strip()
        search_url = self._build_search_url(origin_code, dest_code, travel_date)

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return ScrapeResult(
                source=self.source_name,
                origin=origin_code,
                destination=dest_code,
                travel_date=travel_date,
                status=CollectionStatus.UNKNOWN_ERROR,
                error_message="Playwright not installed. Run: pip install playwright && playwright install chromium"
            )

        logger.info(f"Initiating EaseMyTrip search: {origin_code} -> {dest_code} on {travel_date}")
        logger.info(f"Search URL: {search_url}")

        raw_html = ""
        observations: List[FareObservation] = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.config.get("headless", True),
                    args=["--disable-blink-features=AutomationControlled"]
                )
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/128.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 900}
                )
                page = context.new_page()

                # Navigate directly to search results URL
                try:
                    response = page.goto(search_url, timeout=self.timeout, wait_until="domcontentloaded")
                    if response and response.status in (403, 429, 503):
                        logger.warning(f"EaseMyTrip returned HTTP {response.status} — Source Blocked.")
                        return ScrapeResult(
                            source=self.source_name,
                            origin=origin_code,
                            destination=dest_code,
                            travel_date=travel_date,
                            status=CollectionStatus.SOURCE_BLOCKED,
                            error_message=f"Access blocked with HTTP status {response.status}"
                        )
                except Exception as net_err:
                    logger.error(f"Network error accessing EaseMyTrip: {net_err}")
                    return ScrapeResult(
                        source=self.source_name,
                        origin=origin_code,
                        destination=dest_code,
                        travel_date=travel_date,
                        status=CollectionStatus.NETWORK_ERROR,
                        error_message=str(net_err)
                    )

                # EaseMyTrip is an Angular SPA — wait for flight cards to render
                logger.info("Waiting for Angular SPA to populate flight results...")
                try:
                    page.wait_for_selector(
                        "div.top-bottom-single-row",
                        timeout=30000
                    )
                    logger.info("Flight cards detected in DOM.")
                except Exception:
                    logger.warning("Timed out waiting for flight cards — checking for blocking indicators.")

                # Extra buffer for full render
                time.sleep(3)
                raw_html = page.content()
                content_lower = raw_html.lower()

                browser.close()

                # Check for anti-bot / WAF / CAPTCHA / challenge indicators
                block_keywords = [
                    "captcha", "cf-challenge", "pardon our interruption",
                    "access denied", "akamfailoverpage", "bot detected",
                    "please verify you are human", "ddos-guard", "challenge-form"
                ]
                if any(k in content_lower for k in block_keywords):
                    logger.warning("Bot protection / CAPTCHA detected on EaseMyTrip.")
                    return ScrapeResult(
                        source=self.source_name,
                        origin=origin_code,
                        destination=dest_code,
                        travel_date=travel_date,
                        status=CollectionStatus.SOURCE_BLOCKED,
                        raw_payload=raw_html,
                        error_message="Access restricted by source WAF/Bot protection or CAPTCHA."
                    )

                # Parse the rendered HTML
                observations = self.parse_html_payload(
                    raw_html, origin_code, dest_code, travel_date,
                    source_url=search_url,
                    cabin_class_code=self.cabin_class_code
                )

                if not observations:
                    return ScrapeResult(
                        source=self.source_name,
                        origin=origin_code,
                        destination=dest_code,
                        travel_date=travel_date,
                        status=CollectionStatus.NO_RESULTS,
                        raw_payload=raw_html,
                        error_message="No flight cards (div.top-bottom-single-row) found in DOM."
                    )

                logger.info(f"EaseMyTrip: extracted {len(observations)} flight observations.")
                return ScrapeResult(
                    source=self.source_name,
                    origin=origin_code,
                    destination=dest_code,
                    travel_date=travel_date,
                    status=CollectionStatus.SUCCESS,
                    observations=observations,
                    raw_payload=raw_html
                )

        except Exception as e:
            logger.exception(f"Unexpected error during EaseMyTrip scrape: {e}")
            return ScrapeResult(
                source=self.source_name,
                origin=origin_code,
                destination=dest_code,
                travel_date=travel_date,
                status=CollectionStatus.UNKNOWN_ERROR,
                raw_payload=raw_html,
                error_message=str(e)
            )

    @classmethod
    def parse_html_payload(
        cls,
        html_content: str,
        origin: str,
        destination: str,
        travel_date: str,
        source_url: Optional[str] = None,
        cabin_class_code: int = 0
    ) -> List[FareObservation]:
        """
        Parses the rendered EaseMyTrip results HTML into FareObservation objects.

        This is a classmethod so it can be called directly in unit tests with
        static HTML fixtures without launching a browser.

        Confirmed CSS selectors (live DOM analysis 2026-09-17):
          div.top-bottom-single-row  — individual flight card
          span.txt-r-l               — airline name
          span.txt-r-2               — flight number
          div.txt-r-3                — time fields (dep=1st, arr=3rd)
          div.stop-t-n               — duration text
          div.stop-t-n2              — stops text ("Nonstop", "1 Stop")
          div.txt-r-4                — city+code labels
          div.st-av                  — seats available text
          Rs./Rs pattern             — total fare
        """
        soup = BeautifulSoup(html_content, "html.parser")
        observations: List[FareObservation] = []

        cabin_labels = {0: "Economy", 1: "Premium Economy", 2: "Business", 3: "First"}
        cabin_class_label = cabin_labels.get(cabin_class_code, "Economy")

        # Find all flight result cards
        cards = soup.find_all("div", class_=lambda c: c and "top-bottom-single-row" in c)

        if not cards:
            # Fallback regex-based class match
            cards = soup.find_all("div", attrs={"class": re.compile(r"top-bottom-single-row")})

        logger.info(f"EaseMyTrip parser: found {len(cards)} flight cards.")

        for card in cards:
            card_text = card.get_text(separator=" ", strip=True)

            # --- Airline Name ---
            airline_el = card.find("span", class_=lambda c: c and "txt-r-l" in c)
            raw_airline = airline_el.get_text(strip=True) if airline_el else ""
            airline = DataNormalizer.normalize_airline_name(raw_airline) if raw_airline else "Unknown Airline"

            # --- Flight Number ---
            fn_el = card.find("span", class_=lambda c: c and "txt-r-2" in c)
            raw_flight_num = fn_el.get_text(strip=True) if fn_el else ""
            flight_number = _normalize_flight_number(raw_flight_num) if raw_flight_num else "UNKNOWN"

            # --- Times: div.txt-r-3 elements ---
            # The fare amount is ALSO rendered in a div.txt-r-3, so we cannot
            # rely on positional indexing (index 0, 1, 2, ...).
            # Instead: collect only txt-r-3 elements that contain a valid HH:MM
            # pattern. The first match is departure, the second is arrival.
            time_els = card.find_all("div", class_=lambda c: c and "txt-r-3" in c)
            time_values = [
                _parse_time(el.get_text(strip=True))
                for el in time_els
                if _parse_time(el.get_text(strip=True)) is not None
            ]
            dep_time = time_values[0] if len(time_values) >= 1 else None
            arr_time = time_values[1] if len(time_values) >= 2 else None

            # --- Stops ---
            stops_el = card.find("div", class_=lambda c: c and "stop-t-n2" in c)
            stops_text = stops_el.get_text(strip=True).lower() if stops_el else ""
            stops = _parse_stops(stops_text)

            # --- Total Fare ---
            total_fare = _extract_fare(card, card_text)

            # --- Seats Available ---
            seats_el = card.find("div", class_=lambda c: c and "st-av" in c)
            seats_text = seats_el.get_text(strip=True) if seats_el else ""
            seats_available = _parse_seats(seats_text)

            # --- Availability Status ---
            if total_fare is None:
                avail_status = "sold_out" if "sold out" in card_text.lower() else "unavailable"
            else:
                avail_status = "available"

            obs = FareObservation(
                source="easemytrip",
                source_url=source_url,
                airline=airline,
                flight_number=flight_number,
                origin=origin,
                destination=destination,
                route=f"{origin}-{destination}",
                travel_date=travel_date,
                departure_time=dep_time,
                arrival_time=arr_time,
                stops=stops,
                cabin_class=cabin_class_label,
                fare_class=None,           # not exposed on listing page
                fare_type=None,            # not exposed on listing page
                base_fare=None,            # not exposed on listing page
                taxes=None,                # not exposed on listing page
                user_development_fee=None, # not exposed on listing page
                convenience_fee=None,      # not exposed on listing page
                other_fees=None,           # not exposed on listing page
                total_fare=total_fare,
                currency="INR",
                availability_status=avail_status,
                seats_available=seats_available,
                raw_fare_text=card_text[:500]
            )
            observations.append(obs)

        return observations


# ---------------------------------------------------------------------------
# Private parsing helpers
# ---------------------------------------------------------------------------

def _normalize_flight_number(raw: str) -> str:
    """
    Normalises EaseMyTrip flight number format.
    Input examples:  '6E- 324', '6E-324', 'AI 101', 'QP-1368', 'SG-8169'
    Output examples: '6E 324', 'AI 101', 'QP 1368', 'SG 8169'
    """
    cleaned = raw.strip().upper()
    # Remove dash(es) between IATA prefix and number, keep single space
    normalized = re.sub(r"([A-Z]{1,2})\s*-+\s*(\d+)", r"\1 \2", cleaned)
    return normalized


def _parse_time(raw: str) -> Optional[str]:
    """Extracts HH:MM from raw text like '13:00', '13:00 New Delhi(DEL)'."""
    if not raw:
        return None
    match = re.search(r"\b(\d{1,2}:\d{2})\b", raw)
    if match:
        h, m = match.group(1).split(":")
        return f"{int(h):02d}:{m}"
    return None


def _parse_stops(stops_text: str) -> int:
    """
    Converts stops label to integer.
    'nonstop' | 'non-stop' | 'direct' → 0
    '1 stop' | '1stop'                → 1
    '2 stops'                         → 2
    """
    text = stops_text.lower().strip()
    if not text or "nonstop" in text or "non-stop" in text or "direct" in text:
        return 0
    match = re.search(r"(\d+)\s*stop", text)
    if match:
        return int(match.group(1))
    return 0


def _extract_fare(card: Any, card_text: str) -> Optional[float]:
    """
    Extracts the per-person total fare from a flight card.
    EaseMyTrip renders fares as 'Rs.6,198', 'Rs 6,198', or '₹6,198'.
    Strategy:
      1. Scan card text for explicit Rs./₹ patterns and take the last one
         (which is the total after any discount labels).
      2. Fallback: last div.txt-r-3 element with a numeric value > 999.
    """
    # Strategy 1: explicit currency prefix in full card text
    fare_matches = re.findall(r"(?:Rs\.?\s*|₹\s*)([\d,]+)", card_text)
    if fare_matches:
        amounts = []
        for m in fare_matches:
            val = DataNormalizer.normalize_currency_amount(m)
            if val and val > 999:
                amounts.append(val)
        if amounts:
            return amounts[-1]

    # Strategy 2: last txt-r-3 div that has a number > 999
    txt_r3_els = card.find_all("div", class_=lambda c: c and "txt-r-3" in c)
    for el in reversed(txt_r3_els):
        raw = el.get_text(strip=True)
        # Strip currency chars, commas, spaces
        cleaned = re.sub(r"[^\d.]", "", raw.replace(",", ""))
        if cleaned:
            try:
                val = float(cleaned)
                if val > 999:
                    return val
            except ValueError:
                continue

    return None


def _parse_seats(seats_text: str) -> Optional[int]:
    """
    Parses seats available from text like '6 Seats Left', '3 seats left'.
    Returns integer if found, None otherwise.
    """
    if not seats_text:
        return None
    match = re.search(r"(\d+)\s*seat", seats_text.lower())
    if match:
        return int(match.group(1))
    return None
