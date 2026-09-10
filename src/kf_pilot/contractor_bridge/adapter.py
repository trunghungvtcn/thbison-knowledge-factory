"""LOCAL_SHADOW adapter over contractor public APIs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import hashlib
import json

from kf_pilot.runtime_contract import ContractError, RunContract, canonical_bytes, sha256_file

from .mapping import CONTRACTOR_BASELINE, FACTORY_BASELINE
from .pins import (
    TERMINAL_STATES,
    holds_for_pins,
    mark_allowed,
    normalize_pins,
    pin_record,
    transport_is_allowed,
)


class BridgeError(ContractError):
    pass


def _require_contractor() -> dict[str, Any]:
    try:
        from grok_asset_store import AssetStore, DictReader, SourceRef
        from grok_job_ledger import JobLedger
        from grok_locator import LocatorProfile, LocatorResolver
        from grok_notion_projection import FakeTransport, Projector
    except ImportError as exc:
        raise BridgeError(
            "BLOCKED_INPUT: contractor public packages not importable "
            f"({exc}). Use pipeline-lab-contractor-m1-m5@{CONTRACTOR_BASELINE}."
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
    SCOPE = "kf.j3.local_shadow"
    WORKER = "j3-shadow-worker"
    TARGET = "sandbox-page-001"
    TOKEN = "local-shadow-token"
    RECEIPT_NAME = "shadow-receipt.json"

    def __init__(
        self,
        work_root: Path,
        *,
        transport: Any | None = None,
        j1_commit_sha: str | None = None,
        j1_input_hash: str | None = None,
        j2_commit_sha: str | None = None,
        j2_input_hash: str | None = None,
        j1_input_sha: str | None = None,
        j2_env_sha: str | None = None,
    ) -> None:
        self.work_root = Path(work_root)
        self.work_root.mkdir(parents=True, exist_ok=True)
        raw = normalize_pins(
            j1_commit_sha=j1_commit_sha,
            j1_input_hash=j1_input_hash,
            j2_commit_sha=j2_commit_sha,
            j2_input_hash=j2_input_hash,
            j1_input_sha=j1_input_sha,
            j2_env_sha=j2_env_sha,
        )
        self.j1_commit_sha = raw["j1_commit_sha"]
        self.j1_input_hash = raw["j1_input_hash"]
        self.j2_commit_sha = raw["j2_commit_sha"]
        self.j2_input_hash = raw["j2_input_hash"]
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
            self.transport = mark_allowed(
                pkgs["FakeTransport"](allowed_targets={self.TARGET}, token=self.TOKEN)
            )
        else:
            self.transport = transport

    def close(self) -> None:
        self.ledger.close()

    def _pin_record(self) -> dict[str, Any]:
        return pin_record(
            {
                "j1_commit_sha": self.j1_commit_sha,
                "j1_input_hash": self.j1_input_hash,
                "j2_commit_sha": self.j2_commit_sha,
                "j2_input_hash": self.j2_input_hash,
            }
        )

    def _holds_for_pins(self) -> list[str]:
        return holds_for_pins(self._pin_record())

    def _request_digest(self, contract: RunContract, snapshot_sha: str) -> str:
        pins = self._pin_record()
        payload = {
            "fingerprint": contract.fingerprint(),
            "snapshot_sha256": snapshot_sha,
            "factory_baseline": FACTORY_BASELINE,
            "contractor_baseline": CONTRACTOR_BASELINE,
            "j1_commit_sha": pins["j1_commit_sha"],
            "j1_input_hash": pins["j1_input_hash"],
            "j2_commit_sha": pins["j2_commit_sha"],
            "j2_input_hash": pins["j2_input_hash"],
            "pin_roles": pins["pin_roles"],
        }
        return hashlib.sha256(canonical_bytes(payload)).hexdigest()

    def _fail(self, reason: str, **kw: Any) -> ShadowResult:
        extra = kw.pop("extra_holds", None) or []
        holds = list(kw.pop("holds", [])) + list(extra)
        evidence = dict(kw.pop("evidence", None) or {})
        evidence.setdefault("pins", self._pin_record())
        evidence.setdefault("real_data_pass", False)
        evidence.setdefault("hash_verified", False)
        return ShadowResult(status="FAILED", reason_code=reason, hold_reasons=holds, evidence=evidence, **kw)

    def _receipt_path(self) -> Path:
        return self.work_root / self.RECEIPT_NAME

    def _load_receipt(self) -> dict[str, Any] | None:
        path = self._receipt_path()
        if not path.is_file():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None
        return raw if isinstance(raw, dict) else None

    def _receipt_proves(
        self,
        receipt: dict[str, Any] | None,
        *,
        job_id: str,
        fingerprint: str,
        digest: str,
    ) -> bool:
        if not receipt:
            return False
        return (
            receipt.get("contractor_job_id") == job_id
            and receipt.get("fingerprint") == fingerprint
            and receipt.get("request_digest") == digest
            and receipt.get("projection_status") == "ok"
            and receipt.get("mode") == "LOCAL_SHADOW"
        )

    def _pin_evidence(self, pins: dict[str, Any], **extra: Any) -> dict[str, Any]:
        synthetic = pins.get("j1_hash_status") == "SYNTHETIC" or pins.get("j2_hash_status") == "SYNTHETIC"
        evidence = {
            "pins": pins,
            "real_data_pass": False,
            "hash_verified": False,
            "synthetic_fixture": synthetic,
            "synthetic_pass": False,
            "j2_role": "environment",
            "transport_type": type(self.transport).__name__,
            "transport_allowed": transport_is_allowed(self.transport),
        }
        evidence.update(extra)
        return evidence

    def _result_digest(self, job_id: str, snapshot_sha: str) -> str:
        return hashlib.sha256(
            canonical_bytes({"job_id": job_id, "snapshot": snapshot_sha, "mode": "LOCAL_SHADOW"})
        ).hexdigest()

    def _project_event(self, fp: str, result_digest: str) -> dict[str, Any]:
        return {
            "target": self.TARGET,
            "event_id": "j3-" + fp[:16],
            "revision": 0,
            "mapping_version": 1,
            "properties": {"Status": "SUCCEEDED", "Result Ref": result_digest[:16]},
        }

    def _transport_denied(
        self,
        *,
        job_id: str | None,
        fp: str,
        actual_sha: str,
        manifest: str,
        holds: list[str],
        pins: dict[str, Any],
        envelopes: dict[str, Any],
        resumed: bool = False,
    ) -> ShadowResult | None:
        if transport_is_allowed(self.transport):
            return None
        status = "RECONCILE_REQUIRED" if resumed else "FAILED"
        reason = "TRANSPORT_NOT_ALLOWED"
        return ShadowResult(
            status=status,
            reason_code=reason,
            contractor_job_id=job_id,
            fingerprint=fp,
            snapshot_sha256=actual_sha,
            manifest_sha256=manifest,
            hold_reasons=holds + ["TRANSPORT_NOT_ALLOWED"],
            envelopes=envelopes,
            evidence=self._pin_evidence(
                pins,
                transport_allowed=False,
                resumed=resumed,
                projection_complete=False,
            ),
        )

    def _persist_receipt(
        self,
        *,
        job_id: str,
        fp: str,
        actual_sha: str,
        manifest: str,
        digest: str,
        holds: list[str],
        pins: dict[str, Any],
        envelopes: dict[str, Any],
    ) -> tuple[dict[str, Any], str] | ShadowResult:
        evidence_path = self._receipt_path()
        receipt = {
            "mode": "LOCAL_SHADOW",
            "production_writes": False,
            "live_notion": False,
            "factory_baseline": FACTORY_BASELINE,
            "contractor_baseline": CONTRACTOR_BASELINE,
            "fingerprint": fp,
            "contractor_job_id": job_id,
            "snapshot_sha256": actual_sha,
            "manifest_sha256": manifest,
            "hold_reasons": holds,
            "pins": pins,
            "request_digest": digest,
            "transport_allowed": True,
            "transport_type": type(self.transport).__name__,
            "projection_status": "ok",
            "projection_event_id": "j3-" + fp[:16],
            "receipt_kind": "LOCAL_SHADOW_DURABLE",
            "j2_role": "environment",
            "hash_verified": False,
            "real_data_pass": False,
        }
        evidence_path.write_bytes(canonical_bytes(receipt) + b"\n")
        receipt_sha = sha256_file(evidence_path)
        outbox = json.dumps(
            {
                "event_id": receipt["projection_event_id"],
                "receipt": evidence_path.name,
                "receipt_sha256": receipt_sha,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        marked = self.ledger.mark_projected(job_id, outbox, result_payload=receipt_sha)
        envelopes["mark_projected"] = marked
        if marked.get("status") != "ok":
            return self._fail(
                str(marked.get("reason_code") or "MARK_PROJECTED_FAILED"),
                contractor_job_id=job_id,
                fingerprint=fp,
                snapshot_sha256=actual_sha,
                manifest_sha256=manifest,
                envelopes=envelopes,
                holds=holds,
                evidence=self._pin_evidence(pins, projection_complete=False, receipt=evidence_path.name),
            )
        return receipt, receipt_sha

    def _project_and_persist(
        self,
        *,
        job_id: str,
        fp: str,
        actual_sha: str,
        manifest: str,
        digest: str,
        holds: list[str],
        pins: dict[str, Any],
        envelopes: dict[str, Any],
        resumed: bool = False,
    ) -> ShadowResult:
        denied = self._transport_denied(
            job_id=job_id,
            fp=fp,
            actual_sha=actual_sha,
            manifest=manifest,
            holds=holds,
            pins=pins,
            envelopes=envelopes,
            resumed=resumed,
        )
        if denied is not None:
            return denied
        result_digest = self._result_digest(job_id, actual_sha)
        event = self._project_event(fp, result_digest)
        try:
            projected = self.projector.project(event, 0, self.transport, token=self.TOKEN)
        except Exception as exc:
            envelopes["project"] = {
                "status": "error",
                "reason_code": "PROJECT_CRASH",
                "error": type(exc).__name__,
            }
            status = "RECONCILE_REQUIRED" if resumed else "FAILED"
            return ShadowResult(
                status=status,
                reason_code="PROJECT_CRASH",
                contractor_job_id=job_id,
                fingerprint=fp,
                snapshot_sha256=actual_sha,
                manifest_sha256=manifest,
                hold_reasons=holds + ["RECONCILE_REQUIRED:PROJECT_CRASH"],
                envelopes=envelopes,
                evidence=self._pin_evidence(pins, resumed=resumed, projection_complete=False),
            )
        envelopes["project"] = projected
        if projected.get("status") != "ok":
            reason = str(projected.get("reason_code") or "PROJECT_FAILED")
            if resumed:
                return ShadowResult(
                    status="RECONCILE_REQUIRED",
                    reason_code=reason,
                    contractor_job_id=job_id,
                    fingerprint=fp,
                    snapshot_sha256=actual_sha,
                    manifest_sha256=manifest,
                    hold_reasons=holds + [f"RECONCILE_REQUIRED:{reason}"],
                    envelopes=envelopes,
                    evidence=self._pin_evidence(pins, resumed=True, projection_complete=False),
                )
            return self._fail(
                reason,
                contractor_job_id=job_id,
                fingerprint=fp,
                snapshot_sha256=actual_sha,
                manifest_sha256=manifest,
                envelopes=envelopes,
                holds=holds,
                evidence=self._pin_evidence(pins, projection_complete=False),
            )
        persisted = self._persist_receipt(
            job_id=job_id,
            fp=fp,
            actual_sha=actual_sha,
            manifest=manifest,
            digest=digest,
            holds=holds,
            pins=pins,
            envelopes=envelopes,
        )
        if isinstance(persisted, ShadowResult):
            if resumed:
                persisted.status = "RECONCILE_REQUIRED"
            return persisted
        _receipt, receipt_sha = persisted
        status, reason = "LOCAL_SHADOW_COMPLETE", "OK"
        if holds:
            status, reason = "HUMAN_HOLD", "BLOCKED_INPUT"
        synthetic = pins.get("j1_hash_status") == "SYNTHETIC" or pins.get("j2_hash_status") == "SYNTHETIC"
        return ShadowResult(
            status=status,
            reason_code=reason,
            contractor_job_id=job_id,
            fingerprint=fp,
            snapshot_sha256=actual_sha,
            manifest_sha256=manifest,
            hold_reasons=holds,
            envelopes=envelopes,
            evidence=self._pin_evidence(
                pins,
                receipt=self.RECEIPT_NAME,
                receipt_sha256=receipt_sha,
                history=self.ledger.history(job_id),
                ledger=self.ledger.get(job_id),
                transport_allowed=True,
                resumed=resumed,
                projection_complete=True,
                synthetic_pass=bool(synthetic and status == "LOCAL_SHADOW_COMPLETE"),
                real_data_pass=False,
            ),
        )

    def _replay(
        self,
        *,
        job_id: str,
        envelopes: dict[str, Any],
        fp: str,
        actual_sha: str,
        manifest: str,
        holds: list[str],
        pins: dict[str, Any],
        digest: str,
    ) -> ShadowResult:
        current = self.ledger.get(job_id)
        envelopes["ledger_get"] = current
        extra = current if isinstance(current, dict) else {}
        state = extra.get("state")
        projection_status = extra.get("projection_status") or "NONE"
        receipt = self._load_receipt()
        envelopes["receipt_present"] = bool(receipt)
        proved = (
            state == "SUCCEEDED"
            and projection_status == "APPLIED"
            and self._receipt_proves(receipt, job_id=job_id, fingerprint=fp, digest=digest)
        )
        if state not in TERMINAL_STATES:
            return ShadowResult(
                status="HUMAN_HOLD",
                reason_code="IDEMPOTENT_HIT_NON_TERMINAL",
                contractor_job_id=job_id,
                fingerprint=fp,
                snapshot_sha256=actual_sha,
                manifest_sha256=manifest,
                hold_reasons=holds + [f"REPLAY_STATE:{state}"],
                envelopes=envelopes,
                evidence=self._pin_evidence(
                    pins,
                    replay=True,
                    ledger_state=state,
                    projection_status=projection_status,
                    projection_complete=False,
                ),
            )
        if proved:
            return ShadowResult(
                status="DUPLICATE_NOOP",
                reason_code="IDEMPOTENT_HIT",
                contractor_job_id=job_id,
                fingerprint=fp,
                snapshot_sha256=actual_sha,
                manifest_sha256=manifest,
                hold_reasons=holds,
                envelopes=envelopes,
                evidence=self._pin_evidence(
                    pins,
                    replay=True,
                    ledger_state=state,
                    projection_status=projection_status,
                    projection_complete=True,
                    receipt=self.RECEIPT_NAME,
                    resumed=False,
                    synthetic_pass=False,
                ),
            )
        if state != "SUCCEEDED":
            return ShadowResult(
                status="RECONCILE_REQUIRED",
                reason_code=f"REPLAY_TERMINAL_{state}",
                contractor_job_id=job_id,
                fingerprint=fp,
                snapshot_sha256=actual_sha,
                manifest_sha256=manifest,
                hold_reasons=holds + [f"RECONCILE_REQUIRED:{state}"],
                envelopes=envelopes,
                evidence=self._pin_evidence(
                    pins,
                    replay=True,
                    ledger_state=state,
                    projection_status=projection_status,
                    projection_complete=False,
                ),
            )
        return self._project_and_persist(
            job_id=job_id,
            fp=fp,
            actual_sha=actual_sha,
            manifest=manifest,
            digest=digest,
            holds=holds,
            pins=pins,
            envelopes=envelopes,
            resumed=True,
        )

    def run(self, contract: RunContract, snapshot_path: Path) -> ShadowResult:
        holds = self._holds_for_pins()
        pins = self._pin_record()
        if contract.mode != "TEST_ONLY":
            return ShadowResult(
                status="HUMAN_HOLD",
                reason_code="MODE_NOT_TEST_ONLY",
                hold_reasons=holds + ["HUMAN_HOLD:NON_TEST_ONLY"],
                evidence=self._pin_evidence(pins, blocked_before=["freeze", "admit", "project"]),
            )
        # B1: missing/malformed dependency HOLDs before freeze, admit, or project.
        if holds:
            return ShadowResult(
                status="HUMAN_HOLD",
                reason_code="BLOCKED_INPUT",
                hold_reasons=holds,
                evidence=self._pin_evidence(
                    pins,
                    blocked_before=["freeze", "admit", "project"],
                    blocked_input=True,
                ),
            )
        contract.validate()
        snapshot = Path(snapshot_path).resolve(strict=True)
        actual_sha = sha256_file(snapshot)
        if actual_sha != contract.input_manifest_sha256.lower():
            raise BridgeError(
                f"snapshot hash mismatch: expected {contract.input_manifest_sha256}, got {actual_sha}"
            )
        (self.work_root / "inputs").mkdir(exist_ok=True)
        locator = "inputs/snapshot.bin"
        dest = self.work_root / locator
        dest.write_bytes(snapshot.read_bytes())
        validated = self.resolver.validate(locator, self.profile)
        resolved = self.resolver.resolve(
            str(self.work_root), locator, self.profile, expected_sha256=actual_sha
        )
        if resolved.get("status") != "ok":
            return self._fail(
                str(resolved.get("reason_code") or "LOCATOR_REJECTED"),
                holds=holds,
                envelopes={"resolve": resolved, "validate": validated},
            )
        freeze = self.store.freeze(
            str(self.work_root / "cas"),
            [self._pkgs["SourceRef"](source_id="s-snapshot", locator=locator, expected_sha256=actual_sha)],
            self._pkgs["DictReader"]({locator: dest.read_bytes()}),
        )
        if freeze.get("status") != "ok":
            return self._fail(
                str(freeze.get("reason_code") or "FREEZE_FAILED"),
                holds=holds,
                envelopes={"freeze": freeze, "resolve": resolved},
            )
        cas_root = str(self.work_root / "cas")
        published = self._pkgs["AssetStore"].is_published(cas_root)
        verified = self._pkgs["AssetStore"].verify_manifest(cas_root)
        if not published or not verified:
            return self._fail(
                "MISSING_EVIDENCE",
                holds=holds,
                extra_holds=["MISSING_EVIDENCE:MANIFEST"],
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
        fp = contract.fingerprint()
        manifest = str(freeze.get("manifest_sha256") or "")
        base = {
            "fingerprint": fp,
            "snapshot_sha256": actual_sha,
            "manifest_sha256": manifest,
            "envelopes": envelopes,
            "holds": holds,
        }
        if admit.get("status") != "ok":
            return self._fail(str(admit.get("reason_code") or "ADMIT_FAILED"), **base)
        job_id = admit.get("job_id")
        base["contractor_job_id"] = job_id
        if admit.get("reason_code") == "IDEMPOTENT_HIT":
            return self._replay(
                job_id=job_id,
                envelopes=envelopes,
                fp=fp,
                actual_sha=actual_sha,
                manifest=manifest,
                holds=holds,
                pins=pins,
                digest=digest,
            )
        reserve = self.ledger.reserve_budget(job_id, contract.attempt_budget, "rsv-" + fp[:16])
        envelopes["reserve"] = reserve
        if reserve.get("status") != "ok":
            return self._fail(str(reserve.get("reason_code") or "RESERVE_FAILED"), **base)
        claim = self.ledger.claim(job_id, self.WORKER, max(1000, contract.timeout_seconds * 1000))
        envelopes["claim"] = claim
        if claim.get("status") != "ok":
            return self._fail(str(claim.get("reason_code") or "CLAIM_FAILED"), **base)
        attempt = self.ledger.record_attempt(job_id, claim["lease_token"], claim["fence"], "transient")
        envelopes["attempt"] = attempt
        if attempt.get("status") != "ok":
            return self._fail(str(attempt.get("reason_code") or "ATTEMPT_FAILED"), **base)
        result_digest = self._result_digest(job_id, actual_sha)
        final = self.ledger.finalize(job_id, claim["lease_token"], claim["fence"], "SUCCEEDED", result_digest)
        envelopes["finalize"] = final
        if final.get("status") != "ok":
            return self._fail(str(final.get("reason_code") or "FINALIZE_FAILED"), **base)
        return self._project_and_persist(
            job_id=job_id,
            fp=fp,
            actual_sha=actual_sha,
            manifest=manifest,
            digest=digest,
            holds=holds,
            pins=pins,
            envelopes=envelopes,
            resumed=False,
        )
