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
