import unittest
from pathlib import Path

class RecoveryWorkflow(unittest.TestCase):
    def test_recovery_precedes_downstream_validation(self):
        s=Path('.github/workflows/update-and-publish.yml').read_text()
        self.assertLess(s.index('Preflight saved research'),s.index('Fetch data, calculate'))
        self.assertLess(s.index('Preserve morning demand recovery'),s.index('Decodo Top50 gated'))
        self.assertLess(s.index('Preserve Top50 recovery'),s.index('Verify Top50 gating'))
        self.assertLess(s.index('Preserve Top50 recovery'),s.index('Verify offline financial'))
        for step,paths in [('Preserve morning demand recovery snapshot',['data/demand.json']),('Preserve Top50 recovery snapshot',['state/decodo_top50.json','data/top50.json'])]:
            part=s.split('      - name: '+step+'\n')[1].split('      - name: ')[0]
            self.assertIn('if: always()',part)
            self.assertIn("outcome == 'success'",part)
            self.assertIn("outcome == 'failure'",part)
            self.assertIn('actions/upload-artifact@v4',part)
            self.assertIn('retention-days: 14',part)
            self.assertIn('if-no-files-found: error',part)
            self.assertNotIn('secrets.',part)
            self.assertNotIn('path: .',part)
            for p in paths:self.assertIn(p,part)
        self.assertNotIn('actions/deploy-pages@',s)
