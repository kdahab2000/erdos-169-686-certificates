import copy
import unittest
from solvers.s686_pell import produce
from verifiers import standalone_verify as st, v686


class PellTests(unittest.TestCase):
    def test_batch_and_caps(self):
        c=produce()
        a=st.verify_pell_batch(c)
        self.assertEqual(a,v686.verify_pell_batch(c))
        self.assertEqual(a['count'],969)
        row=next(r for r in c['rows'] if r['N']=='661')
        self.assertEqual(int(row['m']).bit_length(),252)

    def test_adversarial(self):
        c=produce(2,12)
        mutations=[lambda c:c['rows'].pop(2),
                   lambda c:c['rows'].__setitem__(2,c['rows'][1]),
                   lambda c:c['rows'][0].update(N='4'),
                   lambda c:c['rows'][0].update(u=str(1<<256)),
                   lambda c:c['rows'][0].update(u='2'),
                   lambda c:c['rows'][0].update(v='01'),
                   lambda c:c['rows'][0].update(m='1'),
                   lambda c:c.update(domain='n>=0'),
                   lambda c:c.update(N_max='10001')]
        for mutate in mutations:
            bad=copy.deepcopy(c);mutate(bad)
            with self.assertRaises(ValueError) as a:st.verify_pell_batch(bad)
            with self.assertRaises(ValueError) as b:v686.verify_pell_batch(bad)
            self.assertEqual(str(a.exception),str(b.exception))
