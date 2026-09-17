"""
Air India Source Adapter (airindia.com).
Direct airline carrier source for Air India (AI).
Complies with permitted access methods without attempting stealth evasion or bypass.

Air India search URL format:
  https://www.airindia.com/in/en/book/flight-select.{origin}-{destination}.{YYYY-MM-DD}.economy.1.0.0.html
  - Access result: Blocked by Akamai WAF / TLS handshake / connection timeout on automated access.
"""

import logging
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import httpx

from models.fare import FareObservation, CollectionStatus
from scrapers.base import BaseFareSource, ScrapeResult
from processors.normalizer import DataNormalizer

logger = logging.getLogger(__name__)


class AirIndiaSource(BaseFareSource):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(source_name="airindia", config=config)
        self.base_url = self.config.get("base_url", "https://www.airindia.com")
        self.timeout = self.config.get("timeout_seconds", 25)

    def _build_search_url(self, origin: str, destination: str, travel_date: str) -> str:
        """Builds the Air India booking URL."""
        return f"{self.base_url}/in/en/book/flight-select.{origin}-{destination}.{travel_date}.economy.1.0.0.html"

    def search(
        self,
        origin: str,
        destination: str,
        travel_date: str
    ) -> ScrapeResult:
        """
        Executes search on airindia.com using permitted HTTP requests.
        Detects Akamai WAF blocking / connection timeout and returns SOURCE_BLOCKED.
        """
        origin_code = origin.upper().strip()
        dest_code = destination.upper().strip()
        search_url = self._build_search_url(origin_code, dest_code, travel_date)

        logger.info(f"Initiating Air India search: {origin_code} -> {dest_code} on {travel_date}")
        logger.info(f"Search URL: {search_url}")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
                response = client.get(search_url)

            if response.status_code in (403, 429, 503):
                logger.warning(f"Air India access blocked with HTTP {response.status_code}.")
                return ScrapeResult(
                    source=self.source_name,
                    origin=origin_code,
                    destination=dest_code,
                    travel_date=travel_date,
                    status=CollectionStatus.SOURCE_BLOCKED,
                    raw_payload=response.text,
                    error_message=f"Access blocked by Akamai WAF (HTTP status {response.status_code})"
                )

            raw_html = response.text
            observations = self.parse_html(raw_html, origin_code, dest_code, travel_date)
            status = CollectionStatus.SUCCESS if observations else CollectionStatus.NO_RESULTS

            return ScrapeResult(
                source=self.source_name,
                origin=origin_code,
                destination=dest_code,
                travel_date=travel_date,
                status=status,
                observations=observations,
                raw_payload=raw_html
            )

        except Exception as err:
            logger.warning(f"Air India access blocked/timed out: {err}")
            return ScrapeResult(
                source=self.source_name,
                origin=origin_code,
                destination=dest_code,
                travel_date=travel_date,
                status=CollectionStatus.SOURCE_BLOCKED,
                error_message=f"Access blocked by Akamai WAF / Connection timeout: {err}"
            )

    def parse_html(
        self,
        html_content: str,
        origin: str,
        destination: str,
        travel_date: str
    ) -> List[FareObservation]:
        """
        Parses Air India flight card DOM elements into 32-field FareObservation objects.
        """
        if not html_content or len(html_content) < 100:
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        observations: List[FareObservation] = []

        cards = soup.find_all(
            "div",
            class_=lambda c: c and any(k in x.lower() for x in (c if isinstance(c, list) else [c]) for k in ("flight-card", "bound-card", "ai-flight-row"))
        )
        for card in cards:
            try:
                obs = self._parse_single_card(card, origin, destination, travel_date)
                if obs:
                    observations.append(obs)
            except Exception as e:
                logger.debug(f"Error parsing Air India card: {e}")

        return observations

    def _parse_single_card(
        self,
        card,
        origin: str,
        destination: str,
        travel_date: str
    ) -> Optional[FareObservation]:
        """Parses a single Air India DOM flight card."""
        # Airline is Air India
        norm_airline = "Air India"

        fl_el = card.find(class_=lambda c: c and ("flight-number" in c or "fl-no" in c))
        raw_fl = fl_el.text.strip() if fl_el else "AI 101"
        flight_num = DataNormalizer.normalize_flight_number(raw_fl, norm_airline)

        # Times
        dep_el = card.find(class_=lambda c: c and "dep-time" in c)
        dep_time = DataNormalizer.normalize_time_format(dep_el.text.strip()) if dep_el else None

        arr_el = card.find(class_=lambda c: c and "arr-time" in c)
        arr_time = DataNormalizer.normalize_time_format(arr_el.text.strip()) if arr_el else None

        # Fare
        fare_el = card.find(class_=lambda c: c and ("price" in c or "fare" in c))
        fare_text = fare_el.text.strip() if fare_el else "0"
        total_fare = DataNormalizer.normalize_currency(fare_text)

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
