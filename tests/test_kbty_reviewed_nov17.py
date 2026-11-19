import unittest
from kbty_sec import SOURCE, OUTPUT, assemble_base, read_json

class ReviewedNovember17(unittest.TestCase):
    def test_verified_form_497_and_historical_deferrals(self):
        config = read_json(SOURCE, {})
        saved = read_json(OUTPUT, {})
        rebuilt = assemble_base(config, saved)
        rows = {x['accession']:x for x in rebuilt['filings']}
        self.assertGreaterEqual(rebuilt['latest_verified_filing_date'], '2026-11-17')
        self.assertEqual(rebuilt['filings'], saved['filings'])
        self.assertEqual(len(rows), len(rebuilt['filings']))
        prospectus = rows['0001213900-26-120950']
        self.assertEqual((prospectus['form'], prospectus['filed_date'], prospectus['document_date']),
                         ('497', '2026-11-17', '2026-10-28'))
        for suffix, day in [('104530','09-29'), ('108274','10-09'), ('109810','10-15'), ('111722','10-22')]:
            row=rows['0001213900-26-'+suffix]
            self.assertEqual((row['form'],row['filed_date']), ('485BXT','2026-'+day))
        for suffix in ('117289','111721','109809','108272','104527'):
            self.assertNotIn('0001213900-26-'+suffix, rows)
