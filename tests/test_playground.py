"""Exercise the actual browser host adapter against the reference VM."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('playground_bridge', ROOT/'docs/playground/bridge.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

class PlaygroundTests(unittest.TestCase):
    def test_examples(self):
        for sample in json.loads((ROOT/'docs/playground/examples.json').read_text()):
            with self.subTest(sample=sample['id']):
                result = bridge.run_playground(sample['source'], sample['grant'])
                self.assertEqual(result['ok'], sample['id'] not in ('budget', 'untrusted'))
                if sample['id'] == 'hello': self.assertEqual(result['output'], 'Hello, world!')
                if sample['id'] == 'structured': self.assertEqual(result['output'], 'SHIN notebook\n3')
    def test_grant_is_required_and_vm_state_is_fresh(self):
        source = 'permit model "demo"; print(check_text(infer("demo", "ok"), 10));'
        self.assertTrue(bridge.run_playground(source, True)['ok'])
        self.assertIn('host denied', bridge.run_playground(source)['error'])
        self.assertIn('host denied', bridge.run_playground(source, 'true')['error'])
        self.assertTrue(bridge.run_playground('let x = 1;')['ok'])
        self.assertFalse(bridge.run_playground('print(x);')['ok'])
    def test_large_source_and_output_are_bounded(self):
        self.assertIn('source exceeds', bridge.run_playground('a'*65537)['error'])
        result = bridge.run_playground('while true { print("' + 'x'*1000 + '"); }')
        self.assertFalse(result['ok'])
        self.assertIn('output_bytes', result['error'])
        self.assertLessEqual(len(result['output'].encode()), 8192)
    def test_user_source_is_not_python_and_markup_stays_text(self):
        self.assertFalse(bridge.run_playground('import js')['ok'])
        result = bridge.run_playground('print("<img src=x onerror=alert(1)>");')
        self.assertTrue(result['ok'])
        self.assertEqual(result['output'], '<img src=x onerror=alert(1)>')
