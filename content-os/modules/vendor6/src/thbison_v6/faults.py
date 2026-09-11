"""Fault injection for simulators."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FaultPlan:
    timeout: bool = False
    status_429: bool = False
    schema_drift: bool = False
    unknown_after_accept: bool = False
    kill_after_admit: bool = False
    revoked_midflight: bool = False
    flags: dict = field(default_factory=dict)

    def reset(self) -> None:
        self.timeout = False
        self.status_429 = False
        self.schema_drift = False
        self.unknown_after_accept = False
        self.kill_after_admit = False
        self.revoked_midflight = False
        self.flags.clear()
