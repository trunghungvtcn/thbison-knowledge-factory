"""Transport implementations; only explicit staging CLI can select live HTTP."""
from copy import deepcopy
import json
import os
import urllib.error
import urllib.request

from .harness import Blocked, FIELDS, ident, validate_plan, validate_properties


class MemoryTransport:
    mode = 'MEMORY'

    def __init__(self, target_id, page_ids, plan):
        self.target = ident(target_id)
        self.patches = []
        self.schema = {k: {'type': v, 'options': ['RESOLVED', 'REVIEW_REQUIRED', 'BEFORE_TEST']} for k, v in FIELDS.items()}
        self.pages = {}
        for page, record in zip(page_ids, plan['records']):
            self.pages[ident(page)] = {'target_id': self.target, 'marker': record['synthetic_id'], 'archived': False,
                'properties': {k: ({'rich_text': [{'type': 'text', 'text': {'content': 'before ' + record['synthetic_id']}}]}
                    if kind == 'rich_text' else {'select': {'name': 'BEFORE_TEST'}}) for k, kind in FIELDS.items()}}
            self.pages[ident(page)]['properties'].update({'Decision': {'select': {'name': 'PENDING'}},
                'Reviewer Note': {'rich_text': [{'type': 'text', 'text': {'content': 'Human note — preserve exactly'}}]}})

    def read_schema(self, target_id):
        if ident(target_id) != self.target:
            raise Blocked('wrong staging target')
        return deepcopy(self.schema)

    def read_page(self, page_id):
        return deepcopy(self.pages[ident(page_id)])

    def patch_page(self, page_id, properties):
        self.patches.append((page_id, deepcopy(properties)))
        self.pages[ident(page_id)]['properties'].update(deepcopy(properties))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Blocked('Notion redirect refused')


class NotionStagingTransport:
    mode = 'NOTION_STAGING'

    def __init__(self, target_id, page_ids, token, plan, denied):
        if not token or not token.strip():
            raise Blocked('dedicated staging token required')
        self.plan = deepcopy(plan)
        self.denied = tuple(denied)
        self.target, self.page_order = validate_plan(plan, os.environ.get('V161_ENV'), target_id, page_ids, denied)
        self.ids = set(self.page_order)
        self._before = None
        self._token = token
        self._opener = urllib.request.build_opener(NoRedirect())

    def _call(self, method, route, body=None):
        allowed = {('GET', '/data_sources/' + self.target)} | {
            (m, '/pages/' + p) for p in self.ids for m in ('GET', 'PATCH')}
        if (method, route) not in allowed:
            raise Blocked('HTTP route outside fixed staging allowlist')
        if method == 'PATCH' and (set(body or {}) != {'properties'} or set(body['properties']) - set(FIELDS)):
            raise Blocked('only staging system-property patches permitted')
        if method == 'PATCH':
            validate_plan(self.plan, os.environ.get('V161_ENV'), self.target, self.page_order, self.denied)
            page = route.split('/')[-1]
            if self._before is None or page not in self._before:
                raise Blocked('durable staging snapshot required before write')
            expected = self.plan['records'][self.page_order.index(page)]['properties']
            if body['properties'] not in (expected, self._before[page]['properties']):
                raise Blocked('patch differs from snapshotted apply/rollback values')
            validate_properties(body['properties'])
        request = urllib.request.Request('https://api.notion.com/v1' + route,
            data=None if body is None else json.dumps(body, ensure_ascii=False, allow_nan=False).encode(),
            headers={'Authorization': 'Bearer ' + self._token, 'Notion-Version': '2026-03-11', 'Content-Type': 'application/json'}, method=method)
        # No blind retries: an uncertain write is handled by read-back/recovery.
        try:
            with self._opener.open(request, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as exc:
            raise Blocked(f'Notion staging HTTP {exc.code}; response omitted') from None
        except (urllib.error.URLError, TimeoutError):
            raise Blocked('Notion staging transport failed; details omitted') from None

    def read_schema(self, target_id):
        if ident(target_id) != self.target:
            raise Blocked('wrong staging target')
        data = self._call('GET', '/data_sources/' + self.target)
        title = ''.join(x.get('plain_text', x.get('text', {}).get('content', '')) for x in data.get('title', []))
        if not title.startswith('V161-STAGING'):
            raise Blocked('data-source title must start V161-STAGING')
        return {name: {'type': prop['type'], 'options': [o['name'] for o in prop.get('select', {}).get('options', [])]}
            for name, prop in data['properties'].items()}

    def read_page(self, page_id):
        data = self._call('GET', '/pages/' + ident(page_id))
        parent = data.get('parent', {})
        if parent.get('type') != 'data_source_id' or ident(parent.get('data_source_id')) != self.target:
            raise Blocked('page must be directly in configured staging data source')
        props = data['properties']
        titles = [v for v in props.values() if v.get('type') == 'title']
        if len(titles) != 1:
            raise Blocked('missing synthetic page title marker')
        marker = ''.join(x.get('plain_text', x.get('text', {}).get('content', '')) for x in titles[0]['title'])
        return {'target_id': self.target, 'marker': marker, 'properties': props,
            'archived': bool(data.get('archived') or data.get('in_trash'))}

    def patch_page(self, page_id, properties):
        self._call('PATCH', '/pages/' + ident(page_id), {'properties': properties})

    def arm_from_snapshot(self, directory):
        before = json.loads((directory/'staging_before.json').read_text(encoding='utf-8'))
        plan = json.loads((directory/'staging_plan.json').read_text(encoding='utf-8'))
        rollback = json.loads((directory/'staging_rollback_plan.json').read_text(encoding='utf-8'))
        if plan != self.plan or set(before) != self.ids or len(rollback) != len(self.ids):
            raise Blocked('snapshot does not cover the exact staging plan')
        for row in rollback:
            if row['properties'] != before[row['page_id']]['properties']:
                raise Blocked('rollback snapshot mismatch')
        self._before = before
