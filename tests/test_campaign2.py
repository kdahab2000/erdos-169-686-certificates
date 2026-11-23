import copy
import hashlib
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from solvers.gk_bnb import solve
from solvers.s686_search import _m_for_n, search, sweep
from verifiers import standalone_verify as solo
from verifiers.common import canonical_json_bytes, find_k_ap, fraction_object
from verifiers.proof_replay import replay_proof
from verifiers.v169 import (block_enclosure, padded_member, tail_compatible,
                            verify_block_digit, verify_head_tail, verify_prefix)
from verifiers.v686 import verify_null


class Campaign2Tests(unittest.TestCase):
    def rejects_both(self, cert, modular, **kwargs):
        with self.assertRaises(ValueError):
            modular(cert, **kwargs)
        with self.assertRaises(ValueError):
            solo.verify_certificate(cert, **kwargs)

    def test_local_runner_saves_replayable_proof(self):
        from benchmarks.run_local import run_169
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root/'benchmarks') as folder:
            results=run_169(3,[5],1,2,folder)
            self.assertEqual(results[0]['status'],'PREFIX_OPTIMAL')
            proof=solo.load_strict(Path(folder)/'g3_5.json')
            self.assertTrue(replay_proof(proof)['valid'])
            self.assertTrue(solo.replay(proof)['valid'])

    def test_forged_leaves(self):
        proof = solve(3, 4)['proof']
        for status in ('feasible', 'infeasible'):
            forged = copy.deepcopy(proof)
            forged['tree'] = [{'op':'leaf','status':status}]
            self.assertFalse(replay_proof(forged)['valid'])
            with self.assertRaises(ValueError):
                solo.replay(forged)

    def test_prefix_binding(self):
        proof = solve(3, 5)['proof']
        witness = dict(schema='erd169.finite.v1', k='3', N='5',
                       members=proof['witness'], score=proof['witness_score'])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def put(name, obj):
                raw = canonical_json_bytes(obj)
                (root/name).write_bytes(raw)
                return hashlib.sha256(raw).hexdigest()
            wrapper = dict(schema='erd169.prefix_opt.v1', k='3', N='5',
                           witness_sha256=put('w.json',witness),
                           proof_sha256=put('p.json',proof),
                           proof_format='erd169.bnb.v1', tie_policy='first')
            self.assertTrue(verify_prefix(wrapper,root)['valid'])
            self.assertTrue(solo.verify_certificate(wrapper,root)['valid'])
            for key,value in [('N','6'),('k','4'),('proof_sha256','0'*64),('witness_sha256','1'*64)]:
                bad = dict(wrapper, **{key:value})
                self.rejects_both(bad,verify_prefix,base_dir=root)
            borrowed=solve(3,6)['proof']
            digest=put('borrowed.json',borrowed)
            self.rejects_both(dict(wrapper,proof_sha256=digest),verify_prefix,base_dir=root)
            (root/'p.json').unlink()
            self.rejects_both(wrapper,verify_prefix,base_dir=root)

    def test_exhaustive_prefixes(self):
        for k in range(3,7):
            previous = Fraction()
            for n in range(1,15):
                proof = solve(k,n)['proof']
                best = max(sum((Fraction(1,j) for j in range(1,n+1) if mask>>(j-1)&1),Fraction())
                           for mask in range(1<<n)
                           if find_k_ap([j for j in range(1,n+1) if mask>>(j-1)&1],k) is None)
                got = Fraction(int(proof['witness_score']['num']),int(proof['witness_score']['den']))
                self.assertEqual(best,got)
                self.assertTrue(replay_proof(proof)['valid'])
                self.assertTrue(solo.replay(proof)['valid'])
                self.assertTrue(0 <= got-previous <= Fraction(1,n))
                previous = got

    def test_null_forgery_and_bounds(self):
        cert = dict(schema='erd686.null.v1',s='3',k_set=['3'],method='bounded_box',
                    box={'k_max':'3','n_max':'11'},domain='n>=1')
        self.rejects_both(cert,verify_null)
        cert['s']='2'
        self.assertTrue(verify_null(cert)['valid'])
        self.assertTrue(solo.verify_certificate(cert)['valid'])
        for ks in ([],['3','3'],['5','3']):
            self.rejects_both(dict(cert,k_set=ks),verify_null)
        cert['box']['k_max']='2'
        self.rejects_both(cert,verify_null)
        cert.update(method='divisor_complete',box=None,k_set=['3'])
        self.rejects_both(cert,verify_null)
        cert.update(s='10',k_set=['2'])
        self.rejects_both(cert,verify_null)

    def test_square_sweep_oracle_and_nonsquare(self):
        for N in (4,9,16,25,36,100):
            for k in (2,3,4,5,8):
                expected = [(n,m) for n in range(1,101) if (m:=_m_for_n(N,k,n)) is not None]
                self.assertEqual(expected,list(sweep(N,k,100)))
        self.assertIsNone(search(7,[5],1)['certificate'])
        self.assertGreater(len(search(6,[2],10000)['certificates']),1)

    def test_block_and_cap(self):
        lb,ub=block_enclosure(5,[0,1,2,3],1,2)
        cert=dict(schema='erd169.block_digit.v1',k='5',p='5',block_len='1',
                  D=['0','1','2','3'],s='1',depth='2',lb=fraction_object(lb),ub=fraction_object(ub))
        self.assertEqual(verify_block_digit(cert),solo.verify_certificate(cert))
        for change in ({'D':['1','2','3','4']},{'p':'6'},{'k':'3'},{'depth':'1000000'}, {'ub':{'num':'0','den':'1'}}):
            self.rejects_both(dict(cert,**change),verify_block_digit)

    def test_head_reference_roundtrip_and_binding(self):
        lo,hi = block_enclosure(5,[0,1,2,3],1,2)
        ref = dict(schema='erd169.block_digit.v1',k='5',p='5',block_len='1',D=['0','1','2','3'],s='1',depth='2',lb=fraction_object(lo),ub=fraction_object(hi))
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            raw=canonical_json_bytes(ref)
            (root/'ref.json').write_bytes(raw)
            cert=dict(schema='erd169.head_tail.v1',k='5',p='5',D=ref['D'],s='1',L='1',added=[],removed=[],delta={'num':'0','den':'1'},pure_ref_sha256=hashlib.sha256(raw).hexdigest())
            self.assertEqual(verify_head_tail(cert,root),solo.verify_certificate(cert,root))
            negative=dict(cert,removed=['1'],delta={'num':'-1','den':'1'})
            self.assertEqual(verify_head_tail(negative,root),solo.verify_certificate(negative,root))
            self.rejects_both(dict(cert,delta={'num':'-0','den':'1'}),verify_head_tail,base_dir=root)
            self.rejects_both(dict(cert,s='2'),verify_head_tail,base_dir=root)
            self.rejects_both(dict(cert,pure_ref_sha256='0'*64),verify_head_tail,base_dir=root)
            self.rejects_both(dict(cert,D=['1','2','3','4']),verify_head_tail,base_dir=root)

    def test_legacy_digitset_does_not_inherit_prime_rule(self):
        from verifiers.v169 import verify_digitset
        cert=dict(schema='erd169.digitset.v1', k='3',B='5',D=['0','1','2','3'],s='1',L='1',Q='1',head_lb={'num':'0','den':'1'},tail_lb={'num':'0','den':'1'})
        self.rejects_both(cert,verify_digitset)

    def test_tail_fixtures_and_internal_aps(self):
        digits=[0,1,2,3]
        self.assertFalse(tail_compatible(5,1,1,digits))
        self.assertTrue(tail_compatible(3380,1,6,digits))
        differences=[d for d in range(1,15625) if all(padded_member(3379+j*d,digits) for j in range(1,5))]
        self.assertEqual(differences,[1,2,3,7,12,13,187,188,207,2062,2063,2082])
        cert=dict(schema='erd169.head_tail.v1', k='5',p='5',D=list(map(str,digits)),s='1',L='6',
                  added=['3380'],removed=[],delta={'num':'1','den':'3380'},pure_ref_sha256='0'*64)
        self.rejects_both(cert,verify_head_tail)
        cert.update(L='1',added=['5'],delta={'num':'1','den':'5'})
        self.rejects_both(cert,verify_head_tail)

    def test_automaton_brute_force_small(self):
        # False results need a finite witness; true results exclude these bounded candidates.
        for L in (1,2,3):
            for s in (1,4):
                for a in (1,2,5,9,19):
                    answers=[]
                    for engine in (tail_compatible,solo.tail_compatible):
                        answers.append(engine(a,s,L,[0,1,2,3]))
                    self.assertEqual(*answers)
                    found=any(all(a+j*d >= s+5**L and padded_member(a+j*d-s,[0,1,2,3]) for j in range(1,5))
                              for d in range(1,10000))
                    self.assertEqual(answers[0],not found)


if __name__ == '__main__':
    unittest.main()
