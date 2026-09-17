"""
Route Discovery & Catalog Generator for Indian Domestic Air Routes (Member 1 - SIH26056).
Discovers, validates, and catalogizes Indian domestic origin-destination airport pairs.
"""

import os
import csv
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Set

logger = logging.getLogger("RouteDiscovery")

# Authoritative Master Registry of Indian Domestic Airports (IATA Code, City, Airport Name, State)
INDIAN_DOMESTIC_AIRPORTS: Dict[str, Dict[str, str]] = {
    "DEL": {"city": "New Delhi", "name": "Indira Gandhi International Airport", "state": "Delhi"},
    "BOM": {"city": "Mumbai", "name": "Chhatrapati Shivaji Maharaj International Airport", "state": "Maharashtra"},
    "BLR": {"city": "Bengaluru", "name": "Kempegowda International Airport", "state": "Karnataka"},
    "CCU": {"city": "Kolkata", "name": "Netaji Subhash Chandra Bose International Airport", "state": "West Bengal"},
    "HYD": {"city": "Hyderabad", "name": "Rajiv Gandhi International Airport", "state": "Telangana"},
    "MAA": {"city": "Chennai", "name": "Chennai International Airport", "state": "Tamil Nadu"},
    "AMD": {"city": "Ahmedabad", "name": "Sardar Vallabhbhai Patel International Airport", "state": "Gujarat"},
    "PNQ": {"city": "Pune", "name": "Pune Airport", "state": "Maharashtra"},
    "GOI": {"city": "Goa (Dabolim)", "name": "Dabolim Airport", "state": "Goa"},
    "GOX": {"city": "Goa (Mopa)", "name": "Manohar International Airport", "state": "Goa"},
    "JAI": {"city": "Jaipur", "name": "Jaipur International Airport", "state": "Rajasthan"},
    "COK": {"city": "Kochi", "name": "Cochin International Airport", "state": "Kerala"},
    "TRV": {"city": "Thiruvananthapuram", "name": "Trivandrum International Airport", "state": "Kerala"},
    "IXC": {"city": "Chandigarh", "name": "Shaheed Bhagat Singh International Airport", "state": "Chandigarh"},
    "LKO": {"city": "Lucknow", "name": "Chaudhary Charan Singh International Airport", "state": "Uttar Pradesh"},
    "PAT": {"city": "Patna", "name": "Jayprakash Narayan Airport", "state": "Bihar"},
    "GAU": {"city": "Guwahati", "name": "Lokpriya Gopinath Bordoloi International Airport", "state": "Assam"},
    "BBI": {"city": "Bhubaneswar", "name": "Biju Patnaik Airport", "state": "Odisha"},
    "VNS": {"city": "Varanasi", "name": "Lal Bahadur Shastri International Airport", "state": "Uttar Pradesh"},
    "IXB": {"city": "Bagdogra", "name": "Bagdogra Airport", "state": "West Bengal"},
    "BDQ": {"city": "Vadodara", "name": "Vadodara Airport", "state": "Gujarat"},
    "IDR": {"city": "Indore", "name": "Devi Ahilya Bai Holkar Airport", "state": "Madhya Pradesh"},
    "NAG": {"city": "Nagpur", "name": "Dr. Babasaheb Ambedkar International Airport", "state": "Maharashtra"},
    "RPR": {"city": "Raipur", "name": "Swami Vivekananda Airport", "state": "Chhattisgarh"},
    "SXR": {"city": "Srinagar", "name": "Sheikh ul-Alam International Airport", "state": "Jammu & Kashmir"},
    "IXJ": {"city": "Jammu", "name": "Jammu Airport", "state": "Jammu & Kashmir"},
    "ATQ": {"city": "Amritsar", "name": "Sri Guru Ram Dass Jee International Airport", "state": "Punjab"},
    "VTZ": {"city": "Visakhapatnam", "name": "Visakhapatnam International Airport", "state": "Andhra Pradesh"},
    "IXE": {"city": "Mangalore", "name": "Mangaluru International Airport", "state": "Karnataka"},
    "TRZ": {"city": "Tiruchirappalli", "name": "Tiruchirappalli International Airport", "state": "Tamil Nadu"},
    "CJB": {"city": "Coimbatore", "name": "Coimbatore International Airport", "state": "Tamil Nadu"},
    "IXM": {"city": "Madurai", "name": "Madurai Airport", "state": "Tamil Nadu"},
    "IXA": {"city": "Agartala", "name": "Maharaja Bir Bikram Airport", "state": "Tripura"},
    "IMF": {"city": "Imphal", "name": "Bir Tikendrajit International Airport", "state": "Manipur"},
    "DIB": {"city": "Dibrugarh", "name": "Dibrugarh Airport", "state": "Assam"},
    "STV": {"city": "Surat", "name": "Surat International Airport", "state": "Gujarat"},
    "UDR": {"city": "Udaipur", "name": "Maharana Pratap Airport", "state": "Rajasthan"},
    "JDH": {"city": "Jodhpur", "name": "Jodhpur Airport", "state": "Rajasthan"},
    "DED": {"city": "Dehradun", "name": "Jolly Grant Airport", "state": "Uttarakhand"},
    "IXR": {"city": "Ranchi", "name": "Birsa Munda Airport", "state": "Jharkhand"},
    "GWL": {"city": "Gwalior", "name": "Rajmata Vijaya Raje Scindia Airport", "state": "Madhya Pradesh"},
    "KUU": {"city": "Kullu", "name": "Kullu-Manali Airport", "state": "Himachal Pradesh"},
    "DHM": {"city": "Dharamshala", "name": "Kangra Airport", "state": "Himachal Pradesh"}
}

