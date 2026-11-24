import json,unittest
from fractions import Fraction
from pathlib import Path
from solvers.puncture_search import cylinder_loss_bounds
from verifiers.standalone_verify import cyclic_progressions

class SearchTests(unittest.TestCase):
    def test_search_claims_and_frontiers(self):
        for name in ('walker','puncture','window_probe','h0_orbits','h0_residual','z125'):
            r=json.loads(Path(f'benchmarks/c4_{name}.json').read_text())
            self.assertEqual(r['claim'],'none')
        r=json.loads(Path('benchmarks/c4_h0_residual.json').read_text())
        edges=[sum(1<<x for x in e) for e in cyclic_progressions(125)]
        for row in r['unexplored_branches']:
            selected,todo=int(row['selected_mask']),int(row['undecided_mask'])
            self.assertFalse(selected&todo)
            self.assertLess((selected|todo).bit_length(),126)
            self.assertFalse(any(selected&e==e for e in edges))
    def test_cylinder_enclosure(self):
        lb,ub=cylinder_loss_bounds([1,0,0])
        values=[25]; total=Fraction()
        for _ in range(6):
            total+=sum((Fraction(1,1+x) for x in values),Fraction())
            values=[5*x+d for x in values for d in range(4)]
        self.assertLessEqual(lb,total);self.assertGreaterEqual(ub,total)
        with self.assertRaises(ValueError):cylinder_loss_bounds([0,1])

    def test_residual_checkpoint_roundtrip(self):
        from solvers.z125_solver import residual_probe
        fibres=json.loads(Path('benchmarks/c4_h0_orbits.json').read_text())
        checkpoint=json.loads(Path('benchmarks/c4_h0_residual.json').read_text())
        resumed=residual_probe(fibres,max_seconds=0,checkpoint=checkpoint)
        self.assertEqual(resumed['unexplored_branches'],checkpoint['unexplored_branches'])
        self.assertEqual(resumed['nodes'],'0')
        self.assertEqual(resumed['status'],'unresolved')
