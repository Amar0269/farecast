"""
Yatra Source Adapter (yatra.com).
Uses permitted HTTP requests to extract live airfare observations from Yatra's server-rendered payload.
Complies with permitted access methods without stealth evasion or anti-bot bypass.

Yatra Search URL:
  https://flight.yatra.com/air-search/dom2/trigger?type=O&origin={origin}&originCode={origin}&destination={dest}&destinationCode={dest}&flight_depart_date={DD/MM/YYYY}&ADT=1&CHD=0&INF=0&class=Economy
"""

import re
import json
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

            raw_html = response.text
            if response.status_code in (403, 429, 503):
                logger.warning(f"Yatra HTTP status {response.status_code}.")
                observations = self.parse_html(raw_html, origin_code, dest_code, travel_date)
                if observations:
                    logger.info(f"Successfully extracted {len(observations)} observations from response body despite HTTP {response.status_code}.")
                    return ScrapeResult(
                        source=self.source_name,
                        origin=origin_code,
                        destination=dest_code,
                        travel_date=travel_date,
                        status=CollectionStatus.SUCCESS,
                        observations=observations,
                        raw_payload=raw_html
                    )
                return ScrapeResult(
                    source=self.source_name,
                    origin=origin_code,
                    destination=dest_code,
                    travel_date=travel_date,
                    status=CollectionStatus.SOURCE_BLOCKED,
                    raw_payload=raw_html,
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
        Parses Yatra search HTML payload into 32-field FareObservation objects.
        Tries embedded mainData JSON payload first, falling back to DOM cards.
        """
        if not html_content or len(html_content) < 100:
            return []

        # 1. Try parsing embedded mainData JSON payload
        json_observations = self.parse_json_payload(html_content, origin, destination, travel_date)
        if json_observations:
            logger.info(f"Successfully extracted {len(json_observations)} observations from Yatra mainData JSON payload.")
            return json_observations

        # 2. Fall back to parsing DOM flight cards
        soup = BeautifulSoup(html_content, "html.parser")
        observations: List[FareObservation] = []

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

    def parse_json_payload(
        self,
        html_content: str,
        origin: str,
        destination: str,
        travel_date: str
    ) -> List[FareObservation]:
        """Parses embedded mainData JSON payload from Yatra server response if present."""
        idx = html_content.find("resultData")
        if idx == -1:
            return []

        m_start = html_content.rfind("mainData", 0, idx)
        if m_start == -1:
            return []
        brace_start = html_content.find("{", m_start)
        if brace_start == -1 or brace_start > idx:
            return []

        try:
            decoder = json.JSONDecoder()
            parsed, _ = decoder.raw_decode(html_content, brace_start)
        except Exception as e:
            logger.error(f"JSON raw_decode error: {e}")
            return []

        observations: List[FareObservation] = []
        res_list = parsed.get("resultData", [])
        search_url = self._build_search_url(origin, destination, travel_date)
        seen_keys = set()

        for res in res_list:
            flt_sched = res.get("fltSchedule", {})
            fare_details = res.get("fareDetails", {})

            fare_map = {}
            for rk, fdict in fare_details.items():
                if isinstance(fdict, dict):
                    for fid, fare_info in fdict.items():
                        adt = fare_info.get("O", {}).get("ADT", {})
                        if adt:
                            fare_map[fid] = adt

            for rk, flights in flt_sched.items():
                if isinstance(flights, list):
                    for fl in flights:
                        fl_id = fl.get("ID")
                        od_list = fl.get("OD", [])
                        if not od_list:
                            continue
                        od = od_list[0]
                        fs_list = od.get("FS", [])
                        if not fs_list:
                            continue
                        fs = fs_list[0]

                        raw_airline = fs.get("acn") or fs.get("ac") or "Unknown"
                        raw_fl = f"{fs.get('ac', '')} {fs.get('fl', '')}".strip()
                        dep_time = fs.get("dd")
                        arr_time = fs.get("ad")
                        stops = int(od.get("ts", 0)) if str(od.get("ts", 0)).isdigit() else 0

                        fare_info = fare_map.get(fl_id, {})
                        base_fare = float(fare_info.get("bf", 0)) if fare_info.get("bf") else None
                        total_fare = float(fare_info.get("tf", 0)) if fare_info.get("tf") else None
                        udf = float(fare_info.get("UDF", 0)) if fare_info.get("UDF") else None
                        yq = float(fare_info.get("YQ", 0)) if fare_info.get("YQ") else 0.0

                        taxes = None
                        if total_fare is not None and base_fare is not None:
                            taxes = max(0.0, total_fare - base_fare)
                        elif yq > 0:
                            taxes = yq

                        norm_airline = DataNormalizer.normalize_airline_name(raw_airline)
                        flight_num = DataNormalizer.normalize_flight_number(raw_fl, norm_airline)
                        fare_class = od.get("fareId") or fl.get("fareId")
                        if total_fare is None:
                            continue

                        dedup_key = f"{norm_airline}_{flight_num}_{dep_time}_{total_fare}"
                        if dedup_key in seen_keys:
                            continue
                        seen_keys.add(dedup_key)

                        obs = FareObservation(
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
                            cabin_class=od.get("classtype") or "Economy",
                            fare_class=fare_class,
                            base_fare=base_fare,
                            taxes=taxes,
                            user_development_fee=udf,
                            total_fare=total_fare,
                            currency="INR",
                            availability_status="available",
                            raw_fare_text=json.dumps(fl)[:500]
                        )
                        observations.append(obs)

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
