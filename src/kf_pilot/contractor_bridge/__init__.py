"""LOCAL_SHADOW bridge from KF runtime contract to contractor public APIs.

Does not wrap contractor internals. Does not talk to live Notion or paid models.
"""

from .adapter import LocalShadowAdapter, ShadowResult
from .mapping import CONTRACTOR_BASELINE, PUBLIC_API_MAP, SYMBOL_MAP

MODE = "LOCAL_SHADOW"
LOCAL_SHADOW = MODE

__all__ = [
    "CONTRACTOR_BASELINE",
    "LOCAL_SHADOW",
    "MODE",
    "LocalShadowAdapter",
    "PUBLIC_API_MAP",
    "SYMBOL_MAP",
    "ShadowResult",
]
