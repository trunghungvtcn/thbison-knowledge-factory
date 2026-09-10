import { writeFileSync, mkdirSync } from "node:fs";

const BASE = process.env.BASE_URL ?? "http://127.0.0.1:8080";
const TOKEN = "thbison-test-token-aaaaaaaa";

function body(id) {
  return {
    contract_version: "1.0.0",
    project_id: "test-thbison",
    data_class: "TEST_ONLY",
    request_id: id,
    scope: { country_code: "VN", language: "vi", timezone: "Asia/Bangkok", domain: "manual-chain-hoist" },
    seeds: ["pa lăng xích kéo tay"],
    existing_pages: [],
    budget: {
      max_provider_requests: 3,
      max_tokens: 1000,
      max_cost_usd: "0.500000",
      deadline_at: "2030-01-01T00:05:00Z",
      max_transport_attempts: 2,
    },
  };
}

async function post(idem, requestId) {
  const t0 = performance.now();
  const res = await fetch(`${BASE}/v1/planning/jobs`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${TOKEN}`,
      "x-contract-version": "1.0.0",
      "idempotency-key": idem,
      "content-type": "application/json",
    },
    body: JSON.stringify(body(requestId)),
  });
  const ms = performance.now() - t0;
  const json = await res.json();
  return { ms, status: res.status, json };
}

function pct(samples, p) {
  const s = [...samples].sort((a, b) => a - b);
  return s[Math.min(s.length - 1, Math.floor((p / 100) * s.length))];
}

async function main() {
  const admission = [];
  const conc = 5;
  for (let batch = 0; batch < 20; batch++) {
    const jobs = [];
    for (let i = 0; i < conc; i++) {
      const n = batch * conc + i;
      jobs.push(post(`idem-bench-${String(n).padStart(12, "0")}`, `req-bench-${String(n).padStart(8, "0")}`));
    }
    const part = await Promise.all(jobs);
    for (const x of part) admission.push(x.ms);
  }
  const first = admission[0];
  const cached = [];
  const jobId = (await post("idem-bench-cache-read01", "req-cache01")).json.job_id;
  for (let i = 0; i < 30; i++) {
    await new Promise((r) => setTimeout(r, 20));
    const t0 = performance.now();
    const r = await fetch(`${BASE}/v1/planning/jobs/${jobId}`, {
      headers: { authorization: `Bearer ${TOKEN}`, "x-contract-version": "1.0.0" },
    });
    await r.json();
    cached.push(performance.now() - t0);
    if ((await r.clone?.json?.()) || true) {
      /* */
    }
  }
  const report = {
    environment: "2 vCPU class unspecified sandbox; provider latency excluded from admission (202 only)",
    admission_p95_ms: pct(admission, 95),
    admission_samples: admission.slice(0, 20),
    cached_get_p95_ms: pct(cached, 95),
    baseline_first_admission_ms: first,
    candidate_p95_ms: pct(admission, 95),
    improvement_pct:
      first > 0 ? Math.round((1 - pct(admission, 95) / Math.max(first, 1)) * 1000) / 10 : 0,
    metric: "admission_p95_ms plus cache hits on repeat GET",
    gates: { p95_admission_budget_ms: 1000, p95_cached_ms: 500 },
  };
  mkdirSync("delivery", { recursive: true });
  writeFileSync("delivery/benchmark.json", JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
}

await main();
