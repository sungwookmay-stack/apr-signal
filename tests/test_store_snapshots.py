import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('store_snapshots',Path('scripts/store_snapshots.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class StoreSnapshots(unittest.TestCase):
    def run_case(self, remote, push_codes):
        calls=[]
        def fake(*args,check=True):
            calls.append(args);out='';rc=0
            if args==('rev-parse','HEAD'):out='base\n'
            elif args==('rev-parse','FETCH_HEAD'):out='new\n'
            elif args==('diff','--cached','--name-only'):out='data/a.json\n'
            elif args[:2]==('diff','--name-only'):out='\n'.join(remote)
            elif args[0]=='push':rc=push_codes.pop(0)
            return subprocess.CompletedProcess(args,rc,out,'')
        with patch.object(m,'git',fake):
            try:m.main()
            except RuntimeError as e:return calls,str(e)
        return calls,None
    def test_initial_success(self):
        c,e=self.run_case([], [0]);self.assertIsNone(e);self.assertFalse(any(a[0]=='fetch' for a in c))
    def test_disjoint_data_retries_once(self):
        c,e=self.run_case(['data/b.json'],[1,0]);self.assertIsNone(e)
        self.assertEqual(sum(a[0]=='push' for a in c),2)
        self.assertIn(('rebase','--onto','new','base'),c)
    def test_overlap_never_rebases(self):
        c,e=self.run_case(['data/a.json'],[1]);self.assertIn('Concurrent',e)
        self.assertFalse(any(a[0]=='rebase' for a in c))
    def test_code_change_never_rebases(self):
        c,e=self.run_case(['build_data.py'],[1]);self.assertIn('Concurrent',e)
        self.assertEqual(sum(a[0]=='push' for a in c),1)
    def test_retry_exhausted(self):
        c,e=self.run_case(['data/b.json'],[1,1]);self.assertIn('exhausted',e)
        self.assertEqual(sum(a[0]=='push' for a in c),2)
    def test_no_force_or_collectors(self):
        s=Path('scripts/store_snapshots.py').read_text()
        self.assertNotIn('--force',s);self.assertNotIn('build_data.py',s)
        self.assertFalse(m.safe_rebase({'data/a.json'},set()))
