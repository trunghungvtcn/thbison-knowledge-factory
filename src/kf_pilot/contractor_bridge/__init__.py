"""LOCAL_SHADOW bridge from KF runtime contract to contractor public APIs."""

from .adapter import LocalShadowAdapter, ShadowResult
from .mapping import CONTRACTOR_BASELINE, J1_REVIEWED, J2_PUBLISHED, PUBLIC_API_MAP, SYMBOL_MAP
from .pins import J2_ENV_COMMIT, mark_allowed, transport_is_allowed

MODE = "LOCAL_SHADOW"
LOCAL_SHADOW = MODE

__all__ = [
    "CONTRACTOR_BASELINE",
    "J1_REVIEWED",
    "J2_ENV_COMMIT",
    "J2_PUBLISHED",
    "LOCAL_SHADOW",
    "MODE",
    "LocalShadowAdapter",
    "PUBLIC_API_MAP",
    "SYMBOL_MAP",
    "ShadowResult",
    "mark_allowed",
    "transport_is_allowed",
]
