"""Explicit local or separately configured staging-only test cycle."""
import argparse
import json
import os
from pathlib import Path
import sys
from uuid import UUID, uuid5

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from kf_pilot.v161_staging.harness import Blocked, GuardedAdapter, run_cycle, validate_plan
from kf_pilot.v161_staging.transports import MemoryTransport, NotionStagingTransport

REQUIRED = ('V161_ENV', 'V161_STAGING_TARGET_ID', 'V161_STAGING_NOTION_TOKEN', 'V161_STAGING_PAGE_IDS')
NAMESPACE = UUID('c6a5d339-eab8-41b0-8060-280cfac60809')


def production_page_ids():
    mapping = ROOT/'v16_migration/v161-inputs/v15_all_page_mappings.json'
    snapshot = ROOT/'v16_migration/v161-inputs/live_snapshot_raw.json'
    # Missing deny-list inputs is an error, not permission to continue.
    ids = {r['notion_page_id'] for r in json.loads(mapping.read_text(encoding='utf-8'))}
    ids.update(r['url'].rstrip('/').split('/')[-1] for r in json.loads(snapshot.read_text(encoding='utf-8'))['results'])
    return ids


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--remote', action='store_true', help='Only after dedicated staging setup/authorization')
    parser.add_argument('--output', type=Path, required=True, help='Must be a new directory')
    args = parser.parse_args()
    plan = json.loads((ROOT/'staging/synthetic_staging_plan.json').read_text(encoding='utf-8'))
    denied = production_page_ids()
    missing = [key for key in REQUIRED if not os.environ.get(key, '').strip()]
    if args.remote:
        if missing:
            print(json.dumps({'status': 'REMOTE_STAGING_NOT_RUN', 'missing_environment': missing}))
            return 2
        env = os.environ['V161_ENV']
        target = os.environ['V161_STAGING_TARGET_ID']
        try:
            pages = json.loads(os.environ['V161_STAGING_PAGE_IDS'])
        except json.JSONDecodeError:
            raise Blocked('V161_STAGING_PAGE_IDS must be JSON array') from None
        validate_plan(plan, env, target, pages, denied)
        transport = NotionStagingTransport(target, pages, os.environ['V161_STAGING_NOTION_TOKEN'], plan, denied)
    else:
        env = 'STAGING'
        target = str(uuid5(NAMESPACE, 'OFFLINE-MEMORY-TARGET'))
        pages = [str(uuid5(NAMESPACE, r['synthetic_id'])) for r in plan['records']]
        transport = MemoryTransport(target, pages, plan)
    adapter = GuardedAdapter(transport, plan, env, target, pages, denied)
    result = run_cycle(adapter, args.output)
    if not args.remote:
        result['missing_environment'] = missing
        result['scope'] = 'Offline in-memory fixture; UUIDs are not remote configuration'
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Blocked as exc:
        print('STAGING_BLOCKED: ' + str(exc), file=sys.stderr)
        sys.exit(2)