# 6 Reference SIH Representative Routes
SIH_REFERENCE_ROUTES = {
    ("DEL", "BOM"), ("DEL", "BLR"), ("BOM", "BLR"),
    ("DEL", "CCU"), ("BLR", "HYD"), ("MAA", "DEL")
}


class RouteDiscovery:
    def __init__(self, source_name: str = "yatra"):
        self.source_name = source_name

    def is_valid_domestic_code(self, code: str) -> bool:
        """Verifies if an IATA code belongs to a valid Indian domestic airport."""
        return code.upper().strip() in INDIAN_DOMESTIC_AIRPORTS

    def discover_routes_from_payload(self, html_content: str) -> Set[Tuple[str, str]]:
        """
        Dynamically extracts origin-destination routes embedded inside Yatra response HTML/JSON payload.
        """
        discovered: Set[Tuple[str, str]] = set()
        if not html_content:
            return discovered

        try:
            # Check for cityNames / airportNames or flight schedule keys in JSON
            idx = html_content.find("resultData")
            if idx != -1:
                m_start = html_content.rfind("mainData", 0, idx)
                if m_start != -1:
                    brace_start = html_content.find("{", m_start)
                    if brace_start != -1 and brace_start < idx:
                        decoder = json.JSONDecoder()
                        parsed, _ = decoder.raw_decode(html_content, brace_start)
                        res_list = parsed.get("resultData", [])
                        for res in res_list:
                            flt_sched = res.get("fltSchedule", {})
                            for k in flt_sched.keys():
                                # Flight schedule keys format e.g. DELBOM20261017
                                if len(k) >= 14 and k[:3] in INDIAN_DOMESTIC_AIRPORTS and k[3:6] in INDIAN_DOMESTIC_AIRPORTS:
                                    orig, dest = k[:3], k[3:6]
                                    if orig != dest:
                                        discovered.add((orig, dest))
        except Exception as e:
            logger.debug(f"Payload route extraction error: {e}")

        return discovered

    def generate_full_domestic_catalog(
        self,
        extracted_routes: Optional[Set[Tuple[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Generates the complete Indian domestic route catalog.
        Combines top Indian city-pairs and dynamically extracted routes.
        Preserves directionality (DEL-BOM vs BOM-DEL).
        Filters out international, invalid, and self-loop routes.
        """
        catalog: List[Dict[str, Any]] = []
        seen_pairs: Set[Tuple[str, str]] = set()
        discovered_at = datetime.now(timezone.utc).isoformat()

        airports = sorted(list(INDIAN_DOMESTIC_AIRPORTS.keys()))

        # Top 15 key hubs for high-density matrix generation
        primary_hubs = ["DEL", "BOM", "BLR", "CCU", "HYD", "MAA", "AMD", "PNQ", "GOI", "COK", "LKO", "PAT", "GAU", "JAI", "SXR"]

        # Generate directional pairs between primary hubs and all airports
        candidate_pairs: List[Tuple[str, str]] = []

        # 1. Primary hub cross-connects (highest frequency domestic routes)
        for orig in primary_hubs:
            for dest in airports:
                if orig != dest:
                    candidate_pairs.append((orig, dest))

        # 2. Add dynamically extracted routes if provided
        if extracted_routes:
            for pair in extracted_routes:
                if pair[0] in INDIAN_DOMESTIC_AIRPORTS and pair[1] in INDIAN_DOMESTIC_AIRPORTS and pair[0] != pair[1]:
                    if pair not in candidate_pairs:
                        candidate_pairs.append(pair)

        # Build catalog items with metadata
        route_id_counter = 1
        for orig, dest in candidate_pairs:
            if (orig, dest) in seen_pairs:
                continue
            seen_pairs.add((orig, dest))

            orig_info = INDIAN_DOMESTIC_AIRPORTS[orig]
            dest_info = INDIAN_DOMESTIC_AIRPORTS[dest]
            route_str = f"{orig}-{dest}"

            status = "REF_SIH" if (orig, dest) in SIH_REFERENCE_ROUTES else "DISCOVERED"
            if extracted_routes and (orig, dest) in extracted_routes:
                status = "VERIFIED_LIVE"

            catalog.append({
                "route_id": f"R{route_id_counter:04d}",
                "route": route_str,
                "origin": orig_info["city"],
                "origin_code": orig,
                "destination": dest_info["city"],
                "destination_code": dest,
                "domestic": True,
                "source": self.source_name,
                "discoverability_status": status,
                "discovered_at": discovered_at
            })
            route_id_counter += 1

        logger.info(f"Generated Indian Domestic Route Catalog with {len(catalog)} directional routes across {len(airports)} domestic airports.")
        return catalog

    def export_catalog(
        self,
        catalog: List[Dict[str, Any]],
        processed_dir: str = "data/processed"
    ) -> Dict[str, str]:
        """Exports the route catalog to CSV and JSON formats."""
        os.makedirs(processed_dir, exist_ok=True)
        csv_path = os.path.join(processed_dir, "route_catalog.csv")
        json_path = os.path.join(processed_dir, "route_catalog.json")

        headers = [
            "route_id", "route", "origin", "origin_code", "destination",
            "destination_code", "domestic", "source", "discoverability_status", "discovered_at"
        ]

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for row in catalog:
                writer.writerow(row)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2)

        logger.info(f"Exported Route Catalog: CSV={csv_path}, JSON={json_path}")
        return {"csv": csv_path, "json": json_path}
