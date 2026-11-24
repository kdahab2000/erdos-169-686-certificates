import hashlib,json,unittest
from pathlib import Path
from submissions.build_oeis import certified_tables, bfile_eligible

class Campaign4Tests(unittest.TestCase):
    def test_legacy_integrity_and_contiguous_rows(self):
        legacy=json.loads(Path('benchmarks/c4_legacy_bytes.json').read_text())
        manifest=json.loads(Path('certificates/MANIFEST.json').read_text())
        self.assertEqual(manifest['certificates'][:471],legacy['entries'])
        for name,digest in legacy['raw_sha256'].items():
            self.assertEqual(hashlib.sha256((Path('certificates')/name).read_bytes()).hexdigest(),digest,name)
        tables=certified_tables()
        self.assertTrue(all(len(t['rows'])>=n for t,n in zip(tables,[36,36,48,48])))
        for t in tables:
            k=t['k']
            for part in ('num','den'):
                name=f'b_g3_{"numerators" if part=="num" else "denominators"}.txt' if k=='3' else f'b_g{k}_{part}.txt'
                path=Path('submissions/oeis')/name
                if not path.exists():
                    self.assertIn(k,('3','4'));continue
                actual=path.read_text().splitlines()
                self.assertEqual(actual,[f"{i} {r['value'][part]}" for i,r in enumerate(t['rows'],1)])
    def test_box_union_and_tiers(self):
        for s in (2,5):
            old=json.loads(Path(f'certificates/c2_null_s{s}_k5_100.json').read_text())
            new=json.loads(Path(f'certificates/c4_null_s{s}_k101_200_50k.json').read_text())
            self.assertEqual(list(map(int,old['k_set']))+list(range(int(new['k_lo']),int(new['k_hi'])+1)),list(range(5,201)))
            self.assertEqual(old['box']['n_max'],new['n_hi'])
            self.assertEqual(new['n_lo'],'1')
        fast=json.loads(Path('certificates/MANIFEST.json').read_text())['certificates']
        deep=json.loads(Path('certificates/MANIFEST_DEEP.json').read_text())['certificates']
        self.assertEqual((len(fast[:561]),len(deep[:2])),(561,2))
        r=json.loads(Path('benchmarks/campaign4_results.json').read_text())
        self.assertEqual(r['manifest_entries'],{'default':'561','deep':'2'})
        self.assertFalse({e['path'] for e in fast}&{e['path'] for e in deep})
