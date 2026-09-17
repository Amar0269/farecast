"""Scrapers package."""
from .base import BaseFareSource, ScrapeResult
from .indigo import IndigoSource
from .easemytrip import EaseMyTripSource
from .ixigo import IxigoSource
from .yatra import YatraSource
from .airindia import AirIndiaSource
from .airindiaexpress import AirIndiaExpressSource
from .akasa import AkasaSource
from .spicejet import SpiceJetSource
from .cleartrip import CleartripSource
from .goibibo import GoibiboSource
from .makemytrip import MakeMyTripSource

__all__ = [
    "BaseFareSource",
    "ScrapeResult",
    "IndigoSource",
    "EaseMyTripSource",
    "IxigoSource",
    "YatraSource",
    "AirIndiaSource",
    "AirIndiaExpressSource",
    "AkasaSource",
    "SpiceJetSource",
    "CleartripSource",
    "GoibiboSource",
    "MakeMyTripSource",
]
