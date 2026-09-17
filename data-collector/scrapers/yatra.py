"""
Yatra Source Adapter (yatra.com).
Uses permitted HTTP requests to extract live airfare observations from Yatra's server-rendered payload.
Complies with permitted access methods without stealth evasion or anti-bot bypass.

Yatra Search URL:
  https://flight.yatra.com/air-search/dom2/trigger?type=O&origin={origin}&originCode={origin}&destination={dest}&destinationCode={dest}&flight_depart_date={DD/MM/YYYY}&ADT=1&CHD=0&INF=0&class=Economy
"""

import re
import logging
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import httpx

from models.fare import FareObservation, CollectionStatus
from scrapers.base import BaseFareSource, ScrapeResult
from processors.normalizer import DataNormalizer

logger = logging.getLogger(__name__)


def _fmt_date_ddmmyyyy(travel_date: str) -> str:
    """Converts YYYY-MM-DD to DD/MM/YYYY for Yatra URL parameter."""
    parts = travel_date.split("-")
    if len(parts) == 3:
        yyyy, mm, dd = parts
        return f"{dd}/{mm}/{yyyy}"
    return travel_date


class YatraSource(BaseFareSource):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(source_name="yatra", config=config)
        self.base_url = self.config.get("base_url", "https://flight.yatra.com")
        self.timeout = self.config.get("timeout_seconds", 30)

    def _build_search_url(self, origin: str, destination: str, travel_date: str) -> str:
        """Builds the Yatra flight search URL."""
        url_date = _fmt_date_ddmmyyyy(travel_date)
        return (
            f"{self.base_url}/air-search/dom2/trigger"
            f"?type=O&origin={origin}&originCode={origin}"
            f"&destination={destination}&destinationCode={destination}"
            f"&flight_depart_date={url_date}&ADT=1&CHD=0&INF=0&class=Economy"
        )

    def search(
        self,
        origin: str,
        destination: str,
        travel_date: str
    ) -> ScrapeResult:
        """
        Executes live flight search on Yatra using permitted HTTP request.
        Parses pre-rendered HTML payload into 32-field FareObservation objects.
        """
        origin_code = origin.upper().strip()
        dest_code = destination.upper().strip()
        search_url = self._build_search_url(origin_code, dest_code, travel_date)

        logger.info(f"Initiating Yatra search: {origin_code} -> {dest_code} on {travel_date}")
        logger.info(f"Search URL: {search_url}")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=True, headers=headers) as client:
                response = client.get(search_url)

            if response.status_code in (403, 429, 503):
                logger.warning(f"Yatra access blocked with HTTP {response.status_code}.")
                return ScrapeResult(
                    source=self.source_name,
                    origin=origin_code,
                    destination=dest_code,
                    travel_date=travel_date,
                    status=CollectionStatus.SOURCE_BLOCKED,
                    raw_payload=response.text,
                    error_message=f"Access blocked with HTTP status {response.status_code}"
                )

            raw_html = response.text
            observations = self.parse_html(raw_html, origin_code, dest_code, travel_date)
            status = CollectionStatus.SUCCESS if observations else CollectionStatus.NO_RESULTS

            logger.info(f"Yatra search completed successfully. Extracted {len(observations)} observations.")
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
            logger.error(f"Network error accessing Yatra: {err}")
            return ScrapeResult(
                source=self.source_name,
                origin=origin_code,
                destination=dest_code,
                travel_date=travel_date,
                status=CollectionStatus.NETWORK_ERROR,
                error_message=str(err)
            )

    def parse_html(
        self,
        html_content: str,
        origin: str,
        destination: str,
        travel_date: str
    ) -> List[FareObservation]:
        """
        Parses Yatra flight card DOM elements into 32-field FareObservation objects.
        """
        if not html_content or len(html_content) < 100:
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        observations: List[FareObservation] = []

        # Target Yatra flight card items
        cards = soup.find_all(
            "div",
            class_=lambda c: c and any("flightitem" in x.lower() for x in (c if isinstance(c, list) else [c]))
        )
        seen_keys = set()

        for card in cards:
            try:
                obs = self._parse_single_card(card, origin, destination, travel_date)
                if obs:
                    dedup_key = f"{obs.airline}_{obs.flight_number}_{obs.departure_time}_{obs.total_fare}"
                    if dedup_key not in seen_keys:
                        seen_keys.add(dedup_key)
                        observations.append(obs)
            except Exception as e:
                logger.debug(f"Error parsing Yatra card: {e}")

        return observations

    def _parse_single_card(
        self,
        card,
        origin: str,
        destination: str,
        travel_date: str
    ) -> Optional[FareObservation]:
        """Parses a single Yatra DOM flight card."""
        strings = list(card.stripped_strings)
        if len(strings) < 6:
            return None

        # Airline & Flight number
        airline_el = card.find("div", class_=re.compile(r"airline-name", re.I))
        if airline_el:
            name_span = airline_el.find("span")
            raw_airline = name_span.text.strip() if name_span else strings[0]
            fl_p = airline_el.find("p", class_=re.compile(r"fl-no", re.I))
            raw_fl = fl_p.text.strip() if fl_p else (strings[1] if len(strings) > 1 else "YT-000")
        else:
            raw_airline = strings[0]
            raw_fl = strings[1] if len(strings) > 1 else "YT-000"

        norm_airline = DataNormalizer.normalize_airline_name(raw_airline)
        flight_num = DataNormalizer.normalize_flight_number(raw_fl, norm_airline)

        # Times
        times = []
        for s in strings:
            if re.match(r"^\d{1,2}:\d{2}$", s):
                times.append(s)

        dep_time = times[0] if len(times) >= 1 else None
        arr_time = times[1] if len(times) >= 2 else None

        # Stops
        stops = 0
        for s in strings:
            s_lower = s.lower()
            if "non" in s_lower or "0 stop" in s_lower:
                stops = 0
                break
            elif "1 stop" in s_lower:
                stops = 1
                break
            elif "2 stop" in s_lower:
                stops = 2
                break

        # Total Fare
        total_fare = None
        for s in reversed(strings):
            clean_str = re.sub(r"[^\d.]", "", s.replace(",", ""))
            if clean_str.isdigit() and len(clean_str) >= 3:
                val = float(clean_str)
                if 1000 <= val <= 100000:
                    total_fare = val
                    break

        missing = []
        if not dep_time: missing.append("departure_time")
        if not arr_time: missing.append("arrival_time")
        if total_fare is None: missing.append("total_fare")

        search_url = self._build_search_url(origin, destination, travel_date)

        return FareObservation(
            source=self.source_name,
            source_url=search_url,
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
