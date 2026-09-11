from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

HOPS = ("planning", "knowledge", "writer", "runtime", "cms")


class MissingAdapterError(RuntimeError):
    def __init__(self, hop: str, mode: str):
        super().__init__(f"MISSING_ADAPTER:{hop}:mode={mode}")
        self.hop = hop
        self.mode = mode


@dataclass
class HopBinding:
    hop: str
    kind: str  # STUB | ACTUAL
    impl: Any
    vendor: str
    endpoint: str | None = None


class AdapterRegistry:
    """Select STUB vs ACTUAL per hop. Labels alone never imply ACTUAL."""

    def __init__(self, mode: str, stub_hops: frozenset[str] | None = None):
        self.mode = mode
        self.stub_hops = stub_hops or frozenset()
        self.bindings: dict[str, HopBinding] = {}

    def bind(self, hop: str, kind: str, impl: Any, vendor: str, endpoint: str | None = None) -> None:
        if hop not in HOPS:
            raise ValueError(hop)
        if kind not in {"STUB", "ACTUAL"}:
            raise ValueError(kind)
        self.bindings[hop] = HopBinding(hop, kind, impl, vendor, endpoint)

    def require(self) -> None:
        if self.mode == "REFERENCE_ONLY":
            for hop, b in self.bindings.items():
                if b.kind != "STUB":
                    raise MissingAdapterError(hop, self.mode)
            return
        if self.mode == "ACTUAL_COMPONENTS":
            for hop in HOPS:
                b = self.bindings.get(hop)
                if b is None or b.kind != "ACTUAL":
                    raise MissingAdapterError(hop, self.mode)
            return
        if self.mode == "MIXED":
            for hop in HOPS:
                b = self.bindings.get(hop)
                if hop in self.stub_hops:
                    if b is None or b.kind != "STUB":
                        raise MissingAdapterError(hop, self.mode)
                else:
                    if b is None or b.kind != "ACTUAL":
                        raise MissingAdapterError(hop, self.mode)
            return
        if self.mode == "STAGING":
            # staging still requires explicit ACTUAL adapters for live hops
            for hop in HOPS:
                b = self.bindings.get(hop)
                if b is None:
                    raise MissingAdapterError(hop, self.mode)
            return

    def labels(self) -> dict[str, str]:
        return {h: self.bindings[h].kind if h in self.bindings else "MISSING" for h in HOPS}
