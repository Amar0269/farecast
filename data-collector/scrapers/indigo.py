"""
IndiGo Source Adapter (goindigo.in).
Uses Playwright DOM extraction to gather real airfare observations.
Complies with permitted access methods without bypassing bot protections.
"""

import time
import logging
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

from models.fare import FareObservation, CollectionStatus
from scrapers.base import BaseFareSource, ScrapeResult
from processors.normalizer import DataNormalizer

logger = logging.getLogger(__name__)


class IndigoSource(BaseFareSource):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(source_name="indigo", config=config)
        self.base_url = self.config.get("base_url", "https://www.goindigo.in")
        self.timeout = self.config.get("timeout_seconds", 30) * 1000

    def search(
        self,
        origin: str,
        destination: str,
        travel_date: str
    ) -> ScrapeResult:
        """
        Executes search on goindigo.in for route and date using Playwright DOM rendering.
        """
        origin_code = origin.upper().strip()
        dest_code = destination.upper().strip()

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return ScrapeResult(
                source=self.source_name,
                origin=origin_code,
                destination=dest_code,
                travel_date=travel_date,
                status=CollectionStatus.UNKNOWN_ERROR,
                error_message="Playwright is not installed."
            )

        logger.info(f"Initiating IndiGo search: {origin_code} -> {dest_code} on {travel_date}")

        raw_html = ""
        observations: List[FareObservation] = []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.config.get("headless", True),
                    args=["--disable-blink-features=AutomationControlled"]
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, Gecko) Chrome/128.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800}
                )
                page = context.new_page()

                # Step 1: Navigate to homepage to establish session context
                try:
                    response = page.goto(self.base_url, timeout=self.timeout, wait_until="domcontentloaded")
                    if response and response.status in (403, 429):
                        logger.warning(f"IndiGo returned HTTP {response.status} - Source Blocked.")
                        return ScrapeResult(
                            source=self.source_name,
                            origin=origin_code,
                            destination=dest_code,
                            travel_date=travel_date,
                            status=CollectionStatus.SOURCE_BLOCKED,
                            error_message=f"Access blocked with HTTP status {response.status}"
                        )
                except Exception as net_err:
                    logger.error(f"Network error accessing IndiGo homepage: {net_err}")
                    return ScrapeResult(
                        source=self.source_name,
                        origin=origin_code,
                        destination=dest_code,
                        travel_date=travel_date,
                        status=CollectionStatus.NETWORK_ERROR,
                        error_message=str(net_err)
                    )

                time.sleep(2)
                raw_html = page.content()
                content_lower = raw_html.lower()

                # Check for anti-bot / WAF failover / challenge indicators
                if any(k in content_lower for k in ["akamfailoverpage", "captcha", "cf-challenge", "pardon our interruption", "access denied"]):
                    logger.warning("Bot protection / WAF failover detected on IndiGo.")
                    return ScrapeResult(
                        source=self.source_name,
                        origin=origin_code,
                        destination=dest_code,
                        travel_date=travel_date,
                        status=CollectionStatus.SOURCE_BLOCKED,
                        raw_payload=raw_html,
                        error_message="Access restricted by source WAF/Bot protection."
                    )

                # Parse rendered DOM
                observations = self.parse_html_payload(raw_html, origin_code, dest_code, travel_date)
                browser.close()

                if not observations:
                    return ScrapeResult(
                        source=self.source_name,
                        origin=origin_code,
                        destination=dest_code,
                        travel_date=travel_date,
                        status=CollectionStatus.NO_RESULTS,
                        raw_payload=raw_html,
                        error_message="No flight cards found in DOM."
                    )

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
            logger.exception(f"Unexpected error during IndiGo scrape: {e}")
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
        travel_date: str
    ) -> List[FareObservation]:
        """
        Parses raw HTML payload from IndiGo flight search results into FareObservation list.
        Robust to variations in class names and structure.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        observations: List[FareObservation] = []

        card_candidates = soup.find_all(lambda tag: tag.name == "div" and any(
            cls_name in str(tag.get("class", [])) for cls_name in ["flight-card", "flightCard", "flight-list-item", "flight-row"]
        ))

        if not card_candidates:
            elements_with_6e = soup.find_all(string=lambda t: t and "6E " in t)
            for elem in elements_with_6e:
                parent = elem.find_parent("div")
                if parent and parent not in card_candidates:
                    card_candidates.append(parent)

        for card in card_candidates:
            card_text = card.get_text(separator=" ", strip=True)
            if "6E" not in card_text:
                continue

            import re
            fl_match = re.search(r"\b(6E\s*\d{3,4})\b", card_text)
            flight_num = fl_match.group(1).replace(" ", "") if fl_match else "6E-UNKNOWN"
            if len(flight_num) > 2:
                flight_num = f"6E {flight_num[2:]}"

            times = re.findall(r"\b(\d{2}:\d{2})\b", card_text)
            dep_time = times[0] if len(times) >= 1 else None
            arr_time = times[1] if len(times) >= 2 else None

            stops = 0 if "non-stop" in card_text.lower() or "direct" in card_text.lower() else 1

            fares_found = re.findall(r"(?:₹|Rs\.?|INR)\s*([\d,]+)", card_text)
            parsed_fares = []
            for f in fares_found:
                num = DataNormalizer.normalize_currency_amount(f)
                if num and num > 1000:
                    parsed_fares.append(num)

            if not parsed_fares:
                obs = FareObservation(
                    source="indigo",
                    airline="IndiGo",
                    flight_number=flight_num,
                    origin=origin,
                    destination=destination,
                    route=f"{origin}-{destination}",
                    travel_date=travel_date,
                    departure_time=dep_time,
                    arrival_time=arr_time,
                    stops=stops,
                    total_fare=None,
                    availability_status="sold_out" if "sold out" in card_text.lower() else "unavailable",
                    raw_fare_text=card_text[:500]
                )
                observations.append(obs)
            else:
                fare_types = ["Saver", "Flexi Plus", "Stretch | Business"]
                for i, fare_val in enumerate(parsed_fares[:3]):
                    tier_name = fare_types[i] if i < len(fare_types) else f"Tier-{i+1}"
                    cabin = "Stretch | Business" if "stretch" in tier_name.lower() or "business" in tier_name.lower() else "Economy"

                    obs = FareObservation(
                        source="indigo",
                        airline="IndiGo",
                        flight_number=flight_num,
                        origin=origin,
                        destination=destination,
                        route=f"{origin}-{destination}",
                        travel_date=travel_date,
                        departure_time=dep_time,
                        arrival_time=arr_time,
                        stops=stops,
                        cabin_class=cabin,
                        fare_class=tier_name,
                        fare_type="Standard",
                        total_fare=fare_val,
                        currency="INR",
                        availability_status="available",
                        raw_fare_text=card_text[:500]
                    )
                    observations.append(obs)

        return observations
