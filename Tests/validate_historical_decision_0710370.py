"""Targeted historical reconstruction regression, no invented real trade facts."""
import unittest
from Reasoning.Cap.historical_decision_reconstruction import reconstruct_historical_decision

class HistoricalReconstructionTests(unittest.TestCase):
    def test_observer_concern_is_not_gm_intent(self):
        r=reconstruct_historical_decision({'decision':'Illustrative trade','decision_date':'2026-01-15','evidence':[
          {'kind':'contemporary','statement':'Left-wing depth was limited','source':'dated roster snapshot','published_date':'2026-01-14'},
          {'kind':'observer_interpretation','statement':'Observer questioned positional balance','source':'dated commentary','published_date':'2026-01-16'},
          {'kind':'subsequent_outcome','statement':'Later roster adjustment','source':'dated transaction','published_date':'2026-02-01'}]})
        self.assertFalse(r.confirmed_intent)
        self.assertIn('not established',r.scout_summary())
        self.assertEqual(len(r.later_outcomes),1)
    def test_hindsight_is_not_contemporary(self):
        with self.assertRaises(ValueError):
            reconstruct_historical_decision({'decision':'Illustrative trade','decision_date':'2026-01-15','evidence':[
                {'kind':'contemporary','statement':'Future result','source':'later report','published_date':'2026-03-01'}]})
    def test_direct_statement_requires_explicit_evidence_flag(self):
        base={'decision':'Illustrative trade','decision_date':'2026-01-15','evidence':[
            {'kind':'management_statement','statement':'We prioritized positional balance','source':'press transcript','published_date':'2026-01-15'}]}
        self.assertFalse(reconstruct_historical_decision(base).confirmed_intent)
        base['evidence'][0]['direct_evidence_of_intent']=True
        self.assertEqual(len(reconstruct_historical_decision(base).confirmed_intent),1)

if __name__=='__main__': unittest.main()
