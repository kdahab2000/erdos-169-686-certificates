import copy
import hashlib
import json
import tempfile
import unittest
from fractions import Fraction
from itertools import combinations
from pathlib import Path

from solvers.f5_decisive import (build_tail_automaton, edges_for, minimum_hitting_cost,
                                bnb, z125_search, solve_dual)
from solvers.head_tail import head_edges
from verifiers import v169, standalone_verify as solo
from verifiers.common import canonical_json_bytes

ROOT=Path(__file__).resolve().parents[1]
CERTS=ROOT/'certificates'


class RigidityTests(unittest.TestCase):
    def test_certificates_and_independent_candidate_completeness(self):
        for L in (6,7,8):
            cert=json.loads((CERTS/f'c3_rigidity_L{L}.json').read_text())
            generated=solve_dual(L)
            self.assertEqual(generated['status'],'feasible exact dual')
            self.assertEqual(generated['dual_arcs'],cert['dual_arcs'])
            a=build_tail_automaton(L)
            stored=json.loads((ROOT/f'benchmarks/head_candidates_L{L}.json').read_text())
            self.assertEqual(list(map(str,a)),stored['tail_compatible'])
            for module in (v169,solo):
                self.assertEqual(module.rigidity_candidates(L),a)
                self.assertEqual(module.verify_certificate(cert,CERTS),
                                 dict(valid=True,max_delta={'num':'0','den':'1'},unique_optimum=False))

    def test_edge_enumeration_parity(self):
        # Existing brute scanner is exhaustive but slower. Check all A6,A7 and
        # first/middle/last A8 candidates, as required by the plan.
        for L in (6,7,8):
            candidates=build_tail_automaton(L)
            if L==8:
                candidates=[candidates[0],candidates[len(candidates)//2],candidates[-1]]
            for a in candidates:
                self.assertEqual(edges_for(a,L),head_edges(a,1,L,[0,1,2,3]))
        self.assertEqual(len(edges_for(3380,6)),80)

    def test_ten_tamper_categories(self):
        original=json.loads((CERTS/'c3_rigidity_L6.json').read_text())
        bad=[]
        c=copy.deepcopy(original); c['candidates'].pop(); bad.append(('dropped candidate',c))
        c=copy.deepcopy(original); c['candidates'].insert(0,'2'); bad.append(('extra candidate',c))
        c=copy.deepcopy(original); c['dual_arcs'][0]['weight']={'num':'1','den':'1'}; bad.append(('overload',c))
        for diff in ('0','-1'):
            c=copy.deepcopy(original); c['dual_arcs'][0]['diff']=diff; bad.append(('bad difference',c))
        c=copy.deepcopy(original); c['dual_arcs'][0]['start']='3127'; bad.append(('forged progression',c))
        c=copy.deepcopy(original); c['dual_arcs'][0].update(start='3380',diff='15625'); bad.append(('tail-only arc',c))
        for fraction in ({'num':'2','den':'6760'},{'num':'-1','den':'3380'}):
            c=copy.deepcopy(original); c['dual_arcs'][0]['weight']=fraction; bad.append(('invalid fraction',c))
        c=copy.deepcopy(original); c['dual_arcs'].append(copy.deepcopy(c['dual_arcs'][0])); bad.append(('duplicate',c))
        c=copy.deepcopy(original); c['L']='7'; bad.append(('changed level',c))
        # The exact boundary is checked directly below; a forged boundary arc
        # is also rejected without relying on a stale certificate digest.
        c=copy.deepcopy(original); c['dual_arcs'][0].update(start='3380',diff='12246'); bad.append(('cutoff arc',c))
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            ref=CERTS/'c2_pure5_depth1.json'
            (path/ref.name).write_bytes(ref.read_bytes())
            for label,cert in bad:
                with self.subTest(label=label):
                    raw=canonical_json_bytes(cert)
                    (path/'bad.json').write_bytes(raw)
                    digest=hashlib.sha256(raw).hexdigest()
                    answer=solo.verify_entry({'path':'bad.json','sha256':digest},path)
                    self.assertFalse(answer['valid'])
                    self.assertNotIn('sha256 mismatch',answer.get('error',''))
                    with self.assertRaises(ValueError):
                        v169.verify_certificate(cert,path)

    def test_cutoff_is_tail(self):
        for module in (v169,solo):
            self.assertEqual(module.rigidity_head_terms([3380,15625,15626,15627],3380,15626),[15625])

    def test_real_cutoff_arc_does_not_load_tail_capacity(self):
        cert=json.loads((CERTS/'c3_rigidity_L7.json').read_text())
        # 78126 = 1+5**7 is a genuine baseline tail point. This arc puts
        # weight 1/55215 > 1/78126 on it, which is legal because it is tail.
        cert['dual_arcs']=[arc for arc in cert['dual_arcs'] if arc['a']!='55215']
        cert['dual_arcs'].append(dict(a='55215',start='9393',diff='22911',
                                     weight=dict(num='1',den='55215')))
        for module in (v169,solo):
            self.assertTrue(module.verify_certificate(cert,CERTS)['valid'])

    def test_l9_gate(self):
        candidates=build_tail_automaton(9)
        stored=json.loads((ROOT/'benchmarks/head_candidates_L9.json').read_text())
        self.assertEqual(list(map(str,candidates)),stored['tail_compatible'])
        self.assertEqual(len(candidates),1994)
        reflected={3*(5**9-1)//4+2-a for a in candidates}
        self.assertEqual(reflected,set(candidates))
        self.assertTrue(all(v169.tail_compatible(a,1,9,[0,1,2,3]) for a in candidates))
        # Exhaustive agreement on small levels tests the aggregate decision in
        # addition to the full previously certified L6..L8 scans.
        for L in range(1,5):
            direct=[a for a in range(1,5**L+1) if not v169.padded_member(a-1,[0,1,2,3])
                    and v169.tail_compatible(a,1,L,[0,1,2,3])]
            self.assertEqual(build_tail_automaton(L),direct)

    def test_exact_hitting_cost_against_small_exhaustive_oracle(self):
        edges=[{2,3},{3,5},{2,7},{5,7}]
        vertices=set().union(*edges)
        exact=min(sum((Fraction(1,r) for r in subset),Fraction())
                  for size in range(len(vertices)+1) for subset in combinations(vertices,size)
                  if all(set(subset)&e for e in edges))
        result=minimum_hitting_cost(edges)
        self.assertTrue(result['complete'])
        self.assertEqual(Fraction(int(result['cost']['num']),int(result['cost']['den'])),exact)
        limited=minimum_hitting_cost(edges,max_nodes=0)
        self.assertFalse(limited['complete'])
        a6=bnb(6)
        self.assertEqual(a6['status'],'complete')
        self.assertEqual(len(a6['subsets']),4)
        self.assertTrue(all(int(row['delta']['num'])<=0 for row in a6['subsets']))

    def test_z125_incomplete_is_explicit(self):
        result=z125_search(max_nodes=1)
        self.assertEqual(result['distinct_progressions'],'7525')
        self.assertEqual(result['status'],'unresolved')
        digits=set(map(int,result['digits']))
        self.assertTrue(all(not all((a+j*d)%125 in digits for j in range(5))
                            for a in range(125) for d in range(1,125)))
