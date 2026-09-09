from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .canonical import GateError


@dataclass(frozen=True)
class Compatibility:
    compatible: bool
    reason: str


@dataclass(frozen=True)
class Runtime:
    """Repository-owned callbacks; never import a callback named in input JSON.

    version_id MUST call the actual repository identity algorithm. verify_upstream
    MUST reload/validate the real V16.3 binding referenced by upstream_binding_hash.
    check_v162 MUST run the unchanged V16.2 validation on a candidate conversion.
    This package intentionally supplies no fake production implementation.
    """
    data_class: str
    identity_contract_id: str
    version_id: Callable[[str, dict], str]
    verify_upstream: Callable[[dict, dict], None]
    check_v162: Callable[[dict, dict], Compatibility]


def repository_runtime() -> Runtime:
    raise GateError("REPOSITORY_ADAPTER_NOT_CONNECTED",
                    "Implement callbacks against the checked-out V16.2/V16.3 repo; see docs/INTEGRATION.md")


