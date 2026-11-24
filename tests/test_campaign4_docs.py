import json,re,unittest
from pathlib import Path

class Campaign4DocsTests(unittest.TestCase):
    def test_claims_resolve_and_readme_numbers(self):
        r=json.loads(Path('benchmarks/campaign4_results.json').read_text())
        entries=[]
        for name in ('MANIFEST.json','MANIFEST_DEEP.json'):
            entries+=json.loads((Path('certificates')/name).read_text())['certificates']
        paths={e['path'] for e in entries}
        for claim in r['claims']:
            references=claim.get('certificates',[])+([claim['certificate']] if 'certificate' in claim else [])
            self.assertTrue(set(references)<=paths)
        readme=Path('README.md').read_text()
        q=json.loads(Path('certificates/c4_pure5_q_depth10.json').read_text())
        self.assertIn(q['lb_num'],readme);self.assertIn(q['ub_num'],readme)
        self.assertIn('168 exact reduced rational rows',readme)
        self.assertIn('0, 0, 0, 0, 0, 2, 28, 260, 1994',readme)
        self.assertIn('L=1…5 computed, uncertified',readme)
        self.assertIn('64 ≤ maximum ≤ 80; unresolved',readme)
        self.assertIn('k=5…200; 1≤n≤50,000',readme)
        self.assertIn('Dr. Khaled Aboeldahab',readme)
        self.assertEqual(r['manifest_entries'],{'default':'561','deep':'2'})
    def test_no_local_paths_or_literature_claims(self):
        paths=[Path('README.md'),Path('CITATION.cff'),Path('docs/CAMPAIGN4_CHECKS.md'),Path('docs/CAMPAIGN4_REPORT_AR.md')]
        for path in paths:
            text=path.read_text()
            self.assertNotRegex(text,r'file://|/Volumes/|/Users/')
        readme=Path('README.md').read_text()
        self.assertNotRegex(readme.lower(),r'world record|instant record|4\.43975|computoergosum|wr[oó]blewski')
