import unittest
from clinical_trials import collect, extract, snapshot

def study(name='APR Co., Ltd.', nct='NCT07871708'):
    return {'protocolSection': {'sponsorCollaboratorsModule': {'leadSponsor': {'name': name, 'class': 'INDUSTRY'}}, 'identificationModule': {'nctId': nct, 'briefTitle': 'Test'}, 'statusModule': {'overallStatus': 'RECRUITING'}}}

class ClinicalTests(unittest.TestCase):
    def test_identity(self):
        self.assertIsNotNone(extract(study()))
        self.assertIsNone(extract(study('Aprea Therapeutics')))
        self.assertIsNone(extract(study('APR Research Ltd.')))
    def test_pagination(self):
        pages=iter([{'studies':[study()], 'nextPageToken':'two'}, {'studies':[study(nct='NCT00000001')]}])
        self.assertEqual(len(collect(lambda _:next(pages))),2)
    def test_loop_and_invalid(self):
        with self.assertRaises(ValueError): collect(lambda _:{'studies':[], 'nextPageToken':'same'})
        with self.assertRaises(ValueError): collect(lambda _:{})
    def test_history_missing_and_repeat(self):
        first=snapshot({},[extract(study())],'one')
        repeat=snapshot(first,[extract(study())],'two')
        self.assertEqual(len(repeat['events']),1)
        missing=snapshot(repeat,[],'three')
        self.assertFalse(missing['records'][0]['present'])
        self.assertEqual(missing['observed_count'],0)
        self.assertEqual(missing['records'][0]['first_seen'],'one')
