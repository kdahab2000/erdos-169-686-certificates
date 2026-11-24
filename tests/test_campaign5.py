import hashlib
import json
import unittest
from pathlib import Path
from submissions.build_oeis import bfile_eligible
from solvers.s686_divisor import solve_square
from verifiers import standalone_verify as st, v686


class Campaign5Tests(unittest.TestCase):
    def test_legacy_and_append_only(self):
        baseline=json.loads(Path('benchmarks/c5_legacy_bytes.json').read_text())
        self.assertEqual(len(baseline['raw_sha256']),563)
        for path,digest in baseline['raw_sha256'].items():
            self.assertEqual(hashlib.sha256((Path('certificates')/path).read_bytes()).hexdigest(),digest,path)
        all_entries=[]
        for name,old in baseline['manifests'].items():
            entries=json.loads((Path('certificates')/name).read_text())['certificates']
            self.assertEqual(entries[:len(old)],old)
            self.assertTrue(all(e['path'].startswith('c5_') or e['path'].startswith('deep/c5_') for e in entries[len(old):]))
            all_entries.extend(entries)
        old_entries=[e for entries in baseline['manifests'].values() for e in entries]
        old_hashes={e['sha256'] for e in old_entries}
        new_entries=[e for e in all_entries if e['path'] not in baseline['raw_sha256']]
        self.assertEqual(len(new_entries),len({e['sha256'] for e in new_entries}))
        self.assertFalse(old_hashes & {e['sha256'] for e in new_entries})

    def test_square_atlas_all_cells(self):
        atlas=json.loads(Path('benchmarks/c5_square_atlas.json').read_text())
        self.assertEqual([r['s'] for r in atlas['rows']],list(range(2,101)))
        self.assertEqual(atlas['counts'],{'k2_positive':24,'k4_positive':0,'neither':75})
        entries=json.loads(Path('certificates/MANIFEST.json').read_text())['certificates']
        bound={e['path']:e['sha256'] for e in entries}
        scan=Path('benchmarks/square_results.json')
        for row in atlas['rows']:
            decision=solve_square(row['s'])
            self.assertEqual(bool(decision['witnesses']['2']),row['k2']['kind']=='rep')
            self.assertEqual(decision['witnesses']['4'],[])
            self.assertEqual(row['scan_coverage']['raw_sha256'],hashlib.sha256(scan.read_bytes()).hexdigest())
            for cell in [row['k2'],row['k4']]+row['higher_k_witnesses']:
                self.assertEqual(bound[cell['path']],cell['sha256'])
                c=json.loads((Path('certificates')/cell['path']).read_text())
                self.assertEqual(st.verify_certificate(c),v686.verify_certificate(c))
            if row['family_4t2']:
                t=row['family_4t2']['t'];n=t-1;m=4*t*t+4*t-1
                self.assertEqual((m+1)*(m+2),row['N']*(n+1)*(n+2))
                self.assertGreaterEqual(m,n+2)

    def test_bfile_boundary_and_no_false_closure(self):
        self.assertFalse(bfile_eligible(55,36));self.assertTrue(bfile_eligible(56,36))
        m=json.loads(Path('benchmarks/c5_z125_measure.json').read_text())
        self.assertEqual(m['claim'],'none')
        self.assertFalse(Path('certificates/c5_z125_max.json').exists())
        tables=json.loads(Path('benchmarks/oeis_tables.json').read_text())['tables']
        self.assertTrue(all(int(t['endpoint'])>=56 for t in tables if int(t['k'])>=5))
