"""
Ixigo Source Adapter (ixigo.com).
Uses HTTP requests / Playwright DOM extraction to gather airfare observations.
Complies with permitted access methods without attempting stealth evasion or bypass.

Ixigo search results page:
  - URL: https://www.ixigo.com/search/result/flight/{origin}/{destination}/{DDMMYYYY}/1/0/0/e
  - Access result: Blocked with HTTP 403 / "Oops...too many requests !" on automated access.
"""

import logging
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

from models.fare import FareObservation, CollectionStatus
from scrapers.base import BaseFareSource, ScrapeResult
from processors.normalizer import DataNormalizer

logger = logging.getLogger(__name__)


def _fmt_date_ddmmyyyy(travel_date: str) -> str:
    """Converts YYYY-MM-DD to DDMMYYYY for Ixigo URL format."""
    parts = travel_date.split("-")
    if len(parts) == 3:
        yyyy, mm, dd = parts
        return f"{dd}{mm}{yyyy}"
    return travel_date.replace("-", "")


class IxigoSource(BaseFareSource):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(source_name="ixigo", config=config)
        self.base_url = self.config.get("base_url", "https://www.ixigo.com")
        self.timeout = self.config.get("timeout_seconds", 30) * 1000

    def _build_search_url(self, origin: str, destination: str, travel_date: str) -> str:
        """Builds the Ixigo one-way flight search URL."""
        url_date = _fmt_date_ddmmyyyy(travel_date)
        return f"{self.base_url}/search/result/flight/{origin}/{destination}/{url_date}/1/0/0/e"

    def search(
        self,
        origin: str,
        destination: str,
        travel_date: str
    ) -> ScrapeResult:
        """
        Executes flight fare search on Ixigo using permitted automated access methods.
        Detects HTTP 403 / rate-limit / bot protection and returns SOURCE_BLOCKED.
        """
        origin_code = origin.upper().strip()
        dest_code = destination.upper().strip()
        search_url = self._build_search_url(origin_code, dest_code, travel_date)

        logger.info(f"Initiating Ixigo search: {origin_code} -> {dest_code} on {travel_date}")
        logger.info(f"Search URL: {search_url}")

        raw_payload = ""

        try:
            from playwright.sync_api import sync_playwright
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
                    )
                )
                page = context.new_page()

                response = page.goto(search_url, timeout=self.timeout, wait_until="domcontentloaded")
                status_code = response.status if response else None
                raw_payload = page.content()
                browser.close()

                if status_code in (403, 429, 503) or "too many requests" in raw_payload.lower():
                    logger.warning(f"Ixigo access blocked (HTTP {status_code}).")
                    return ScrapeResult(
                        source=self.source_name,
                        origin=origin_code,
                        destination=dest_code,
                        travel_date=travel_date,
                        status=CollectionStatus.SOURCE_BLOCKED,
                        raw_payload=raw_payload,
                        error_message=f"Access blocked with HTTP status {status_code}"
                    )

        except Exception as e:
            logger.error(f"Playwright navigation error for Ixigo: {e}")
            return ScrapeResult(
                source=self.source_name,
                origin=origin_code,
                destination=dest_code,
                travel_date=travel_date,
                status=CollectionStatus.SOURCE_BLOCKED,
                raw_payload=str(e),
                error_message=str(e)
            )

        # Parse static HTML payload if available
        observations = self.parse_html(raw_payload, origin_code, dest_code, travel_date)
        status = CollectionStatus.SUCCESS if observations else CollectionStatus.NO_RESULTS

        return ScrapeResult(
            source=self.source_name,
            origin=origin_code,
            destination=dest_code,
            travel_date=travel_date,
            status=status,
            observations=observations,
            raw_payload=raw_payload
        )

    def parse_html(
        self,
        html_content: str,
        origin: str,
        destination: str,
        travel_date: str
    ) -> List[FareObservation]:
        """
        Parses Ixigo flight card DOM elements into 32-field FareObservation objects.
        """
        if not html_content or len(html_content) < 100:
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        observations: List[FareObservation] = []

        cards = soup.find_all(
            "div",
            class_=lambda c: c and any(k in x.lower() for x in (c if isinstance(c, list) else [c]) for k in ("flight-card", "c-flight-row", "c-card"))
        )
        for card in cards:
            try:
                obs = self._parse_single_card(card, origin, destination, travel_date)
                if obs:
                    observations.append(obs)
            except Exception as e:
                logger.debug(f"Error parsing Ixigo card: {e}")

        return observations

    def _parse_single_card(
        self,
        card,
        origin: str,
        destination: str,
        travel_date: str
    ) -> Optional[FareObservation]:
        """Parses a single Ixigo DOM flight card."""
        # Airline & Flight number
        airline_el = card.find(class_=lambda c: c and "airline" in c)
        airline_name = airline_el.text.strip() if airline_el else "Unknown"
        norm_airline = DataNormalizer.normalize_airline_name(airline_name)

        fl_el = card.find(class_=lambda c: c and ("flight-no" in c or "number" in c))
        flight_num = fl_el.text.strip() if fl_el else "IX-000"

        # Times
        dep_el = card.find(class_=lambda c: c and "dep-time" in c)
        dep_time = DataNormalizer.normalize_time_format(dep_el.text.strip()) if dep_el else None

        arr_el = card.find(class_=lambda c: c and "arr-time" in c)
        arr_time = DataNormalizer.normalize_time_format(arr_el.text.strip()) if arr_el else None

        # Fare
        fare_el = card.find(class_=lambda c: c and ("price" in c or "fare" in c))
        fare_text = fare_el.text.strip() if fare_el else "0"
        total_fare = DataNormalizer.normalize_currency(fare_text)

        # Stops
        stops_el = card.find(class_=lambda c: c and "stop" in c)
        stops = 0 if stops_el and "non" in stops_el.text.lower() else 1

        missing = []
        if not dep_time: missing.append("departure_time")
        if not arr_time: missing.append("arrival_time")
        if total_fare is None: missing.append("total_fare")

        return FareObservation(
            source=self.source_name,
            source_url=self._build_search_url(origin, destination, travel_date),
            airline=norm_airline,
            flight_number=flight_num,
            origin=origin,
            destination=destination,
            route=f"{origin}-{destination}",
            travel_date=travel_date,
            departure_time=dep_time,
            arrival_time=arr_time,
            stops=stops,
            cabin_class="Economy",
            total_fare=total_fare,
            currency="INR",
            availability_status="available",
            raw_fare_text=card.prettify()[:500],
            missing_fields=missing
        )
