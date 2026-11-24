import copy,json,unittest
from pathlib import Path
from verifiers import standalone_verify as st,v169

class RigidityV2Tests(unittest.TestCase):
    def test_parity_and_tampering(self):
        c=json.loads(Path('certificates/c4_rigidity_L9.json').read_text())
        self.assertEqual(len(c['candidates']),1994)
        with st.digest_run('certificates'):
            self.assertEqual(st.verify_certificate(c,Path('certificates')),v169.verify_certificate(c,Path('certificates')))
            for mutate in (lambda b:b['candidates'].pop(),lambda b:b['dual_arcs'][0].update(weight={'num':'10','den':'1'}),lambda b:b['dual_arcs'][0].update(diff='1')):
                bad=copy.deepcopy(c);mutate(bad)
                with self.assertRaises(st.BadCertificate):st.verify_certificate(bad,Path('certificates'))
                with self.assertRaises(ValueError):v169.verify_certificate(bad,Path('certificates'))
