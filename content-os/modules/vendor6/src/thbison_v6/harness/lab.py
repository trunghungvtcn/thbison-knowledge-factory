"""Isolated lab environment. All chain hops dispatch through the registry."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from thbison_v6.adapters.registry import AdapterRegistry, HOPS, MissingAdapterError
from thbison_v6.contract_validate import assert_valid
from thbison_v6.faults import FaultPlan
from thbison_v6.hashutil import payload_digest, sha256_hex
from thbison_v6.ledger import Clock, FileLedger
from thbison_v6.simulators.cms import CmsSimulator
from thbison_v6.simulators.knowledge import KnowledgeSimulator
from thbison_v6.simulators.planning import PlanningSimulator, REQUIRED_BRIEF_FIELDS
from thbison_v6.simulators.runtime import RuntimeSimulator
from thbison_v6.simulators.writer import WriterSimulator

MODES = ("REFERENCE_ONLY", "ACTUAL_COMPONENTS", "MIXED", "STAGING")


class RegistryModeMismatch(ValueError):
    pass


@dataclass
class HopTrace:
    hops: list[dict] = field(default_factory=list)

    def add(self, rec: dict) -> str:
        self.hops.append(rec)
        return rec.get("digest", "")


class Lab:
    def __init__(
        self,
        mode: str = "REFERENCE_ONLY",
        root: Path | None = None,
        registry: AdapterRegistry | None = None,
        stub_hops: frozenset[str] | None = None,
    ):
        if mode not in MODES:
            raise ValueError(mode)
        self.mode = mode
        self.root = Path(root or tempfile.mkdtemp(prefix="v6lab-"))
        (self.root / "data").mkdir(parents=True, exist_ok=True)
        self.ledger = FileLedger(self.root / "data")
        self.clock = Clock()
        self.faults = FaultPlan()
        self.trace = HopTrace()
        # Local simulators remain available for unit tests / REFERENCE bindings.
        self.planning = PlanningSimulator(self.ledger, self.faults)
        self.knowledge = KnowledgeSimulator(self.ledger, self.faults)
        self.writer = WriterSimulator(self.ledger, self.clock, self.faults)
        self.runtime = RuntimeSimulator(self.ledger, self.clock, self.faults)
        self.cms = CmsSimulator(self.ledger, self.clock, self.faults)
        self.contract_digest = self._read_contract_digest()
        if registry is not None and registry.mode != mode:
            raise RegistryModeMismatch(f"REGISTRY_MODE_MISMATCH:lab={mode}:registry={registry.mode}")
        self.registry = registry or AdapterRegistry(mode, stub_hops)
        if registry is None:
            if mode == "REFERENCE_ONLY":
                self.registry.bind("planning", "STUB", self.planning, "VENDOR_1")
                self.registry.bind("knowledge", "STUB", self.knowledge, "VENDOR_4")
                self.registry.bind("writer", "STUB", self.writer, "VENDOR_2")
                self.registry.bind("runtime", "STUB", self.runtime, "VENDOR_3")
                self.registry.bind("cms", "STUB", self.cms, "VENDOR_5")
        self.registry.require()

    def _read_contract_digest(self) -> str:
        pin = os.environ.get("CONTRACT_DIGEST", "").strip()
        here = Path(__file__).resolve().parents[3] / "CONTRACT_SHA256.txt"
        if here.exists():
            return here.read_text(encoding="utf-8").strip()
        return pin or "UNPINNED"

    def assert_contract(self, presented: str) -> None:
        if presented != self.contract_digest:
            raise ValueError("UNSUPPORTED_CONTRACT")

    def hop_kind(self, name: str) -> str:
        b = self.registry.bindings.get(name)
        return b.kind if b else "MISSING"

    def _impl(self, hop: str) -> Any:
        b = self.registry.bindings.get(hop)
        if b is None:
            raise MissingAdapterError(hop, self.mode)
        return b

    def _record(self, hop: str, payload: Any) -> None:
        b = self._impl(hop)
        impl = b.impl
        digest = payload_digest(payload) if not isinstance(payload, (str, bytes)) else sha256_hex(payload)
        transport = getattr(impl, "transport_name", None) or getattr(getattr(impl, "client", None), "transport_name", None)
        verified = bool(getattr(impl, "verified_component", False))
        self.trace.add(
            {
                "hop": hop,
                "producer": f"{b.vendor}-{b.kind}",
                "digest": digest,
                "stub": b.kind == "STUB",
                "kind": b.kind,
                "impl": type(impl).__name__,
                "vendor": b.vendor,
                "endpoint": b.endpoint,
                "transport": transport,
                "verified_component": verified,
            }
        )

    def run_chain(
        self,
        project_id: str = "proj-lab",
        publish_mode: str = "STAGING_DRAFT",
        destination_id: str = "cms-sandbox",
    ) -> dict[str, Any]:
        """Single execution path: every hop uses registry.impl. No simulator fallback."""
        self.registry.require()
        for hop in HOPS:
            self._impl(hop)

        planning = self._impl("planning").impl
        knowledge = self._impl("knowledge").impl
        writer = self._impl("writer").impl
        runtime = self._impl("runtime").impl
        cms = self._impl("cms").impl

        plan = planning.plan({"project_id": project_id})
        brief = plan["brief"] if isinstance(plan, dict) and "brief" in plan else plan
        missing = [f for f in REQUIRED_BRIEF_FIELDS if f not in brief]
        if missing:
            raise ValueError(f"BRIEF_INCOMPLETE:{missing}")
        assert_valid("ContentBrief", brief)
        self._record("planning", brief)

        bundle = knowledge.query(brief)
        assert_valid("EvidenceBundle", bundle)
        self._record("knowledge", bundle)

        article = writer.draft(brief, bundle)
        assert_valid("ArticlePackage", article)
        self._record("writer", article)

        approval = writer.approve(article, destination_id)
        assert_valid("ApprovalRecord", approval)
        self._record("writer", approval)

        job = runtime.admit(
            project_id,
            "publish",
            f"idem-{article['article_id']}-{article['article_revision']}",
            {"article_id": article["article_id"], "article_revision": article["article_revision"]},
        )
        req = {
            "contract_version": "1.0.0",
            "project_id": project_id,
            "data_class": "TEST_ONLY",
            "request_id": job["idempotency_key"],
            "article_id": article["article_id"],
            "article_revision": article["article_revision"],
            "content_sha256": article["content_sha256"],
            "evidence_snapshot_sha256": article["evidence_snapshot_sha256"],
            "approval_id": approval["approval_id"],
            "destination_id": destination_id,
            "mode": publish_mode,
            "scheduled_at": None,
        }
        assert_valid("PublishRequest", req)
        receipt = cms.publish(req, approval)
        assert_valid("PublicationReceipt", receipt)
        runtime.complete(job["job_id"], receipt)
        self._record("cms", receipt)
        self._record("runtime", job)
        return {
            "plan": plan,
            "brief": brief,
            "bundle": bundle,
            "article": article,
            "approval": approval,
            "receipt": receipt,
            "job": job,
            "trace": self.trace.hops,
        }

    def run_reference_chain(self, **kwargs: Any) -> dict[str, Any]:
        """Alias of run_chain. Dispatch is always via registry (stubs in REFERENCE_ONLY)."""
        return self.run_chain(**kwargs)

    def persist_trace(self) -> Path:
        p = self.root / "trace.json"
        p.write_text(json.dumps(self.trace.hops, indent=2), encoding="utf-8")
        return p
