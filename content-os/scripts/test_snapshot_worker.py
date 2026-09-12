import hashlib
import json
import unittest
from snapshot_worker import SOURCES, inspect

class WorkerTests(unittest.TestCase):
    def payload(self):
        return {'schema_version': '1.0.0', 'source': 'notion-mcp-readonly', 'collections': [
            {'data_source_id': k, 'rows': [{'record_id': 'a'*32, 'name': 'fixture', 'properties': {'Status': 'HOLD'}}]} for k in SOURCES]}
    def run_input(self, data):
        raw = json.dumps(data).encode()
        return inspect(raw, hashlib.sha256(raw).hexdigest())
    def test_valid_no_approval_escalation(self):
        r = self.run_input(self.payload())
        self.assertEqual(r['status_counts']['knowledge'], {'HOLD': 1})
        self.assertFalse(r['production_ready'])
        self.assertEqual(r['remote_writes'], 0)
    def test_hash_rejected(self):
        with self.assertRaisesRegex(ValueError, 'HASH'): inspect(b'{}', '0'*64)
    def test_duplicate_rejected(self):
        p = self.payload(); p['collections'][0]['rows'] *= 2
        with self.assertRaisesRegex(ValueError, 'DUPLICATE'): self.run_input(p)
    def test_unknown_collection(self):
        p = self.payload(); p['collections'][0]['data_source_id'] = 'other'
        with self.assertRaisesRegex(ValueError, 'ALLOWLIST'): self.run_input(p)
    def test_wrong_schema(self):
        p = self.payload(); p['schema_version'] = '2'
        with self.assertRaisesRegex(ValueError, 'ENVELOPE'): self.run_input(p)

if __name__ == '__main__': unittest.main()
