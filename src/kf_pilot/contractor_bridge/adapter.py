"""LOCAL_SHADOW adapter. Calls contractor public APIs with injectable FakeTransport."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import hashlib

from kf_pilot.runtime_contract import ContractError, RunContract, canonical_bytes, sha256_file

from .mapping import CONTRACTOR_BASELINE, FACTORY_BASELINE


class BridgeError(ContractError):
    pass


def _require_contractor() -> dict[str, Any]:
    """Import contractor public packages. Missing install is BLOCKED_INPUT, not a mock."""
    try:
        from grok_asset_store import AssetStore, DictReader, SourceRef
        from grok_job_ledger import JobLedger
        from grok_locator import LocatorProfile, LocatorResolver
        from grok_notion_projection import FakeTransport, Projector
    except ImportError as exc:
        raise BridgeError(
            "BLOCKED_INPUT: contractor public packages not importable "
            f"({exc}). Install grok-locator / grok-asset-store / grok-job-ledger / "
            "grok-notion-projection from pipeline-lab-contractor-m1-m5@"
            f"{CONTRACTOR_BASELINE} or set PYTHONPATH to those src/ trees."
        ) from exc
    return {
        "AssetStore": AssetStore,
        "DictReader": DictReader,
        "SourceRef": SourceRef,
        "JobLedger": JobLedger,
        "LocatorProfile": LocatorProfile,
        "LocatorResolver": LocatorResolver,
        "FakeTransport": FakeTransport,
        "Projector": Projector,
    }


@dataclass
class ShadowResult:
    status: str
    reason_code: str
    mode: str = "LOCAL_SHADOW"
    contractor_job_id: str | None = None
    fingerprint: str = ""
    snapshot_sha256: str = ""
    manifest_sha256: str = ""
    production_writes: bool = False
    live_notion: bool = False
    hold_reasons: list[str] = field(default_factory=list)
    envelopes: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "mode": self.mode,
            "contractor_job_id": self.contractor_job_id,
            "fingerprint": self.fingerprint,
            "snapshot_sha256": self.snapshot_sha256,
            "manifest_sha256": self.manifest_sha256,
            "production_writes": self.production_writes,
            "live_notion": self.live_notion,
            "hold_reasons": list(self.hold_reasons),
            "envelopes": self.envelopes,
            "evidence": self.evidence,
        }


class LocalShadowAdapter:
    """Maps a TEST_ONLY RunContract onto contractor JobLedger + AssetStore.

    Projection uses FakeTransport only. Missing J1/J2 pins do not invent evidence.
    """

    SCOPE = "kf.j3.local_shadow"
    WORKER = "j3-shadow-worker"
    TARGET = "sandbox-page-001"
    TOKEN = "local-shadow-token"

    def __init__(
        self,
        work_root: Path,
        *,
        transport: Any | None = None,
        j1_input_sha: str | None = None,
        j2_env_sha: str | None = None,
    ) -> None:
        self.work_root = Path(work_root)
        self.work_root.mkdir(parents=True, exist_ok=True)
        self.j1_input_sha = j1_input_sha
        self.j2_env_sha = j2_env_sha
        pkgs = _require_contractor()
        self._pkgs = pkgs
        self.resolver = pkgs["LocatorResolver"]()
        self.store = pkgs["AssetStore"]()
        self.ledger = pkgs["JobLedger"](str(self.work_root / "jobs.db"))
        self.projector = pkgs["Projector"]()
        self.profile = pkgs["LocatorProfile"](
            dialect="posix",
            root_id="j3-shadow",
            case_policy="sensitive",
            unicode_policy="nfc_only",
        )
        if transport is None:
            self.transport = pkgs["FakeTransport"](
                allowed_targets={self.TARGET},
                token=self.TOKEN,
            )
        else:
            self.transport = transport

    def close(self) -> None:
        self.ledger.close()

    def _holds_for_pins(self) -> list[str]:
        holds: list[str] = []
        if not self.j1_input_sha:
            holds.append("BLOCKED_INPUT:J1_INPUT_SHA_UNPUBLISHED")
        if not self.j2_env_sha:
            holds.append("BLOCKED_INPUT:J2_ENV_SHA_UNPUBLISHED")
        return holds

    def _request_digest(self, contract: RunContract, snapshot_sha: str) -> str:
        payload = {
            "fingerprint": contract.fingerprint(),
            "snapshot_sha256": snapshot_sha,
            "factory_baseline": FACTORY_BASELINE,
            "contractor_baseline": CONTRACTOR_BASELINE,
        }
        return hashlib.sha256(canonical_bytes(payload)).hexdigest()

    def run(self, contract: RunContract, snapshot_path: Path) -> ShadowResult:
        holds = self._holds_for_pins()
        if contract.mode != "TEST_ONLY":
            return ShadowResult(
                status="HUMAN_HOLD",
                reason_code="MODE_NOT_TEST_ONLY",
                hold_reasons=holds + ["HUMAN_HOLD:NON_TEST_ONLY"],
            )
        contract.validate()

        snapshot = Path(snapshot_path).resolve(strict=True)
        actual_sha = sha256_file(snapshot)
        if actual_sha != contract.input_manifest_sha256.lower():
            raise BridgeError(
                f"snapshot hash mismatch: expected {contract.input_manifest_sha256}, got {actual_sha}"
            )

        inputs = self.work_root / "inputs"
        inputs.mkdir(exist_ok=True)
        locator = "inputs/snapshot.bin"
        dest = self.work_root / locator
        dest.write_bytes(snapshot.read_bytes())

        validated = self.resolver.validate(locator, self.profile)
        resolved = self.resolver.resolve(
            str(self.work_root), locator, self.profile, expected_sha256=actual_sha
        )
        if resolved.get("status") != "ok":
            return ShadowResult(
                status="FAILED",
                reason_code=str(resolved.get("reason_code") or "LOCATOR_REJECTED"),
                hold_reasons=holds,
                envelopes={"resolve": resolved, "validate": validated},
            )

        SourceRef = self._pkgs["SourceRef"]
        DictReader = self._pkgs["DictReader"]
        freeze = self.store.freeze(
            str(self.work_root / "cas"),
            [SourceRef(source_id="s-snapshot", locator=locator, expected_sha256=actual_sha)],
            DictReader({locator: dest.read_bytes()}),
        )
        if freeze.get("status") != "ok":
            return ShadowResult(
                status="FAILED",
                reason_code=str(freeze.get("reason_code") or "FREEZE_FAILED"),
                hold_reasons=holds,
                envelopes={"freeze": freeze, "resolve": resolved},
            )

        cas_root = str(self.work_root / "cas")
        published = self._pkgs["AssetStore"].is_published(cas_root)
        verified = self._pkgs["AssetStore"].verify_manifest(cas_root)
        if not published or not verified:
            return ShadowResult(
                status="FAILED",
                reason_code="MISSING_EVIDENCE",
                hold_reasons=holds + ["MISSING_EVIDENCE:MANIFEST"],
                envelopes={"freeze": freeze, "published": published, "verified": verified},
            )

        digest = self._request_digest(contract, actual_sha)
        admit = self.ledger.admit(self.SCOPE, contract.fingerprint(), digest)
        envelopes: dict[str, Any] = {
            "validate": validated,
            "resolve": resolved,
            "freeze": freeze,
            "verified": verified,
            "admit": admit,
        }
        if admit.get("status") != "ok":
            return ShadowResult(
                status="FAILED",
                reason_code=str(admit.get("reason_code") or "ADMIT_FAILED"),
                fingerprint=contract.fingerprint(),
                snapshot_sha256=actual_sha,
                hold_reasons=holds,
                envelopes=envelopes,
            )

        job_id = admit.get("job_id")
        if admit.get("reason_code") == "IDEMPOTENT_HIT":
            result = ShadowResult(
                status="DUPLICATE_NOOP",
                reason_code="IDEMPOTENT_HIT",
                contractor_job_id=job_id,
                fingerprint=contract.fingerprint(),
                snapshot_sha256=actual_sha,
                manifest_sha256=str(freeze.get("manifest_sha256") or ""),
                hold_reasons=holds,
                envelopes=envelopes,
                evidence={"replay": True, "factory_baseline": FACTORY_BASELINE, "contractor_baseline": CONTRACTOR_BASELINE},
            )
            if holds:
                result.status = "HUMAN_HOLD"
                result.reason_code = "BLOCKED_INPUT"
            return result

        reserve = self.ledger.reserve_budget(
            job_id, contract.attempt_budget, "rsv-" + contract.fingerprint()[:16]
        )
        envelopes["reserve"] = reserve
        claim = self.ledger.claim(job_id, self.WORKER, max(1000, contract.timeout_seconds * 1000))
        envelopes["claim"] = claim
        if claim.get("status") != "ok":
            return ShadowResult(
                status="FAILED",
                reason_code=str(claim.get("reason_code") or "CLAIM_FAILED"),
                contractor_job_id=job_id,
                fingerprint=contract.fingerprint(),
                snapshot_sha256=actual_sha,
                hold_reasons=holds,
                envelopes=envelopes,
            )

        attempt = self.ledger.record_attempt(
            job_id, claim["lease_token"], claim["fence"], "transient"
        )
        envelopes["attempt"] = attempt
        result_digest = hashlib.sha256(
            canonical_bytes({"job_id": job_id, "snapshot": actual_sha, "mode": "LOCAL_SHADOW"})
        ).hexdigest()
        final = self.ledger.finalize(
            job_id, claim["lease_token"], claim["fence"], "SUCCEEDED", result_digest
        )
        envelopes["finalize"] = final

        event = {
            "target": self.TARGET,
            "event_id": "j3-" + contract.fingerprint()[:16],
            "revision": 0,
            "mapping_version": 1,
            "properties": {
                "Status": "SUCCEEDED",
                "Result Ref": result_digest[:16],
            },
        }
        projected = self.projector.project(event, 0, self.transport, token=self.TOKEN)
        envelopes["project"] = projected

        live_calls = [
            c for c in getattr(self.transport, "calls", [])
            if not str(type(self.transport).__name__).startswith("Fake")
        ]
        if live_calls:
            return ShadowResult(
                status="HUMAN_HOLD",
                reason_code="LIVE_TRANSPORT_FORBIDDEN",
                contractor_job_id=job_id,
                hold_reasons=holds + ["HUMAN_HOLD:LIVE_TRANSPORT"],
                envelopes=envelopes,
            )

        status = "LOCAL_SHADOW_COMPLETE"
        reason = "OK"
        if holds:
            status = "HUMAN_HOLD"
            reason = "BLOCKED_INPUT"

        evidence_path = self.work_root / "shadow-receipt.json"
        receipt = {
            "mode": "LOCAL_SHADOW",
            "production_writes": False,
            "live_notion": False,
            "factory_baseline": FACTORY_BASELINE,
            "contractor_baseline": CONTRACTOR_BASELINE,
            "fingerprint": contract.fingerprint(),
            "contractor_job_id": job_id,
            "snapshot_sha256": actual_sha,
            "manifest_sha256": freeze.get("manifest_sha256"),
            "hold_reasons": holds,
            "transport_calls": list(getattr(self.transport, "calls", [])),
        }
        evidence_path.write_bytes(canonical_bytes(receipt) + b"\n")

        return ShadowResult(
            status=status,
            reason_code=reason,
            contractor_job_id=job_id,
            fingerprint=contract.fingerprint(),
            snapshot_sha256=actual_sha,
            manifest_sha256=str(freeze.get("manifest_sha256") or ""),
            hold_reasons=holds,
            envelopes=envelopes,
            evidence={
                "receipt": evidence_path.name,
                "receipt_sha256": sha256_file(evidence_path),
                "history": self.ledger.history(job_id),
                "ledger": self.ledger.get(job_id),
                "transport_class": type(self.transport).__name__,
            },
        )
