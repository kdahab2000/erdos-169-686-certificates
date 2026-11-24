import hashlib
import json
from math import gcd
from pathlib import Path
import subprocess
import sys
import unittest

from submissions.build_oeis import build, SECTIONS, bfile_eligible

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'submissions/oeis'


def parse(text):
    fields={}
    key=None
    for line in text.splitlines():
        if line in SECTIONS:
            key=line
            fields[key]=[]
        elif key:
            fields[key].append(line)
    return {key:'\n'.join(value).strip() for key,value in fields.items()}


class Campaign3OeisTests(unittest.TestCase):
    def test_deterministic_rendering_and_contracts(self):
        before={p.name:p.read_bytes() for p in OUT.glob('*.txt')}
        build()
        after={p.name:p.read_bytes() for p in OUT.glob('*.txt')}
        self.assertEqual(before,after)
        self.assertEqual(len(after),13)
        for path in OUT.glob('batch*.txt'):
            fields=parse(path.read_text())
            self.assertEqual(tuple(fields),SECTIONS)
            self.assertLessEqual(len(fields['DATA']),260)
            self.assertTrue(fields['PROG'].endswith('# _Khaled Aboeldahab_, Nov 24 2026'))
            self.assertEqual(fields['AUTHOR'],'_Khaled Aboeldahab_, Nov 24 2026')
            self.assertNotIn('A??????',fields['CROSSREFS'])
            self.assertTrue(fields['PROG'].startswith('(Python)\n'))
            self.assertNotIn('Novelty',fields['COMMENTS'])

    def test_tables_bfiles_and_matched_truncation(self):
        tables=json.loads((ROOT/'benchmarks/oeis_tables.json').read_text())['tables']
        for table in tables:
            k=int(table['k'])
            counts=[]
            for part in ('num','den'):
                name=f'b_g3_{"numerators" if part=="num" else "denominators"}.txt' if k==3 else f'b_g{k}_{part}.txt'
                pattern=f'batch1_*g3_{"numerators" if part=="num" else "denominators"}.txt' if k==3 else f'batch2_g{k}_{part}.txt'
                fields=parse(next(OUT.glob(pattern)).read_text())
                data=fields['DATA'].split(', ')
                if bfile_eligible(len(table['rows']),len(data)):
                    rows=[line.split() for line in (OUT/name).read_text().splitlines()]
                    self.assertEqual(rows,[[str(i),r['value'][part]] for i,r in enumerate(table['rows'],1)])
                    self.assertIn('b-file',fields['COMMENTS'])
                else:
                    self.assertFalse((OUT/name).exists())
                    self.assertNotIn('b-file',fields['COMMENTS'])
                self.assertEqual(data,[r['value'][part] for r in table['rows'][:len(data)]])
                counts.append(len(data))
                large=next((i for i,r in enumerate(table['rows'],1) if int(r['value'][part])>1),1)
                self.assertEqual(fields['OFFSET'],f'1,{large}')
            self.assertEqual(counts[0],counts[1])
            for row in table['rows']:
                self.assertEqual(gcd(int(row['value']['num']),int(row['value']['den'])),1)
        self.assertFalse((OUT/'b_tail_compat_base5.txt').exists())

    def test_standalone_programs(self):
        for path in sorted(OUT.glob('batch*.txt')):
            fields=parse(path.read_text())
            run=subprocess.run([sys.executable,'-B','-c',fields['PROG'].split('\n',1)[1]],capture_output=True,text=True,timeout=10,cwd='/tmp')
            self.assertEqual(run.returncode,0,run.stderr)
            n=6 if 'tail_compat' in path.name else 12
            self.assertEqual(run.stdout.strip().split(', '),fields['DATA'].split(', ')[:n],path.name)
