import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SKILL = Path(__file__).resolve().parents[1] / 'skills' / 'adaptive-training-coach'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SKILL / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


renderer = load('render_plan')
initializer = load('init_data')
SAMPLE = json.loads((SKILL / 'assets/sample-plan.json').read_text(encoding='utf-8'))


class ToolsTest(unittest.TestCase):
    def test_initialization_preserves_existing_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory, _ = initializer.initialize(Path(tmp) / 'data')
            (directory / 'profile.md').write_text('confirmed profile', encoding='utf-8')
            (directory / 'sessions' / 'actual.md').write_text('history', encoding='utf-8')
            _, created = initializer.initialize(directory)
            self.assertEqual(created, [])
            self.assertEqual((directory / 'profile.md').read_text(), 'confirmed profile')
            self.assertEqual((directory / 'sessions' / 'actual.md').read_text(), 'history')

    def test_all_prescription_content_survives_both_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory, manifest = renderer.render(SAMPLE, Path(tmp) / 'export')
            digest = hashlib.sha256((directory / 'plan.json').read_bytes()).hexdigest()
            self.assertEqual(manifest['sha256'], digest)
            md = (directory / 'plan.md').read_text(encoding='utf-8')
            pages = '\n'.join((directory / name).read_text(encoding='utf-8') for name in manifest['html'])
            for ex in SAMPLE['exercises']:
                for key in renderer.EXERCISE:
                    values = ex[key] if key == 'cues' else [ex[key]]
                    for value in values:
                        self.assertIn(value, md)
                        self.assertIn(renderer.escape(value), pages)
            for key in ('rationale',):
                self.assertIn(SAMPLE[key], md)
                self.assertIn(renderer.escape(SAMPLE[key]), pages)
            for key in renderer.LISTS:
                for value in SAMPLE[key]:
                    self.assertIn(value, md)
                    self.assertIn(renderer.escape(value), pages)

    def test_untrusted_text_is_escaped_in_html(self):
        plan = copy.deepcopy(SAMPLE)
        payload = '<script>alert("x")</script><img src="https://example.invalid">'
        plan['exercises'][0]['setup'] = payload
        rendered = '\n'.join(renderer.documents(plan, '123'))
        self.assertNotIn(payload, rendered)
        self.assertIn(renderer.escape(payload), rendered)
        self.assertIn("default-src 'none'", rendered)

    def test_invalid_input_has_no_output_side_effect(self):
        for mutate in (lambda p: p.update(version='latest'),
                       lambda p: p.update(date='2026-02-30'),
                       lambda p: p.update(training_id='../secret'),
                       lambda p: p['exercises'][0].update(load=''),
                       lambda p: p.update(stop_rules=[])):
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as tmp:
                plan = copy.deepcopy(SAMPLE)
                mutate(plan)
                target = Path(tmp) / 'export'
                with self.assertRaises(ValueError):
                    renderer.render(plan, target)
                self.assertFalse(target.exists())

    def test_new_export_does_not_overwrite_existing_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory, _ = renderer.render(SAMPLE, Path(tmp) / 'export')
            before = (directory / 'plan.json').read_bytes()
            new = copy.deepcopy(SAMPLE)
            new['version'] = 'v2'
            with self.assertRaises(ValueError):
                renderer.render(new, directory)
            self.assertEqual((directory / 'plan.json').read_bytes(), before)

    def test_png_failure_does_not_claim_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'export'
            with patch.object(renderer, 'screenshot', side_effect=RuntimeError('missing browser')):
                with self.assertRaises(RuntimeError):
                    renderer.render(SAMPLE, target, png=True)
            manifest = json.loads((target / 'manifest.json').read_text())
            self.assertEqual(manifest['png_status'], 'failed')
            self.assertEqual(manifest['png'], [])
            self.assertTrue((target / 'plan.md').exists())


if __name__ == '__main__':
    unittest.main()
