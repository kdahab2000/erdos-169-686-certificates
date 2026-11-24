import copy,json,unittest
from pathlib import Path
from verifiers import standalone_verify as st,v169

class CyclicTests(unittest.TestCase):
    def test_proof_and_mutation(self):
        c=json.loads(Path('certificates/c4_z25_max.json').read_text())
        self.assertEqual(st.verify_certificate(c),v169.verify_certificate(c))
        for mutate in (lambda b:b['proof'].pop(),lambda b:b.update(max_cardinality='15'),lambda b:b['witness'].__setitem__(0,'24'),lambda b:b['proof'].append(b['proof'][0])):
            bad=copy.deepcopy(c);mutate(bad)
            with self.assertRaises(st.BadCertificate):st.verify_certificate(bad)

    def test_h0_missing_orbit_coverage_and_caps(self):
        from verifiers.standalone_verify import canonical_bytes
        import hashlib
        base=json.loads(Path('certificates/c4_z25_max.json').read_text())
        fibre=base['witness']
        c={'schema':'erd169.cyclic_max.v1','modulus':'125','p':'5','max_cardinality':'64',
           'witness':[str(a+5*b+25*d) for d in range(4) for b in range(4) for a in range(4)],
           'mode':'h0_orbit_bnb','proof':{'z25_ref_sha256':hashlib.sha256(canonical_bytes(base)).hexdigest(),
             'orbits':[{'fibre':fibre,'tree':[{'op':'prune','bound':'coset'}]}]}}
        with st.digest_run('certificates'):
            with self.assertRaisesRegex(st.BadCertificate,'incomplete H0 affine orbit coverage'):st.verify_certificate(c,Path('certificates'))
            with self.assertRaisesRegex(ValueError,'incomplete H0 affine orbit coverage'):v169.verify_certificate(c,Path('certificates'))
        c['proof']['orbits']*=1001
        with self.assertRaisesRegex(st.BadCertificate,'orbit cap'):st.verify_certificate(c,Path('certificates'))

class CyclicV2Tests(unittest.TestCase):
    def replay(self,nodes,selected,excluded,maximum,full,parts,cap):
        results=[]
        for module in (st,v169):
            try:
                module._replay_h0_v2(nodes,set(selected),set(excluded),maximum,set(full),parts,parts,cap)
                results.append(None)
            except ValueError as e:results.append(str(e))
        self.assertEqual(results[0],results[1])
        return results[0]

    def test_synthetic_replay(self):
        # A tiny replay domain tests the same node engine; it is not a Z125 proof.
        nodes=[{'op':'force','j':'4','ap':['0','1']},{'op':'prune','bound':'packing','aps':[]}]
        self.assertIsNone(self.replay(nodes,range(4),[],4,range(5),[set(range(5))],4))
        nodes=[{'op':'branch','j':'4'},{'op':'conflict','ap':['0','1']},{'op':'prune','bound':'dominance'}]
        self.assertIsNone(self.replay(nodes,range(4),[],4,range(5),[set(range(5))],4))
        # Overfull densest fibre must give upper=0, not a negative slack sum.
        self.assertIsNone(self.replay([{'op':'prune','bound':'dominance'}],range(5),[],0,range(5),[set(range(5))],4))
        # Active sets may overlap on selected points only.
        self.assertIsNone(self.replay([{'op':'prune','bound':'packing','aps':[['0','1'],['0','2']]}],{0,2,4,6},[],7,range(9),[set(range(9))],9))

    def test_node_adversaries(self):
        cases=[([{'op':'force','j':'5','ap':['0','1']}],range(4),[],4),
               ([{'op':'force','j':'4','ap':['0','1']}],range(3),[],4),
               ([{'op':'conflict','ap':['0','1']}],range(4),[],4),
               ([{'op':'prune','bound':'dominance'}],[],[],3),
               ([{'op':'prune','bound':'packing','aps':[['0','1'],['0','1']]}],[],[],4),
               ([{'op':'prune','bound':'packing','aps':[['0','1']]}],[],[0],4),
               ([{'op':'branch','j':'4'}],range(4),[],4),
               ([{'op':'prune','bound':'dominance'},{'op':'prune','bound':'dominance'}],range(5),[],4)]
        for nodes,sel,exc,maximum in cases:
            self.assertIsNotNone(self.replay(nodes,sel,exc,maximum,range(6),[set(range(6))],4))

    def test_schema_adversaries(self):
        import hashlib
        ref=json.loads(Path('certificates/c4_z25_max.json').read_text())
        c=dict(schema='erd169.cyclic_max.v2',modulus='125',p='5',max_cardinality='64',
               witness=[str(a+5*b+25*d) for d in range(4) for b in range(4) for a in range(4)],mode='h0_orbit_bnb',
               proof={'z25_ref_sha256':hashlib.sha256(st.canonical_bytes(ref)).hexdigest(),
                      'orbits':[{'fibre':ref['witness'],'tree':[{'op':'prune','bound':'dominance'}]}]})
        def duplicate(c):c['proof']['orbits']*=2
        def oversized(c):c['proof']['orbits'][0]['tree']=[{}]*1000001
        for mutate in [lambda c:None,duplicate,oversized,lambda c:c['proof'].update(orbits=[]),
                       lambda c:c['proof'].update(z25_ref_sha256='0'*64),lambda c:c['witness'].__setitem__(1,'0')]:
            bad=copy.deepcopy(c);mutate(bad)
            for module in (st,v169):
                with self.assertRaises(ValueError):module.verify_certificate(bad,Path('certificates'))
