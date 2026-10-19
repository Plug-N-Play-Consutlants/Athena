import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
"""Deterministic arithmetic and failure-path tests; not live-source acceptance."""
import unittest
from Reasoning.Cap.cba_obligation_calculator import CapRuleContext, calculate_contract_charge


class CalculationTests(unittest.TestCase):
    def setUp(self):
        self.rules = CapRuleContext('fixture-season', '2026-07-01', '2027-06-30',
                                    'fixture:CBA-rule-reference', 1200000)
        self.row = dict(evidence_id='e1', subject_id='player1', source_id='src',
                        provenance='contract-line-1', effective_from='2026-10-01',
                        effective_to='2027-04-30', contract_verified=True,
                        status_verified=True, aav=5000000)

    def test_active_aav(self):
        self.assertEqual(calculate_contract_charge(self.row | {'status': 'active_roster_spc'}, self.rules).amount, 5000000)

    def test_retention(self):
        charge = calculate_contract_charge(self.row | dict(status='retained_salary',
                                 retention_numerator=1, retention_denominator=4), self.rules)
        self.assertEqual((charge.amount, charge.charge_class), (1250000, 'retained_salary'))

    def test_buried(self):
        self.assertEqual(calculate_contract_charge(self.row | {'status': 'buried_contract'}, self.rules).amount, 3800000)
        self.assertEqual(calculate_contract_charge(self.row | {'status': 'buried_contract', 'aav': 900000}, self.rules).amount, 0)

    def test_reject_invalid_evidence_and_rule(self):
        for override in ({'contract_verified': False}, {'status_verified': False},
                         {'effective_from': '2025-10-01'}, {'aav': 4.5}, {'source_id': ''}):
            with self.subTest(override=override), self.assertRaises(ValueError):
                calculate_contract_charge(self.row | {'status': 'active_roster_spc'} | override, self.rules)

    def test_reject_invalid_retention(self):
        for num, den in ((3, 4), (1, 0), (-1, 4), (1.5, 4)):
            with self.subTest(num=num, den=den), self.assertRaises(ValueError):
                calculate_contract_charge(self.row | dict(status='retained_salary',
                    retention_numerator=num, retention_denominator=den), self.rules)

    def test_no_unsupported_ltir_or_fractional_dollar(self):
        with self.assertRaises(ValueError):
            calculate_contract_charge(self.row | {'status': 'ltir_relief'}, self.rules)
        with self.assertRaises(ValueError):
            calculate_contract_charge(self.row | dict(status='retained_salary', aav=101,
                retention_numerator=1, retention_denominator=2), self.rules)


if __name__ == '__main__':
    unittest.main()
