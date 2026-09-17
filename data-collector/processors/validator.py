"""
Data Validator & Deduplicator Module.
Provides deterministic deduplication within sources and statistical outlier flagging.
"""

import hashlib
import numpy as np
from typing import List
from models.fare import FareObservation


class DataValidator:
    @staticmethod
    def generate_duplicate_key(obs: FareObservation) -> str:
        """
        Generates a deterministic unique hashing key for deduplication within the SAME source.
        Same flight appearing across different sources represents different source observations.
        """
        raw_key = (
            f"{obs.source.lower()}|"
            f"{obs.airline.lower()}|"
            f"{obs.flight_number.upper().replace(' ', '')}|"
            f"{obs.origin.upper()}|"
            f"{obs.destination.upper()}|"
            f"{obs.travel_date}|"
            f"{(obs.departure_time or '').strip()}|"
            f"{(obs.fare_class or 'STANDARD').upper()}"
        )
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @classmethod
    def deduplicate(cls, observations: List[FareObservation]) -> List[FareObservation]:
        """
        Identifies and flags duplicate observations from the same source.
        Does NOT drop observations; sets duplicate_flag = True for subsequent occurrences.
        """
        seen_keys = set()
        for obs in observations:
            key = cls.generate_duplicate_key(obs)
            if key in seen_keys:
                obs.duplicate_flag = True
            else:
                seen_keys.add(key)
                obs.duplicate_flag = False
        return observations

    @staticmethod
    def flag_outliers(observations: List[FareObservation], factor: float = 1.5) -> List[FareObservation]:
        """
        Flags price outliers using the Interquartile Range (IQR) method on total_fare.
        Does NOT delete extreme fares (airfares are dynamic).
        Sets outlier_flag = True for values outside [Q1 - factor*IQR, Q3 + factor*IQR].
        """
        fares = [obs.total_fare for obs in observations if obs.total_fare is not None and obs.total_fare > 0]
        if len(fares) < 4:
            # Need minimum observations for reliable IQR
            return observations

        q25, q75 = np.percentile(fares, [25, 75])
        iqr = q75 - q25
        lower_bound = q25 - (factor * iqr)
        upper_bound = q75 + (factor * iqr)

        for obs in observations:
            if obs.total_fare is not None:
                if obs.total_fare < lower_bound or obs.total_fare > upper_bound:
                    obs.outlier_flag = True
                else:
                    obs.outlier_flag = False

        return observations
