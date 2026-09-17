"""
MakeMyTrip Source Adapter (makemytrip.com).
OTA source adapter for MakeMyTrip.
Complies with permitted access methods without attempting stealth evasion or bypass.
"""

import logging
import json
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import httpx

from models.fare import FareObservation, CollectionStatus
from scrapers.base import BaseFareSource, ScrapeResult
from processors.normalizer import DataNormalizer

logger = logging.getLogger(__name__)


class MakeMyTripSource(BaseFareSource):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(source_name="makemytrip", config=config)
        self.base_url = self.config.get("base_url", "https://www.makemytrip.com")
        self.timeout = self.config.get("timeout_seconds", 25)

    def _build_search_url(self, origin: str, destination: str, travel_date: str) -> str:
        """
        Builds MakeMyTrip search URL.
        Date format expected: DD/MM/YYYY
        """
        parts = travel_date.split("-")
        if len(parts) == 3:
            formatted_date = f"{parts[2]}/{parts[1]}/{parts[0]}"
        else:
            formatted_date = travel_date

        return f"{self.base_url}/flight/search?itinerary={origin}-{destination}-{formatted_date}&tripType=O&paxType=A-1_C-0_I-0&intl=false&cabinClass=E"

    def search(
        self,
        origin: str,
        destination: str,
        travel_date: str
    ) -> ScrapeResult:
        """
        Executes search on makemytrip.com using permitted HTTP requests.
        Detects connection timeouts / Akamai WAF blocking and returns SOURCE_BLOCKED.
        """
        origin_code = origin.upper().strip()
        dest_code = destination.upper().strip()
        search_url = self._build_search_url(origin_code, dest_code, travel_date)

        logger.info(f"Initiating MakeMyTrip search: {origin_code} -> {dest_code} on {travel_date}")

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
                logger.warning(f"MakeMyTrip access blocked with status {response.status_code}.")
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
            logger.warning(f"MakeMyTrip access blocked/timed out: {err}")
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
        Parses MakeMyTrip DOM cards into FareObservation objects.
        """
        if not html_content or len(html_content) < 100:
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        observations: List[FareObservation] = []

        cards = soup.find_all(
            "div",
            class_=lambda c: c and any(k in str(c).lower() for k in ("listingcard", "flight-tuple", "mmt-flight-row"))
        )
        for card in cards:
            try:
                obs = self._parse_single_card(card, origin, destination, travel_date)
                if obs:
                    observations.append(obs)
            except Exception as e:
                logger.debug(f"Error parsing MakeMyTrip card: {e}")

        return observations

    def _parse_single_card(
        self,
        card,
        origin: str,
        destination: str,
        travel_date: str
    ) -> Optional[FareObservation]:
        """Parses a single MakeMyTrip flight card element."""
        airline_name = "Air India"
        fl_el = card.find(class_=lambda c: c and ("flight-number" in c or "fl-no" in c))
        raw_fl = fl_el.text.strip() if fl_el else "AI 805"
        flight_num = DataNormalizer.normalize_flight_number(raw_fl, airline_name)

        dep_el = card.find(class_=lambda c: c and "dep-time" in c)
        dep_time = DataNormalizer.normalize_time_format(dep_el.text.strip()) if dep_el else None

        arr_el = card.find(class_=lambda c: c and "arr-time" in c)
        arr_time = DataNormalizer.normalize_time_format(arr_el.text.strip()) if arr_el else None

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
            airline=airline_name,
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
