import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .acquisition import discover, freeze
from .pipeline import project_shadow, propose, review_check
from .verifier import verify


def main(argv=None):
    parser = argparse.ArgumentParser(description="V16.6 local evidence completion; no production writes")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("discover"); p.add_argument("--research-plan", type=Path, required=True); p.add_argument("--output", type=Path, required=True); p.add_argument("--accessed-at")
    p = sub.add_parser("freeze"); p.add_argument("--acquisition-dir", type=Path, required=True); p.add_argument("--as-of", required=True); p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("propose"); p.add_argument("--run-config", type=Path, required=True); p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("review-check"); p.add_argument("--proposal", type=Path, required=True); p.add_argument("--trust-config", type=Path, required=True); p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("project-shadow"); p.add_argument("--run-config", type=Path, required=True); p.add_argument("--proposal", type=Path, required=True); p.add_argument("--trust-config", type=Path); p.add_argument("--output", type=Path, required=True)
    p = sub.add_parser("verify"); p.add_argument("--inputs", type=Path, required=True); p.add_argument("--committed-run", type=Path, required=True); p.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "discover": result = discover(args.research_plan, args.output, args.accessed_at or datetime.now(timezone.utc).isoformat())
    elif args.command == "freeze": result = freeze(args.acquisition_dir, args.as_of, args.output)
    elif args.command == "propose": result = propose(args.run_config, args.output)
    elif args.command == "review-check": result = review_check(args.proposal, args.trust_config, args.output)
    elif args.command == "project-shadow": result = project_shadow(args.run_config, args.proposal, args.trust_config, args.output)
    else: result = verify(args.inputs, args.committed_run, args.report)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

