"""
Abstract base class for all airline and OTA source adapters.
Ensures source-agnostic architecture.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from models.fare import FareObservation, CollectionStatus


class ScrapeResult(BaseModel):
    source: str
    origin: str
    destination: str
    travel_date: str
    collection_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: CollectionStatus
    observations: List[FareObservation] = Field(default_factory=list)
    raw_payload: Optional[str] = Field(default=None, description="Raw HTML or JSON captured from site")
    error_message: Optional[str] = Field(default=None)


class BaseFareSource(ABC):
    def __init__(self, source_name: str, config: Optional[Dict[str, Any]] = None):
        self.source_name = source_name
        self.config = config or {}

    @abstractmethod
    def search(
        self,
        origin: str,
        destination: str,
        travel_date: str
    ) -> ScrapeResult:
        """
        Executes a flight fare search for specified route and date.
        Must return a ScrapeResult object containing observations and raw payload.
        """
        pass
