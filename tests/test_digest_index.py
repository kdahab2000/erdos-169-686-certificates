import hashlib
import tempfile
import unittest
from pathlib import Path
from verifiers.standalone_verify import digest_run, resolve_digest, canonical_bytes, BadCertificate

class DigestIndexTests(unittest.TestCase):
    def test_same_size_rewrite_and_mutable_return(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'c.json'
            old={'x':'1'}; new={'x':'2'}
            digest=hashlib.sha256(canonical_bytes(old)).hexdigest()
            path.write_bytes(canonical_bytes(old))
            with digest_run(directory):
                resolve_digest(digest,directory)['x']='9'
                self.assertEqual(resolve_digest(digest,directory),old)
            path.write_bytes(canonical_bytes(new))
            with digest_run(directory):
                with self.assertRaises(BadCertificate):
                    resolve_digest(digest,directory)
