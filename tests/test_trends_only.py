import unittest
from trends_only import validated


class TestManualRefresh(unittest.TestCase):
    cfg = {'markets': [{'code': 'US'}], 'trends_terms': {'default': ['medicube']}}
    def row(self, date, dataset, partial=False):
        return {'date': date, 'country': 'US', 'term': 'medicube', 'index': 42,
                'partial': partial, 'dataset': dataset}
    def test_new_full_window(self):
        old = [self.row('2026-11-12', 'old'), self.row('2026-11-13', 'old', True)]
        new = [self.row('2026-11-17', 'API.SH_US_2026-11-19'),
               self.row('2026-11-18', 'API.SH_US_2026-11-19', True)]
        self.assertEqual(validated(old, new, self.cfg, '2026-11-19'), (new, {'US': new}))
    def test_stale_partial_duplicate_series_keep_old(self):
        old = [self.row('2026-11-12', 'old'), self.row('2026-11-13', 'old', True)]
        for new in ([], old, [self.row('2026-11-18', 'API.SH_US_2026-11-19', True)],
                    [self.row('2026-11-18', 'API.SH_US_2026-11-19')]*2):
            self.assertEqual(validated(old, new, self.cfg, '2026-11-19'), (old, {}))
